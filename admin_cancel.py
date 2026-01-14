from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fallback cancel handler for admin conversation."""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Admin panel closed.")
    elif update.message:
        await update.message.reply_text("Admin panel closed.")
    
    context.user_data.clear()
    return ConversationHandler.END
