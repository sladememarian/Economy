import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from app.config import PROXY_URL, require_bot_token
from app.database.mongo import close_database, init_database

from app.bot.handlers.start import router as start_router
from app.bot.handlers.job import router as job_router
from app.bot.handlers.profile import router as profile_router
from app.bot.handlers.business import router as business_router


async def main() -> None:
    token = require_bot_token()

    await init_database()

    session = AiohttpSession(
        proxy=PROXY_URL,
    )

    bot = Bot(
        token=token,
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
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())