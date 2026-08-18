from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def my_businesses_menu(
    businesses: list[dict],
) -> InlineKeyboardMarkup:

    buttons = []

    for business in businesses:

        buttons.append([
            InlineKeyboardButton(
                text=(
                    f"{business['emoji']} "
                    f"{business['name']} "
                    f"(Lv.{business['level']})"
                ),
                callback_data=(
                    f"mybusiness:{business['id']}"
                ),
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🔙 برگشت",
            callback_data="business",
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def business_actions(
    business_id: int,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 دریافت درآمد",
                    callback_data=(
                        f"collect:{business_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬆️ ارتقا",
                    callback_data=(
                        f"upgrade:{business_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 برگشت",
                    callback_data="my_businesses",
                )
            ],
        ]
    )