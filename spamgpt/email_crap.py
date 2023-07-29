import datetime
import email
import imaplib
import logging
import os
import re
import smtplib
import time
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime

import shortuuid

from .types import EmailAddress
from .types import EmailMessage
from .types import Thread


def parse_payload(msg):
    body = msg.get_payload(decode=True)

    if msg.get_content_charset() is None:
        return body.decode()
    else:
        return body.decode(msg.get_content_charset())


def get_body_from_email(msg: Message) -> str | None:
    if msg.is_multipart():
        for part in msg.get_payload():
            if part.get_content_type() == "text/plain":
                return parse_payload(part)
        return None
    else:
        return parse_payload(msg)


def parse_email(raw_email: bytes) -> EmailMessage:
    email_message: Message = email.message_from_bytes(raw_email)

    # Get the headers
    sender: EmailAddress = email_message["From"]
    recipient: EmailAddress = email_message["X-Delivered-To"] or email_message["To"]
    message_id = email_message["Message-ID"].strip("\r\n <>")
    in_reply_to = email_message["In-Reply-To"]
    in_reply_to = in_reply_to.strip("\r\n <>") if in_reply_to else None
    subject = email_message["Subject"]
    date = parsedate_to_datetime(email_message["Date"])

    # Get plain text body and decode
    body = get_body_from_email(email_message)
    if not body:
        raise ValueError("No body found in message.")
    body = (
        re.search(
            r"\A(?P<message>.*?)(^On .*?, .*? wrote:.*$|)\Z",
            body,
            re.DOTALL | re.MULTILINE,
        )
        .group("message")  # type: ignore
        .strip()
    )

    return EmailMessage(
        id=message_id,
        in_reply_to=in_reply_to,
        date=date,
        subject=subject,
        sender=sender,
        recipient=recipient,
        body=body,
    )


class MailHelper:
    def __init__(
        self,
        imap_username: str,
        imap_password: str,
        imap_host: str,
        imap_port: int,
        mailbox: str,
        smtp_username: str,
        smtp_password: str,
        smtp_host: str,
        smtp_port: int,
    ) -> None:
        self.imap = imaplib.IMAP4_SSL(imap_host, imap_port)
        self.imap.login(imap_username, imap_password)
        self._mailbox = mailbox
        self.imap.select(mailbox)

        self.smtp = smtplib.SMTP(smtp_host, smtp_port)
        self.smtp.starttls()
        self.smtp.login(smtp_username, smtp_password)

    def get_message(self, uid: str) -> EmailMessage:
        # Fetch the email (headers and full body).
        result, data = self.imap.uid("fetch", uid, "(BODY[])")

        return parse_email(data[0][1])

    def get_message_by_id(self, message_id: str) -> EmailMessage:
        # Note: This only works in the `.select()`ed mailbox.
        _, data = self.imap.uid(
            "SEARCH",
            None,  # type: ignore
            f'HEADER Message-ID "<{message_id}>"',
        )
        if not data[0]:
            raise ValueError(f"No message found with message-id {message_id}")
        num = data[0].split()[-1]
        _, data = self.imap.uid("fetch", num, "(RFC822)")
        return parse_email(data[0][1])

    def add_to_folder(self, message: MIMEMultipart):
        """Copy a message to the SpamGPT folder."""
        self.imap.append(
            self._mailbox,
            None,  # type: ignore
            imaplib.Time2Internaldate(time.time()),
            str(message).encode("utf-8"),
        )

    def get_email_threads(self) -> set[Thread]:
        _, data = self.imap.uid("search", None, "ALL")  # type: ignore

        threads: dict[str, Thread] = {}
        messages = [self.get_message(num) for num in data[0].split()]

        # Here, we need to make sure we've fetched all messages, no matter where
        # they are. To do this, we need to construct the set of all the messages
        # `in-reply-to` IDs we've seen, then subtract the set of `message-id`s we've
        # seen. Then, we need to fetch the difference.
        missing_message_ids = {
            message.in_reply_to
            for message in messages
            if message.in_reply_to is not None
        } - {message.id for message in messages}

        if missing_message_ids:
            logging.warn(
                f"Couldn't find some messages in the {self._mailbox} folder: {missing_message_ids}"
            )

        # Sort messages chronologically here, so we don't miss IDs due to trying to
        # get the reply before the message that's being replied to.
        for message in sorted(messages):
            if not message.in_reply_to:
                # This is the first message in the thread.
                threads[message.id] = Thread(id=message.id, messages=[message])
            else:
                threads[message.in_reply_to].add_message(message)
                # Add a reference to this message's ID to the dictionary containing
                # the threads, so the next message knows where to find it (using its
                # in-reply-to).
                threads[message.id] = threads[message.in_reply_to]

        # Deduplicate threads before returning.
        return set(threads.values())

    def send_mail(
        self,
        sender: EmailAddress,
        recipient: EmailAddress,
        subject: str,
        body: str,
        in_reply_to: str,
    ) -> MIMEMultipart:
        """Send an email through an SMTP server."""
        message = MIMEMultipart()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject
        # I've noticed that if the message ID host is not correct, other servers
        # (I tried Gmail) might reject the Message ID, and create their own,
        # which would mean we can no longer keep track of this message thread.
        message[
            "Message-ID"
        ] = f"<{shortuuid.uuid()}@{os.getenv('MESSAGE_ID_HOST', '')}>"
        message["In-Reply-To"] = f"<{in_reply_to}>"
        message["References"] = f"<{in_reply_to}>"
        message["Date"] = datetime.datetime.utcnow().strftime(
            "%a, %d %b %Y %H:%M:%S +0000"
        )
        message.attach(MIMEText(body, "plain"))

        self.smtp.sendmail(sender, recipient, message.as_string())

        return message
