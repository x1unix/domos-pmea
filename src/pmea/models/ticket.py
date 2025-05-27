from typing import TypedDict

class SupportTicketInputs(TypedDict):
    """Fields required to create a support ticket."""
    severity: str
    title: str
    property_id: int
    reporter_name: str
    reporter_email: str
    description: str

class SupportTicket(SupportTicketInputs):
    """Customer support ticket created by agent."""
    id: str
    created_at: str
