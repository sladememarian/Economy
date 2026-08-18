from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def profile_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 بروزرسانی",
                    callback_data="profile",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 برگشت",
                    callback_data="main_menu",
                ),
            ],
        ]
    )