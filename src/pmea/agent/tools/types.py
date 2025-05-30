from dataclasses import dataclass
import logging
from typing import List, Protocol
from langchain_core.tools import BaseTool
from pmea.mailer.types import Message
from pmea.models import Property, PropertySearchQuery, SupportTicketInputs


class MailReplyer(Protocol):
    """Abstract interface to reply to a mail thread."""

    async def reply_in_thread(
        self, thread_id: str, parent_msg: Message, body: str
    ) -> None:
        """Sends a mail reply to the given thread."""

    async def forward_message(
        self, parent_msg: Message, dst_email: str, body: str | None
    ) -> None:
        """Forwards a mail to the given email address."""


class PropertiesStore(Protocol):
    def find_properties(self, query: PropertySearchQuery) -> List[Property]:
        """Finds properties matching the given query."""

    def get_property_by_id(self, property_id: int) -> Property | None:
        """Gets a property by its ID."""

    def property_exists(self, property_id: int) -> bool:
        """Checks if a property exists."""


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
