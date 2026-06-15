"""Telegram inline and reply keyboards."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["📧 ایمیل", "📅 تقویم"],
            ["🏢 رزرو اتاق", "👥 مخاطبان"],
            ["🔓 خروج از حساب"],
        ],
        resize_keyboard=True,
        input_field_placeholder="یه گزینه انتخاب کن...",
    )


def email_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 صندوق ورودی", callback_data="email:inbox:0")],
        [InlineKeyboardButton("✉️ ارسال ایمیل", callback_data="email:compose")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")],
    ])


def email_list_keyboard(offset: int, has_more: bool) -> InlineKeyboardMarkup:
    buttons = []
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"email:inbox:{offset - 10}"))
    if has_more:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"email:inbox:{offset + 10}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="email:menu")])
    return InlineKeyboardMarkup(buttons)


def email_read_keyboard(email_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ پاسخ", callback_data=f"email:reply:{email_id}")],
        [InlineKeyboardButton("🔙 برگشت به صندوق", callback_data="email:inbox:0")],
    ])


def calendar_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 رویدادهای پیش رو", callback_data="cal:upcoming")],
        [InlineKeyboardButton("➕ ایجاد رویداد", callback_data="cal:create")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")],
    ])


def rooms_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 رزرو هوشمند با AI", callback_data="rooms:ai_book")],
        [InlineKeyboardButton("📋 لیست اتاق‌ها", callback_data="rooms:list")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")],
    ])


def contacts_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")],
    ])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو", callback_data="cancel")],
    ])


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تأیید", callback_data=f"confirm:{action}"),
            InlineKeyboardButton("❌ لغو", callback_data="cancel"),
        ]
    ])
