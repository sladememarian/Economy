"""Test setup.

Every test runs against a throwaway in memory mongo, so the real database is
never touched. Set MONGO_TEST_URI to run the same suite against the container
from docker compose instead.
"""

import os

import pytest
import pytest_asyncio

from app.database import mongo


MONGO_TEST_URI = os.getenv("MONGO_TEST_URI")


@pytest_asyncio.fixture
async def database():
    """Fresh empty database with the real indexes in place."""
    if MONGO_TEST_URI:
        from pymongo import AsyncMongoClient

        client = AsyncMongoClient(MONGO_TEST_URI, tz_aware=True)
        db = client["economy_test"]

        # a previous run may have left documents behind
        for name in await db.list_collection_names():
            await db.drop_collection(name)

    else:
        from mongomock_motor import AsyncMongoMockClient

        client = AsyncMongoMockClient()
        db = client["economy_test"]

    mongo.set_database(db)
    await mongo.init_database()

    yield db

    if MONGO_TEST_URI:
        await client.close()

    mongo.set_database(None)


@pytest_asyncio.fixture
async def new_player(database):
    """Factory for players, so tests do not repeat the signup call."""
    from app.services.player import create_player

    async def make(
        telegram_id: int = 1001,
        username: str = "player",
        first_name: str = "Player",
    ) -> dict:
        return await create_player(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )

    return make
