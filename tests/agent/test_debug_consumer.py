import datetime
import logging
import os
import uuid
import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import Callable, Generator
import redis.asyncio as aioredis
from langchain_redis import RedisChatMessageHistory
from langchain_core.chat_history import (
    BaseChatMessageHistory,
    InMemoryChatMessageHistory,
)
from pmea.agent import LLMMailConsumer, ConsumerConfig, CallToolsDependencies
from pmea.agent.utils import sanitize_session_id
from pmea.config import (
    LoggerConfig,
    LLMConfig,
    setup_logging,
    StorageConfig,
    EmailConfig,
    OllamaOptions,
)
from pmea.mailer import (
    Message,
    Contact,
    MessageHeaders,
    MailSender,
    ThreadUpdater,
    MailFileWriter,
)
from pmea.repository.properties import PropertiesRepository
from pmea.repository.tickets import TicketRepository

def getboolenv(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in ["true", "1"]

TEST_REDIS_DSN = os.getenv("TEST_REDIS_DSN", "redis://localhost:6379/0")
USE_REDIS = getboolenv("USE_REDIS", True)
REDIS_FLUSH_BEFORE_TEST = getboolenv("REDIS_FLUSH_BEFORE_TEST", True)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAIL_IGNORED_DOMAINS = set(["gmail.com", "example.com", "example.org"])

llm_config_gemini_20_flash = (lambda:
    LLMConfig(
        provider="google",
        model_name="gemini-2.0-flash",
        temperature=1.0,
        model_options={
            "with_thinking": False,
        },
    )
)

llm_config_ollama_qwen14b = (lambda: 
    LLMConfig(
        provider="ollama",
        model_name="qwen3:14b",
        temperature=0.6,
        model_options={
            "with_thinking": False,
        },
        ollama_options=OllamaOptions(
            context_length=12288,
        ),
    )
)

@dataclass
class CollectedReply:
    thread_id: str
    parent_msg: Message
    body: str


class MockThreadUpdater(ThreadUpdater):
    async def add_thread_message(self, _message_id: str, _thread_id: str) -> None:
        pass


class MailReplyerMock(MailSender):
    _replies: list[CollectedReply] = []

    def __init__(
        self,
        forwarded_mails_dir: Path,
        ignored_domains: set[str] = MAIL_IGNORED_DOMAINS,
    ):
        cfg = EmailConfig(
            imap_host="",
            smtp_host="",
            username="",
            password="",
        )
        fw = MailFileWriter(forwarded_mails_dir)
        super().__init__(cfg, MockThreadUpdater(), fw, ignored_domains)

    def replies(self) -> list[CollectedReply]:
        return self._replies

    async def reply_in_thread(
        self, thread_id: str, parent_msg: Message, body: str
    ) -> None:
        logging.info(f"Received reply: {body}")
        self._replies.append(CollectedReply(thread_id, parent_msg, body))


in_mem_history = InMemoryChatMessageHistory()


def make_chat_history(thread_id: str) -> BaseChatMessageHistory:
    if not USE_REDIS:
        return in_mem_history

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


async def run_llm_consumer(
    thread_id: str, cfg_func: Callable[[], LLMConfig], messages: list[MessageInput]
) -> list[CollectedReply]:
    mod_dir = Path(__file__).resolve().parent
    data_dir = mod_dir.parent.parent / "data"
    storage_cfg = StorageConfig(
        tickets_dir=data_dir / "tickets_db.json",
        forwarded_messages_dir=data_dir / "forwarded_messages",
        properties=data_dir / "properties_db.json",
    )

    setup_logging(LoggerConfig(level=LOG_LEVEL))
    if USE_REDIS and REDIS_FLUSH_BEFORE_TEST:
        redis_client = aioredis.from_url(TEST_REDIS_DSN)
        await redis_client.flushdb()
        await redis_client.aclose()

    cfg = cfg_func()
    replyer = MailReplyerMock(storage_cfg.forwarded_messages_dir)
    props_store = PropertiesRepository(storage_cfg.properties)
    tickets_store = TicketRepository(storage_cfg.tickets_dir)
    tool_deps = CallToolsDependencies(replyer, props_store, tickets_store)
    for msg in iter_messages("Hello", messages):
        # Memory and model instance have to be recreated for each message to get history working.
        consumer_config = ConsumerConfig(
            get_chat_model=cfg.get_model_provider(),
            get_history=make_chat_history,
        )

        llm_consumer = LLMMailConsumer(consumer_config, tool_deps)
        await llm_consumer.consume_thread_message(thread_id, msg)
    replies = replyer.replies()
    logging.info("--- Received Replies: ---")
    for i, reply in enumerate(replies):
        logging.info(
            f"[ #{i} Thread ID: {reply.thread_id}; To: {reply.parent_msg.sender.email} ]"
        )
        logging.info(reply.body)
    return replies


@pytest.mark.asyncio
async def test_debug_ai_consumer_memory_ollama():
    thread_id = "00000000-0000-0000-0000-000000001001"
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
        ),
    ]

    replies = await run_llm_consumer(thread_id, llm_config_ollama_qwen14b, messages)
    assert len(replies) > 0


@pytest.mark.asyncio
async def test_debug_ai_consumer_memory_gemini():
    thread_id = "00000000-0000-0000-0000-000000001002"
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
        ),
    ]

    replies = await run_llm_consumer(thread_id, llm_config_gemini_20_flash, messages)
    assert len(replies) > 0


@pytest.mark.asyncio
async def test_debug_ai_consumer_infer_tenant_info_ollama():
    thread_id = "00000000-0000-0000-0000-000000002001"
    messages: list[MessageInput] = [
        MessageInput(
            receiver=Contact(name="Agent", email="agent@example.com"),
            sender=Contact(name="Michael Lee", email="michael.lee@example.com"),
            body=(
                "Hello, please remind me what is my apartment's address?",
                "I forgot it.",
            ),
        ),
    ]

    replies = await run_llm_consumer(thread_id, llm_config_ollama_qwen14b, messages)
    assert len(replies) > 0

@pytest.mark.asyncio
async def test_debug_ai_consumer_infer_tenant_info_gemini():
    thread_id = "00000000-0000-0000-0000-000000002002"
    messages: list[MessageInput] = [
        MessageInput(
            receiver=Contact(name="Agent", email="agent@example.com"),
            sender=Contact(name="Michael Lee", email="michael.lee@example.com"),
            body=(
                "Hello, please remind me what is my apartment's address?",
                "I forgot it.",
            ),
        ),
    ]

    replies = await run_llm_consumer(thread_id, llm_config_gemini_20_flash, messages)
    assert len(replies) > 0
