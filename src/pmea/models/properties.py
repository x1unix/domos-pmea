from dataclasses import dataclass
from typing import List

@dataclass
class Tenant:
    name: str
    email: str
    phone: str

@dataclass
class Property:
    property_id: int
    apartment: str
    address: str
    city: str
    tenant: Tenant
    stakeholder_email: str
    monthly_rent_usd_cents: int

@dataclass
class PropertySearchQuery:
    address: str | None = None
    apartment: str | None = None
    city: str | None = None
    tenant_name: str | None = None
    tenant_email: str | None = None
