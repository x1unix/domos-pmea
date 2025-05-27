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
        description=(
            "Building number, street name and apartment number. Can be partial or full."
            "Example: '221 Baker St, Apt 2D' or '3 Hillow Ave, 3rd Floor'"
        )
    )

    city: str | None = Field(description="City of the property to find. Example: 'New York' or 'San Francisco'")
    tenant_name: str | None = Field(description="First and last name of the tenant to find. Example: 'John Doe' or 'Jane Smith'")
    tenant_email: str | None = Field(description="Email of the tenant to find")

class TenantInfo(BaseModel):
    name: str = Field(description="First and last name of the tenant")
    email: str = Field(description="Email of the tenant")
    phone: str = Field(description="Phone number of the tenant")

class PropertyInfo(BaseModel):
    address: str = Field(description="Address of the property")
    city: str = Field(description="City of the property")
    tenant: TenantInfo = Field(description="Tenant information")
    stakeholder_email: str = Field(description="Email of the stakeholder that manages this property")
    monthly_rent_usd_cents: int = Field(description="Monthly rent price in USD cents")

class FindPropertiesTool(BaseAsyncTool):
    name: str = "find_properties"
    args_schema: Type[BaseModel] = FindPropertyInput
    description: str = (
        "Tool to use for assistant to find matching properties (apartments) by address or city or tenant's name or email"
        "If you don't have enough or precise information, you can try partial search by providing only part of the information."
        "In that case, you will get a list of all matching properties (apartments) and you can ask user to provide more information to pick a correct one."
        ""
        "Returns a JSON string with object:"
        "{\"success\": boolean, \"data\": list of objects | null}"
        ""
        "`success` indicates if the tool call was successful or had an error and failed."
        "If `success` is true and `data` is null or empty, it means that no properties were found matching the given query."
        ""
        "Each object in `data` array looks like this:"
        "```json"
        "{"
        "    \"property_id\": 1,"
        "    \"address\": \"123 Main St, Anytown, USA\","
        "    \"city\": \"Anytown\","
        "    \"stakeholder_email\": \"alice@example.com\","
        "    \"monthly_rent_usd_cents\": 230000,"
        "    \"tenant\": {"
        "        \"name\": \"John Doe\","
        "        \"email\": \"john.doe@example.com\","
        "        \"phone\": \"+1-202-555-0100\""
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
            city: str | None = None,
            tenant_name: str | None = None,
            tenant_email: str | None = None,
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        ) -> str:
            ctx_key = f"{self._context.thread_id}:{self._context.original_message.headers.msg_id}"
            try:
                logger.info(
                    "%s tool called: params=%s; msg=%s",
                    self.name,
                    { "address": address, "city": city, "tenant_name": tenant_name, "tenant_email": tenant_email },
                    ctx_key,
                ) 
                query = PropertySearchQuery(
                    address=address,
                    city=city,
                    tenant_name=tenant_name,
                    tenant_email=tenant_email,
                )
                properties = self._properties_store.find_properties(query)
                return json.dumps({ "success": True, "data": [asdict(p) for p in properties] if properties else [] })
            except Exception as e:
                logger.error(
                    "%s tool returned error: %s (params=%s; msg=%s)",
                    self.name, e,
                    { "address": address, "city": city, "tenant_name": tenant_name, "tenant_email": tenant_email },
                    ctx_key,
                ) 
                return json.dumps({ "success": False })

class GetPropertyByIdInput(BaseModel):
    property_id: int = Field(description="ID of the property to get information about")

class GetPropertyByIdTool(BaseAsyncTool):
    name: str = "get_property_by_id"
    args_schema: Type[BaseModel] = GetPropertyByIdInput
    description: str = (
        "Tool returns property information by property ID."
        "This tool can be used instead of find_properties if you know exact property ID."
        ""
        "Returns a JSON string with object:"
        "{\"success\": boolean, \"data\": object | null }"
        ""
        "`success` indicates if the tool call was successful or had an error and failed."
        "If `data` is null but `success` is true, it means that property with given ID was not found."
        ""
        "Object `data` array looks like this:"
        "```json"
        "{"
        "    \"property_id\": 1,"
        "    \"address\": \"123 Main St, Anytown, USA\","
        "    \"city\": \"Anytown\","
        "    \"stakeholder_email\": \"alice@example.com\","
        "    \"monthly_rent_usd_cents\": 230000,"
        "    \"tenant\": {"
        "        \"name\": \"John Doe\","
        "        \"email\": \"john.doe@example.com\","
        "        \"phone\": \"+1-202-555-0100\""
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
            property_id: int | str | None = None,
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        ) -> str:
            ctx_key = f"{self._context.thread_id}:{self._context.original_message.headers.msg_id}"
            try:
                logger.info(
                    "%s tool called: params=%s; msg=%s",
                    self.name,
                    { "property_id": property_id },
                    ctx_key,
                ) 
                result = self._properties_store.get_property_by_id(int(property_id))
                return json.dumps({ "success": True, "data": asdict(result) if result else None })
            except Exception as e:
                logger.error(
                    "%s tool returned error: %s (params=%s; msg=%s)",
                    self.name, e,
                    { "property_id": property_id },
                    ctx_key,
                ) 
                return json.dumps({ "success": False })