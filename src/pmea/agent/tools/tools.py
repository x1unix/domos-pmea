from dataclasses import dataclass
from langchain_core.tools import BaseTool
from .reply_to_user import ReplyToCustomerTool
from .types import ToolContext, MailReplyer

@dataclass
class CallToolsDependencies:
    replyer: MailReplyer

def build_call_tools(ctx: ToolContext, deps: CallToolsDependencies) -> list[BaseTool]:
    """Constructs a list of tools that can be called by the agent."""
    return [
        ReplyToCustomerTool(ctx, deps.replyer)
    ]