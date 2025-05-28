import redis.asyncio as aioredis
from langchain_redis import RedisChatMessageHistory
from ..agent import ConsumerConfig, sanitize_session_id
from ..config import RedisConfig, Config


async def make_redis_client(cfg: RedisConfig) -> aioredis.Redis:
    redis_client = aioredis.from_url(cfg.dsn)
    try:
        await redis_client.ping()
    except Exception as e:
        raise Exception(f"failed to connect to Redis: {e}")


def make_consumer_config(config: Config) -> ConsumerConfig:
    return ConsumerConfig(
        get_chat_model=config.llm.get_model_provider(),
        system_prompt_extra=config.llm.get_system_prompt_extra(),
        get_history=(
            lambda thread_id:
            # TODO: use connection pool for Redis.
            RedisChatMessageHistory(
                session_id=sanitize_session_id(thread_id),
                redis_url=config.redis.dsn,
                ttl=config.chats.ttl,
            )
        ),
    )
