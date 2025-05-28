import logging
from dataclasses import dataclass
from typing import Callable
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel
from langchain.agents import create_tool_calling_agent, AgentExecutor

from ..mailer import ThreadConsumer, Message
from .prompts import SYSTEM_PROMPT, build_error_response, message_to_prompt
from .tools import CallToolsDependencies, build_call_tools, ToolContext
from .utils import InferenceResult, output_from_inference_result

MSG_HISTORY_KEY = "history"  # For openai - "chat_history"
MSG_INPUT_KEY = "input"
MSG_OUTPUT_KEY = "output"

@dataclass
class ConsumerConfig:
    get_chat_model: Callable[[], BaseChatModel]
    get_history: Callable[[str], BaseChatMessageHistory]
    system_prompt_extra: str | None

class LLMMailConsumer(ThreadConsumer):
    """Routes incoming email threads to LLM."""

    _logger: logging.Logger = logging.getLogger(__name__)
    _deps: CallToolsDependencies
    _config: ConsumerConfig

    def __init__(self, config: ConsumerConfig, deps: CallToolsDependencies):
        self._deps = deps
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

        result: InferenceResult | None = None
        try:
            result = await self._run_inference(thread_id, m)
            self._logger.info("Msg: %s:%s; inference done", thread_id, m.uid)
        except Exception as e:
            await self._handle_error(e, thread_id, m)
            raise e

        output = output_from_inference_result(result)
        if output:
            await self._deps.replyer.reply_in_thread(thread_id, m, output)

    async def _handle_error(self, err: Exception, thread_id: str, m: Message) -> str:
        try:
            # Notify user about the error.
            # TODO: reroute message to stakeholders.
            self._logger.error(
                "error during AI inference: %s (thread_id=%s; msg_id=%s)",
                err,
                thread_id,
                m.headers.msg_id,
            )
            await self._deps.replyer.reply_in_thread(
                thread_id, m, build_error_response(thread_id, err)
            )
        except Exception as e:
            self._logger.error(
                "failed to notify user about error: %s (thread_id=%s; msg_id=%s)",
                e, thread_id, m.headers.msg_id,
            )

    def _build_chain(self, ctx: ToolContext) -> RunnableWithMessageHistory:
        """Builds a chain for the given thread and message."""
        system_prompt = SYSTEM_PROMPT
        if self._config.system_prompt_extra:
            system_prompt += f"\n{self._config.system_prompt_extra}"

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt),
                MessagesPlaceholder(variable_name=MSG_HISTORY_KEY),
                HumanMessage(content=f"{{{MSG_INPUT_KEY}}}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        # TODO: refactor to make tools stateless.
        tools = build_call_tools(ctx, self._deps)
        model = self._config.get_chat_model()
        agent_runnable = create_tool_calling_agent(prompt=prompt, llm=model, tools=tools)
        agent = AgentExecutor(agent=agent_runnable, tools=tools, verbose=True)
        chain_with_memory = RunnableWithMessageHistory(
            agent,
            get_session_history=self._config.get_history,
            input_messages_key=MSG_INPUT_KEY,
            history_messages_key=MSG_HISTORY_KEY,
        )
        return chain_with_memory

    async def _run_inference(self, thread_id: str, m: Message) -> InferenceResult:
        ctx = ToolContext(thread_id, m)
        chain = self._build_chain(ctx)
        input_msg = {
            MSG_INPUT_KEY: message_to_prompt(thread_id, m),
        }

        session_cfg = {
            "configurable": {
                # Keep AI session ID in sync with mail thread ID.
                "session_id": thread_id,
            },
        }

        # TODO: filter out AI thoughts (`<think>...</think>`) from the response.
        return await chain.ainvoke(input=input_msg, config=session_cfg)
