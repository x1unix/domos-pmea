import asyncio
import logging

from ..agent.consumer import ConsumerConfig
from ..agent.tools.tools import CallToolsDependencies
from ..mailer.sender import MailSender
from ..repository.properties import PropertiesRepository
from ..repository.threads import ThreadsRepository
from ..repository.tickets import TicketRepository
from ..agent import LLMMailConsumer
from ..config import Config
from .utils import make_consumer_config, make_redis_client
from ..mailer import (
    ThreadMailConsumer,
    IncomingMailListener,
    ListenerConfig,
    MailFileWriter,
)

logger = logging.getLogger(__name__)

class ServerApplication:
    listener: IncomingMailListener
    _config: Config

    def __init__(self, config: Config):
        self._config = config

    def run(self):
        logger.info(f"starting service...")
        try:
            asyncio.run(self._arun())
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info(f"service stopped")
            return

    async def _arun(self):
        redis_client = make_redis_client(self._config.redis)

        # If enabled - forward "@example.com" mails to file writer.
        file_writer: MailFileWriter | None = None
        if self._config.storage.forwarded_messages_dir:
            file_writer = MailFileWriter(self._config.storage.forwarded_messages_dir)

        threads_repo = ThreadsRepository(redis_client)
        mail_sender = MailSender(self._config.email, threads_repo, file_writer)
        consumer_config = make_consumer_config(self._config)

        tickets_repo = TicketRepository(self._config.storage.tickets_dir)
        props_repo = PropertiesRepository(self._config.storage.properties)
        tool_deps = CallToolsDependencies(mail_sender, props_repo, tickets_repo)
        llm_consumer = LLMMailConsumer(consumer_config, tool_deps)
        listener_config = ListenerConfig(self._config.email, self._config.listener)
        self.listener = IncomingMailListener(
            config=listener_config,
            consumer=ThreadMailConsumer(llm_consumer, threads_repo),
            last_uid_store=threads_repo,
        )

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.listener.start())
