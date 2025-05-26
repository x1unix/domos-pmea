from dataclasses import dataclass
import logging
from ..config import RedisConfig, ChatsConfig
from ..mailer import ThreadConsumer, Message

@dataclass
class ConsumerConfig:
    redis: RedisConfig
    options: ChatsConfig

class LLMMailConsumer(ThreadConsumer):
    """Routes incoming email threads to LLM."""
    _logger: logging.Logger = logging.getLogger(__name__)
    _config: ConsumerConfig

    def __init__(self, config: ConsumerConfig):
        self._config = config

    async def consume_thread_message(self, thread_id: str, m: Message) -> None:
        self._logger.info(
            f"Thread {thread_id}: New email: uid={m.uid}; from={m.sender}; to={m.receiver}; dt={m.sent_at}; subj={m.subject};"
        )
        self._logger.info(f"body: {m.body}")