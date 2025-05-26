import asyncio
import re
from typing import Protocol
from aioimaplib import aioimaplib
from dataclasses import dataclass
import logging
from ..config import EmailConfig, ListenerOptions
from .utils import iter_messages, parse_message_headers, parse_msg_payload, uid_from_fetch_line
from email.utils import parsedate_to_datetime
from email import message
from .types import Contact, Message

UID_RX = re.compile(rb"\* \d+ EXISTS")

@dataclass
class ListenerConfig:
    email_provider: EmailConfig
    options: ListenerOptions

class MailConsumer(Protocol):
    """Abstract interface to implement mail handler."""
    async def consume_mail(self, m: Message) -> None:
        pass

class IncomingMailListener:
    """Listens for new messages and passes them to consumer."""
    _config: ListenerConfig
    _msg_queue: asyncio.Queue[tuple[int, message.Message]] | None = None
    _running: bool = False
    _client: aioimaplib.IMAP4 | aioimaplib.IMAP4_SSL | None = None
    _last_uid: int | None = None
    _consumer: MailConsumer
    _logger: logging.Logger = logging.getLogger(__name__)

    def __init__(self, config: ListenerConfig, consumer: MailConsumer):
        self._config = config
        self._consumer = consumer

    async def start(self):
        self._running = True
        self._msg_queue = asyncio.Queue[tuple[int, message.Message]](self._config.options.msg_queue_size)
        await self._connect_and_idle()

    async def _update_last_uid(self, uid: int):
        # TODO: persist last UID!
        self._last_uid = max(self._last_uid, uid)

    async def _get_last_uid(self) -> int:
        # TODO: get last UID from a persistent storage.
        if self._last_uid is None:
            self._logger.warning("last UID is not set, using first UID")
            self._last_uid = 0

        return self._last_uid

    async def _connect_and_idle(self):
        ssl = self._config.email_provider.use_ssl
        imap_host = self._config.email_provider.imap_host
        imap_port = self._config.email_provider.imap_port
        try:
            # TODO: add retry logic.
            self._logger.info("connecting to IMAP server...")
            if ssl:
                self._client = aioimaplib.IMAP4_SSL(imap_host, imap_port)
            else:
                self._client = aioimaplib.IMAP4(imap_host, imap_port)

            await self._client.wait_hello_from_server()
            code, rsp = await self._client.login(
                self._config.email_provider.username,
                self._config.email_provider.password,
            )
            if code != "OK":
                raise Exception(f"can't login to IMAP server: {rsp} (code: {code})")
        except Exception as e:
            self._logger.error(f"can't connect to IMAP server: {e}", exc_info=True)
            raise

        # Fetch messages that were missed while offline.
        self._logger.info("fetching missed messages...")
        await self._check_missed_messages()
        await self._start_consumers()

        self._logger.info("starting IDLE loop...")
        await self._idle_loop()

    async def _check_missed_messages(self):
        # TODO: process dead letter queue.
        await self._fetch_messages()

    async def _fetch_messages(self):
        # TODO: implement a dead letter queue.
        last_uid = await self._get_last_uid()

        self._logger.info(f"fetching messages since uid {last_uid}...")
        query = f"{last_uid + 1}:*"
        await self._client.select(self._config.email_provider.mailbox)
        code, lines = await self._client.uid("FETCH", query, "(UID)")
        if code != "OK":
            raise Exception(f"failed to fetch messages: {code} {lines}")

        if not lines:
            self._logger.info(f"no messages found since {last_uid}")
            return

        # Explicitly specify UIDs to fetch to avoid accessing deleted messages or Gmail-style expunging.
        uids: list[int] = []
        for line in lines:
            if not line:
                continue
            msg_uid = uid_from_fetch_line(line)
            if msg_uid is None:
                continue
            uids.append(msg_uid)

        # Bulk fetch messages in chunks. Can't do in parallel due to IMAP protocol limitations.
        chunk_size = self._config.options.msg_fetch_batch_size
        for i in range(0, len(uids), chunk_size):
            # TODO: dead-letter queue for unfetched uids.
            chunk = uids[i:i + chunk_size]
            await self._fetch_messages_bulk(chunk)

    async def _fetch_messages_bulk(self, uids: list[int]):
        self._logger.debug(f"fetching messages chunk {uids}...")
        code, msg_data = await self._client.uid("FETCH", ",".join(map(str, uids)), "(RFC822)")
        if code != "OK":
            raise Exception(f"failed to fetch msg batch [{uids}:{uids[-1]}]: {code} {msg_data}")
        for uid, msg in iter_messages(msg_data):
            await self._update_last_uid(uid)
            await self._msg_queue.put((uid, msg))

    async def _idle_loop(self):
        # TODO: this panics on a new mail, fix it later.
        reconnect_delay = self._config.email_provider.reconnect_delay
        idle_timeout = self._config.email_provider.idle_timeout

        while self._running:
            try:
                await self._client.idle_start(timeout=idle_timeout)
                push = await self._client.wait_server_push()
                await self._client.idle_done()

                if not UID_RX.match(push.lines[0]):
                    continue

                await self._fetch_messages()
            except Exception as e:
                self._logger.error(f"Error in IMAP idle loop: {e}", exc_info=True)
                await asyncio.sleep(reconnect_delay)
                try:
                    await self._connect_and_idle()
                except Exception as conn_e:
                    self._logger.error(f"reconnection failed: {conn_e}", exc_info=True)
                    await asyncio.sleep(reconnect_delay)

    async def _start_consumers(self):
        for i in range(self._config.options.worker_count):
            asyncio.create_task(self._listen_queue(i))

    async def _listen_queue(self, worker_id: int):
        self._logger.info(f"starting consumer #{worker_id}...")
        while self._running:
            msg_uid, msg = await self._msg_queue.get()
            try:
                await self._handle_message(msg_uid, msg)
            except Exception as e:
                self._logger.error(
                    f"worker#{worker_id}: cannot handle message #{msg_uid}: {e}",
                    exc_info=True,
                )

    async def _handle_message(self, uid: int, msg: message.Message):
        sender = Contact.parse(msg.get("From", ""))
        if sender.email in self._config.options.ignore_addresses:
            self._logger.info(f"ignoring message from {sender.email}")
            return

        receiver = Contact.parse(msg.get("To", ""))
        subject = msg.get("Subject", "")
        sent_at = parsedate_to_datetime(msg.get("Date", ""))
        body = parse_msg_payload(msg)
        headers = parse_message_headers(msg)

        if not body:
            self._logger.warning(
                f"no body found in message from {sender.email} (#{uid}), skipping..."
            )
            return

        m = Message(
            uid=uid,
            sender=sender, 
            receiver=receiver, 
            subject=subject, 
            body=body, 
            sent_at=sent_at, 
            headers=headers,
        )
        await self._consumer.consume_mail(m)
