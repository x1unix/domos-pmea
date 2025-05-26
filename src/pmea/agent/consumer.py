from asyncio import Protocol
from dataclasses import dataclass
import logging
from ..config import RedisConfig, ChatsConfig
from ..mailer import ThreadConsumer, Message

REDIS_KEY_AI_CHATS = "ai_chat:"

class MailReplyer(Protocol):
    async def reply_in_thread(self, thread_id: str, parent_msg: Message, body: str) -> None:
        pass

@dataclass
class ConsumerConfig:
    redis: RedisConfig
    options: ChatsConfig

class LLMMailConsumer(ThreadConsumer):
    """Routes incoming email threads to LLM."""
    _logger: logging.Logger = logging.getLogger(__name__)
    _replyer: MailReplyer
    _config: ConsumerConfig

    def __init__(self, config: ConsumerConfig, replyer: MailReplyer):
        self._config = config
        self._replyer = replyer

    async def consume_thread_message(self, thread_id: str, m: Message) -> None:
        self._logger.info(
            f"Thread {thread_id}: New email: uid={m.uid}; from={m.sender}; dt={m.sent_at}; subj={m.subject};"
        )
        self._logger.info(f"body: {m.body[:64]}")
        await self._replyer.reply_in_thread(thread_id, m, "Hello, world!")