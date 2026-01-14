import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from dotenv import load_dotenv
from database import init_db, get_session_scope
from handlers import setup_conv, report_conv, profile, leaderboard, help_command, badges, reading_now, stats
from my_books_handler import my_books_conv
from admin_panel import admin_panel_conv
from scheduler_tasks import send_daily_checkin, send_reminder, close_questionnaire, send_daily_report, send_weekly_summary
from pytz import timezone

# Load environment variables
load_dotenv()

# Logging setup
# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv('BOT_TOKEN')

def main():
    # Load Config
    from utils import get_admin_ids
    ADMIN_IDS = get_admin_ids()
    TIMEZONE = os.getenv('TIMEZONE', 'Etc/GMT-5')

    if not TOKEN:
        print("Error: BOT_TOKEN not found in environment variables.")
        return

    # Initialize DB
    Session = init_db()
    
    # Init Badges
    from gamification import init_badges
    with get_session_scope(Session) as session:
        init_badges(session)
    
    # Post-init to set commands
    async def post_init(application):
        await application.bot.set_my_commands([
            ('start', 'Join the reading club'),
            ('report', 'Submit your daily reading'),
            ('my_books', 'Manage your books'),
            ('profile', 'View stats & achievements'),
            ('stats', 'Detailed reading analytics'),
            ('leaderboard', 'Club rankings'),
            ('badges', 'See badge collection'),
            ('reading_now', 'Currently reading books'),
            ('change_club', 'Switch to a different club'),
            ('help', 'Show help message')
        ])

    # Build Application with Persistence
    from telegram.ext import PicklePersistence
    persistence = PicklePersistence(filepath='bot_data.pickle')
    
    application = ApplicationBuilder().token(TOKEN).post_init(post_init).persistence(persistence).build()
    
    # Add Handlers
    application.add_handler(setup_conv)
    application.add_handler(report_conv)
    application.add_handler(my_books_conv)
    application.add_handler(CommandHandler('profile', profile))
    application.add_handler(CommandHandler('leaderboard', leaderboard))
    application.add_handler(CommandHandler('badges', badges))
    application.add_handler(CommandHandler('reading_now', reading_now))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('stats', stats))
    
    # Callbacks
    from handlers import view_finished_books
    application.add_handler(CallbackQueryHandler(view_finished_books, pattern="^view_finished_books_"))
    
    # Admin Panel (interactive)
    application.add_handler(admin_panel_conv)
    
    # Error handler for graceful exception logging
    async def error_handler(update, context):
        """Log errors caused by updates."""
        logging.error(f"Exception while handling an update: {context.error}")
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ An error occurred. Please try again later."
                )
            except Exception:
                pass
    
    application.add_error_handler(error_handler)
        
    # Setup Scheduler
    job_queue = application.job_queue
    
    # Timezone
    tz = timezone(TIMEZONE)
    
    # Schedule tasks
    # 18:00 Check-in
    job_queue.run_daily(send_daily_checkin, time=datetime.time(hour=18, minute=0, tzinfo=tz))
    
    # 20:00 Reminder
    job_queue.run_daily(send_reminder, time=datetime.time(hour=20, minute=0, tzinfo=tz))
    
    # 22:00 Reminder
    job_queue.run_daily(send_reminder, time=datetime.time(hour=22, minute=0, tzinfo=tz))
    
    # 00:00 Close Questionnaire
    job_queue.run_daily(close_questionnaire, time=datetime.time(hour=0, minute=0, tzinfo=tz))
    
    # 00:01 Daily Report
    job_queue.run_daily(send_daily_report, time=datetime.time(hour=0, minute=1, tzinfo=tz))
    
    # Weekly Summary - Every Sunday at 20:00
    job_queue.run_daily(send_weekly_summary, time=datetime.time(hour=20, minute=0, tzinfo=tz), days=(6,))  # 6 = Sunday
    
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    import datetime
    main()
