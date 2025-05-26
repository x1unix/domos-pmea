from dataclasses import dataclass
import datetime
import logging
import pytest
import redis.asyncio as aioredis
from langchain_redis import RedisChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from pmea.agent.consumer import LLMMailConsumer, ConsumerConfig, MailReplyer
from pmea.agent.utils import sanitize_session_id
from pmea.config import LoggerConfig, LLMConfig, setup_logging
from pmea.mailer import Message, Contact, MessageHeaders

@dataclass
class CollectedReply:
     thread_id: str
     parent_msg: Message
     body: str

class MailReplyerMock(MailReplyer):
    _replies: list[CollectedReply] = []
    def replies(self) -> list[CollectedReply]:
        return self._replies
    
    async def reply_in_thread(self, thread_id: str, parent_msg: Message, body: str) -> None:
        self._replies.append(CollectedReply(thread_id, parent_msg, body))

TEST_REDIS_DSN = "redis://localhost:6379/0"
USE_REDIS = False

def make_chat_history(thread_id: str, with_redis: bool = False) -> BaseChatMessageHistory:
    if with_redis:
        return RedisChatMessageHistory(
            # RedisChatMessageHistory throws AttributeError if redis_connection is used instead.
            # At: langchain_redis/chat_message_history.py:140
            redis_url=TEST_REDIS_DSN,
            session_id=sanitize_session_id(thread_id),
        )
    return InMemoryChatMessageHistory()

@pytest.mark.asyncio
async def test_debug_ai_consumer():
    setup_logging(LoggerConfig(level="INFO"))
    thread_id = "f8d0ae53-fa12-418b-8736-3e2c75cf9902"
    msg = Message(
        uid="test",
        receiver=Contact(name="Agent", email="agent@example.com"),
        sender=Contact(name="User", email="user@example.com"),
        sent_at=datetime.datetime.now(),
        subject="Hello",
        body="Hello, how are you?",
        headers=MessageHeaders(
            msg_id="<1b169af6-5ac6-48f8-9aa7-0ba5e3419630@example.com>",
            in_reply_to=None,
            references=None,
        ),
    )

    setup_logging(LoggerConfig(level="INFO"))
    redis_client = aioredis.from_url(TEST_REDIS_DSN)
    await redis_client.ping()
    await redis_client.flushdb()
    await redis_client.aclose()
    try:
        llm_config = LLMConfig(
            provider="ollama",
            model_name="qwen3:8b",
            temperature=0.4,
        )

        consumer_config = ConsumerConfig(
            chat_model=llm_config.create_chat_model(),
            get_history=(lambda thread_id:
                make_chat_history(thread_id, with_redis=USE_REDIS)
            )
        )

        replyer = MailReplyerMock()
        llm_consumer = LLMMailConsumer(consumer_config, replyer)
        await llm_consumer.consume_thread_message(thread_id, msg)
        replies = replyer.replies()
        assert len(replies) > 0
        logging.info("--- Received Replies: ---")
        for reply in replies:
            logging.info(f"Thread ID: {reply.thread_id}")
            logging.info(f"To: {reply.parent_msg.sender.email}")
            logging.info(f"Body: {reply.body}")
            logging.info("---")
    finally:
        await redis_client.aclose()
