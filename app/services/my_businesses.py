import aiosqlite

from app.database.db import DATABASE_PATH
from app.services.businesses import BUSINESSES


from datetime import datetime, timezone


def calculate_income(
    business_type: str,
    level: int,
    last_income_at: str,
) -> int:

    business = BUSINESSES.get(business_type)

    if business is None:
        return 0

    try:
        last_time = datetime.strptime(
            last_income_at,
            "%Y-%m-%d %H:%M:%S",
        ).replace(tzinfo=timezone.utc)

    except (ValueError, TypeError):
        return 0

    now = datetime.now(timezone.utc)

    elapsed_seconds = (
        now - last_time
    ).total_seconds()

    hours = int(elapsed_seconds // 3600)

    if hours <= 0:
        return 0

    income_per_hour = (
        business.income_per_hour * level
    )

    return hours * income_per_hour


# ==================================================
# کسب‌وکارهای بازیکن
# ==================================================

async def get_my_businesses(
    telegram_id: int,
) -> list[dict]:

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                b.id,
                b.business_type,
                b.level,
                b.purchased_at,
                b.last_income_at
            FROM businesses b
            JOIN players p
                ON p.id = b.player_id
            WHERE p.telegram_id = ?
            ORDER BY b.id ASC
            """,
            (telegram_id,),
        )

        rows = await cursor.fetchall()

        result = []

        for row in rows:

            business = BUSINESSES.get(
                row["business_type"]
            )

            if business is None:
                continue

            income = calculate_income(
                business_type=row["business_type"],
                level=row["level"],
                last_income_at=row["last_income_at"],
            )

            result.append({
                "id": row["id"],
                "business_type": row["business_type"],
                "name": business.name,
                "emoji": business.emoji,
                "level": row["level"],
                "income_per_hour": (
                    business.income_per_hour
                    * row["level"]
                ),
                "pending_income": income,
            })

        return result


# ==================================================
# دریافت درآمد
# ==================================================

async def collect_business_income(
    telegram_id: int,
    business_id: int,
) -> tuple[bool, str]:

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # جلوگیری از دریافت همزمان درآمد
        await db.execute("BEGIN IMMEDIATE")

        try:
            cursor = await db.execute(
                """
                SELECT
                    b.id,
                    b.business_type,
                    b.level,
                    b.last_income_at,
                    p.id AS player_id,
                    w.id AS wallet_id,
                    w.balance
                FROM businesses b
                JOIN players p
                    ON p.id = b.player_id
                JOIN wallets w
                    ON w.player_id = p.id
                WHERE b.id = ?
                  AND p.telegram_id = ?
                """,
                (
                    business_id,
                    telegram_id,
                ),
            )

            business_row = await cursor.fetchone()

            if business_row is None:
                await db.rollback()

                return (
                    False,
                    "❌ کسب‌وکار پیدا نشد.",
                )

            business = BUSINESSES.get(
                business_row["business_type"]
            )

            if business is None:
                await db.rollback()

                return (
                    False,
                    "❌ نوع کسب‌وکار نامعتبر است.",
                )

            # محاسبه درآمد
            income = calculate_income(
                business_type=business_row["business_type"],
                level=business_row["level"],
                last_income_at=business_row["last_income_at"],
            )
            print(
                "DEBUG COLLECT:",
                {
                    "telegram_id": telegram_id,
                    "business_id": business_id,
                    "last_income_at": business_row["last_income_at"],
                    "income": income,
                    "balance": business_row["balance"],
                }
            )

            if income <= 0:
                await db.rollback()

                return (
                    False,
                    f"⏳ <b>هنوز درآمدی برای دریافت نداری.</b>\n\n"
                    f"{business.emoji} "
                    f"<b>{business.name}</b>\n"
                    f"⭐ سطح: "
                    f"<b>{business_row['level']}</b>\n"
                    f"💰 درآمد ساعتی: "
                    f"<b>{business.income_per_hour * business_row['level']:,}</b> 🪙",
                )

            new_balance = (
                business_row["balance"] + income
            )

            # افزایش موجودی
            await db.execute(
                """
                UPDATE wallets
                SET balance = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    new_balance,
                    business_row["wallet_id"],
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
                    business_row["wallet_id"],
                    income,
                    new_balance,
                    "BUSINESS_INCOME",
                    f"درآمد {business.name}",
                ),
            )

            # مهم:
            # زمان دریافت درآمد را همین لحظه ثبت می‌کنیم
            await db.execute(
                """
                UPDATE businesses
                SET last_income_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    business_id,
                ),
            )

            await db.commit()

            return (
                True,
                f"💰 <b>درآمد دریافت شد!</b>\n\n"
                f"{business.emoji} "
                f"<b>{business.name}</b>\n"
                f"⭐ سطح: "
                f"<b>{business_row['level']}</b>\n\n"
                f"💵 درآمد دریافتی: "
                f"<b>+{income:,}</b> 🪙\n"
                f"💳 موجودی جدید: "
                f"<b>{new_balance:,}</b> 🪙",
            )

        except Exception:
            await db.rollback()
            raise