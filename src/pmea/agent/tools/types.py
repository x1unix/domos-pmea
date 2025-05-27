from dataclasses import dataclass
import logging
from typing import List, Protocol
from langchain_core.tools import BaseTool
from pmea.mailer.types import Message
from pmea.models import Apartment, PropertySearchQuery, SupportTicketInputs

class MailReplyer(Protocol):
    """Abstract interface to reply to a mail thread."""
    async def reply_in_thread(
        self, thread_id: str, parent_msg: Message, body: str
    ) -> None:
        """Sends a mail reply to the given thread."""

class PropertiesStore(Protocol):
    def find_properties(self, query: PropertySearchQuery) -> List[Apartment]:
        """Finds properties matching the given query."""
    
    def get_property_by_id(self, property_id: str) -> Apartment | None:
        """Gets a property by its ID."""

class TicketCreator(Protocol):
    """Abstract interface to create a support ticket."""
    def create_ticket(self, ticket: SupportTicketInputs) -> str:
        """Creates a support ticket."""

@dataclass
class ToolContext:
    thread_id: str
    original_message: Message

class BaseAsyncTool(BaseTool):
    """Base class for async tools with stub implementation for sync methods."""
    def _run(self, *args, **kwargs) -> None:
        """Stub implementation for sync method"""
        logging.warning("attempt to call synchronous method")
        raise Exception("this tool doesn't support synchronous calls")