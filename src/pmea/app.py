import logging
from .config import Config, load_config, setup_logging

logger = logging.getLogger(__name__)

class Application:
    def __init__(self, config: Config):
        self.config = config

    def run(self):
        logger.info("Hello from domos-pmea!")
        logger.info(f"IMAP Server from config: {self.config.email.imap_host}")
        # Add more application logic here, using self.config
        logger.info("Application finished.")

    @staticmethod
    def create() -> 'Application': # Return type hint adjusted for forward reference
        config = load_config()
        setup_logging(config.logging)
        
        # Call self (which is the class Application due to @staticmethod) to instantiate
        app = Application(config) 
        return app 