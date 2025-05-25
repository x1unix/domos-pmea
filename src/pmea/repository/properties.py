import json
from typing import Any, List
from ..models import Apartment, Tenant



class PropertiesRepository:
    _properties: List[Apartment]

    def __init__(self, properties_path: str):
        with open(properties_path, "r") as f:
            raw_data: List[dict[str, Any]] = json.load(f)
        return [
            Apartment(
                property_id=item["property_id"],
                building_number=item["building_number"],
                street_name=item["street_name"],
                city=item["city"],
                unit=item["unit"],
                tenant=Tenant(**item["tenant"]),
                stakeholder_email=item["stakeholder_email"],
                monthly_rent_usd_cents=item["monthly_rent_usd_cents"]
            )
            for item in raw_data
        ]
