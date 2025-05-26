from dataclasses import dataclass
import datetime
import logging
from typing import Generator
import uuid
import pytest
import redis.asyncio as aioredis
from langchain_redis import RedisChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from pmea.agent.consumer import LLMMailConsumer, ConsumerConfig
from pmea.agent.tools import MailReplyer, CallToolsDependencies
from pmea.agent.utils import sanitize_session_id
from pmea.config import LoggerConfig, LLMConfig, setup_logging
from pmea.mailer import Message, Contact, MessageHeaders

TEST_REDIS_DSN = "redis://localhost:6379/0"
USE_REDIS = True
REDIS_FLUSH_BEFORE_TEST = False

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
        logging.info(f"Received reply: {body}")
        self._replies.append(CollectedReply(thread_id, parent_msg, body))

def make_chat_history(thread_id: str) -> BaseChatMessageHistory:
    if not USE_REDIS:
        return InMemoryChatMessageHistory()

    return RedisChatMessageHistory(
        # RedisChatMessageHistory throws AttributeError if redis_connection is used instead.
        # At: langchain_redis/chat_message_history.py:140
        redis_url=TEST_REDIS_DSN,
        session_id=sanitize_session_id(thread_id),
    )

def make_msg_id() -> str:
    return f"<{uuid.uuid4()}@example.com>"

@dataclass
class MessageInput:
    receiver: Contact
    sender: Contact
    body: str

def iter_messages(subject: str, input: list[MessageInput]) -> Generator[Message, None]:
    prev_msg_id: str | None = None
    references: list[str] | None = None
    for i, msg_input in enumerate(input):
        msg_id = make_msg_id()
        if prev_msg_id and references:
            references.append(prev_msg_id)
        elif prev_msg_id:
            references = [prev_msg_id]

        msg = Message(
            uid=str(i),
            receiver=msg_input.receiver,
            sender=msg_input.sender,
            subject=subject,
            sent_at=datetime.datetime.now(),
            body=msg_input.body,
            headers=MessageHeaders(
                msg_id=msg_id,
                in_reply_to=prev_msg_id,
                references=references,
            ),
        )
        prev_msg_id = msg_id
        yield msg


@pytest.mark.asyncio
async def test_debug_ai_consumer():
    setup_logging(LoggerConfig(level="INFO"))
    if USE_REDIS and REDIS_FLUSH_BEFORE_TEST:
        redis_client = aioredis.from_url(TEST_REDIS_DSN)
        await redis_client.flushdb()
        await redis_client.aclose()

    thread_id = "f8d0ae53-fa12-418b-8736-3e2c75cf9902"
    messages: list[MessageInput] = [
       MessageInput(
            receiver=Contact(name="Agent", email="agent@example.com"),
            sender=Contact(name="User", email="user@example.com"),
            body="Hello, how are you?",
        ),
       MessageInput(
            receiver=Contact(name="Agent", email="agent@example.com"),
            sender=Contact(name="User", email="user@example.com"),
            body="What is my name? And what did I ask you in previous message?",
        ) 
    ]
    
    replyer = MailReplyerMock()
    llm_config = LLMConfig(
        provider="ollama",
        model_name="qwen3:8b",
        temperature=0.4,
    )
    
    for msg in iter_messages("Hello", messages):
        consumer_config = ConsumerConfig(
            get_chat_model=llm_config.get_model_provider(),
            get_history=make_chat_history,
        )

        llm_consumer = LLMMailConsumer(consumer_config, CallToolsDependencies(replyer))

        await llm_consumer.consume_thread_message(thread_id, msg)
    replies = replyer.replies()
    assert len(replies) > 0
    logging.info("--- Received Replies: ---")
    for i, reply in enumerate(replies):
        logging.info(f"[ #{i} Thread ID: {reply.thread_id}; To: {reply.parent_msg.sender.email} ]")
        logging.info(reply.body)
