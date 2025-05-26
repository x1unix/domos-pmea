import asyncio
import logging
import redis.asyncio as aioredis

from pmea.agent.consumer import ConsumerConfig
from pmea.mailer.sender import MailSender
from pmea.repository.threads import ThreadsRepository
from .agent import LLMMailConsumer
from .config import Config, load_config, setup_logging
from .mailer import ThreadMailConsumer, IncomingMailListener, ListenerConfig

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

        threads_repo = ThreadsRepository(redis_client)
        mail_sender = MailSender(self._config.email, threads_repo)
        consumer_config = ConsumerConfig(
            redis=self._config.redis,
            options=self._config.chats,
            chat_model=self._config.llm.create_chat_model(),
        )

        llm_consumer = LLMMailConsumer(consumer_config, mail_sender)
        listener_config = ListenerConfig(self._config.email, self._config.listener)
        self.listener = IncomingMailListener(
            config=listener_config,
            consumer=ThreadMailConsumer(llm_consumer, threads_repo),
            last_uid_store=threads_repo,
        )

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.listener.start())

    @staticmethod
    def create() -> 'Application': # Return type hint adjusted for forward reference
        config = load_config()
        setup_logging(config.logging)
        
        # Call self (which is the class Application due to @staticmethod) to instantiate
        app = Application(config) 
        return app 