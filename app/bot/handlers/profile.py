from aiogram import Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.profile import profile_menu
from app.services.profile import get_profile


router = Router()


def build_profile_text(player: dict) -> str:
    level = player["level"]
    xp = player["xp"]

    xp_required = level * 100

    if xp_required > 0:
        progress = min(int((xp / xp_required) * 10), 10)
    else:
        progress = 0

    progress_bar = "🟩" * progress + "⬜" * (10 - progress)

    return (
        f"👤 <b>پروفایل {player['first_name']}</b>\n\n"
        f"⭐ سطح: <b>{level}</b>\n"
        f"⚡ تجربه: <b>{xp} / {xp_required}</b>\n"
        f"{progress_bar}\n\n"
        f"🪙 کیف پول: <b>{player['balance']:,}</b>\n"
        f"🏦 بانک: <b>0</b>\n\n"
        f"🏪 کسب‌وکارها: <b>0</b>\n"
        f"🏠 املاک: <b>0</b>\n\n"
        f"💰 ثروت خالص: <b>{player['balance']:,}</b>\n\n"
        f"📊 <b>آمار</b>\n"
        f"💼 کارهای انجام‌شده: <b>{player['total_jobs']}</b>\n"
        f"💵 درآمد کل: <b>{player['total_earned']:,}</b>"
    )


@router.callback_query(lambda callback: callback.data == "profile")
async def profile_handler(callback: CallbackQuery) -> None:
    player = await get_profile(callback.from_user.id)

    await callback.answer()

    if player is None:
        await callback.message.answer(
            "❌ بازیکن پیدا نشد. ابتدا /start را بزن."
        )
        return

    await callback.message.edit_text(
        build_profile_text(player),
        reply_markup=profile_menu(),
    )