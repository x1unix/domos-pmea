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
    building_number: str
    street_name: str
    city: str
    unit: str
    tenant: Tenant
    stakeholder_email: str
    monthly_rent_usd_cents: int