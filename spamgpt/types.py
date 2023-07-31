import datetime
from email.utils import parseaddr

from pydantic import BaseModel

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

    def is_from(self, addresses: set[str]) -> bool:
        """
        Check if the sender's address ends with any of my addresses.

        We check for the ending because this allows us to match entire domains
        as well (e.g. `@stavros.io`).
        """
        sender_email = parseaddr(self.sender)[1]
        for address in addresses:
            if sender_email.lower().endswith(address.lower()):
                return True
        return False

    def __lt__(self, other: "EmailMessage") -> bool:
        return self.date < other.date


class Thread(BaseModel):
    id: str
    messages: list[EmailMessage] = []

    @property
    def subject(self) -> str:
        return self.messages[0].subject

    @property
    def sender(self) -> EmailAddress:
        return self.messages[0].sender

    @property
    def recipient(self) -> EmailAddress:
        return self.messages[0].recipient

    def add_message(self, message: EmailMessage) -> None:
        self.messages.append(message)

        # Always keep messages sorted by date.
        self.messages.sort()

    def __hash__(self) -> int:
        return hash(self.id)
