from dataclasses import dataclass
import json
from typing import Any, List
from ..models import Apartment, Tenant

@dataclass
class PropertySearchQuery:
    address: str | None = None
    tenant_name: str | None = None
    tenant_email: str | None = None

class PropertiesRepository:
    _properties: List[Apartment]

    def __init__(self, properties_path: str):
        with open(properties_path, "r") as f:
            raw_data: List[dict[str, Any]] = json.load(f)
            self._properties = [
                Apartment(
                    property_id=item["property_id"],
                    address=item["address"],
                    city=item["city"],
                    tenant=Tenant(**item["tenant"]),
                    stakeholder_email=item["stakeholder_email"],
                    monthly_rent_usd_cents=item["monthly_rent_usd_cents"]
                )
                for item in raw_data
            ]

    def find_property(self, query: PropertySearchQuery) -> List[Apartment]:
        if not query.address and not query.tenant_name and not query.tenant_email:
            raise ValueError("At least one search criteria must be provided.")

        results = self._properties

        if query.address:
            addr = query.address.lower()
            results = [
                p for p in results
                if p.address.lower().startswith(addr)
            ]

        if query.tenant_name:
            tenant_name = query.tenant_name.lower()
            results = [
                p for p in results
                if p.tenant and tenant_name in p.tenant.name.lower()
            ]

        if query.tenant_email:
            results = [
                p for p in results
                if p.tenant and p.tenant.email and query.tenant_email.lower() == p.tenant.email.lower()
            ]
        
        return results

    def get_property_by_id(self, property_id: str) -> Apartment | None:
        for prop in self._properties:
            if prop.property_id == property_id:
                return prop
        return None
