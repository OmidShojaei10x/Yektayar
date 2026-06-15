"""Contacts/directory search handler."""
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from bot.keyboards import contacts_keyboard, cancel_keyboard
from exchange.client import search_contacts
from storage.session_store import get_credentials

SEARCH_QUERY = 30


def _format_contacts(contacts: list[dict]) -> str:
    if not contacts:
        return "❌ هیچ مخاطبی پیدا نشد."
    lines = ["👥 *نتایج جستجو:*\n"]
    for c in contacts:
        lines.append(
            f"👤 *{c['name']}*\n"
            + (f"   📧 {c['email']}\n" if c["email"] else "")
            + (f"   📞 {c['phone']}\n" if c["phone"] else "")
            + (f"   🏢 {c['department']}\n" if c["department"] else "")
            + (f"   💼 {c['title']}\n" if c["title"] else "")
            + "─────────\n"
        )
    return "".join(lines)


async def show_contacts_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message or update.callback_query.message
    await msg.reply_text(
        "👥 *جستجوی مخاطبان*\n\nنام مخاطب یا بخش مورد نظر را وارد کن:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


async def start_contact_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👥 نام مخاطب را وارد کن:",
        reply_markup=cancel_keyboard(),
    )
    return SEARCH_QUERY


async def do_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.message.text.strip()
    user_id = update.effective_user.id
    creds = await get_credentials(user_id)
    if not creds:
        await update.message.reply_text("❌ لطفاً ابتدا وارد شو (/start)")
        return ConversationHandler.END

    searching = await update.message.reply_text(f"🔍 در حال جستجو برای «{query}»...")
    contacts = await search_contacts(creds[0], creds[1], query)
    text = _format_contacts(contacts)
    await searching.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=contacts_keyboard(),
    )
    return ConversationHandler.END


async def cancel_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ لغو شد.")
    else:
        await update.message.reply_text("❌ لغو شد.")
    return ConversationHandler.END


def build_contacts_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^👥 مخاطبان$"), start_contact_search)
        ],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, do_search)],
        },
        fallbacks=[CallbackQueryHandler(cancel_search, pattern="^cancel$")],
        name="contacts_search",
    )
