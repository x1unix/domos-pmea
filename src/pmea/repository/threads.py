import redis.asyncio as aioredis
import uuid
from typing import Optional, Set
from ..config import RedisConfig

REDIS_THREAD_KEY_PREFIX = "thread:"
REDIS_MSG_ID_KEY_PREFIX = "msg:"

class ThreadsRepository:
    """Repository for keeping track of email message-to-thread mappings."""
    _redis_client: aioredis.Redis
    def __init__(self, redis_client: aioredis.Redis):
        self._redis_client = redis_client
        # self._redis_client = aioredis.Redis.from_url(cfg.dsn, decode_responses=True)

    async def get_thread_for_message(self, message_id: str) -> Optional[str]:
        """
        Retrieves the thread ID associated with a given message ID.
        Returns None if the message ID is not found or not linked to any thread.
        """
        key = f"{REDIS_MSG_ID_KEY_PREFIX}{message_id}"
        return await self._redis_client.get(key)

    async def create_new_thread_id(self) -> str:
        """
        Generates a new unique thread ID.
        """
        return str(uuid.uuid4())

    async def link_message_to_thread(self, message_id: str, thread_id: str) -> None:
        """
        Links a message ID to a thread ID in Redis.
        This involves two operations:
        1. Storing the mapping from message_id to thread_id (msg:<message_id> -> thread_id).
        2. Adding the message_id to the set of messages for the thread (thread:<thread_id> -> {message_id, ...}).
        """
        msg_key = f"{REDIS_MSG_ID_KEY_PREFIX}{message_id}"
        await self._redis_client.set(msg_key, thread_id)

        thread_key = f"{REDIS_THREAD_KEY_PREFIX}{thread_id}"
        await self._redis_client.sadd(thread_key, message_id)

    async def get_messages_in_thread(self, thread_id: str) -> Set[str]:
        """
        Retrieves all message IDs belonging to a specific thread.
        Returns an empty set if the thread does not exist or has no messages.
        """
        key = f"{REDIS_THREAD_KEY_PREFIX}{thread_id}"
        result = await self._redis_client.smembers(key)
        return result or set()