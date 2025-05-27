import logging
import json
from typing import Optional, Type
from pydantic import BaseModel, Field, EmailStr
from langchain_core.callbacks import AsyncCallbackManagerForToolRun

from .types import BaseAsyncTool, MailReplyer, PropertiesStore, ToolContext


class ForwardToStakeholderInputModel(BaseModel):
    """Fields required to forward a mail."""

    property_id: int = Field(
        ..., description="ID of the property to contact a stakeholder about"
    )
    additional_comments: str | None = Field(
        None,
        description="Optional additional comments to include in the email (string or null)",
    )


logger = logging.getLogger(__name__)


class ForwardToStakeholderTool(BaseAsyncTool):
    name: str = "forward_to_stakeholder"
    args_schema: Type[BaseModel] = ForwardToStakeholderInputModel
    description: str = (
        "Tool to forward received message to a property manager (stakeholder) of a building."
        "Returns a JSON string with object:"
        '{"success": boolean, "error": string | null }'
        ""
        "`success` indicates if the tool call was successful or had an error and failed."
        "`error` is optional field that contains error message if `success` is false, otherwise it's null."
    )

    _context: ToolContext
    _properties_store: PropertiesStore
    _mail_replyer: MailReplyer

    def __init__(
        self,
        context: ToolContext,
        properties_store: PropertiesStore,
        replyer: MailReplyer,
    ):
        super().__init__()
        self._context = context
        self._replyer = replyer
        self._properties_store = properties_store

    async def _arun(
        self,
        property_id: int,
        additional_comments: str | None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        ctx_key = (
            f"{self._context.thread_id}:{self._context.original_message.headers.msg_id}"
        )
        property = self._properties_store.get_property_by_id(property_id)
        if not property:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Property with ID {property_id} does not exist",
                }
            )

        try:
            logger.info(
                "%s tool called: property_id=%s; msg=%s",
                self.name,
                property_id,
                ctx_key,
            )
            await self._replyer.forward_message(
                parent_msg=self._context.original_message,
                dst_email=property.stakeholder_email,
                body=additional_comments,
            )
            return json.dumps({"success": True})
        except Exception as e:
            logger.error(
                "%s tool returned error: %s (params=%s; msg=%s)",
                self.name,
                e,
                property_id,
                ctx_key,
            )
            return json.dumps({"success": False, "error": str(e)})
