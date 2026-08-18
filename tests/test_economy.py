import pytest

from app.database import mongo
from app.services import economy
from app.services.economy import (
    InsufficientFunds,
    InvalidAmount,
    PlayerNotFound,
    SelfTransfer,
    TransactionType,
)


# ==================================================
# Reading
# ==================================================

async def test_get_balance_returns_starting_balance(new_player):
    player = await new_player()

    assert await economy.get_balance(player["telegram_id"]) == 10_000


async def test_get_wallet_exposes_player_and_balance(new_player):
    player = await new_player()

    wallet = await economy.get_wallet(player["telegram_id"])

    assert wallet["player_id"] == player["id"]
    assert wallet["telegram_id"] == player["telegram_id"]
    assert wallet["balance"] == 10_000


async def test_get_balance_unknown_player(database):
    with pytest.raises(PlayerNotFound):
        await economy.get_balance(999_999)


# ==================================================
# Adding money
# ==================================================

async def test_add_money_increases_balance(new_player):
    player = await new_player()

    new_balance = await economy.add_money(
        telegram_id=player["telegram_id"],
        amount=500,
        transaction_type=TransactionType.JOB_REWARD,
    )

    assert new_balance == 10_500
    assert await economy.get_balance(player["telegram_id"]) == 10_500


async def test_add_money_records_transaction(new_player):
    player = await new_player()

    await economy.add_money(
        telegram_id=player["telegram_id"],
        amount=250,
        transaction_type=TransactionType.JOB_REWARD,
        description="دستمزد",
    )

    transactions = await economy.get_transactions(player["telegram_id"])
    latest = transactions[0]

    assert latest["amount"] == 250
    assert latest["balance_after"] == 10_250
    assert latest["transaction_type"] == TransactionType.JOB_REWARD
    assert latest["description"] == "دستمزد"
    assert latest["player_id"] == player["id"]


async def test_add_money_can_update_player_fields_at_once(new_player):
    player = await new_player()

    await economy.add_money(
        telegram_id=player["telegram_id"],
        amount=100,
        transaction_type=TransactionType.JOB_REWARD,
        also_inc={"xp": 15, "total_jobs": 1},
        also_set={"level": 3},
    )

    document = await mongo.players().find_one(
        {"telegram_id": player["telegram_id"]}
    )

    assert document["balance"] == 10_100
    assert document["xp"] == 15
    assert document["total_jobs"] == 1
    assert document["level"] == 3


@pytest.mark.parametrize("amount", [0, -1, -500])
async def test_add_money_rejects_non_positive(new_player, amount):
    player = await new_player()

    with pytest.raises(InvalidAmount):
        await economy.add_money(player["telegram_id"], amount)

    assert await economy.get_balance(player["telegram_id"]) == 10_000


@pytest.mark.parametrize("amount", [1.5, "100", None, True])
async def test_add_money_rejects_non_integer(new_player, amount):
    player = await new_player()

    with pytest.raises(InvalidAmount):
        await economy.add_money(player["telegram_id"], amount)


async def test_add_money_unknown_player(database):
    with pytest.raises(PlayerNotFound):
        await economy.add_money(999_999, 100)


# ==================================================
# Removing money
# ==================================================

async def test_remove_money_decreases_balance(new_player):
    player = await new_player()

    new_balance = await economy.remove_money(
        telegram_id=player["telegram_id"],
        amount=4_000,
        transaction_type=TransactionType.BUSINESS_PURCHASE,
    )

    assert new_balance == 6_000
    assert await economy.get_balance(player["telegram_id"]) == 6_000


async def test_remove_money_records_negative_amount(new_player):
    player = await new_player()

    await economy.remove_money(
        telegram_id=player["telegram_id"],
        amount=1_000,
        transaction_type=TransactionType.BUSINESS_PURCHASE,
        description="خرید",
    )

    latest = (await economy.get_transactions(player["telegram_id"]))[0]

    assert latest["amount"] == -1_000
    assert latest["balance_after"] == 9_000


async def test_remove_money_can_spend_whole_balance(new_player):
    player = await new_player()

    assert await economy.remove_money(player["telegram_id"], 10_000) == 0


async def test_remove_money_insufficient_funds(new_player):
    player = await new_player()

    with pytest.raises(InsufficientFunds) as error:
        await economy.remove_money(player["telegram_id"], 10_001)

    assert error.value.balance == 10_000
    assert error.value.required == 10_001
    assert error.value.missing == 1


async def test_insufficient_funds_leaves_balance_untouched(new_player):
    player = await new_player()

    with pytest.raises(InsufficientFunds):
        await economy.remove_money(player["telegram_id"], 50_000)

    assert await economy.get_balance(player["telegram_id"]) == 10_000


async def test_insufficient_funds_writes_no_transaction(new_player):
    player = await new_player()

    before = len(await economy.get_transactions(player["telegram_id"]))

    with pytest.raises(InsufficientFunds):
        await economy.remove_money(player["telegram_id"], 50_000)

    after = len(await economy.get_transactions(player["telegram_id"]))

    assert before == after


@pytest.mark.parametrize("amount", [0, -100])
async def test_remove_money_rejects_non_positive(new_player, amount):
    player = await new_player()

    with pytest.raises(InvalidAmount):
        await economy.remove_money(player["telegram_id"], amount)


# ==================================================
# Transactions
# ==================================================

async def test_signup_creates_initial_balance_transaction(new_player):
    player = await new_player()

    transactions = await economy.get_transactions(player["telegram_id"])

    assert len(transactions) == 1
    assert transactions[0]["transaction_type"] == TransactionType.INITIAL_BALANCE
    assert transactions[0]["amount"] == 10_000
    assert transactions[0]["balance_after"] == 10_000


async def test_get_transactions_is_newest_first(new_player):
    player = await new_player()

    for amount in (100, 200, 300):
        await economy.add_money(
            player["telegram_id"],
            amount,
            TransactionType.JOB_REWARD,
        )

    transactions = await economy.get_transactions(player["telegram_id"])

    assert [t["amount"] for t in transactions] == [300, 200, 100, 10_000]


async def test_get_transactions_respects_limit(new_player):
    player = await new_player()

    for _ in range(5):
        await economy.add_money(
            player["telegram_id"],
            10,
            TransactionType.JOB_REWARD,
        )

    assert len(await economy.get_transactions(player["telegram_id"], limit=2)) == 2


async def test_get_transactions_rejects_bad_limit(new_player):
    player = await new_player()

    with pytest.raises(InvalidAmount):
        await economy.get_transactions(player["telegram_id"], limit=0)


async def test_transactions_are_isolated_per_player(new_player):
    first = await new_player(telegram_id=1, username="a", first_name="A")
    second = await new_player(telegram_id=2, username="b", first_name="B")

    await economy.add_money(
        first["telegram_id"],
        777,
        TransactionType.JOB_REWARD,
    )

    assert len(await economy.get_transactions(first["telegram_id"])) == 2
    assert len(await economy.get_transactions(second["telegram_id"])) == 1


# ==================================================
# Transfers
# ==================================================

async def test_transfer_money_moves_between_players(new_player):
    sender = await new_player(telegram_id=1, username="a", first_name="A")
    receiver = await new_player(telegram_id=2, username="b", first_name="B")

    result = await economy.transfer_money(
        from_telegram_id=sender["telegram_id"],
        to_telegram_id=receiver["telegram_id"],
        amount=2_500,
    )

    assert result["amount"] == 2_500
    assert result["sender_balance"] == 7_500
    assert result["receiver_balance"] == 12_500

    assert await economy.get_balance(sender["telegram_id"]) == 7_500
    assert await economy.get_balance(receiver["telegram_id"]) == 12_500


async def test_transfer_records_both_sides(new_player):
    sender = await new_player(telegram_id=1, username="a", first_name="A")
    receiver = await new_player(telegram_id=2, username="b", first_name="B")

    await economy.transfer_money(
        sender["telegram_id"],
        receiver["telegram_id"],
        1_000,
    )

    sent = (await economy.get_transactions(sender["telegram_id"]))[0]
    received = (await economy.get_transactions(receiver["telegram_id"]))[0]

    assert sent["transaction_type"] == TransactionType.TRANSFER_OUT
    assert sent["amount"] == -1_000
    assert sent["related_player_id"] == receiver["id"]

    assert received["transaction_type"] == TransactionType.TRANSFER_IN
    assert received["amount"] == 1_000
    assert received["related_player_id"] == sender["id"]


async def test_transfer_more_than_balance_fails(new_player):
    sender = await new_player(telegram_id=1, username="a", first_name="A")
    receiver = await new_player(telegram_id=2, username="b", first_name="B")

    with pytest.raises(InsufficientFunds):
        await economy.transfer_money(
            sender["telegram_id"],
            receiver["telegram_id"],
            20_000,
        )

    assert await economy.get_balance(sender["telegram_id"]) == 10_000
    assert await economy.get_balance(receiver["telegram_id"]) == 10_000


async def test_transfer_to_self_is_rejected(new_player):
    player = await new_player()

    with pytest.raises(SelfTransfer):
        await economy.transfer_money(
            player["telegram_id"],
            player["telegram_id"],
            100,
        )

    assert await economy.get_balance(player["telegram_id"]) == 10_000


async def test_transfer_to_unknown_player_keeps_money(new_player):
    sender = await new_player()

    with pytest.raises(PlayerNotFound):
        await economy.transfer_money(
            sender["telegram_id"],
            999_999,
            500,
        )

    assert await economy.get_balance(sender["telegram_id"]) == 10_000


async def test_transfer_refunds_sender_when_credit_fails(new_player, monkeypatch):
    sender = await new_player(telegram_id=1, username="a", first_name="A")
    receiver = await new_player(telegram_id=2, username="b", first_name="B")

    real_add_money = economy.add_money

    async def failing_add_money(telegram_id, amount, *args, **kwargs):
        # blow up only on the credit half of the transfer
        if telegram_id == receiver["telegram_id"]:
            raise RuntimeError("mongo went away")

        return await real_add_money(telegram_id, amount, *args, **kwargs)

    monkeypatch.setattr(economy, "add_money", failing_add_money)

    with pytest.raises(RuntimeError):
        await economy.transfer_money(
            sender["telegram_id"],
            receiver["telegram_id"],
            3_000,
        )

    # the debit must have been given back
    assert await economy.get_balance(sender["telegram_id"]) == 10_000
    assert await economy.get_balance(receiver["telegram_id"]) == 10_000

    refund = (await economy.get_transactions(sender["telegram_id"]))[0]

    assert refund["transaction_type"] == TransactionType.TRANSFER_REFUND
    assert refund["amount"] == 3_000
