import time

import aiosqlite

from app.database.db import DATABASE_PATH
from app.services.jobs import JOBS


async def do_work(
    telegram_id: int,
    job_id: str,
) -> tuple[bool, str]:

    job = JOBS.get(job_id)

    if job is None:
        return False, "❌ این شغل وجود ندارد."

    now = int(time.time())

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                p.id AS player_id,
                p.level,
                p.xp,
                p.total_jobs,
                p.total_earned,
                w.id AS wallet_id,
                w.balance
            FROM players p
            JOIN wallets w ON w.player_id = p.id
            WHERE p.telegram_id = ?
            """,
            (telegram_id,),
        )

        player = await cursor.fetchone()

        if player is None:
            return False, "❌ بازیکن پیدا نشد."

        # بررسی سطح شغل
        if player["level"] < job.required_level:
            return False, (
                f"🔒 <b>{job.name}</b> قفل است.\n\n"
                f"⭐ برای باز کردن این شغل به سطح "
                f"<b>{job.required_level}</b> نیاز داری."
            )

        # بررسی Cooldown
        cursor = await db.execute(
            """
            SELECT last_work_at
            FROM job_cooldowns
            WHERE player_id = ?
              AND job_id = ?
            """,
            (player["player_id"], job.id),
        )

        cooldown = await cursor.fetchone()

        if cooldown:
            elapsed = now - cooldown["last_work_at"]

            if elapsed < job.cooldown:
                remaining = job.cooldown - elapsed

                return False, (
                    f"⏳ هنوز نمی‌تونی دوباره کار کنی.\n\n"
                    f"💼 شغل: {job.emoji} {job.name}\n"
                    f"⏱ زمان باقی‌مانده: <b>{remaining} ثانیه</b>"
                )

        # محاسبه اطلاعات جدید
        new_balance = player["balance"] + job.reward
        new_xp = player["xp"] + job.xp

        new_total_jobs = player["total_jobs"] + 1
        new_total_earned = player["total_earned"] + job.reward

        old_level = player["level"]
        new_level = old_level

        # Level Up
        xp_required = old_level * 100

        if new_xp >= xp_required:
            new_level += 1

        # آپدیت Wallet
        await db.execute(
            """
            UPDATE wallets
            SET balance = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                new_balance,
                player["wallet_id"],
            ),
        )

        # آپدیت Player
        await db.execute(
            """
            UPDATE players
            SET xp = ?,
                level = ?,
                total_jobs = ?,
                total_earned = ?
            WHERE id = ?
            """,
            (
                new_xp,
                new_level,
                new_total_jobs,
                new_total_earned,
                player["player_id"],
            ),
        )

        # ثبت تراکنش
        await db.execute(
            """
            INSERT INTO transactions (
                wallet_id,
                amount,
                balance_after,
                transaction_type,
                description
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                player["wallet_id"],
                job.reward,
                new_balance,
                "JOB_REWARD",
                f"دستمزد {job.name}",
            ),
        )

        # ثبت Cooldown
        await db.execute(
            """
            INSERT INTO job_cooldowns (
                player_id,
                job_id,
                last_work_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(player_id, job_id)
            DO UPDATE SET last_work_at = excluded.last_work_at
            """,
            (
                player["player_id"],
                job.id,
                now,
            ),
        )

        await db.commit()

    message = (
        f"{job.emoji} <b>{job.name}</b>\n\n"
        f"✅ کار با موفقیت انجام شد!\n\n"
        f"💰 درآمد: <b>+{job.reward:,}</b> 🪙\n"
        f"⚡ تجربه: <b>+{job.xp}</b>\n"
        f"💳 موجودی: <b>{new_balance:,}</b> 🪙\n"
        f"📊 تعداد کارها: <b>{new_total_jobs}</b>"
    )

    if new_level > old_level:
        message += (
            f"\n\n🎉 <b>Level Up!</b>\n"
            f"⭐ سطح جدید: <b>{new_level}</b>"
        )

    return True, message