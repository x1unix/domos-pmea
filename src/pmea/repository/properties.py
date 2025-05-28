import json
from typing import Any, List
from ..models import Property, Tenant, PropertySearchQuery

class PropertiesRepository:
    _properties: List[Property]
    _property_ids: dict[str, int]

    def __init__(self, properties_path: str):
        with open(properties_path, "r") as f:
            raw_data: List[dict[int, Any]] = json.load(f)
            self._properties = [
                Property(
                    property_id=int(item["property_id"]),
                    apartment=item["apartment"],
                    address=item["address"],
                    tenant=Tenant(**item["tenant"]),
                    stakeholder_email=item["stakeholder_email"],
                    monthly_rent_usd_cents=item["monthly_rent_usd_cents"]
                )
                for item in raw_data
            ]
            self._property_ids = {a.property_id: i for i, a in enumerate(self._properties)}

    def property_exists(self, property_id: int) -> bool:
        i = self._property_ids.get(property_id)
        return i is not None

    def get_property_by_id(self, property_id: int) -> Property | None:
        i = self._property_ids.get(property_id)
        if i is None:
            return None
        return self._properties[i]

    def find_properties(self, query: PropertySearchQuery) -> List[Property]:
        if not query.address and not query.tenant_name and not query.tenant_email:
            raise ValueError("At least one search criteria must be provided.")

        results = self._properties

        if query.address:
            addr = query.address.lower()
            results = [
                p for p in results
                if p.address.lower().startswith(addr)
            ]
        
        if query.apartment:
            apartment = query.apartment.lower()
            results = [
                p for p in results
                if p.apartment.lower() == apartment
            ]

        if query.tenant_name:
            tenant_name = query.tenant_name.lower()
            results = [
                p for p in results
                if p.tenant and tenant_name in p.tenant.name.lower()
            ]

        return results