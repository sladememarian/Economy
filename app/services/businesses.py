from dataclasses import dataclass


@dataclass(frozen=True)
class Business:
    id: str
    name: str
    description: str
    emoji: str
    price: int
    income_per_hour: int
    required_level: int
    max_level: int = 10
    upgrade_multiplier: float = 1.5
    income_multiplier: float = 1.0


BUSINESSES = {
    "fast_food": Business(
        id="fast_food",
        name="فست‌فود",
        description="یک کسب‌وکار غذایی با درآمد پایدار.",
        emoji="🍔",
        price=5_000,
        income_per_hour=250,
        required_level=1,
        max_level=10,
        upgrade_multiplier=1.5,
        income_multiplier=1.0,
    ),
    "cafe": Business(
        id="cafe",
        name="کافه",
        description="کافه‌ای با درآمد مناسب و قابل توسعه.",
        emoji="☕",
        price=15_000,
        income_per_hour=800,
        required_level=2,
        max_level=10,
        upgrade_multiplier=1.6,
        income_multiplier=1.0,
    ),
    "repair_shop": Business(
        id="repair_shop",
        name="تعمیرگاه",
        description="تعمیرگاهی با درآمد بالا برای سرمایه‌گذاران حرفه‌ای.",
        emoji="🔧",
        price=40_000,
        income_per_hour=2_500,
        required_level=5,
        max_level=10,
        upgrade_multiplier=1.7,
        income_multiplier=1.0,
    ),
}


def get_all_businesses() -> dict[str, Business]:
    return BUSINESSES


def get_business_info(
    business_type: str,
) -> Business | None:
    return BUSINESSES.get(business_type)


def get_upgrade_price(
    business: Business,
    current_level: int,
) -> int:
    if current_level < 1:
        raise ValueError("current_level must be positive")

    if current_level >= business.max_level:
        raise ValueError("business is already at max level")

    return max(
        1,
        round(
            business.price
            * (
                business.upgrade_multiplier
                ** current_level
            )
        ),
    )


def get_income_per_hour(
    business: Business,
    level: int,
) -> int:
    if level < 1:
        raise ValueError("level must be positive")

    return max(
        0,
        round(
            business.income_per_hour
            * business.income_multiplier
            * level
        ),
    )