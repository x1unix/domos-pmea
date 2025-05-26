from __future__ import annotations

from typing import Optional, Type

from pydantic import BaseModel, Field
from langchain_core.callbacks import (
    CallbackManagerForToolRun,
    AsyncCallbackManagerForToolRun,
)

from .types import BaseAsyncTool, ToolContext, MailReplyer

class ReplyToCustomerInput(BaseModel):
    text: str = Field(description="Message body the assistant should send back to the user")

class ReplyToCustomerTool(BaseAsyncTool):
    name: str = "reply_to_user"
    description: str = """
       Tool to use for assistant to send reply back to user.
       Message body should contain just message text, no headers.
    """
    args_schema: Type[BaseModel] = ReplyToCustomerInput
    # return_direct: bool = True

    _replyer: MailReplyer
    _context: ToolContext

    def __init__(self, context: ToolContext, replyer: MailReplyer):
        super().__init__()
        self._replyer = replyer
        self._context = context

    async def _arun(
            self,
            text: str,
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        ) -> str:
            await self._replyer.reply_in_thread(
                self._context.thread_id,
                self._context.original_message,
                text,
            )
            return "Reply sent successfully"