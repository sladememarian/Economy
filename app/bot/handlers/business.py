from aiogram import Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.business import business_menu
from app.bot.keyboards.my_businesses import (
    my_businesses_menu,
    business_actions,
)

from app.services.business import (
    buy_business,
    upgrade_business,
)

from app.services.my_businesses import (
    get_my_businesses,
    collect_business_income,
)


router = Router()


# =========================
# 🏪 لیست کسب‌وکارها
# =========================

@router.callback_query(
    lambda callback: callback.data == "business"
)
async def business_handler(
    callback: CallbackQuery,
) -> None:

    await callback.answer()

    await callback.message.edit_text(
        "🏪 <b>کسب‌وکار</b>\n\n"
        "اینجا می‌تونی کسب‌وکار بخری "
        "و ازش درآمد کسب کنی.\n\n"
        "💡 هر کسب‌وکار درآمد ساعتی داره.",
        reply_markup=business_menu(),
    )


# =========================
# 🏪 کسب‌وکارهای من
# =========================

@router.callback_query(
    lambda callback: callback.data == "my_businesses"
)
async def my_businesses_handler(
    callback: CallbackQuery,
) -> None:

    businesses = await get_my_businesses(
        callback.from_user.id
    )

    await callback.answer()

    if not businesses:
        await callback.message.edit_text(
            "🏪 <b>کسب‌وکارهای من</b>\n\n"
            "هنوز هیچ کسب‌وکاری نداری.\n\n"
            "از بخش کسب‌وکارها اولین "
            "سرمایه‌گذاری خودت رو انجام بده. 🚀",
            reply_markup=business_menu(),
        )
        return

    text = "🏪 <b>کسب‌وکارهای من</b>\n\n"

    for business in businesses:
        text += (
            f"{business['emoji']} "
            f"<b>{business['name']}</b>\n"
            f"⭐ سطح: {business['level']}\n"
            f"💰 درآمد: "
            f"{business['income_per_hour']:,} 🪙 / ساعت\n"
            f"💵 درآمد آماده: "
            f"{business['pending_income']:,} 🪙\n\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=my_businesses_menu(businesses),
    )


# =========================
# 💰 خرید کسب‌وکار
# =========================

@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("business:")
    )
)
async def buy_business_handler(
    callback: CallbackQuery,
) -> None:

    business_id = callback.data.split(":", 1)[1]

    success, text = await buy_business(
        telegram_id=callback.from_user.id,
        business_id=business_id,
    )

    await callback.answer(
        "✅ خرید انجام شد!"
        if success
        else "❌ خرید انجام نشد."
    )

    await callback.message.edit_text(
        text,
        reply_markup=business_menu(),
    )


# =========================
# 🏪 جزئیات کسب‌وکار
# =========================

@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("mybusiness:")
    )
)
async def business_details_handler(
    callback: CallbackQuery,
) -> None:

    business_id = int(
        callback.data.split(":", 1)[1]
    )

    businesses = await get_my_businesses(
        callback.from_user.id
    )

    business = next(
        (
            item
            for item in businesses
            if item["id"] == business_id
        ),
        None,
    )

    await callback.answer()

    if business is None:
        await callback.message.edit_text(
            "❌ کسب‌وکار پیدا نشد.",
            reply_markup=business_menu(),
        )
        return

    text = (
        f"{business['emoji']} "
        f"<b>{business['name']}</b>\n\n"
        f"⭐ سطح: <b>{business['level']}</b>\n"
        f"💰 درآمد ساعتی: "
        f"<b>{business['income_per_hour']:,}</b> 🪙\n"
        f"💵 درآمد آماده: "
        f"<b>{business['pending_income']:,}</b> 🪙"
    )

    await callback.message.edit_text(
        text,
        reply_markup=business_actions(
            business_id
        ),
    )


# =========================
# 💵 دریافت درآمد
# =========================

@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("collect:")
    )
)
async def collect_income_handler(
    callback: CallbackQuery,
) -> None:

    business_id = int(
        callback.data.split(":", 1)[1]
    )

    success, text = await collect_business_income(
        telegram_id=callback.from_user.id,
        business_id=business_id,
    )

    await callback.answer(
        "💰 درآمد دریافت شد!"
        if success
        else "⏳ درآمدی برای دریافت نیست."
    )

    await callback.message.edit_text(
        text,
        reply_markup=business_actions(
            business_id
        ),
    )


# =========================
# ⬆️ ارتقای کسب‌وکار
# =========================

@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("upgrade:")
    )
)
async def upgrade_business_handler(
    callback: CallbackQuery,
) -> None:

    business_id = int(
        callback.data.split(":", 1)[1]
    )

    success, text = await upgrade_business(
        telegram_id=callback.from_user.id,
        business_id=business_id,
    )

    await callback.answer(
        "⬆️ ارتقا انجام شد!"
        if success
        else "❌ ارتقا انجام نشد."
    )

    await callback.message.edit_text(
        text,
        reply_markup=business_actions(
            business_id
        ),
    )