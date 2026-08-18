"""Single place where the app talks to MongoDB.

Services never build their own client, they ask for a collection here.
"""

from typing import Optional

from pymongo import ASCENDING, DESCENDING, AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.config import MONGO_DB_NAME, MONGO_URI


PLAYERS = "players"
TRANSACTIONS = "transactions"
JOB_COOLDOWNS = "job_cooldowns"
BUSINESSES = "businesses"

_client: Optional[AsyncMongoClient] = None
_database: Optional[AsyncDatabase] = None


def get_database() -> AsyncDatabase:
    """Lazily open one shared client for the whole process."""
    global _client, _database

    if _database is None:
        _client = AsyncMongoClient(MONGO_URI, tz_aware=True)
        _database = _client[MONGO_DB_NAME]

    return _database


def set_database(database: AsyncDatabase) -> None:
    """Swap in another database, used by the tests."""
    global _database
    _database = database


def get_collection(name: str) -> AsyncCollection:
    return get_database()[name]


def players() -> AsyncCollection:
    return get_collection(PLAYERS)


def transactions() -> AsyncCollection:
    return get_collection(TRANSACTIONS)


def job_cooldowns() -> AsyncCollection:
    return get_collection(JOB_COOLDOWNS)


def businesses() -> AsyncCollection:
    return get_collection(BUSINESSES)


async def init_database() -> None:
    """Create the indexes the game relies on. Safe to call on every start."""
    await players().create_index(
        [("telegram_id", ASCENDING)],
        unique=True,
        name="telegram_id_unique",
    )

    # transaction history is always read newest first for one player
    await transactions().create_index(
        [("player_id", ASCENDING), ("created_at", DESCENDING)],
        name="player_history",
    )

    # one cooldown row per player and job
    await job_cooldowns().create_index(
        [("player_id", ASCENDING), ("job_id", ASCENDING)],
        unique=True,
        name="player_job_unique",
    )

    await businesses().create_index(
        [("player_id", ASCENDING), ("business_type", ASCENDING)],
        unique=True,
        name="player_business_unique",
    )


async def close_database() -> None:
    global _client, _database

    if _client is not None:
        await _client.close()

    _client = None
    _database = None
