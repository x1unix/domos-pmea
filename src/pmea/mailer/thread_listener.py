"""Provides functionality to map incoming messages to threads."""
import logging
from typing import Optional
from pmea.repository.threads import ThreadsRepository
from .mail_listener import MailConsumer
from .types import Message

class ThreadConsumer:
    """Abstract interface to implement thread-aware mail listener."""
    async def consume_thread_message(self, thread_id: str, m: Message) -> None:
        """Handle new message in a thread."""

class ThreadMailConsumer(MailConsumer):
    """MailConsumer interface implementation which assembles sequence of messages into a thread."""
    _consumer: ThreadConsumer
    _threads_repo: ThreadsRepository
    _logger: logging.Logger = logging.getLogger(__name__)

    def __init__(self, thread_consumer: ThreadConsumer, threads_repo: ThreadsRepository):
        self._consumer = thread_consumer
        self._threads_repo = threads_repo

    async def consume_mail(self, m: Message) -> None:
        """Implements MailConsumer interface."""
        msg_id = m.headers.msg_id

        # If message already exists in a thread, skip it.
        thread_id = await self._threads_repo.get_message_thread_id(msg_id)
        if thread_id:
            self._logger.info("Message %s already exists in thread %s", msg_id, thread_id)
            await self._consumer.consume_thread_message(thread_id, m)
            return

        thread_id = await self._get_thread_id(m)
        if not thread_id:
            thread_id = self._threads_repo.new_thread_id()
            self._logger.info(
                "No thread found for message %s, creating new thread %s.", msg_id, thread_id,
            )
        else:
            self._logger.info("Found thread %s for message %s", thread_id, msg_id)
        await self._threads_repo.add_thread_message(msg_id, thread_id)
        await self._consumer.consume_thread_message(thread_id, m)

    async def _get_thread_id(self, m: Message) -> Optional[str]:
        if not m.headers.in_reply_to and not m.headers.references:
            return None

        if m.headers.in_reply_to:
            thread_id = await self._threads_repo.get_message_thread_id(m.headers.in_reply_to)
            if thread_id:
                return thread_id

        # First guess: if parent message is a reply by LLM - it will be tracked.
        references = m.headers.references
        thread_id = await self._threads_repo.get_message_thread_id(references[-1])
        if thread_id:
            return thread_id

        # Try to lookup if any of referenced messages have a thread.
        references = references[:-1]
        return await self._threads_repo.lookup_thread_id(references)
