import logging
from pathlib import Path
from email.message import EmailMessage
from datetime import datetime


class MailFileWriter:
    """Saves EmailMessage objects to a directory as .txt files for debugging purposes."""

    _directory: Path
    _logger: logging.Logger = logging.getLogger(__name__)

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)

    def save(self, msg: EmailMessage) -> Path:
        """Save the EmailMessage to disk with a timestamped filename."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"mail-{timestamp}.txt"
        filepath = self._directory / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(msg.as_string())

        self._logger.info(f"saved forwarded message to {filepath}")
        return filepath
