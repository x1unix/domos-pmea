import argparse
import os
import logging
import yaml
from pydantic import Field
from typing import Optional, Self
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from .llm import LLMConfig

logger = logging.getLogger(__name__)


class ListenerOptions(BaseSettings):
    """Mail listener configuration"""

    model_config = SettingsConfigDict(extra="ignore", env_prefix="")
    worker_count: int = Field(1, description="Number of workers to handle messages")
    msg_fetch_batch_size: int = Field(
        10, description="Number of messages to fetch per IMAP request"
    )
    msg_queue_size: int = Field(10, description="Messages queue size")
    ignore_addresses: set[str] = Field(
        default_factory=set, description="Addresses to ignore"
    )


class StorageConfig(BaseSettings):
    """Mock data storage configuration"""

    model_config = SettingsConfigDict(extra="ignore", env_prefix="")
    properties: Path = Field(..., description="Path to the properties database")
    tickets_dir: Path = Field(..., description="Path to the directory to store tickets")
    forwarded_messages_dir: Path | None = Field(
        None, description="Path to the directory to store forwarded messages (optional)"
    )


class RedisConfig(BaseSettings):
    """Redis provider configuration"""

    model_config = SettingsConfigDict(extra="ignore", env_prefix="")
    dsn: str = Field(..., description="Redis DSN")


class ChatsConfig(BaseSettings):
    """Chats behavior configuration"""

    model_config = SettingsConfigDict(extra="ignore", env_prefix="")
    ttl: int | None = Field(None, description="Redis key TTL")


class EmailConfig(BaseSettings):
    """Email provider configuration"""

    model_config = SettingsConfigDict(extra="ignore", env_prefix="")
    imap_host: str = Field(..., description="IMAP server hostname")
    imap_port: int = Field(993, description="IMAP server port")
    smtp_host: str = Field(..., description="SMTP server hostname")
    smtp_port: int = Field(587, description="SMTP server port")
    username: str = Field(..., description="Email account username")
    password: str = Field(..., description="Email account password")
    use_ssl: bool = Field(True, description="Whether to use SSL for connections")
    mailbox: str = Field("INBOX", description="Mailbox to monitor")
    idle_timeout: int = Field(
        29 * 60, description="IMAP IDLE timeout in seconds (default: 29 minutes)"
    )
    reconnect_delay: int = Field(
        5, description="Delay in seconds before reconnecting after connection loss"
    )
    reconnect_max_attempts: int = Field(
        3, description="Maximum number of reconnect attempts"
    )
    msg_id_domain: str | None = Field(
        None, description="Domain to use for Message-ID header"
    )

    def with_defaults(self) -> Self:
        if not self.msg_id_domain:
            parts = self.username.split("@")
            if len(parts) < 2:
                raise ValueError(
                    f"cannot extract domain from username: {self.username}"
                )
            self.msg_id_domain = parts[-1]
        return self


class LoggerConfig(BaseSettings):
    """Logging configuration"""

    model_config = SettingsConfigDict(extra="ignore", env_prefix="")
    level: str = Field("INFO", description="Logging level")
    file: Optional[Path] = Field(None, description="Path to log file")


class Config(BaseSettings):
    email: EmailConfig = Field(default_factory=EmailConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    logging: LoggerConfig = Field(default_factory=LoggerConfig)
    listener: ListenerOptions = Field(default_factory=ListenerOptions)
    chats: ChatsConfig = Field(default_factory=ChatsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix="",
    )

    def with_defaults(self) -> Self:
        self.email = self.email.with_defaults()
        self.llm = self.llm
        return self


def load_config_from_flags() -> Config:
    # TODO: figure out why env vars are not working.
    parser = argparse.ArgumentParser(description="Property Manager Email Assistant")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to the YAML config file",
    )

    args, _ = parser.parse_known_args()
    if not args.config:
        raise Exception("No config file provided")
    return load_config_from_file(Path(args.config))


def load_config_from_file(path: Path) -> Config:
    if not os.path.exists(path):
        raise Exception(f"Config file '{path}' doesn't exist.")
    with open(path, "r") as file:
        config_data = yaml.safe_load(file)
        return Config(**config_data).with_defaults()


def setup_logging(config: LoggerConfig):
    # Clear any existing handlers on the root logger
    # This is important to prevent duplicate logs if this function is called multiple times
    # or if basicConfig was called elsewhere.
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in list(root_logger.handlers):  # Iterate over a copy
            root_logger.removeHandler(handler)
            handler.close()  # Close handler to release resources

    # Configure logging
    log_level = getattr(logging, config.level.upper(), logging.INFO)
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers: list[logging.Handler] = []
    if config.file:
        try:
            file_handler = logging.FileHandler(config.file, mode="a")
            file_handler.setFormatter(logging.Formatter(log_format))
            handlers.append(file_handler)
            logger.info(f"Logging to file: {config.file}")
        except Exception as e:
            # If file logging fails, fall back to console and log the error
            console_handler_fallback = logging.StreamHandler()
            console_handler_fallback.setFormatter(logging.Formatter(log_format))
            handlers.append(console_handler_fallback)
            print(
                f"ERROR: Failed to setup file logging for '{config.file}': {e}. Falling back to console."
            )
            logger.error(
                f"Failed to setup file logging for '{config.file}': {e}. Falling back to console."
            )

    else:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(console_handler)

    logging.basicConfig(
        level=log_level, format=log_format, handlers=handlers, force=True
    )
    if config.file and not any(isinstance(h, logging.FileHandler) for h in handlers):
        logger.error(
            f"File logging to '{config.file}' was intended but failed. Using console logging."
        )
