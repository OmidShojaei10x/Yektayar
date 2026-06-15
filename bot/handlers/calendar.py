"""Calendar handlers: view events, create events."""
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import pytz

from bot.keyboards import calendar_menu_keyboard, cancel_keyboard
from exchange.client import get_calendar_events, create_calendar_event
from storage.session_store import get_credentials

TEHRAN_TZ = pytz.timezone("Asia/Tehran")

CREATE_SUBJECT, CREATE_START, CREATE_END, CREATE_LOCATION = range(20, 24)


def _fmt_dt(dt) -> str:
    try:
        local = dt.astimezone(TEHRAN_TZ)
        return local.strftime("%Y/%m/%d %H:%M")
    except Exception:
        return str(dt)


def _format_events(events: list[dict]) -> str:
    if not events:
        return "📭 رویدادی در ۷ روز آینده وجود ندارد."
    lines = ["📅 *رویدادهای پیش رو:*\n"]
    for e in events:
        all_day = " (تمام روز)" if e["is_all_day"] else ""
        lines.append(
            f"🗓 *{e['subject']}*{all_day}\n"
            f"   ⏰ {_fmt_dt(e['start'])} ← {_fmt_dt(e['end'])}\n"
            + (f"   📍 {e['location']}\n" if e["location"] else "")
            + (f"   👤 {e['organizer']}\n" if e["organizer"] else "")
            + "─────────────\n"
        )
    return "\n".join(lines)


async def show_calendar_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message or update.callback_query.message
    await msg.reply_text("📅 *منوی تقویم*", parse_mode="Markdown", reply_markup=calendar_menu_keyboard())


async def show_upcoming(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    creds = await get_credentials(user_id)
    if not creds:
        await query.edit_message_text("❌ لطفاً ابتدا وارد شو (/start)")
        return

    await query.edit_message_text("⏳ در حال دریافت رویدادها...")
    events = await get_calendar_events(creds[0], creds[1])
    text = _format_events(events)
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=calendar_menu_keyboard(),
    )


# ── Create event flow ─────────────────────────────────────────────────────────

async def start_create_event(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    ctx.user_data["new_event"] = {}
    await query.edit_message_text(
        "➕ *ایجاد رویداد جدید*\n\nعنوان رویداد را وارد کن:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    return CREATE_SUBJECT


async def event_got_subject(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["new_event"]["subject"] = update.message.text.strip()
    await update.message.reply_text(
        "زمان شروع را وارد کن (مثال: ۱۴۰۳/۱۰/۱۵ ۱۴:۳۰):",
        reply_markup=cancel_keyboard(),
    )
    return CREATE_START


async def event_got_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    try:
        dt = _parse_datetime(raw)
        ctx.user_data["new_event"]["start"] = dt
        await update.message.reply_text(
            f"✅ شروع: {dt.strftime('%Y/%m/%d %H:%M')}\n\nزمان پایان:",
            reply_markup=cancel_keyboard(),
        )
        return CREATE_END
    except Exception:
        await update.message.reply_text(
            "❌ فرمت نادرست. مثال: 2024-01-15 14:30",
            reply_markup=cancel_keyboard(),
        )
        return CREATE_START


async def event_got_end(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    try:
        dt = _parse_datetime(raw)
        ctx.user_data["new_event"]["end"] = dt
        await update.message.reply_text(
            f"✅ پایان: {dt.strftime('%Y/%m/%d %H:%M')}\n\nمکان (یا 'خیر'):",
            reply_markup=cancel_keyboard(),
        )
        return CREATE_LOCATION
    except Exception:
        await update.message.reply_text("❌ فرمت نادرست.", reply_markup=cancel_keyboard())
        return CREATE_END


async def event_got_location(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    location = "" if text.lower() in ("خیر", "no", "-") else text
    event = ctx.user_data.get("new_event", {})
    user_id = update.effective_user.id
    creds = await get_credentials(user_id)
    if not creds:
        await update.message.reply_text("❌ لطفاً دوباره وارد شو.")
        return ConversationHandler.END

    saving = await update.message.reply_text("⏳ در حال ذخیره رویداد...")
    try:
        await create_calendar_event(
            creds[0], creds[1],
            subject=event["subject"],
            start=event["start"],
            end=event["end"],
            location=location,
        )
        await saving.edit_text(
            f"✅ رویداد *{event['subject']}* ایجاد شد!\n"
            f"📍 {location or 'بدون مکان'}\n"
            f"⏰ {event['start'].strftime('%Y/%m/%d %H:%M')}",
            parse_mode="Markdown",
        )
    except Exception as e:
        await saving.edit_text(f"❌ خطا: {e}")

    ctx.user_data.pop("new_event", None)
    return ConversationHandler.END


def _parse_datetime(text: str) -> datetime:
    for fmt in ("%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt)
            return TEHRAN_TZ.localize(dt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse: {text}")


async def cancel_create(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.pop("new_event", None)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ لغو شد.")
    else:
        await update.message.reply_text("❌ لغو شد.")
    return ConversationHandler.END


def build_create_event_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_create_event, pattern="^cal:create$")],
        states={
            CREATE_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_got_subject)],
            CREATE_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_got_start)],
            CREATE_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_got_end)],
            CREATE_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_got_location)],
        },
        fallbacks=[CallbackQueryHandler(cancel_create, pattern="^cancel$")],
        name="create_event",
    )
