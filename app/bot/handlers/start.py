from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main import main_menu
from app.services.player import create_player, get_player


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    telegram_id = message.from_user.id

    player = await get_player(telegram_id)

    # بازیکن جدید
    if player is None:
        player = await create_player(
            telegram_id=telegram_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )

        await message.answer(
            "🎉 <b>به امپراتوری خوش اومدی!</b>\n\n"
            f"👤 بازیکن: <b>{player['first_name']}</b>\n"
            "🪙 سرمایه اولیه: <b>۱۰٬۰۰۰ سکه</b>\n"
            "⭐ سطح: <b>۱</b>\n"
            "⚡ تجربه: <b>۰</b>\n\n"
            "از اینجا ساختن امپراتوریت رو شروع می‌کنی! 🏛",
            reply_markup=main_menu(),
        )

        return

    # بازیکن قبلی
    await message.answer(
        "🏛 <b>امپراتوری</b>\n\n"
        f"👤 {player['first_name']}\n"
        f"⭐ سطح: <b>{player['level']}</b>\n"
        f"⚡ تجربه: <b>{player['xp']}</b>\n\n"
        f"🪙 موجودی: <b>{player['balance']:,}</b> سکه\n\n"
        "چه کاری می‌خوای انجام بدی؟",
        reply_markup=main_menu(),
    )