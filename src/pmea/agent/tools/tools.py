from dataclasses import dataclass
from langchain_core.tools import BaseTool
from .properties import FindPropertiesTool, GetPropertyByIdTool
from .types import TicketCreator, ToolContext, MailReplyer, PropertiesStore
from .create_ticket import CreateTicketTool

@dataclass
class CallToolsDependencies:
    """Holds dependencies for tools that can be called by the agent."""
    replyer: MailReplyer
    properties_store: PropertiesStore
    ticket_creator: TicketCreator

def build_call_tools(ctx: ToolContext, deps: CallToolsDependencies) -> list[BaseTool]:
    """Constructs a list of tools that can be called by the agent."""
    return [
        FindPropertiesTool(ctx, deps.properties_store),
        GetPropertyByIdTool(ctx, deps.properties_store),
        CreateTicketTool(deps.ticket_creator, deps.properties_store),
    ]