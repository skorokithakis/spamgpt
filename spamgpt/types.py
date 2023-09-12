import datetime
import os
from email.utils import parseaddr

from pydantic import BaseModel

MY_ADDRESSES: set["EmailAddress"] = set(
    address.strip() for address in os.getenv("MY_ADDRESSES", "").split(",")
)

# An email address, of the form `Name <email@address.com>`.
EmailAddress = str


class EmailMessage(BaseModel):
    id: str
    in_reply_to: str | None
    references: list[str] | None
    date: datetime.datetime
    sender: EmailAddress
    recipient: EmailAddress
    subject: str
    body: str

    @property
    def is_from_me(self) -> bool:
        """
        Check if the sender's address ends with any of my addresses.

        We check for the ending because this allows us to match entire domains
        as well (e.g. `@stavros.io`).
        """
        sender_email = parseaddr(self.sender)[1]
        for address in MY_ADDRESSES:
            if sender_email.lower().endswith(address.lower()):
                return True
        return False

    def __lt__(self, other: "EmailMessage") -> bool:
        return self.date < other.date


class Thread(BaseModel):
    id: str
    messages: list[EmailMessage] = []

    @property
    def _first_spam_message(self) -> EmailMessage:
        """
        Return the first spam message.

        This function returns the first message in the thread that is not ours. This is
        necessary because in some threads, the first messasge is from us (eg when the
        spammer's message has been deleted).
        """
        for message in self.messages:
            if not message.is_from_me:
                return message
        else:
            raise ValueError(
                "There's a thread where all the messages are from us, and"
                " it implies that my whole life has been a lie."
            )

    @property
    def subject(self) -> str:
        return self.messages[0].subject

    @property
    def sender(self) -> EmailAddress:
        return self._first_spam_message.sender

    @property
    def recipient(self) -> EmailAddress:
        return self._first_spam_message.recipient

    def add_message(self, message: EmailMessage) -> None:
        self.messages.append(message)

        # Always keep messages sorted by date.
        self.messages.sort()

    def __hash__(self) -> int:
        return hash(self.id)
