import datetime
import email
import imaplib
import os
import re
import smtplib
import time
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime

import bleach
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
            body = get_body_from_email(part)
            if body:
                return body
        return None
    else:
        if msg.get_content_type() == "text/plain":
            return parse_payload(msg)
        elif msg.get_content_type() == "text/html":
            # Remove HTML.
            return bleach.clean(parse_payload(msg), tags=[], strip=True)
        else:
            return None


def clean_body(body: str) -> str:
    """Remove any quoted messages from the body."""
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    body = re.sub(r"\n\n+", r"\n\n", body)
    body = re.split(
        "^On .*?, .*?, at .*?, .*? wrote:$|^\-+Original Message\-+$",
        body,
        flags=re.MULTILINE,
    )[0].strip()
    return body


def parse_email(raw_email: bytes) -> EmailMessage:
    email_message: Message = email.message_from_bytes(raw_email)

    # Get the headers
    sender: EmailAddress = email_message["From"]
    recipient: EmailAddress = email_message["X-Delivered-To"] or email_message["To"]
    message_id = email_message["Message-ID"].strip("\r\n <>")
    in_reply_to = email_message["In-Reply-To"]
    in_reply_to = in_reply_to.strip("\r\n <>") if in_reply_to else None
    references = [
        item
        for item in (
            [item.strip("<>") for item in re.split(r"\s+", email_message["References"])]
            if email_message["References"]
            else []
        )
        if item
    ]
    subject = email_message["Subject"]
    date = parsedate_to_datetime(email_message["Date"])

    # Get plain text body and decode
    body = get_body_from_email(email_message)
    if not body:
        raise ValueError("No body found in message.")

    body = clean_body(body)

    return EmailMessage(
        id=message_id,
        in_reply_to=in_reply_to,
        references=references,
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

        # Here, we construct a dictionary of message IDs and their corresponding
        # threads. We do this to be able to easily look up which message a
        # message is a reply to, since we can just look up the `in-reply-to` in
        # this dictionary.
        # We sort messages chronologically first, so we don't miss IDs due to
        # trying to get the reply before the message that's being replied to.
        for message in sorted(messages):
            thread = None
            # We want to find the thread this message is in. To do this, we try
            # to find any message referenced in this message's `in-reply-to` or
            # `references` headers.
            # Construct the list of message IDs to search for.
            search_for = []
            if message.in_reply_to:
                search_for.append(message.in_reply_to)
            if message.references:
                search_for.extend(message.references)
            for message_id in search_for:
                if message_id and message_id in threads:
                    # We found the thread we're looking for.
                    thread = threads[message_id]
                    break
            if thread is None:
                # This is the first message in the thread (or we can't find the
                # previous message).
                threads[message.id] = Thread(id=message.id, messages=[message])
            else:
                thread.add_message(message)
                # Add a reference to this message's ID to the dictionary containing
                # the threads, so the next message knows where to find it (using its
                # in-reply-to).
                threads[message.id] = thread

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
