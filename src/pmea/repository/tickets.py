import datetime
import json
import logging
from pathlib import Path
import uuid

from pmea.models import SupportTicketInputs

class TicketRepository:
    """Stub implementation of filesystem-based ticket repository."""
    _directory: Path
    _logger: logging.Logger = logging.getLogger(__name__)

    def __init__(self, directory: str):
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)

    def create_ticket(self, ticket: SupportTicketInputs) -> str:
        ticket_id = str(uuid.uuid4())
        ticket["id"] = ticket_id
        ticket["created_at"] = datetime.datetime.now(datetime.UTC).isoformat()

        path = self._directory / f"{ticket_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ticket, f, indent=2, ensure_ascii=False)

        self._logger.info("saved ticket '%s' as file '%s'", ticket_id, path)
        return ticket_id