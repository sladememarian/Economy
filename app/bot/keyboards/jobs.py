from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.jobs import JOBS


def jobs_menu() -> InlineKeyboardMarkup:
    buttons = []

    for job in JOBS.values():
        buttons.append([
            InlineKeyboardButton(
                text=f"{job.emoji} {job.name}",
                callback_data=f"job:{job.id}",
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