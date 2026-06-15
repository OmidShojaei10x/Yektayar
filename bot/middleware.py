"""Auth guard middleware: checks if user is logged in before handling requests."""
from telegram import Update
from telegram.ext import ContextTypes
from storage.session_store import is_authenticated


OPEN_COMMANDS = {"/start", "/help", "/cancel"}


async def require_auth(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    """Return True if user is authenticated, else prompt login."""
    if update.message and update.message.text:
        cmd = update.message.text.split()[0]
        if cmd in OPEN_COMMANDS:
            return True

    user_id = update.effective_user.id if update.effective_user else None
    if user_id and await is_authenticated(user_id):
        return True

    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if msg:
        await msg.reply_text(
            "❌ ابتدا باید وارد شوی.\n/start رو بزن تا وارد حسابت بشی."
        )
    return False
