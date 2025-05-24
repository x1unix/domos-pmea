from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import argparse
import os
import logging

# Logger for this module
logger = logging.getLogger(__name__)

class AppConfig(BaseSettings):
    # IMAP Settings
    imap_server: str = Field(..., validation_alias='IMAP_SERVER')
    imap_port: int = Field(993, validation_alias='IMAP_PORT')
    imap_username: str = Field(..., validation_alias='IMAP_USERNAME')
    imap_password: str = Field(..., validation_alias='IMAP_PASSWORD')

    # SMTP Settings
    smtp_server: str = Field(..., validation_alias='SMTP_SERVER')
    smtp_port: int = Field(587, validation_alias='SMTP_PORT')
    smtp_username: str = Field(..., validation_alias='SMTP_USERNAME')
    smtp_password: str = Field(..., validation_alias='SMTP_PASSWORD')

    # LLM API Key
    # llm_api_key: str | None = Field(None, validation_alias='LLM_API_KEY')

    # Database URL (Optional)
    # database_url: str | None = Field(None, validation_alias='DATABASE_URL')

    # Logging Configuration
    log_file: str | None = Field(None, validation_alias='LOG_FILE')

    model_config = SettingsConfigDict(env_file=os.getenv('ENV_FILE', 'config.env'), extra='ignore', case_sensitive=True)


def load_config() -> AppConfig:
    parser = argparse.ArgumentParser(description="Property Manager Email Assistant")
    parser.add_argument(
        "--env-file",
        type=str,
        default=os.getenv('ENV_FILE', 'config.env'),
        help="Path to the environment file (default: config.env)",
    )
    args, _ = parser.parse_known_args()

    if not args.env_file:
        # Rely on host env vars.
        return AppConfig()
    
    if not os.path.exists(args.env_file):
        raise Exception(f"Environment file '{args.env_file}' doesn't exist.")

    return AppConfig(env_file=args.env_file) 


def setup_logging(config: AppConfig):
    # Clear any existing handlers on the root logger
    # This is important to prevent duplicate logs if this function is called multiple times
    # or if basicConfig was called elsewhere.
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in list(root_logger.handlers): # Iterate over a copy
            root_logger.removeHandler(handler)
            handler.close() # Close handler to release resources

    # Configure logging
    log_level = logging.INFO # Or make this configurable via AppConfig later
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers: list[logging.Handler] = []
    if config.log_file:
        try:
            file_handler = logging.FileHandler(config.log_file, mode='a')
            file_handler.setFormatter(logging.Formatter(log_format))
            handlers.append(file_handler)
            logger.info(f"Logging to file: {config.log_file}")
        except Exception as e:
            # If file logging fails, fall back to console and log the error
            console_handler_fallback = logging.StreamHandler()
            console_handler_fallback.setFormatter(logging.Formatter(log_format))
            handlers.append(console_handler_fallback)
            # Log the error using a temporary basic config if our main one isn't up yet
            # This logging call uses the module logger, which might not be configured yet
            # if setup_logging is failing. So, we also print to stderr.
            print(f"ERROR: Failed to setup file logging for '{config.log_file}': {e}. Falling back to console.")
            logger.error(f"Failed to setup file logging for '{config.log_file}': {e}. Falling back to console.")

    else:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(console_handler)

    # Apply the handlers and level to the root logger
    # Using basicConfig to set level and handlers for the root logger
    # Force=True is important if basicConfig might have been called before (e.g. by a library)
    logging.basicConfig(level=log_level, format=log_format, handlers=handlers, force=True)
    # After basicConfig, the root logger is configured. Our module logger will use this config.
    # We can re-log the file logging error here if it occurred, so it goes to the now-configured logger.
    if config.log_file and not any(isinstance(h, logging.FileHandler) for h in handlers):
        logger.error(f"File logging to '{config.log_file}' was intended but failed. Using console logging.")
