from asyncio import Protocol
from email.utils import make_msgid
from email.message import EmailMessage
import logging
from aiosmtplib import SMTP
from ..config import EmailConfig
from .types import Message
from .file_writer import MailFileWriter

DEFAULT_IGNORED_DOMAINS = set(["example.com", "example.org"])

class ThreadUpdater(Protocol):
    async def add_thread_message(self, message_id: str, thread_id: str) -> None:
        pass


class MailSender:
    _msg_id_domain: str
    _sender: str
    _smtp: SMTP
    _logger: logging.Logger
    _thread_updater: ThreadUpdater
    _file_writer: MailFileWriter | None
    _ignored_domains: set[str]

    def __init__(
        self,
        config: EmailConfig,
        thread_updater: ThreadUpdater,
        file_writer: MailFileWriter | None = None,
        ignored_domains: set[str] = DEFAULT_IGNORED_DOMAINS,
    ):
        self._logger = logging.getLogger(__name__)
        self._msg_id_domain = config.msg_id_domain
        self._sender = config.username
        self._thread_updater = thread_updater
        self._file_writer = file_writer
        self._ignored_domains = ignored_domains
        self._smtp = SMTP(
            hostname=config.smtp_host,
            port=config.smtp_port,
            username=config.username,
            password=config.password,
        )

    def _should_ignore_domain(self, email: str) -> bool:
        parts = email.split("@")
        return len(parts) > 1 and parts[1] in self._ignored_domains

    async def forward_message(
        self, parent_msg: Message, dst_email: str, body: str | None
    ):
        msg_id = make_msgid(domain=self._msg_id_domain)
        msg = EmailMessage()
        msg["Message-ID"] = msg_id
        msg["From"] = self._sender
        msg["To"] = dst_email
        msg["Subject"] = f"FWD: {parent_msg.subject}"

        forward_header = f"\n\n---\n\nForwarded message from {parent_msg.sender.email}"
        if body:
            msg_content = body + forward_header
            msg_content += "\n".join(
                [f"> {line}" for line in parent_msg.body.splitlines()]
            )
            msg.set_content(msg_content)
        else:
            msg.set_content(parent_msg.body + forward_header)

        if self._should_ignore_domain(dst_email) and self._file_writer:
            self._file_writer.save(msg)
            return

        # TODO: dead letter queue for failed messages.
        try:
            self._logger.info(f"sending forwarded message to {dst_email}")
            await self._smtp.connect()
            await self._smtp.send_message(msg)
        except Exception as e:
            raise Exception(f"failed to send forward message to {dst_email}") from e
        finally:
            self._smtp.close()

    async def reply_in_thread(self, thread_id: str, parent_msg: Message, body: str):
        """
        Reply to a message in a thread.
        """
        parent_msg_id = parent_msg.headers.msg_id
        receiver = parent_msg.sender.email
        parent_msg_refs = parent_msg.headers.references

        # Preserve own name in the reply.
        from_addr = self._sender
        if self._sender == parent_msg.receiver.email:
            from_addr = parent_msg.receiver.to_addr()

        new_msg_refs = parent_msg_id
        if parent_msg_refs:
            new_msg_refs = f"{" ".join(parent_msg_refs)} {new_msg_refs}"

        msg_id = make_msgid(domain=self._msg_id_domain)
        msg = EmailMessage()
        msg["Message-ID"] = msg_id
        msg["In-Reply-To"] = parent_msg_id
        msg["References"] = new_msg_refs
        msg["From"] = from_addr
        msg["To"] = receiver
        msg["Subject"] = parent_msg.subject
        msg["X-PMEA-Thread-ID"] = thread_id  # For debugging purposes.
        msg.set_content(body)

        # TODO: dead letter queue for failed messages.
        try:
            # TODO: should connection be closed after sending?
            await self._smtp.connect()
            await self._smtp.send_message(msg)
        except Exception as e:
            raise Exception(
                f"failed to send reply to {receiver} in thread {thread_id}"
            ) from e
        finally:
            self._smtp.close()

        self._logger.info(f"sent reply to {receiver} in thread {thread_id}")
        try:
            await self._thread_updater.add_thread_message(msg_id, thread_id)
        except Exception as e:
            raise Exception(
                f"failed to add incoming message to a thread {thread_id}"
            ) from e
