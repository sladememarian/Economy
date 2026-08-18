from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.businesses import BUSINESSES


def business_menu() -> InlineKeyboardMarkup:
    buttons = []

    for business in BUSINESSES.values():
        buttons.append([
            InlineKeyboardButton(
                text=(
                    f"{business.emoji} "
                    f"{business.name} "
                    f"• {business.price:,} 🪙"
                ),
                callback_data=f"business:{business.id}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🏪 کسب‌وکارهای من",
            callback_data="my_businesses",
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            text="🔙 برگشت",
            callback_data="main_menu",
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )