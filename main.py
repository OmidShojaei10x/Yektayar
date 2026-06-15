"""Entry point for the Yektayar Telegram bot."""
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

import config
from storage.session_store import init_db
from bot.handlers.auth import build_auth_conversation, logout
from bot.handlers.email import (
    show_email_menu,
    show_inbox,
    read_email_command,
    build_compose_conversation,
)
from bot.handlers.calendar import show_calendar_menu, show_upcoming, build_create_event_conversation
from bot.handlers.contacts import build_contacts_conversation
from bot.handlers.rooms import show_rooms_menu, show_room_list, build_ai_booking_conversation
from bot.middleware import require_auth

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def help_command(update: Update, ctx) -> None:
    await update.message.reply_text(
        "📖 *راهنمای یکتایار*\n\n"
        "• /start — ورود به حساب Exchange\n"
        "• /logout — خروج از حساب\n"
        "• /help — نمایش این راهنما\n\n"
        "از منوی پایین برای دسترسی به ایمیل، تقویم، مخاطبان و رزرو اتاق استفاده کن.",
        parse_mode="Markdown",
    )


async def main_menu_router(update: Update, ctx) -> None:
    if not await require_auth(update, ctx):
        return
    text = update.message.text
    if text == "📧 ایمیل":
        await show_email_menu(update, ctx)
    elif text == "📅 تقویم":
        await show_calendar_menu(update, ctx)
    elif text == "🏢 رزرو اتاق":
        await show_rooms_menu(update, ctx)
    elif text == "👥 مخاطبان":
        from bot.handlers.contacts import start_contact_search
        await start_contact_search(update, ctx)
    elif text == "🔓 خروج از حساب":
        await logout(update, ctx)


async def callback_router(update: Update, ctx) -> None:
    query = update.callback_query
    data = query.data

    if data == "main_menu":
        await query.answer()
        from bot.keyboards import main_menu_keyboard
        await query.message.reply_text("منوی اصلی:", reply_markup=main_menu_keyboard())
        return

    if data == "email:menu":
        await query.answer()
        from bot.keyboards import email_menu_keyboard
        await query.edit_message_text("📧 منوی ایمیل", reply_markup=email_menu_keyboard())
        return

    if data.startswith("email:inbox:"):
        if not await require_auth(update, ctx):
            return
        await show_inbox(update, ctx)
        return

    if data == "cal:upcoming":
        if not await require_auth(update, ctx):
            return
        await show_upcoming(update, ctx)
        return

    if data == "rooms:list":
        if not await require_auth(update, ctx):
            return
        await show_room_list(update, ctx)
        return

    if data == "cancel":
        await query.answer()
        await query.edit_message_text("❌ لغو شد.")
        return


async def email_deeplink(update: Update, ctx) -> None:
    if not await require_auth(update, ctx):
        return
    await read_email_command(update, ctx)


async def post_init(app: Application) -> None:
    await init_db()
    logger.info("Database initialized.")


def main() -> None:
    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Conversation handlers (order matters)
    app.add_handler(build_auth_conversation())
    app.add_handler(build_compose_conversation())
    app.add_handler(build_create_event_conversation())
    app.add_handler(build_contacts_conversation())
    app.add_handler(build_ai_booking_conversation())

    # Simple commands
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("logout", logout))

    # Email deep links (/email_XXXX)
    app.add_handler(MessageHandler(filters.Regex(r"^/email_"), email_deeplink))

    # Menu button router
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(
            "^(📧 ایمیل|📅 تقویم|🏢 رزرو اتاق|👥 مخاطبان|🔓 خروج از حساب)$"
        ),
        main_menu_router,
    ))

    # Inline button fallback router
    app.add_handler(CallbackQueryHandler(callback_router))

    logger.info("Yektayar bot started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
