import logging
import json
from typing import Optional, Type
from pydantic import BaseModel, Field, EmailStr
from langchain_core.callbacks import AsyncCallbackManagerForToolRun

from pmea.models import SupportTicketInputs
from .types import BaseAsyncTool, TicketCreator

class SupportTicketInputModel(BaseModel):
    """Fields required to create a support ticket."""
    severity: str = Field(..., description="Issue severity, e.g. 'low', 'medium', 'high'")
    title: str = Field(..., description="Short title of the issue")
    property_id: int = Field(..., description="ID of the property the ticket relates to")
    reporter_name: str = Field(..., description="Name of the person reporting the issue")
    reporter_email: EmailStr = Field(..., description="Email of the person reporting the issue")
    description: str = Field(..., description="Detailed description of the problem")

logger = logging.getLogger(__name__)

class CreateTicketTool(BaseAsyncTool):
    name: str = "create_ticket"
    args_schema: Type[BaseModel] = SupportTicketInputModel
    description: str = (
        "Tool to use for assistant to create a support ticket."
        "Returns a JSON string with object:"
        "{\"success\": boolean, \"id\": string | null }"
        ""
        "`success` indicates if the tool call was successful or had an error and failed."
        "`id` contains created ticket ID if `success` is true, otherwise it's null."
    )

    _ticket_creator: TicketCreator

    def __init__(self, ticket_creator: TicketCreator):
        super().__init__()
        self._ticket_creator = ticket_creator
    
    async def _arun(
            self,
            severity: str,
            title: str,
            property_id: int,
            reporter_name: str,
            reporter_email: EmailStr,
            description: str,
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        ) -> str:
            ctx_key = f"{self._context.thread_id}:{self._context.original_message.headers.msg_id}"
            ticket: SupportTicketInputs = {
                "severity": severity,
                "title": title,
                "property_id": property_id,
                "reporter_name": reporter_name,
                "reporter_email": reporter_email,
                "description": description,
            }

            try:
                logger.info(
                    "%s tool called: params=%s; msg=%s",
                    self.name, ticket, ctx_key,
                ) 
                ticket_id = self._ticket_creator.create_ticket(ticket)
                return json.dumps({ "success": True, "id": ticket_id })
            except Exception as e:
                logger.error(
                    "%s tool returned error: %s (params=%s; msg=%s)",
                    self.name, e, ticket, ctx_key,
                )
                return json.dumps({ "success": False })