from dataclasses import dataclass
from langchain_core.tools import BaseTool
# from .reply_to_user import ReplyToUserTool
from .properties import FindPropertiesTool, GetPropertyByIdTool
from .types import ToolContext, MailReplyer, PropertiesStore

@dataclass
class CallToolsDependencies:
    replyer: MailReplyer
    properties_store: PropertiesStore

def build_call_tools(ctx: ToolContext, deps: CallToolsDependencies) -> list[BaseTool]:
    """Constructs a list of tools that can be called by the agent."""
    return [
        # ReplyToUserTool(ctx, deps.replyer),
        FindPropertiesTool(ctx, deps.properties_store),
        GetPropertyByIdTool(ctx, deps.properties_store),
    ]