"""Email handlers: inbox, read, compose."""
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from bot.keyboards import email_menu_keyboard, email_list_keyboard, email_read_keyboard, cancel_keyboard
from exchange.client import get_inbox, get_email_body, send_email
from storage.session_store import get_credentials
import config

COMPOSE_TO, COMPOSE_SUBJECT, COMPOSE_BODY = range(10, 13)


def _format_email_list(emails: list[dict], offset: int) -> str:
    if not emails:
        return "📭 صندوق ورودی خالی است."
    lines = [f"📥 *ایمیل‌ها* (#{offset + 1}–{offset + len(emails)})\n"]
    for i, e in enumerate(emails):
        icon = "📩" if not e["is_read"] else "📨"
        attach = "📎" if e["has_attachments"] else ""
        lines.append(
            f"{icon}{attach} `{offset + i + 1}.` *{e['subject'][:40]}*\n"
            f"   از: {e['from_name']}\n"
            f"   {_fmt_time(e['received'])}\n"
            f"   /email\\_{e['id'][:8]}\n"
        )
    return "\n".join(lines)


def _fmt_time(dt) -> str:
    if dt is None:
        return ""
    try:
        import pytz
        tehran = pytz.timezone("Asia/Tehran")
        local = dt.astimezone(tehran)
        return local.strftime("%Y/%m/%d %H:%M")
    except Exception:
        return str(dt)


async def show_email_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message or update.callback_query.message
    await msg.reply_text("📧 *منوی ایمیل*", parse_mode="Markdown", reply_markup=email_menu_keyboard())


async def show_inbox(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    offset = int(query.data.split(":")[-1])

    user_id = update.effective_user.id
    creds = await get_credentials(user_id)
    if not creds:
        await query.edit_message_text("❌ لطفاً ابتدا وارد شو (/start)")
        return

    await query.edit_message_text("⏳ در حال دریافت ایمیل‌ها...")
    emails = await get_inbox(creds[0], creds[1], offset=offset, count=config.EMAIL_PAGE_SIZE)
    text = _format_email_list(emails, offset)
    has_more = len(emails) == config.EMAIL_PAGE_SIZE

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=email_list_keyboard(offset, has_more),
    )


async def read_email_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /email_XXXX commands for reading individual emails."""
    text = update.message.text
    email_id_prefix = text.replace("/email_", "").strip()
    user_id = update.effective_user.id

    creds = await get_credentials(user_id)
    if not creds:
        await update.message.reply_text("❌ لطفاً ابتدا وارد شو (/start)")
        return

    msg = await update.message.reply_text("⏳ در حال دریافت ایمیل...")
    emails = await get_inbox(creds[0], creds[1], count=50)
    target = next((e for e in emails if e["id"].startswith(email_id_prefix)), None)

    if not target:
        await msg.edit_text("❌ ایمیل پیدا نشد.")
        return

    detail = await get_email_body(creds[0], creds[1], target["id"])
    if not detail:
        await msg.edit_text("❌ خطا در دریافت متن ایمیل.")
        return

    body_preview = (detail["body"] or "")[:800]
    if len(detail["body"] or "") > 800:
        body_preview += "\n...(ادامه دارد)"

    text_out = (
        f"📧 *{detail['subject']}*\n\n"
        f"👤 از: {detail['from_name']} <{detail['from']}>\n"
        f"📅 تاریخ: {_fmt_time(detail['received'])}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{body_preview}"
    )
    await msg.edit_text(
        text_out,
        parse_mode="Markdown",
        reply_markup=email_read_keyboard(target["id"]),
    )
    ctx.user_data["reply_to_email"] = target


# ── Compose flow ──────────────────────────────────────────────────────────────

async def start_compose(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    ctx.user_data["compose"] = {}
    await query.edit_message_text(
        "✉️ *ارسال ایمیل جدید*\n\nآدرس گیرنده (ایمیل) را وارد کن:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    return COMPOSE_TO


async def compose_got_to(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["compose"]["to"] = [update.message.text.strip()]
    await update.message.reply_text(
        "موضوع ایمیل:", reply_markup=cancel_keyboard()
    )
    return COMPOSE_SUBJECT


async def compose_got_subject(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["compose"]["subject"] = update.message.text.strip()
    await update.message.reply_text(
        "متن ایمیل:", reply_markup=cancel_keyboard()
    )
    return COMPOSE_BODY


async def compose_got_body(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    compose = ctx.user_data.get("compose", {})
    compose["body"] = update.message.text.strip()
    user_id = update.effective_user.id
    creds = await get_credentials(user_id)
    if not creds:
        await update.message.reply_text("❌ خطا: لطفاً دوباره وارد شو.")
        return ConversationHandler.END

    sending = await update.message.reply_text("📤 در حال ارسال...")
    try:
        await send_email(creds[0], creds[1], compose["to"], compose["subject"], compose["body"])
        await sending.edit_text("✅ ایمیل با موفقیت ارسال شد!")
    except Exception as e:
        await sending.edit_text(f"❌ خطا در ارسال: {e}")

    ctx.user_data.pop("compose", None)
    return ConversationHandler.END


async def cancel_compose(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.pop("compose", None)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ لغو شد.")
    else:
        await update.message.reply_text("❌ لغو شد.")
    return ConversationHandler.END


def build_compose_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_compose, pattern="^email:compose$")],
        states={
            COMPOSE_TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, compose_got_to)],
            COMPOSE_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, compose_got_subject)],
            COMPOSE_BODY: [MessageHandler(filters.TEXT & ~filters.COMMAND, compose_got_body)],
        },
        fallbacks=[CallbackQueryHandler(cancel_compose, pattern="^cancel$")],
        name="compose_email",
    )
