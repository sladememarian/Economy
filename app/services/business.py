import aiosqlite

from app.database.db import DATABASE_PATH
from app.services.businesses import BUSINESSES


async def buy_business(
    telegram_id: int,
    business_id: str,
) -> tuple[bool, str]:

    business = BUSINESSES.get(business_id)

    if business is None:
        return False, "❌ این کسب‌وکار وجود ندارد."

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # پیدا کردن بازیکن
        cursor = await db.execute(
            """
            SELECT
                p.id AS player_id,
                p.level,
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

        # بررسی سطح
        if player["level"] < business.required_level:
            return False, (
                f"🔒 <b>{business.name}</b> قفل است.\n\n"
                f"⭐ سطح مورد نیاز: "
                f"<b>{business.required_level}</b>\n"
                f"⭐ سطح فعلی: "
                f"<b>{player['level']}</b>"
            )

        # بررسی خرید قبلی
        cursor = await db.execute(
            """
            SELECT id
            FROM businesses
            WHERE player_id = ?
              AND business_type = ?
            """,
            (
                player["player_id"],
                business.id,
            ),
        )

        existing = await cursor.fetchone()

        if existing is not None:
            return False, (
                f"⚠️ تو قبلاً <b>{business.name}</b> رو خریدی."
            )

        # بررسی موجودی
        if player["balance"] < business.price:
            missing = business.price - player["balance"]

            return False, (
                f"❌ پول کافی نداری.\n\n"
                f"💰 قیمت: <b>{business.price:,}</b> 🪙\n"
                f"💳 موجودی: <b>{player['balance']:,}</b> 🪙\n"
                f"📉 کمبود: <b>{missing:,}</b> 🪙"
            )

        # موجودی جدید
        new_balance = player["balance"] - business.price

        # کم کردن پول
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
                -business.price,
                new_balance,
                "BUSINESS_PURCHASE",
                f"خرید {business.name}",
            ),
        )

        # ثبت کسب‌وکار
        await db.execute(
            """
            INSERT INTO businesses (
                player_id,
                business_type,
                level
            )
            VALUES (?, ?, ?)
            """,
            (
                player["player_id"],
                business.id,
                1,
            ),
        )

        await db.commit()

    return True, (
        f"🎉 <b>خرید موفق!</b>\n\n"
        f"{business.emoji} کسب‌وکار: "
        f"<b>{business.name}</b>\n"
        f"⭐ سطح: <b>1</b>\n\n"
        f"💸 هزینه خرید: "
        f"<b>{business.price:,}</b> 🪙\n"
        f"💰 درآمد ساعتی: "
        f"<b>{business.income_per_hour:,}</b> 🪙\n\n"
        f"💳 موجودی فعلی: "
        f"<b>{new_balance:,}</b> 🪙"
    )






async def upgrade_business(
    telegram_id: int,
    business_id: int,
) -> tuple[bool, str]:

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        await db.execute("BEGIN IMMEDIATE")

        try:
            cursor = await db.execute(
                """
                SELECT
                    b.id,
                    b.business_type,
                    b.level,
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

            row = await cursor.fetchone()

            if row is None:
                await db.rollback()

                return False, "❌ کسب‌وکار پیدا نشد."

            business = BUSINESSES.get(
                row["business_type"]
            )

            if business is None:
                await db.rollback()

                return False, "❌ کسب‌وکار نامعتبر است."

            current_level = row["level"]

            # هزینه ارتقا
            upgrade_price = (
                business.price
                * current_level
            )

            balance = row["balance"]

            if balance < upgrade_price:
                await db.rollback()

                return False, (
                    f"❌ موجودی کافی نیست.\n\n"
                    f"💳 موجودی: "
                    f"<b>{balance:,}</b> 🪙\n"
                    f"💰 هزینه ارتقا: "
                    f"<b>{upgrade_price:,}</b> 🪙"
                )

            new_balance = (
                balance - upgrade_price
            )

            new_level = current_level + 1

            # کم کردن پول
            await db.execute(
                """
                UPDATE wallets
                SET balance = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    new_balance,
                    row["wallet_id"],
                ),
            )

            # ارتقای کسب‌وکار
            await db.execute(
                """
                UPDATE businesses
                SET level = ?
                WHERE id = ?
                """,
                (
                    new_level,
                    business_id,
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
                    row["wallet_id"],
                    -upgrade_price,
                    new_balance,
                    "BUSINESS_UPGRADE",
                    f"ارتقای {business.name} به سطح {new_level}",
                ),
            )

            await db.commit()

            new_income = (
                business.income_per_hour
                * new_level
            )

            return True, (
                f"⬆️ <b>کسب‌وکار ارتقا پیدا کرد!</b>\n\n"
                f"{business.emoji} "
                f"<b>{business.name}</b>\n\n"
                f"⭐ سطح جدید: "
                f"<b>{new_level}</b>\n"
                f"💰 درآمد ساعتی جدید: "
                f"<b>{new_income:,}</b> 🪙\n\n"
                f"💸 هزینه ارتقا: "
                f"<b>{upgrade_price:,}</b> 🪙\n"
                f"💳 موجودی: "
                f"<b>{new_balance:,}</b> 🪙"
            )

        except Exception:
            await db.rollback()
            raise