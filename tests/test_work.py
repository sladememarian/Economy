import time

import pytest

from app.database import mongo
from app.services import economy
from app.services.jobs import JOBS
from app.services.player import create_player, get_player
from app.services.work import (
    calculate_xp,
    do_work,
    format_remaining,
    get_cooldown_remaining,
)


WORKER = JOBS["worker"]
DRIVER = JOBS["driver"]
PROGRAMMER = JOBS["programmer"]


async def set_level(telegram_id: int, level: int) -> None:
    from app.services.player import xp_to_reach

    await mongo.players().update_one(
        {"telegram_id": telegram_id},
        {"$set": {"level": level, "xp": xp_to_reach(level)}},
    )


async def clear_cooldown(telegram_id: int, job_id: str) -> None:
    """Pretend enough time has passed to work again."""
    player = await get_player(telegram_id)

    await mongo.job_cooldowns().update_one(
        {"player_id": player["id"], "job_id": job_id},
        {"$set": {"last_work_at": 0}},
    )


# ==================================================
# XP calculation
# ==================================================

def test_xp_is_full_at_the_job_level():
    assert calculate_xp(job_xp=10, player_level=1, required_level=1) == 10


def test_xp_shrinks_as_you_outgrow_a_job():
    at_level = calculate_xp(job_xp=100, player_level=1, required_level=1)
    outgrown = calculate_xp(job_xp=100, player_level=5, required_level=1)

    assert outgrown < at_level
    assert outgrown == 60


def test_xp_never_drops_below_the_floor():
    tiny = calculate_xp(job_xp=100, player_level=99, required_level=1)

    assert tiny == 25


def test_xp_is_at_least_one():
    assert calculate_xp(job_xp=1, player_level=50, required_level=1) == 1


def test_xp_not_penalised_below_the_job_level():
    assert calculate_xp(job_xp=35, player_level=2, required_level=5) == 35


# ==================================================
# Remaining time text
# ==================================================

def test_format_remaining_seconds_only():
    assert format_remaining(30) == "30 ثانیه"


def test_format_remaining_with_minutes():
    assert format_remaining(95) == "1 دقیقه و 35 ثانیه"


# ==================================================
# Working
# ==================================================

async def test_work_pays_the_reward(database):
    await create_player(1, "a", "A")

    ok, message = await do_work(1, "worker")

    assert ok is True
    assert await economy.get_balance(1) == 10_000 + WORKER.reward
    assert f"+{WORKER.reward:,}" in message


async def test_work_gives_xp_and_counts_the_job(database):
    await create_player(1, "a", "A")

    await do_work(1, "worker")

    player = await get_player(1)

    assert player["xp"] == WORKER.xp
    assert player["total_jobs"] == 1
    assert player["total_earned"] == WORKER.reward


async def test_work_records_a_transaction(database):
    await create_player(1, "a", "A")

    await do_work(1, "worker")

    latest = (await economy.get_transactions(1))[0]

    assert latest["transaction_type"] == economy.TransactionType.JOB_REWARD
    assert latest["amount"] == WORKER.reward
    assert latest["balance_after"] == 10_000 + WORKER.reward


async def test_work_keeps_wallet_and_player_consistent(database):
    await create_player(1, "a", "A")

    for _ in range(3):
        await do_work(1, "worker")
        await clear_cooldown(1, "worker")

    player = await get_player(1)
    latest = (await economy.get_transactions(1))[0]

    # balance, the earned total and the ledger must all agree
    assert player["total_jobs"] == 3
    assert player["total_earned"] == 3 * WORKER.reward
    assert player["balance"] == 10_000 + 3 * WORKER.reward
    assert latest["balance_after"] == player["balance"]


async def test_unknown_job_is_rejected(database):
    await create_player(1, "a", "A")

    ok, message = await do_work(1, "astronaut")

    assert ok is False
    assert "وجود ندارد" in message
    assert await economy.get_balance(1) == 10_000


async def test_unknown_player_cannot_work(database):
    ok, message = await do_work(4242, "worker")

    assert ok is False
    assert "پیدا نشد" in message


async def test_job_locked_below_required_level(database):
    await create_player(1, "a", "A")

    ok, message = await do_work(1, "programmer")

    assert ok is False
    assert str(PROGRAMMER.required_level) in message
    assert await economy.get_balance(1) == 10_000


async def test_job_unlocks_at_the_required_level(database):
    await create_player(1, "a", "A")
    await set_level(1, DRIVER.required_level)

    ok, _ = await do_work(1, "driver")

    assert ok is True


# ==================================================
# Cooldown
# ==================================================

async def test_second_work_is_blocked_by_cooldown(database):
    await create_player(1, "a", "A")

    await do_work(1, "worker")
    ok, message = await do_work(1, "worker")

    assert ok is False
    assert "زمان باقی‌مانده" in message


async def test_cooldown_does_not_pay_twice(database):
    await create_player(1, "a", "A")

    await do_work(1, "worker")
    await do_work(1, "worker")

    player = await get_player(1)

    assert player["total_jobs"] == 1
    assert player["balance"] == 10_000 + WORKER.reward


async def test_work_allowed_again_after_cooldown(database):
    await create_player(1, "a", "A")

    await do_work(1, "worker")
    await clear_cooldown(1, "worker")

    ok, _ = await do_work(1, "worker")

    assert ok is True
    assert (await get_player(1))["total_jobs"] == 2


async def test_cooldowns_are_tracked_per_job(database):
    await create_player(1, "a", "A")
    await set_level(1, DRIVER.required_level)

    await do_work(1, "worker")
    ok, _ = await do_work(1, "driver")

    # a busy worker can still drive
    assert ok is True


async def test_cooldown_remaining_counts_down(database):
    player = await create_player(1, "a", "A")
    now = int(time.time())

    await mongo.job_cooldowns().insert_one(
        {
            "player_id": player["id"],
            "job_id": "worker",
            "last_work_at": now - 10,
        }
    )

    remaining = await get_cooldown_remaining(
        player_id=player["id"],
        job_id="worker",
        cooldown=WORKER.cooldown,
        now=now,
    )

    assert remaining == WORKER.cooldown - 10


async def test_cooldown_remaining_is_zero_for_a_new_job(database):
    player = await create_player(1, "a", "A")

    remaining = await get_cooldown_remaining(
        player_id=player["id"],
        job_id="worker",
        cooldown=WORKER.cooldown,
        now=int(time.time()),
    )

    assert remaining == 0


async def test_concurrent_clicks_only_pay_once(database):
    """Two clicks landing together must not both earn the reward."""
    import asyncio

    await create_player(1, "a", "A")

    results = await asyncio.gather(
        do_work(1, "worker"),
        do_work(1, "worker"),
    )

    succeeded = [ok for ok, _ in results if ok]

    assert len(succeeded) == 1
    assert (await get_player(1))["total_jobs"] == 1
    assert await economy.get_balance(1) == 10_000 + WORKER.reward


# ==================================================
# Level up through working
# ==================================================

async def test_working_eventually_levels_you_up(database):
    await create_player(1, "a", "A")

    leveled = False

    # worker gives 10 xp, level 2 needs 100
    for _ in range(10):
        ok, message = await do_work(1, "worker")

        assert ok is True

        if "Level Up" in message:
            leveled = True

        await clear_cooldown(1, "worker")

    assert leveled is True
    assert (await get_player(1))["level"] == 2


async def test_no_level_up_message_before_the_threshold(database):
    await create_player(1, "a", "A")

    ok, message = await do_work(1, "worker")

    assert ok is True
    assert "Level Up" not in message
    assert (await get_player(1))["level"] == 1


async def test_level_up_shows_the_new_level(database):
    await create_player(1, "a", "A")

    # sit one job short of level 2
    await mongo.players().update_one(
        {"telegram_id": 1},
        {"$set": {"xp": 95}},
    )

    ok, message = await do_work(1, "worker")

    assert ok is True
    assert "Level Up" in message
    assert "سطح جدید: <b>2</b>" in message


async def test_level_up_does_not_reset_xp(database):
    await create_player(1, "a", "A")

    await mongo.players().update_one(
        {"telegram_id": 1},
        {"$set": {"xp": 95}},
    )

    await do_work(1, "worker")

    assert (await get_player(1))["xp"] == 105
