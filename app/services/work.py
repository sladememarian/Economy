import time

from pymongo.errors import DuplicateKeyError

from app.database import mongo
from app.services import economy, player as player_service
from app.services.jobs import JOBS


# xp drops off once a job is far below your level
XP_FALLOFF_PER_LEVEL = 0.1
MIN_XP_MULTIPLIER = 0.25


def calculate_xp(job_xp: int, player_level: int, required_level: int) -> int:
    """Outgrown jobs teach you less, but always at least 1 xp."""
    gap = max(0, player_level - required_level)

    multiplier = max(
        MIN_XP_MULTIPLIER,
        1 - XP_FALLOFF_PER_LEVEL * gap,
    )

    return max(1, round(job_xp * multiplier))


def format_remaining(seconds: int) -> str:
    minutes, seconds = divmod(seconds, 60)

    if minutes:
        return f"{minutes} دقیقه و {seconds} ثانیه"

    return f"{seconds} ثانیه"


# ==================================================
# Cooldowns
# ==================================================

async def get_cooldown_remaining(
    player_id,
    job_id: str,
    cooldown: int,
    now: int,
) -> int:
    """Seconds left before this job can be done again, 0 when ready."""
    document = await mongo.job_cooldowns().find_one(
        {"player_id": player_id, "job_id": job_id}
    )

    if document is None:
        return 0

    elapsed = now - document.get("last_work_at", 0)

    if elapsed >= cooldown:
        return 0

    return cooldown - elapsed


async def claim_cooldown(
    player_id,
    job_id: str,
    cooldown: int,
    now: int,
) -> bool:
    """Stamp the cooldown, but only if the job is really ready.

    Claiming before paying means two fast clicks cannot both earn money.
    """
    result = await mongo.job_cooldowns().update_one(
        {
            "player_id": player_id,
            "job_id": job_id,
            "last_work_at": {"$lte": now - cooldown},
        },
        {"$set": {"last_work_at": now}},
    )

    if result.matched_count == 1:
        return True

    # nothing matched, so either the job is on cooldown or never worked
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
        # a row already exists, which means it was still cooling down
        return False


# ==================================================
# Working
# ==================================================

async def do_work(
    telegram_id: int,
    job_id: str,
) -> tuple[bool, str]:

    job = JOBS.get(job_id)

    if job is None:
        return False, "❌ این شغل وجود ندارد."

    now = int(time.time())

    player = await player_service.get_player(telegram_id)

    if player is None:
        return False, "❌ بازیکن پیدا نشد."

    # بررسی سطح شغل
    if player["level"] < job.required_level:
        return False, (
            f"🔒 <b>{job.name}</b> قفل است.\n\n"
            f"⭐ برای باز کردن این شغل به سطح "
            f"<b>{job.required_level}</b> نیاز داری."
        )

    # بررسی Cooldown برای نشان دادن زمان باقی‌مانده
    remaining = await get_cooldown_remaining(
        player_id=player["id"],
        job_id=job.id,
        cooldown=job.cooldown,
        now=now,
    )

    if remaining > 0:
        return False, (
            f"⏳ هنوز نمی‌تونی دوباره کار کنی.\n\n"
            f"💼 شغل: {job.emoji} {job.name}\n"
            f"⏱ زمان باقی‌مانده: "
            f"<b>{format_remaining(remaining)}</b>"
        )

    # گرفتن قفل Cooldown قبل از پرداخت
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

    # پول، تجربه و آمار در یک نوشتن اتمیک، پس هیچ‌وقت ناهمخوان نمی‌شوند
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

    # سطح از روی تجربه محاسبه می‌شود
    progress = await player_service.sync_level(telegram_id)

    message = (
        f"{job.emoji} <b>{job.name}</b>\n\n"
        f"✅ کار با موفقیت انجام شد!\n\n"
        f"💰 درآمد: <b>+{job.reward:,}</b> 🪙\n"
        f"⚡ تجربه: <b>+{earned_xp}</b>\n"
        f"💳 موجودی: <b>{new_balance:,}</b> 🪙\n"
        f"📊 تعداد کارها: "
        f"<b>{progress['player']['total_jobs']}</b>"
    )

    if progress["leveled_up"]:
        message += (
            f"\n\n🎉 <b>Level Up!</b>\n"
            f"⭐ سطح جدید: <b>{progress['new_level']}</b>"
        )

    return True, message
