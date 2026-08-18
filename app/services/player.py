"""Players: creation, retrieval and level progression.

A player document also holds the wallet balance, so app/services/economy.py
is the module that moves it. Nothing here writes balance directly except the
initial capital handed out at signup.
"""

from datetime import datetime, timezone
from typing import Optional

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.database import mongo
from app.services.economy import PlayerNotFound, TransactionType, record_transaction


STARTING_BALANCE = 10_000

# xp needed for level 2 is 100, level 3 is 300, level 4 is 600 and so on
XP_PER_LEVEL = 100
MAX_LEVEL = 100


class PlayerAlreadyExists(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ==================================================
# Levels
# ==================================================

def xp_to_reach(level: int) -> int:
    """Total xp a player needs to sit at this level."""
    if level <= 1:
        return 0

    # each level costs 100 more than the one before it
    return XP_PER_LEVEL * (level - 1) * level // 2


def level_for_xp(xp: int) -> int:
    """Level for a total xp amount, can jump several levels at once."""
    level = 1

    while level < MAX_LEVEL and xp >= xp_to_reach(level + 1):
        level += 1

    return level


def xp_progress(xp: int) -> dict:
    """Where a player sits inside the current level, for the profile screen."""
    level = level_for_xp(xp)

    current = xp_to_reach(level)
    following = xp_to_reach(level + 1)

    if level >= MAX_LEVEL:
        return {
            "level": level,
            "xp_into_level": 0,
            "xp_needed": 0,
            "is_max_level": True,
        }

    return {
        "level": level,
        "xp_into_level": xp - current,
        "xp_needed": following - current,
        "is_max_level": False,
    }


# ==================================================
# Retrieval
# ==================================================

def _as_player(document: dict) -> dict:
    """Shape a raw document the way handlers expect it."""
    return {
        "id": document["_id"],
        "telegram_id": document["telegram_id"],
        "username": document.get("username"),
        "first_name": document.get("first_name"),
        "level": document.get("level", 1),
        "xp": document.get("xp", 0),
        "total_jobs": document.get("total_jobs", 0),
        "total_earned": document.get("total_earned", 0),
        "balance": document.get("balance", 0),
        "created_at": document.get("created_at"),
    }


async def get_player(telegram_id: int) -> Optional[dict]:
    document = await mongo.players().find_one(
        {"telegram_id": telegram_id}
    )

    if document is None:
        return None

    return _as_player(document)


async def get_player_by_id(player_id) -> Optional[dict]:
    document = await mongo.players().find_one({"_id": player_id})

    if document is None:
        return None

    return _as_player(document)


# ==================================================
# Creation
# ==================================================

async def create_player(
    telegram_id: int,
    username: Optional[str],
    first_name: str,
) -> dict:
    """Create a player with their starting capital already logged."""
    document = {
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name,
        "level": 1,
        "xp": 0,
        "total_jobs": 0,
        "total_earned": 0,
        "balance": STARTING_BALANCE,
        "created_at": _now(),
        "updated_at": _now(),
    }

    try:
        result = await mongo.players().insert_one(document)

    except DuplicateKeyError as error:
        raise PlayerAlreadyExists(
            f"player {telegram_id} already exists"
        ) from error

    # the ledger has to show where the opening balance came from
    await record_transaction(
        player_id=result.inserted_id,
        amount=STARTING_BALANCE,
        balance_after=STARTING_BALANCE,
        transaction_type=TransactionType.INITIAL_BALANCE,
        description="سرمایه اولیه",
    )

    return _as_player({**document, "_id": result.inserted_id})


async def get_or_create_player(
    telegram_id: int,
    username: Optional[str],
    first_name: str,
) -> tuple[dict, bool]:
    """Returns the player and whether it was just created."""
    player = await get_player(telegram_id)

    if player is None:
        try:
            return await create_player(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            ), True

        except PlayerAlreadyExists:
            # two messages arrived at once, the other one won
            player = await get_player(telegram_id)

    # telegram names change, keep ours current
    if (
        player["username"] != username
        or player["first_name"] != first_name
    ):
        await mongo.players().update_one(
            {"telegram_id": telegram_id},
            {
                "$set": {
                    "username": username,
                    "first_name": first_name,
                    "updated_at": _now(),
                }
            },
        )

        player["username"] = username
        player["first_name"] = first_name

    return player, False


# ==================================================
# Progression
# ==================================================

async def add_xp(telegram_id: int, amount: int) -> dict:
    """Give xp and recompute the level from the new total."""
    if amount < 0:
        raise ValueError("xp amount cannot be negative")

    document = await mongo.players().find_one_and_update(
        {"telegram_id": telegram_id},
        {
            "$inc": {"xp": amount},
            "$set": {"updated_at": _now()},
        },
        return_document=ReturnDocument.AFTER,
    )

    if document is None:
        raise PlayerNotFound(
            f"no player with telegram_id {telegram_id}"
        )

    return await sync_level(telegram_id, document)


async def sync_level(
    telegram_id: int,
    document: Optional[dict] = None,
) -> dict:
    """Level is derived from xp, so fix it whenever xp moved."""
    if document is None:
        document = await mongo.players().find_one(
            {"telegram_id": telegram_id}
        )

        if document is None:
            raise PlayerNotFound(
                f"no player with telegram_id {telegram_id}"
            )

    old_level = document.get("level", 1)
    new_level = level_for_xp(document.get("xp", 0))
    if new_level == old_level:
        return {
            "player": _as_player(document),
            "old_level": old_level,
            "new_level": new_level,
            "leveled_up": False,
        }

    await mongo.players().update_one(
        {"telegram_id": telegram_id},
        {"$set": {"level": new_level, "updated_at": _now()}},
    )

    document = {**document, "level": new_level}

    return {
        "player": _as_player(document),
        "old_level": old_level,
        "new_level": new_level,
        "leveled_up": new_level > old_level,
    }
