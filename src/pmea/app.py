import asyncio
import logging
import redis.asyncio as aioredis
from langchain_redis import RedisChatMessageHistory

from pmea.agent.consumer import ConsumerConfig
from pmea.agent.tools.tools import CallToolsDependencies
from pmea.agent.utils import sanitize_session_id
from pmea.mailer.sender import MailSender
from pmea.repository.properties import PropertiesRepository
from pmea.repository.threads import ThreadsRepository
from pmea.repository.tickets import TicketRepository
from .agent import LLMMailConsumer
from .config import Config, load_config_from_flags, setup_logging
from .mailer import (
    ThreadMailConsumer,
    IncomingMailListener,
    ListenerConfig,
    MailFileWriter,
)

logger = logging.getLogger(__name__)


class Application:
    listener: IncomingMailListener
    _config: Config

    def __init__(self, config: Config):
        self._config = config

    def main(self):
        logger.info(f"starting service...")
        try:
            asyncio.run(self._run())
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info(f"service stopped")
            return

    async def _run(self):
        redis_client = aioredis.from_url(self._config.redis.dsn)
        try:
            await redis_client.ping()
        except Exception as e:
            raise Exception(f"failed to connect to Redis: {e}")

        # If enabled - forward "@example.com" mails to file writer.
        file_writer: MailFileWriter | None = None
        if self._config.storage.forwarded_messages_dir:
            file_writer = MailFileWriter(self._config.storage.forwarded_messages_dir)

        threads_repo = ThreadsRepository(redis_client)
        mail_sender = MailSender(self._config.email, threads_repo, file_writer)
        consumer_config = ConsumerConfig(
            get_chat_model=self._config.llm.get_model_provider(),
            system_prompt_extra=self._config.llm.get_system_prompt_extra(),
            get_history=(
                lambda thread_id:
                # TODO: use connection pool for Redis.
                RedisChatMessageHistory(
                    session_id=sanitize_session_id(thread_id),
                    redis_url=self._config.redis.dsn,
                    ttl=self._config.chats.ttl,
                )
            ),
        )

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

    @staticmethod
    def create() -> "Application":  # Return type hint adjusted for forward reference
        config = load_config_from_flags()
        setup_logging(config.logging)

        # Call self (which is the class Application due to @staticmethod) to instantiate
        app = Application(config)
        return app
