from datetime import datetime, timezone

from bson import ObjectId

from app.database import mongo
from app.services import economy
from app.services import player as player_service
from app.services.businesses import (
    BUSINESSES,
    get_income_per_hour,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def calculate_income(
    business_type: str,
    level: int,
    last_income_at: datetime | None,
) -> int:

    business = BUSINESSES.get(
        business_type
    )

    if business is None:
        return 0

    if last_income_at is None:
        return 0

    if last_income_at.tzinfo is None:
        last_income_at = last_income_at.replace(
            tzinfo=timezone.utc
        )

    elapsed_seconds = (
        _now() - last_income_at
    ).total_seconds()

    if elapsed_seconds <= 0:
        return 0

    hours = int(
        elapsed_seconds // 3600
    )

    if hours <= 0:
        return 0

    return hours * get_income_per_hour(
        business,
        level,
    )


async def get_my_businesses(
    telegram_id: int,
) -> list[dict]:

    player = await player_service.get_player(
        telegram_id
    )

    if player is None:
        return []

    cursor = (
        mongo.businesses()
        .find(
            {
                "player_id": player["id"],
            }
        )
        .sort(
            [
                ("created_at", 1),
                ("_id", 1),
            ]
        )
    )

    result = []

    async for document in cursor:
        business = BUSINESSES.get(
            document.get("business_type")
        )

        if business is None:
            continue

        level = document.get(
            "level",
            1,
        )

        result.append(
            {
                "id": document["_id"],
                "business_type": document[
                    "business_type"
                ],
                "name": business.name,
                "description": business.description,
                "emoji": business.emoji,
                "level": level,
                "max_level": business.max_level,
                "income_per_hour": get_income_per_hour(
                    business,
                    level,
                ),
                "pending_income": calculate_income(
                    business_type=document[
                        "business_type"
                    ],
                    level=level,
                    last_income_at=document.get(
                        "last_income_at"
                    ),
                ),
                "price": business.price,
                "purchased_at": document.get(
                    "purchased_at"
                ),
                "last_income_at": document.get(
                    "last_income_at"
                ),
            }
        )

    return result


async def collect_business_income(
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

    level = document.get(
        "level",
        1,
    )

    last_income_at = document.get(
        "last_income_at"
    )

    income = calculate_income(
        business_type=document["business_type"],
        level=level,
        last_income_at=last_income_at,
    )

    if income <= 0:
        return False, (
            "⏳ <b>هنوز درآمدی برای دریافت نداری.</b>\n\n"
            f"{business.emoji} "
            f"<b>{business.name}</b>\n"
            f"⭐ سطح: <b>{level}</b>\n"
            f"💰 درآمد ساعتی: "
            f"<b>{get_income_per_hour(business, level):,}</b> 🪙"
        )

    now = _now()

    updated = await mongo.businesses().update_one(
        {
            "_id": business_id,
            "player_id": player["id"],
            "last_income_at": last_income_at,
        },
        {
            "$set": {
                "last_income_at": now,
                "updated_at": now,
            }
        },
    )

    if updated.modified_count != 1:
        return False, (
            "⏳ درآمد این کسب‌وکار "
            "همین الان دریافت شد."
        )

    try:
        new_balance = await economy.add_money(
            telegram_id=telegram_id,
            amount=income,
            transaction_type=(
                economy.TransactionType.BUSINESS_INCOME
            ),
            description=f"درآمد {business.name}",
        )

    except Exception:
        await mongo.businesses().update_one(
            {
                "_id": business_id,
                "player_id": player["id"],
                "last_income_at": now,
            },
            {
                "$set": {
                    "last_income_at": last_income_at,
                }
            },
        )
        raise

    return True, (
        "💰 <b>درآمد دریافت شد!</b>\n\n"
        f"{business.emoji} "
        f"<b>{business.name}</b>\n"
        f"⭐ سطح: <b>{level}</b>\n\n"
        f"💵 درآمد دریافتی: "
        f"<b>+{income:,}</b> 🪙\n"
        f"💳 موجودی جدید: "
        f"<b>{new_balance:,}</b> 🪙"
    )