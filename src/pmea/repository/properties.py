import json
from typing import Any, List
from ..models import Apartment, Tenant, PropertySearchQuery

class PropertiesRepository:
    _properties: List[Apartment]
    _property_ids: dict[str, int]

    def __init__(self, properties_path: str):
        with open(properties_path, "r") as f:
            raw_data: List[dict[int, Any]] = json.load(f)
            self._properties = [
                Apartment(
                    property_id=int(item["property_id"]),
                    address=item["address"],
                    city=item["city"],
                    tenant=Tenant(**item["tenant"]),
                    stakeholder_email=item["stakeholder_email"],
                    monthly_rent_usd_cents=item["monthly_rent_usd_cents"]
                )
                for item in raw_data
            ]
            self._property_ids = {a.property_id: i for i, a in enumerate(self._properties)}

    def property_exists(self, property_id: int) -> bool:
        return property_id in self._property_ids

    def get_property_by_id(self, property_id: int) -> Apartment | None:
        if not property_id in self._property_ids:
            return None
        i = self._property_ids[property_id]
        return self._properties[i]

    def find_properties(self, query: PropertySearchQuery) -> List[Apartment]:
        if not query.address and not query.tenant_name and not query.tenant_email:
            raise ValueError("At least one search criteria must be provided.")

        results = self._properties

        if query.address:
            addr = query.address.lower()
            results = [
                p for p in results
                if p.address.lower().startswith(addr)
            ]

        if query.city:
            city = query.city.lower()
            results = [
                p for p in results
                if p.city.lower() == city
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