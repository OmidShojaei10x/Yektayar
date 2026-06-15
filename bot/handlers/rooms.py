"""Room booking handlers: AI-assisted and manual."""
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from bot.keyboards import rooms_menu_keyboard, cancel_keyboard
from exchange.client import get_room_lists
from storage.session_store import get_credentials, get_user_state, set_user_state
from ai.booking_agent import run_booking_agent

AI_BOOKING_CHAT = 40


async def show_rooms_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message or update.callback_query.message
    await msg.reply_text(
        "🏢 *رزرو اتاق جلسه*",
        parse_mode="Markdown",
        reply_markup=rooms_menu_keyboard(),
    )


async def show_room_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    creds = await get_credentials(user_id)
    if not creds:
        await query.edit_message_text("❌ لطفاً ابتدا وارد شو (/start)")
        return

    await query.edit_message_text("⏳ در حال دریافت لیست اتاق‌ها...")
    rooms = await get_room_lists(creds[0], creds[1])

    if not rooms:
        await query.edit_message_text(
            "❌ هیچ اتاقی پیدا نشد یا سرور دسترسی لازم را ندارد.\n"
            "از رزرو هوشمند با AI استفاده کن 🤖",
            reply_markup=rooms_menu_keyboard(),
        )
        return

    lines = ["🏢 *اتاق‌های جلسه:*\n"]
    for r in rooms:
        lines.append(f"🚪 *{r['name']}*\n   📧 {r['email']}\n")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=rooms_menu_keyboard(),
    )


# ── AI Booking ────────────────────────────────────────────────────────────────

async def start_ai_booking(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    # Reset conversation history
    await set_user_state(user_id, {"ai_booking_history": []})

    await query.edit_message_text(
        "🤖 *دستیار هوشمند رزرو اتاق*\n\n"
        "سلام! من می‌تونم بهت کمک کنم یه اتاق جلسه رزرو کنی.\n\n"
        "بگو چه زمانی می‌خوای جلسه داشته باشی؟\n"
        "مثلاً: «فردا ساعت ۳ بعدازظهر یه اتاق برای ۲ ساعت می‌خوام»\n\n"
        "برای خروج /cancel بزن.",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    return AI_BOOKING_CHAT


async def ai_booking_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_text = update.message.text.strip()

    creds = await get_credentials(user_id)
    if not creds:
        await update.message.reply_text("❌ لطفاً ابتدا وارد شو (/start)")
        return ConversationHandler.END

    state = await get_user_state(user_id)
    history: list[dict] = state.get("ai_booking_history", [])
    history.append({"role": "user", "content": user_text})

    thinking = await update.message.reply_text("🤔 در حال پردازش...")

    try:
        response = await run_booking_agent(creds[0], creds[1], history)
        history.append({"role": "assistant", "content": response})
        await set_user_state(user_id, {"ai_booking_history": history})
        await thinking.edit_text(response, reply_markup=cancel_keyboard())
    except Exception as e:
        await thinking.edit_text(f"❌ خطا: {e}")
        return ConversationHandler.END

    return AI_BOOKING_CHAT


async def cancel_ai_booking(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    await set_user_state(user_id, {"ai_booking_history": []})
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ رزرو هوشمند لغو شد.")
    else:
        await update.message.reply_text("❌ رزرو هوشمند لغو شد.")
    return ConversationHandler.END


def build_ai_booking_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_ai_booking, pattern="^rooms:ai_book$")],
        states={
            AI_BOOKING_CHAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ai_booking_message),
                CallbackQueryHandler(cancel_ai_booking, pattern="^cancel$"),
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND & filters.Regex("^/cancel$"), cancel_ai_booking),
        ],
        name="ai_booking",
    )
