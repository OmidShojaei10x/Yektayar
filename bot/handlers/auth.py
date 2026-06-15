"""Authentication flow: login/logout with Exchange credentials."""
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.keyboards import main_menu_keyboard, cancel_keyboard
from exchange.client import verify_credentials
from storage.session_store import save_credentials, delete_credentials, is_authenticated

WAITING_USERNAME, WAITING_PASSWORD = range(2)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if await is_authenticated(user_id):
        await update.message.reply_text(
            "👋 خوش اومدی به یکتایار!\nیه گزینه از منو انتخاب کن:",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "👋 سلام! به ربات یکتایار خوش اومدی.\n\n"
        "برای شروع لطفاً با حساب Exchange سازمان وارد شو.\n\n"
        "نام کاربری Exchange خودت رو وارد کن (مثلاً: omid.shojaei):",
        reply_markup=cancel_keyboard(),
    )
    return WAITING_USERNAME


async def received_username(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text.strip()
    if "@" in username:
        username = username.split("@")[0]
    ctx.user_data["exchange_username"] = username

    await update.message.reply_text(
        f"✅ نام کاربری: `{username}`\n\nحالا پسورد Exchange‌ات رو وارد کن:\n"
        "_(پیامت بعد از پردازش پاک می‌شه)_",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    return WAITING_PASSWORD


async def received_password(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text
    username = ctx.user_data.get("exchange_username", "")
    user_id = update.effective_user.id

    # Delete the password message for security
    try:
        await update.message.delete()
    except Exception:
        pass

    checking_msg = await update.message.reply_text("⏳ در حال تأیید اطلاعات...")

    if not await verify_credentials(username, password):
        await checking_msg.edit_text(
            "❌ نام کاربری یا پسورد اشتباه است.\nدوباره تلاش کن یا /start رو بزن."
        )
        return ConversationHandler.END

    await save_credentials(user_id, username, password)
    ctx.user_data.clear()

    await checking_msg.edit_text(
        f"✅ با موفقیت وارد شدی!\n\n"
        f"👤 کاربر: {username}@{__import__('config').EXCHANGE_SERVER}\n\n"
        "از منوی پایین گزینه مورد نظرت رو انتخاب کن:"
    )
    await update.message.reply_text(
        "منوی اصلی:", reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END


async def logout(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    await delete_credentials(user_id)
    ctx.user_data.clear()
    from telegram import ReplyKeyboardRemove
    await update.message.reply_text(
        "👋 از حساب خارج شدی.\nبرای ورود مجدد /start رو بزن.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.clear()
    await update.message.reply_text("❌ لغو شد.")
    return ConversationHandler.END


def build_auth_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_username)
            ],
            WAITING_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_password)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="auth",
        persistent=False,
    )
