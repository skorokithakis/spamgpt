#!/usr/bin/env python3
import argparse
import logging
import os
import sys
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
            "email spam. You want to waste spammers' time by acting genuinely "
            "interested in their offerings, in a way that will fool them.",
        },
        {
            "role": "user",
            "content": os.getenv("PERSONAL_DETAILS", "")
            + " I received a spam message. I would like you to reply to it as me"
            + os.getenv("MY_NAME", "")
            + ", trying to waste as much of the spammer's time as possible. If they "
            "ask you to do anything other than email, e.g. book an appointment or "
            "send them a file, say that you've done it and insist that there's some "
            "problem on their end, and ask them to check again. Always act as if "
            "you're me, and only give me the reply to their message, with no text "
            "before or after.\n\nHere's the message:"
            f"\n\nFrom: {thread.sender}"
            f"\n\nSubject: {thread.subject}"
            f"\n\nBody:\n\n{thread.messages[0].body}",
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


def main(dry_run: bool, export_json: str | None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    imap_url = urlparse(os.getenv("IMAP_URL", ""))
    smtp_url = urlparse(os.getenv("SMTP_URL", ""))

    logging.info("Connecting to mail server...")
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

    logging.info("Fetching email threads...")
    threads = mail.get_email_threads()
    if export_json:
        logging.info(f"Exporting threads to {export_json}...")
        with open(export_json, "w") as f:
            for thread in threads:
                for message in thread.messages:
                    message.sender = (
                        "ChatGPT" if message.is_from(MY_ADDRESSES) else "Spammer"
                    )
                f.write(thread.model_dump_json() + "\n")
        logging.info("Done.")
        return

    for thread in threads:
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
            sent = mail.send_mail(
                sender=thread.recipient,
                recipient=thread.sender,
                subject=thread.subject,
                body=reply,
                in_reply_to=thread.messages[-1].id,
            )
            mail.add_to_folder(sent)


def cli():
    parser = argparse.ArgumentParser(
        description="SpamGPT: AI-powered email spam replies"
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (don't send emails)",
    )
    parser.add_argument(
        "--export-json",
        metavar="FILE",
        help="Export the threads to a file",
    )
    args = parser.parse_args()
    for setting in (
        "SMTP_URL",
        "IMAP_URL",
        "MESSAGE_ID_HOST",
        "OPENAI_API_KEY",
        "MY_ADDRESSES",
    ):
        if not os.getenv(setting):
            sys.exit(
                "ERROR: Necessary configuration environment variable missing:\n\n"
                f"\t{setting}.\n\nPlease see the README for configuring SpamGPT."
            )
    main(dry_run=args.dry_run, export_json=args.export_json)


if __name__ == "__main__":
    cli()
