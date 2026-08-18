
import time
import math
from pymongo.errors import DuplicateKeyError

from app.database import mongo
from app.services import economy, player as player_service
from app.services.jobs import JOBS


XP_FALLOFF_PER_LEVEL = 0.1
MIN_XP_MULTIPLIER = 0.25


def calculate_xp(
    job_xp: int,
    player_level: int,
    required_level: int,
) -> int:
    gap = max(
        0,
        player_level - required_level,
    )

    multiplier = max(
        MIN_XP_MULTIPLIER,
        1 - XP_FALLOFF_PER_LEVEL * gap,
    )

    return max(
        1,
        math.ceil(job_xp * multiplier),
    )


def format_remaining(seconds: int) -> str:
    minutes, seconds = divmod(seconds, 60)

    if minutes:
        return f"{minutes} دقیقه و {seconds} ثانیه"

    return f"{seconds} ثانیه"


async def get_cooldown_remaining(
    player_id,
    job_id: str,
    cooldown: int,
    now: int,
) -> int:
    document = await mongo.job_cooldowns().find_one(
        {
            "player_id": player_id,
            "job_id": job_id,
        }
    )

    if document is None:
        return 0

    last_work_at = document.get("last_work_at", 0)
    elapsed = max(0, now - last_work_at)

    if elapsed >= cooldown:
        return 0

    return cooldown - elapsed


async def claim_cooldown(
    player_id,
    job_id: str,
    cooldown: int,
    now: int,
) -> bool:
    result = await mongo.job_cooldowns().update_one(
        {
            "player_id": player_id,
            "job_id": job_id,
            "last_work_at": {
                "$lte": now - cooldown,
            },
        },
        {
            "$set": {
                "last_work_at": now,
            }
        },
    )

    if result.matched_count == 1:
        return True

    try:
        await mongo.job_cooldowns().insert_one(
            {
                "player_id": player_id,
                "job_id": job_id,
                "last_work_at": now,
            }
        )
        return True

    except DuplicateKeyError:
        return False


async def release_cooldown(
    player_id,
    job_id: str,
    claimed_at: int,
) -> None:
    await mongo.job_cooldowns().delete_one(
        {
            "player_id": player_id,
            "job_id": job_id,
            "last_work_at": claimed_at,
        }
    )


async def do_work(
    telegram_id: int,
    job_id: str,
) -> tuple[bool, str]:

    job = JOBS.get(job_id)

    if job is None:
        return False, "❌ این شغل وجود ندارد."

    player = await player_service.get_player(
        telegram_id
    )

    if player is None:
        return False, "❌ بازیکن پیدا نشد."

    if player["level"] < job.required_level:
        return False, (
            f"🔒 <b>{job.name}</b> قفل است.\n\n"
            f"⭐ سطح مورد نیاز: "
            f"<b>{job.required_level}</b>\n"
            f"⭐ سطح فعلی: "
            f"<b>{player['level']}</b>"
        )

    now = int(time.time())

    remaining = await get_cooldown_remaining(
        player_id=player["id"],
        job_id=job.id,
        cooldown=job.cooldown,
        now=now,
    )

    if remaining > 0:
        return False, (
            "⏳ هنوز نمی‌تونی دوباره کار کنی.\n\n"
            f"💼 شغل: {job.emoji} {job.name}\n"
            f"⏱ زمان باقی‌مانده: "
            f"<b>{format_remaining(remaining)}</b>"
        )

    claimed = await claim_cooldown(
        player_id=player["id"],
        job_id=job.id,
        cooldown=job.cooldown,
        now=now,
    )

    if not claimed:
        return False, (
            f"⏳ هنوز نمی‌تونی دوباره کار کنی.\n\n"
            f"💼 شغل: {job.emoji} {job.name}"
        )

    earned_xp = calculate_xp(
        job_xp=job.xp,
        player_level=player["level"],
        required_level=job.required_level,
    )

    try:
        new_balance = await economy.add_money(
            telegram_id=telegram_id,
            amount=job.reward,
            transaction_type=economy.TransactionType.JOB_REWARD,
            description=f"دستمزد {job.name}",
            also_inc={
                "xp": earned_xp,
                "total_jobs": 1,
                "total_earned": job.reward,
            },
        )

    except Exception:
        await release_cooldown(
            player_id=player["id"],
            job_id=job.id,
            claimed_at=now,
        )
        raise

    progress = await player_service.sync_level(
        telegram_id
    )

    player_after = progress["player"]

    message = (
        f"{job.emoji} <b>{job.name}</b>\n\n"
        "✅ کار با موفقیت انجام شد!\n\n"
        f"💰 درآمد: <b>+{job.reward:,}</b> 🪙\n"
        f"⚡ تجربه: <b>+{earned_xp}</b>\n"
        f"💳 موجودی: <b>{new_balance:,}</b> 🪙\n"
        f"📊 تعداد کارها: "
        f"<b>{player_after['total_jobs']}</b>"
    )

    if progress["leveled_up"]:
        message += (
            "\n\n🎉 <b>Level Up!</b>\n"
            f"⭐ سطح جدید: "
            f"<b>{progress['new_level']}</b>"
        )

    return True, message