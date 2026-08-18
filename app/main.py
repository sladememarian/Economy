import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from app.config import BOT_TOKEN
from app.database.db import init_database

from app.bot.handlers.start import router as start_router
from app.bot.handlers.job import router as job_router
from app.bot.handlers.profile import router as profile_router
from app.bot.handlers.business import router as business_router

PROXY_URL = "socks5://127.0.0.1:10808"


async def main() -> None:
    await init_database()

    session = AiohttpSession(
        proxy=PROXY_URL,
    )

    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )

    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(job_router)
    dp.include_router(profile_router)
    dp.include_router(business_router)

    try:
        print("🎮 بازی در حال اجراست...")
        print("💾 دیتابیس آماده شد")
        print("🤖 ربات آماده دریافت پیام است")

        await dp.start_polling(bot)

    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())