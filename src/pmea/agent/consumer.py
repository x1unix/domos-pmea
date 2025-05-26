import datetime
import logging
from asyncio import Protocol
from dataclasses import dataclass
from typing import Callable
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models import BaseChatModel

from pmea.mailer.types import Contact, MessageHeaders

from .prompts import SYSTEM_PROMPT, build_error_response, message_to_prompt
from ..mailer import ThreadConsumer, Message

MSG_HISTORY_KEY = "history"  # For openai - "chat_history"
MSG_TEXT_KEY = "text"


class MailReplyer(Protocol):
    async def reply_in_thread(
        self, thread_id: str, parent_msg: Message, body: str
    ) -> None:
        """Sends a mail reply to the given thread."""


@dataclass
class ConsumerConfig:
    chat_model: BaseChatModel
    get_history: Callable[[str], BaseChatMessageHistory]


class LLMMailConsumer(ThreadConsumer):
    """Routes incoming email threads to LLM."""

    _logger: logging.Logger = logging.getLogger(__name__)
    _replyer: MailReplyer
    _config: ConsumerConfig

    def __init__(self, config: ConsumerConfig, replyer: MailReplyer):
        self._replyer = replyer
        self._config = config

    async def consume_thread_message(self, thread_id: str, m: Message) -> None:
        self._logger.info(
            "Thread %s: New email: uid=%s; from='%s'; dt=%s; subj='%s';",
            thread_id,
            m.uid,
            m.sender.to_addr(),
            m.sent_at,
            m.subject,
        )
        self._logger.info("Msg: %s:%s; Request:\n%s", thread_id, m.uid, m.body)

        try:
            response = await self._run_inference(thread_id, m)
            self._logger.info("Msg: %s:%s; Response:\n%s", thread_id, m.uid, response)
        except Exception as e:
            await self._handle_error(e, thread_id, m)
            raise e

        await self._replyer.reply_in_thread(thread_id, m, response)

    async def _handle_error(self, err: Exception, thread_id: str, m: Message) -> None:
        try:
            # Notify user about the error.
            # TODO: reroute message to stakeholders.
            self._logger.error(
                "error during AI inference: %s (thread_id=%s; msg_id=%s)",
                err,
                thread_id,
                m.headers.msg_id,
            )
            await self._replyer.reply_in_thread(
                thread_id, m, build_error_response(thread_id, err)
            )
        except Exception as e:
            self._logger.error(
                "failed to notify user about error: %s (thread_id=%s; msg_id=%s)",
                e, thread_id, m.headers.msg_id,
            )

    def _build_chain(self) -> RunnableWithMessageHistory:
        """Builds a chain for the given thread and message."""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name=MSG_HISTORY_KEY),
                ("human", f"{{{MSG_TEXT_KEY}}}"),
            ]
        )

        base_chain = prompt | self._config.chat_model | StrOutputParser()
        chain_with_memory = RunnableWithMessageHistory(
            base_chain,
            self._config.get_history,
            input_messages_key=MSG_TEXT_KEY,
            history_messages_key=MSG_HISTORY_KEY,
        )
        return chain_with_memory

    async def _run_inference(self, thread_id: str, m: Message) -> str:
        chain = self._build_chain()
        input_msg = {
            MSG_TEXT_KEY: message_to_prompt(thread_id, m),
        }

        session_cfg = {
            "configurable": {
                # Keep AI session ID in sync with mail thread ID.
                "session_id": thread_id,
            },
        }
        return await chain.ainvoke(input=input_msg, config=session_cfg)
