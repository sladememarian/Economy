from dataclasses import dataclass


@dataclass(frozen=True)
class Business:
    id: str
    name: str
    emoji: str
    price: int
    income_per_hour: int
    required_level: int
    max_level: int = 10


BUSINESSES = {
    "fast_food": Business(
        id="fast_food",
        name="فست‌فود",
        emoji="🍔",
        price=5_000,
        income_per_hour=250,
        required_level=1,
    ),

    "cafe": Business(
        id="cafe",
        name="کافه",
        emoji="☕",
        price=15_000,
        income_per_hour=800,
        required_level=2,
    ),

    "repair_shop": Business(
        id="repair_shop",
        name="تعمیرگاه",
        emoji="🔧",
        price=40_000,
        income_per_hour=2_500,
        required_level=5,
    ),
}