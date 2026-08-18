"""Central financial API.

Every coin in the game moves through this module, nothing else should touch
a balance directly.

The wallet lives on the player document itself, so money and progression are
updated in a single atomic write and can never drift apart. A single node
MongoDB has no multi document transactions, so anything touching two players
(a transfer) refunds itself if the second half fails.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from pymongo import DESCENDING, ReturnDocument

from app.database import mongo


class EconomyError(Exception):
    """Base error for money operations."""


class PlayerNotFound(EconomyError):
    pass


class InvalidAmount(EconomyError):
    pass


class InsufficientFunds(EconomyError):
    def __init__(self, balance: int, required: int) -> None:
        self.balance = balance
        self.required = required
        self.missing = required - balance

        super().__init__(
            f"balance {balance} is short by {self.missing}"
        )


class SelfTransfer(EconomyError):
    pass


class TransactionType:
    INITIAL_BALANCE = "INITIAL_BALANCE"
    JOB_REWARD = "JOB_REWARD"
    BUSINESS_PURCHASE = "BUSINESS_PURCHASE"
    BUSINESS_UPGRADE = "BUSINESS_UPGRADE"
    BUSINESS_INCOME = "BUSINESS_INCOME"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_REFUND = "TRANSFER_REFUND"
    ADJUSTMENT = "ADJUSTMENT"


def _validate_amount(amount: int) -> int:
    # bool is an int in python, so reject it explicitly
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise InvalidAmount("amount must be a whole number of coins")

    if amount <= 0:
        raise InvalidAmount("amount must be positive")

    return amount


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ==================================================
# Reading
# ==================================================

async def get_wallet(telegram_id: int) -> dict:
    """Money view of a player."""
    player = await mongo.players().find_one(
        {"telegram_id": telegram_id},
        {"_id": 1, "telegram_id": 1, "balance": 1},
    )

    if player is None:
        raise PlayerNotFound(
            f"no player with telegram_id {telegram_id}"
        )

    return {
        "player_id": player["_id"],
        "telegram_id": player["telegram_id"],
        "balance": player.get("balance", 0),
    }


async def get_balance(telegram_id: int) -> int:
    wallet = await get_wallet(telegram_id)

    return wallet["balance"]


async def get_transactions(
    telegram_id: int,
    limit: int = 10,
) -> list[dict]:
    """Newest transactions first."""
    if limit <= 0:
        raise InvalidAmount("limit must be positive")

    wallet = await get_wallet(telegram_id)

    cursor = (
        mongo.transactions()
        .find({"player_id": wallet["player_id"]})
        .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
        .limit(limit)
    )

    return [document async for document in cursor]


# ==================================================
# Writing
# ==================================================

async def record_transaction(
    player_id: ObjectId,
    amount: int,
    balance_after: int,
    transaction_type: str,
    description: Optional[str] = None,
    related_player_id: Optional[ObjectId] = None,
) -> ObjectId:
    """Append one line to the ledger. Amount is negative when money leaves."""
    document = {
        "player_id": player_id,
        "amount": amount,
        "balance_after": balance_after,
        "transaction_type": transaction_type,
        "description": description,
        "related_player_id": related_player_id,
        "created_at": _now(),
    }

    result = await mongo.transactions().insert_one(document)

    return result.inserted_id


async def _change_balance(
    telegram_id: int,
    delta: int,
    transaction_type: str,
    description: Optional[str],
    related_player_id: Optional[ObjectId],
    also_inc: Optional[dict[str, int]],
    also_set: Optional[dict[str, Any]],
) -> int:
    """One atomic update for the balance plus any player fields, then log it."""
    increments = {"balance": delta}

    if also_inc:
        increments.update(also_inc)

    updates: dict[str, Any] = {
        "$inc": increments,
        "$set": {"updated_at": _now()},
    }

    if also_set:
        updates["$set"].update(also_set)

    query: dict[str, Any] = {"telegram_id": telegram_id}

    # the guard is what stops a wallet going negative, even under a race
    if delta < 0:
        query["balance"] = {"$gte": -delta}

    player = await mongo.players().find_one_and_update(
        query,
        updates,
        return_document=ReturnDocument.AFTER,
    )

    if player is None:
        # either the player is gone or the balance guard rejected the update
        wallet = await get_wallet(telegram_id)

        raise InsufficientFunds(
            balance=wallet["balance"],
            required=-delta,
        )

    balance_after = player["balance"]

    await record_transaction(
        player_id=player["_id"],
        amount=delta,
        balance_after=balance_after,
        transaction_type=transaction_type,
        description=description,
        related_player_id=related_player_id,
    )

    return balance_after


async def add_money(
    telegram_id: int,
    amount: int,
    transaction_type: str = TransactionType.ADJUSTMENT,
    description: Optional[str] = None,
    related_player_id: Optional[ObjectId] = None,
    also_inc: Optional[dict[str, int]] = None,
    also_set: Optional[dict[str, Any]] = None,
) -> int:
    """Credit a player and return the new balance.

    also_inc and also_set ride along in the same write, so a caller can bump
    xp or counters without a second update that could fail on its own.
    """
    amount = _validate_amount(amount)

    return await _change_balance(
        telegram_id=telegram_id,
        delta=amount,
        transaction_type=transaction_type,
        description=description,
        related_player_id=related_player_id,
        also_inc=also_inc,
        also_set=also_set,
    )


async def remove_money(
    telegram_id: int,
    amount: int,
    transaction_type: str = TransactionType.ADJUSTMENT,
    description: Optional[str] = None,
    related_player_id: Optional[ObjectId] = None,
    also_inc: Optional[dict[str, int]] = None,
    also_set: Optional[dict[str, Any]] = None,
) -> int:
    """Debit a player and return the new balance.

    Raises InsufficientFunds instead of ever letting a balance go negative.
    """
    amount = _validate_amount(amount)

    return await _change_balance(
        telegram_id=telegram_id,
        delta=-amount,
        transaction_type=transaction_type,
        description=description,
        related_player_id=related_player_id,
        also_inc=also_inc,
        also_set=also_set,
    )


async def transfer_money(
    from_telegram_id: int,
    to_telegram_id: int,
    amount: int,
    description: Optional[str] = None,
) -> dict:
    """Move money between two players."""
    amount = _validate_amount(amount)

    if from_telegram_id == to_telegram_id:
        raise SelfTransfer("cannot transfer money to yourself")

    # both players must exist before any money moves
    sender = await get_wallet(from_telegram_id)
    receiver = await get_wallet(to_telegram_id)

    sender_balance = await remove_money(
        telegram_id=from_telegram_id,
        amount=amount,
        transaction_type=TransactionType.TRANSFER_OUT,
        description=description,
        related_player_id=receiver["player_id"],
    )

    try:
        receiver_balance = await add_money(
            telegram_id=to_telegram_id,
            amount=amount,
            transaction_type=TransactionType.TRANSFER_IN,
            description=description,
            related_player_id=sender["player_id"],
        )

    except Exception:
        # no multi document transactions on a single node, so undo the debit
        await add_money(
            telegram_id=from_telegram_id,
            amount=amount,
            transaction_type=TransactionType.TRANSFER_REFUND,
            description="برگشت انتقال ناموفق",
            related_player_id=receiver["player_id"],
        )

        raise

    return {
        "amount": amount,
        "sender_balance": sender_balance,
        "receiver_balance": receiver_balance,
    }
