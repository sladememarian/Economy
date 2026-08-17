from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💼 کار کردن",
                    callback_data="job",
                ),
                InlineKeyboardButton(
                    text="🏪 کسب‌وکار",
                    callback_data="business",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏦 بانک",
                    callback_data="bank",
                ),
                InlineKeyboardButton(
                    text="🛒 بازار",
                    callback_data="market",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👤 پروفایل",
                    callback_data="profile",
                ),
                InlineKeyboardButton(
                    text="🏆 رتبه‌بندی",
                    callback_data="leaderboard",
                ),
            ],
        ]
    )