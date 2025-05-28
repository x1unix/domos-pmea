import asyncio
from datetime import datetime
from email.utils import make_msgid
from pathlib import Path
from typing import Optional
import uuid
import typer

from ..agent import CallToolsDependencies, MailReplyer
from ..repository.properties import PropertiesRepository
from ..repository.tickets import TicketRepository
from ..agent import LLMMailConsumer
from ..config import Config
from .utils import make_consumer_config
from ..mailer.sender import make_forward_message
from ..mailer import (
    Contact,
    Message,
    MessageHeaders,
    MailFileWriter,
)


class ChatApplication:
    """Debug chat mode application."""

    _config: Config
    _subject: str
    _user: Contact

    def __init__(self, config: Config, user_email: str, user_name: str, subject: str):
        self._config = config
        self._subject = subject
        self._user = Contact(email=user_email, name=user_name)

    def run(self):
        print("=== Chat mode ===")
        print(f"User: {self._user.name} <{self._user.email}>")
        print(f"Subject: {self._subject}\n")
        print("To quit, type '/exit' or press ^D")
        asyncio.run(self._arun())

    async def _arun(self):
        thread_id = str(uuid.uuid4())
        llm_consumer = _build_llm_consumer(self._config)
        chat_contact = Contact(name="Agent", email="agent@example.com")
        seq_id = 0

        while True:
            prompt = _get_user_prompt()
            if not prompt:
                return

            seq_id += 1
            msg = Message(
                uid=seq_id,
                sender=self._user,
                receiver=chat_contact,
                subject=self._subject,
                body=prompt,
                sent_at=datetime.now(),
                headers=MessageHeaders(
                    msg_id=make_msgid(), in_reply_to=None, references=None
                ),
            )
            await llm_consumer.consume_thread_message(thread_id, msg)


class ChatReplyer(MailReplyer):
    """Outcoming messages adapter for chat mode."""

    _writer: MailFileWriter | None

    def __init__(self, forwared_messages_dir: Path | None):
        if forwared_messages_dir:
            self._writer = MailFileWriter(forwared_messages_dir)

    async def reply_in_thread(
        self, thread_id: str, parent_msg: Message, body: str
    ) -> None:
        print("==> Reply from LLM:")
        for line in body.splitlines():
            print(f"==> {line}")

    async def forward_message(
        self, parent_msg: Message, dst_email: str, body: str | None
    ) -> None:
        print(f"[!] Forwarded message to {dst_email}")
        msg_id = make_msgid()
        msg = make_forward_message(
            parent_msg=parent_msg,
            from_email=parent_msg.sender.email,
            msg_id=msg_id,
            dst_email=dst_email,
            body=body,
        )
        if not self._writer:
            print(msg.as_string())
            return
        self._writer.save(msg)


def _build_llm_consumer(config: Config) -> LLMMailConsumer:
    consumer_config = make_consumer_config(config)
    tickets_repo = TicketRepository(config.storage.tickets_dir)
    props_repo = PropertiesRepository(config.storage.properties)
    replyer = ChatReplyer(config.storage.forwarded_messages_dir)
    tool_deps = CallToolsDependencies(replyer, props_repo, tickets_repo)
    return LLMMailConsumer(consumer_config, tool_deps)


def _get_user_prompt() -> Optional[str]:
    while True:
        m = _read_user_prompt()
        if not m:
            continue
        if m == "/exit":
            return None
        return m


def _read_user_prompt() -> Optional[str]:
    lines: list[str] = []
    while True:
        line = typer.prompt(">>>", prompt_suffix=" ")
        if line:
            line = line.strip()
        if not line:
            break
        if not line.endswith("\\"):
            lines.append(line)
            break
        line = line[:-1].strip()
        lines.append(line)
    return "\n".join(lines) if lines else None
