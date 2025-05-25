import asyncio
import logging

from pmea.agent.consumer import ConsumerConfig
from .agent import Consumer
from .config import Config, load_config, setup_logging
from .mailer import IncomingMailListener, ListenerConfig

logger = logging.getLogger(__name__)

class Application:
    listener: IncomingMailListener
    def __init__(self, config: Config):
        self.config = config

        msg_consumer = Consumer(ConsumerConfig(config.redis, config.chats))
        listener_config = ListenerConfig(config.email, config.listener)
        self.listener = IncomingMailListener(listener_config, msg_consumer)

    def main(self):
        logger.info(f"starting service...")
        try:
            asyncio.run(self._run())
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info(f"service stopped")
            return

    async def _run(self):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.listener.start())

    @staticmethod
    def create() -> 'Application': # Return type hint adjusted for forward reference
        config = load_config()
        setup_logging(config.logging)
        
        # Call self (which is the class Application due to @staticmethod) to instantiate
        app = Application(config) 
        return app 