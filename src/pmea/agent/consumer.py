import logging
from asyncio import Protocol
from dataclasses import dataclass
from typing import Optional
from langchain_redis import RedisChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_core.language_models import BaseChatModel

from pmea.agent.utils import build_error_response, message_to_prompt
from ..config import RedisConfig, ChatsConfig
from ..mailer import ThreadConsumer, Message

REDIS_KEY_AI_CHATS = "ai_chat:"
HISTORY_KEY = "history"  # For openai - "chat_history"


class MailReplyer(Protocol):
    async def reply_in_thread(
        self, thread_id: str, parent_msg: Message, body: str
    ) -> None:
        pass


@dataclass
class ConsumerConfig:
    redis: RedisConfig
    options: ChatsConfig
    chat_model: BaseChatModel


class LLMMailConsumer(ThreadConsumer):
    """Routes incoming email threads to LLM."""

    _logger: logging.Logger = logging.getLogger(__name__)
    _replyer: MailReplyer
    _redis_dsn: str
    _chat_ttl: Optional[int]
    _chat_model: BaseChatModel

    def __init__(self, config: ConsumerConfig, replyer: MailReplyer):
        self._replyer = replyer
        self._chat_ttl = config.options.ttl
        self._redis_dsn = config.redis.dsn
        self._chat_model = config.chat_model

    async def consume_thread_message(self, thread_id: str, m: Message) -> None:
        self._logger.info(
            "Thread %s: New email: uid=%s; from='%s'; dt=%s; subj='%s';",
            thread_id, m.uid, m.sender.to_addr(), m.sent_at, m.subject,
        )
        self._logger.info("Msg: %s:%s; Request:\n%s", thread_id, m.uid, m.body)

        try:
            response = await self._run_inference(thread_id, m)
            self._logger.info("Msg: %s:%s; Response:\n%s", thread_id, m.uid, response)
        except Exception as e:
            # Notify user about the error.
            # TODO: reroute message to stakeholders.
            self._logger.error(
                "error during AI inference: %s (thread_id=%s; msg_id=%s)",
                e, thread_id, m.headers.msg_id
            )
            await self._replyer.reply_in_thread(
                thread_id, m, build_error_response(thread_id, e)
            )
            raise e
        await self._replyer.reply_in_thread(thread_id, m, response)

    async def _run_inference(self, thread_id: str, m: Message) -> str:
        # TODO: use connection pool for Redis.
        history = RedisChatMessageHistory(
            session_id=thread_id,
            redis_url=self._redis_dsn,
            key_prefix=REDIS_KEY_AI_CHATS,
            ttl=self._chat_ttl,
        )

        memory = ConversationBufferMemory(
            chat_memory=history,
            memory_key=HISTORY_KEY,
            return_messages=True,
        )

        chain = ConversationChain(
            llm=self._chat_model,
            memory=memory,
            verbose=True,
        )

        prompt = message_to_prompt(m)
        return await chain.apredict(input=prompt)
