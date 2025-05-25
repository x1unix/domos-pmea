from dataclasses import dataclass
from email.utils import parseaddr
import datetime
from typing import Self

@dataclass
class MessageHeaders:
    msg_id: str
    in_reply_to: str | None
    references: list[str] | None

@dataclass
class Contact:
    name: str
    email: str

    @staticmethod
    def parse(raw_contact: str) -> Self:
        name, email = parseaddr(raw_contact)
        return Contact(name, email)

@dataclass
class Message:
    uid: int
    sender: Contact
    receiver: Contact
    subject: str
    body: str
    sent_at: datetime.datetime
    headers: MessageHeaders