from __future__ import annotations

from dataclasses import asdict
import json
import logging
from typing import Optional, Type

from pydantic import BaseModel, Field
from langchain_core.callbacks import AsyncCallbackManagerForToolRun

from .types import BaseAsyncTool, PropertiesStore, ToolContext
from ...models import PropertySearchQuery

logger = logging.getLogger(__name__)


class FindPropertyInput(BaseModel):
    address: str | None = Field(
        None,
        description=(
            "Tenant's building number, street name and apartment number. Can be partial or full."
            "Example: '221 Baker St' or '3 Hillow Ave'"
        ),
    )

    apartment: str | None = Field(
        None,
        description="Apartment number without 'Apt' or 'Unit' prefix",
    )

    tenant_name: str | None = Field(
        None,
        description="First and last name of the tenant to find, optional. Example: 'John Doe' or 'Jane Smith'",
    )


class FindPropertiesTool(BaseAsyncTool):
    name: str = "find_properties"
    args_schema: Type[BaseModel] = FindPropertyInput
    description: str = (
        "Tool to use for assistant to find matching properties (apartments) by address or tenant's name"
        "If you don't have enough or precise information, you can try partial search by providing only part of the information."
        "In that case, you will get a list of all matching properties (apartments) and you can ask user to provide more information to pick a correct one."
        ""
        "Returns a JSON string with object:"
        '{"success": boolean, "data": list of objects | null}'
        ""
        "`success` indicates if the tool call was successful or had an error and failed."
        "If `success` is true and `data` is null or empty, it means that no properties were found matching the given query."
        ""
        "Each object in `data` array looks like this:"
        "```json"
        "{"
        '    "property_id": 1,'
        '    "address": "string",'
        '    "stakeholder_email": "string",'
        '    "monthly_rent_usd_cents": 230000,'
        '    "tenant": {'
        '        "name": "string",'
        '        "email": "string",'
        '        "phone": "string"'
        "    },"
        "}"
        "```"
    )

    _properties_store: PropertiesStore
    _context: ToolContext

    def __init__(self, context: ToolContext, properties_store: PropertiesStore):
        super().__init__()
        self._context = context
        self._properties_store = properties_store

    async def _arun(
        self,
        address: str | None = None,
        tenant_name: str | None = None,
        apartment: str | None = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        ctx_key = (
            f"{self._context.thread_id}:{self._context.original_message.headers.msg_id}"
        )
        params = {
            "address": address,
            "apartment": apartment,
            "tenant_name": tenant_name,
        }
        try:
            logger.info(
                "%s tool called: params=%s; msg=%s",
                self.name,
                params,
                ctx_key,
            )
            query = PropertySearchQuery(
                address=address,
                apartment=apartment,
                tenant_name=tenant_name,
            )
            properties = self._properties_store.find_properties(query)
            return json.dumps(
                {
                    "success": True,
                    "data": [asdict(p) for p in properties] if properties else [],
                }
            )
        except Exception as e:
            logger.error(
                "%s tool returned error: %s (params=%s; msg=%s)",
                self.name,
                e,
                params,
                ctx_key,
            )
            return json.dumps({"success": False})
