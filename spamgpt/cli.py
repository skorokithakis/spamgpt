#!/usr/bin/env python3
import argparse
import logging
import os
from urllib.parse import urlparse

import openai

from .email_crap import MailHelper
from .types import Thread


MY_ADDRESSES = set(os.getenv("MY_ADDRESSES", "").split(","))

openai.api_key = os.getenv("OPENAI_API_KEY")


def get_next_reply(thread: Thread) -> str:
    chat = [
        {
            "role": "system",
            "content": "You are a large language model who regularly gets a lot of "
            "email spam. You want to waste spammers' time, but in a way that they "
            "won't realize you're doing it, with a bit of wry, dry humour.",
        },
        {
            "role": "user",
            "content": os.getenv("PERSONAL_DETAILS", "")
            + " I received a spam message. I would like you to reply to it as "
            "me, trying to waste as much of the spammer's time as possible. Act as if "
            "you're me, Stavros, and only give me the reply to the message, with no "
            "text before or after.\n\nHere's the message:\n\n"
            + thread.messages[0].body,
        },
    ]
    for message in thread.messages[1:]:
        if message.is_from(MY_ADDRESSES):
            chat.append(
                {
                    "role": "user",
                    "content": "Here's the next spam message. Please respond to it as before:\n\n"
                    + message.body,
                }
            )
        else:
            chat.append(
                {
                    "role": "assistant",
                    "content": message.body,
                }
            )
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=chat, temperature=1
    )
    reply = completion["choices"][0]["message"]["content"].strip()
    return reply


def main(dry_run: bool) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    imap_url = urlparse(os.getenv("IMAP_URL", ""))
    smtp_url = urlparse(os.getenv("SMTP_URL", ""))
    mail = MailHelper(
        imap_username=imap_url.username,  # type: ignore
        imap_password=imap_url.password,  # type: ignore
        imap_host=imap_url.hostname,  # type: ignore
        imap_port=imap_url.port,  # type: ignore
        mailbox="SpamGPT",
        smtp_username=smtp_url.username,  # type: ignore
        smtp_password=smtp_url.password,  # type: ignore
        smtp_host=smtp_url.hostname,  # type: ignore
        smtp_port=smtp_url.port,  # type: ignore
    )

    for thread in mail.get_email_threads():
        if thread.messages[-1].is_from(MY_ADDRESSES):
            logging.info(
                f'We\'ve already replied to "{thread.messages[0].subject}", skipping...'
            )
            continue
        else:
            logging.info(
                f'We haven\'t replied to "{thread.messages[0].subject}" yet, replying...'
            )
        reply = get_next_reply(thread)
        logging.info(
            f"Replying from {thread.recipient} to {thread.sender} with:\n\n{reply}"
        )
        if not dry_run:
            message = mail.send_mail(
                sender=thread.recipient,
                recipient=thread.sender,
                subject=thread.subject,
                body=reply,
                in_reply_to=thread.messages[-1].id,
            )
            mail.add_to_folder(message)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SpamGPT: AI-powered email spam replies"
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (don't send emails)",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
