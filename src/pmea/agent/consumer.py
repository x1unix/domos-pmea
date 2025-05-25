from dataclasses import dataclass
import logging
from ..config import RedisConfig, ChatsConfig
from ..mailer import MailConsumer, Message

@dataclass
class ConsumerConfig:
    redis: RedisConfig
    options: ChatsConfig

def chat_id_from_mail(m: Message) -> str:
    return f"{m.sender}-{m.receiver}"

class Consumer(MailConsumer):
    _logger: logging.Logger = logging.getLogger(__name__)
    _config: ConsumerConfig

    def __init__(self, config: ConsumerConfig):
        self._config = config

    async def consume_mail(self, m: Message):
        self._logger.info(f"New email received: from={m.sender}; to={m.receiver}; dt={m.sent_at}; subj={m.subject};")
        self._logger.info(f"body: {m.body}")