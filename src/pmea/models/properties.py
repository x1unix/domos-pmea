from dataclasses import dataclass
from typing import List
import json

@dataclass
class Tenant:
    name: str
    email: str
    phone: str

@dataclass
class Apartment:
    property_id: int
    address: str
    city: str
    tenant: Tenant
    stakeholder_email: str
    monthly_rent_usd_cents: int

@dataclass
class PropertySearchQuery:
    address: str | None = None
    city: str | None = None
    tenant_name: str | None = None
    tenant_email: str | None = None
