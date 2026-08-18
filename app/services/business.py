from datetime import datetime, timezone

from bson import ObjectId

from app.database import mongo
from app.services import economy
from app.services import player as player_service
from app.services.businesses import (
    BUSINESSES,
    get_income_per_hour,
    get_upgrade_price,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def buy_business(
    telegram_id: int,
    business_id: str,
) -> tuple[bool, str]:

    business = BUSINESSES.get(business_id)

    if business is None:
        return False, "❌ این کسب‌وکار وجود ندارد."

    player = await player_service.get_player(
        telegram_id
    )

    if player is None:
        return False, "❌ بازیکن پیدا نشد."

    if player["level"] < business.required_level:
        return False, (
            f"🔒 <b>{business.name}</b> قفل است.\n\n"
            f"⭐ سطح مورد نیاز: "
            f"<b>{business.required_level}</b>\n"
            f"⭐ سطح فعلی: "
            f"<b>{player['level']}</b>"
        )

    existing = await mongo.businesses().find_one(
        {
            "player_id": player["id"],
            "business_type": business.id,
        }
    )

    if existing is not None:
        return False, (
            f"⚠️ تو قبلاً <b>{business.name}</b> رو خریدی."
        )

    try:
        new_balance = await economy.remove_money(
            telegram_id=telegram_id,
            amount=business.price,
            transaction_type=(
                economy.TransactionType.BUSINESS_PURCHASE
            ),
            description=f"خرید {business.name}",
        )

    except economy.InsufficientFunds as error:
        return False, (
            "❌ پول کافی نداری.\n\n"
            f"💳 موجودی: <b>{error.balance:,}</b> 🪙\n"
            f"💰 قیمت: <b>{error.required:,}</b> 🪙\n"
            f"📉 کمبود: <b>{error.missing:,}</b> 🪙"
        )

    now = _now()

    document = {
        "player_id": player["id"],
        "telegram_id": telegram_id,
        "business_type": business.id,
        "level": 1,
        "purchased_at": now,
        "last_income_at": now,
        "created_at": now,
        "updated_at": now,
    }

    try:
        await mongo.businesses().insert_one(document)

    except Exception:
        await economy.add_money(
            telegram_id=telegram_id,
            amount=business.price,
            transaction_type=economy.TransactionType.ADJUSTMENT,
            description=(
                f"بازگشت وجه خرید ناموفق {business.name}"
            ),
        )
        raise

    income = get_income_per_hour(
        business,
        1,
    )

    return True, (
        "🎉 <b>خرید موفق!</b>\n\n"
        f"{business.emoji} "
        f"<b>{business.name}</b>\n"
        f"📝 {business.description}\n\n"
        "⭐ سطح: <b>1</b>\n"
        f"💸 هزینه خرید: "
        f"<b>{business.price:,}</b> 🪙\n"
        f"💰 درآمد ساعتی: "
        f"<b>{income:,}</b> 🪙\n"
        f"💳 موجودی فعلی: "
        f"<b>{new_balance:,}</b> 🪙"
    )


async def upgrade_business(
    telegram_id: int,
    business_id: ObjectId,
) -> tuple[bool, str]:

    player = await player_service.get_player(
        telegram_id
    )

    if player is None:
        return False, "❌ بازیکن پیدا نشد."

    document = await mongo.businesses().find_one(
        {
            "_id": business_id,
            "player_id": player["id"],
        }
    )

    if document is None:
        return False, "❌ کسب‌وکار پیدا نشد."

    business = BUSINESSES.get(
        document.get("business_type")
    )

    if business is None:
        return False, "❌ نوع کسب‌وکار نامعتبر است."

    current_level = document.get(
        "level",
        1,
    )

    if current_level >= business.max_level:
        return False, (
            f"🏆 <b>{business.name}</b>\n\n"
            f"این کسب‌وکار به حداکثر سطح "
            f"<b>{business.max_level}</b> رسیده است."
        )

    upgrade_price = get_upgrade_price(
        business,
        current_level,
    )

    new_level = current_level + 1

    updated = await mongo.businesses().update_one(
        {
            "_id": business_id,
            "player_id": player["id"],
            "level": current_level,
        },
        {
            "$set": {
                "level": new_level,
                "updated_at": _now(),
            }
        },
    )

    if updated.modified_count != 1:
        return (
            False,
            "⏳ این کسب‌وکار همزمان توسط درخواست دیگری تغییر کرد.",
        )

    try:
        new_balance = await economy.remove_money(
            telegram_id=telegram_id,
            amount=upgrade_price,
            transaction_type=(
                economy.TransactionType.BUSINESS_UPGRADE
            ),
            description=(
                f"ارتقای {business.name} "
                f"به سطح {new_level}"
            ),
        )

    except economy.InsufficientFunds as error:
        await mongo.businesses().update_one(
            {
                "_id": business_id,
                "player_id": player["id"],
                "level": new_level,
            },
            {
                "$set": {
                    "level": current_level,
                    "updated_at": _now(),
                }
            },
        )

        return False, (
            "❌ موجودی کافی نیست.\n\n"
            f"💳 موجودی: <b>{error.balance:,}</b> 🪙\n"
            f"💰 هزینه ارتقا: "
            f"<b>{error.required:,}</b> 🪙\n"
            f"📉 کمبود: <b>{error.missing:,}</b> 🪙"
        )

    new_income = get_income_per_hour(
        business,
        new_level,
    )

    return True, (
        "⬆️ <b>کسب‌وکار ارتقا پیدا کرد!</b>\n\n"
        f"{business.emoji} "
        f"<b>{business.name}</b>\n"
        f"📝 {business.description}\n\n"
        f"⭐ سطح جدید: <b>{new_level}</b>\n"
        f"💰 درآمد ساعتی جدید: "
        f"<b>{new_income:,}</b> 🪙\n\n"
        f"💸 هزینه ارتقا: "
        f"<b>{upgrade_price:,}</b> 🪙\n"
        f"💳 موجودی: "
        f"<b>{new_balance:,}</b> 🪙"
    )