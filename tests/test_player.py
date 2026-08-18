import pytest

from app.database import mongo
from app.services import economy
from app.services.player import (
    MAX_LEVEL,
    STARTING_BALANCE,
    PlayerAlreadyExists,
    create_player,
    get_or_create_player,
    get_player,
    get_player_by_id,
    add_xp,
    level_for_xp,
    sync_level,
    xp_progress,
    xp_to_reach,
)


# ==================================================
# Creation
# ==================================================

async def test_create_player_returns_full_player(database):
    player = await create_player(
        telegram_id=555,
        username="pouyan",
        first_name="Pouyan",
    )

    assert player["telegram_id"] == 555
    assert player["username"] == "pouyan"
    assert player["first_name"] == "Pouyan"
    assert player["level"] == 1
    assert player["xp"] == 0
    assert player["total_jobs"] == 0
    assert player["total_earned"] == 0
    assert player["id"] is not None


async def test_new_player_starts_with_starting_balance(database):
    player = await create_player(1, "a", "A")

    assert player["balance"] == STARTING_BALANCE
    assert await economy.get_balance(1) == STARTING_BALANCE


async def test_create_player_logs_initial_balance(database):
    await create_player(1, "a", "A")

    transactions = await economy.get_transactions(1)

    assert len(transactions) == 1
    assert transactions[0]["transaction_type"] == economy.TransactionType.INITIAL_BALANCE
    assert transactions[0]["amount"] == STARTING_BALANCE


async def test_create_player_allows_missing_username(database):
    player = await create_player(1, None, "A")

    assert player["username"] is None


async def test_create_player_twice_is_rejected(database):
    await create_player(1, "a", "A")

    with pytest.raises(PlayerAlreadyExists):
        await create_player(1, "a", "A")


async def test_duplicate_signup_does_not_double_the_money(database):
    await create_player(1, "a", "A")

    with pytest.raises(PlayerAlreadyExists):
        await create_player(1, "a", "A")

    assert await economy.get_balance(1) == STARTING_BALANCE
    assert await mongo.players().count_documents({"telegram_id": 1}) == 1


# ==================================================
# Retrieval
# ==================================================

async def test_get_player_unknown_returns_none(database):
    assert await get_player(4242) is None


async def test_get_player_returns_created_player(database):
    created = await create_player(7, "a", "A")

    found = await get_player(7)

    assert found["id"] == created["id"]
    assert found["balance"] == STARTING_BALANCE


async def test_get_player_by_id(database):
    created = await create_player(7, "a", "A")

    found = await get_player_by_id(created["id"])

    assert found["telegram_id"] == 7


async def test_get_or_create_creates_when_missing(database):
    player, created = await get_or_create_player(9, "a", "A")

    assert created is True
    assert player["balance"] == STARTING_BALANCE


async def test_get_or_create_returns_existing(database):
    first, _ = await get_or_create_player(9, "a", "A")
    second, created = await get_or_create_player(9, "a", "A")

    assert created is False
    assert second["id"] == first["id"]
    assert await mongo.players().count_documents({}) == 1


async def test_get_or_create_refreshes_changed_name(database):
    await create_player(9, "old_name", "Old")

    player, created = await get_or_create_player(9, "new_name", "New")

    assert created is False
    assert player["username"] == "new_name"
    assert player["first_name"] == "New"

    stored = await get_player(9)

    assert stored["username"] == "new_name"
    assert stored["first_name"] == "New"


async def test_get_or_create_keeps_balance_when_refreshing(database):
    await create_player(9, "old", "Old")
    await economy.remove_money(9, 4_000)

    player, _ = await get_or_create_player(9, "new", "New")

    assert player["balance"] == 6_000


# ==================================================
# Level curve
# ==================================================

def test_xp_to_reach_first_levels():
    assert xp_to_reach(1) == 0
    assert xp_to_reach(2) == 100
    assert xp_to_reach(3) == 300
    assert xp_to_reach(4) == 600
    assert xp_to_reach(5) == 1_000


def test_each_level_costs_more_than_the_last():
    steps = [
        xp_to_reach(level + 1) - xp_to_reach(level)
        for level in range(1, 10)
    ]

    assert steps == sorted(steps)
    assert len(set(steps)) == len(steps)


@pytest.mark.parametrize(
    "xp, expected_level",
    [
        (0, 1),
        (99, 1),
        (100, 2),
        (299, 2),
        (300, 3),
        (599, 3),
        (600, 4),
        (1_000, 5),
    ],
)
def test_level_for_xp(xp, expected_level):
    assert level_for_xp(xp) == expected_level


def test_level_for_xp_is_capped():
    assert level_for_xp(10_000_000_000) == MAX_LEVEL


def test_xp_progress_inside_a_level():
    progress = xp_progress(150)

    assert progress["level"] == 2
    assert progress["xp_into_level"] == 50
    assert progress["xp_needed"] == 200
    assert progress["is_max_level"] is False


def test_xp_progress_at_max_level():
    progress = xp_progress(xp_to_reach(MAX_LEVEL))

    assert progress["level"] == MAX_LEVEL
    assert progress["is_max_level"] is True


# ==================================================
# Gaining xp
# ==================================================

async def test_add_xp_accumulates(database):
    await create_player(1, "a", "A")

    await add_xp(1, 30)
    result = await add_xp(1, 40)

    assert result["player"]["xp"] == 70
    assert result["leveled_up"] is False


async def test_add_xp_levels_up(database):
    await create_player(1, "a", "A")

    result = await add_xp(1, 100)

    assert result["leveled_up"] is True
    assert result["old_level"] == 1
    assert result["new_level"] == 2

    assert (await get_player(1))["level"] == 2


async def test_add_xp_can_jump_several_levels(database):
    await create_player(1, "a", "A")

    result = await add_xp(1, 600)

    assert result["old_level"] == 1
    assert result["new_level"] == 4
    assert result["leveled_up"] is True


async def test_add_xp_does_not_touch_balance(database):
    await create_player(1, "a", "A")

    await add_xp(1, 500)

    assert await economy.get_balance(1) == STARTING_BALANCE


async def test_add_xp_rejects_negative(database):
    await create_player(1, "a", "A")

    with pytest.raises(ValueError):
        await add_xp(1, -10)


async def test_add_xp_unknown_player(database):
    with pytest.raises(economy.PlayerNotFound):
        await add_xp(4242, 10)


async def test_sync_level_repairs_a_stale_level(database):
    await create_player(1, "a", "A")

    # pretend an old bug left xp and level out of step
    await mongo.players().update_one(
        {"telegram_id": 1},
        {"$set": {"xp": 1_000, "level": 1}},
    )

    result = await sync_level(1)

    assert result["new_level"] == 5
    assert (await get_player(1))["level"] == 5


async def test_sync_level_is_idempotent(database):
    await create_player(1, "a", "A")
    await add_xp(1, 300)

    result = await sync_level(1)

    assert result["leveled_up"] is False
    assert result["new_level"] == 3
