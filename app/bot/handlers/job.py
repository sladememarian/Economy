from aiogram import Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.jobs import jobs_menu
from app.bot.keyboards.main import main_menu
from app.services.work import do_work


router = Router()


@router.callback_query(lambda callback: callback.data == "job")
async def jobs_handler(callback: CallbackQuery) -> None:
    await callback.answer()

    await callback.message.edit_text(
        "💼 <b>انتخاب شغل</b>\n\n"
        "یکی از شغل‌های زیر رو انتخاب کن:",
        reply_markup=jobs_menu(),
    )


@router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith("job:")
)
async def do_job_handler(callback: CallbackQuery) -> None:
    job_id = callback.data.split(":", 1)[1]

    success, text = await do_work(
        telegram_id=callback.from_user.id,
        job_id=job_id,
    )

    await callback.answer()

    await callback.message.answer(text)


@router.callback_query(lambda callback: callback.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery) -> None:
    await callback.answer()

    await callback.message.edit_text(
        f"🏛 <b>امپراتوری</b>\n\n"
        f"👤 {callback.from_user.first_name}\n\n"
        "چه کاری می‌خوای انجام بدی؟",
        reply_markup=main_menu(),
    )