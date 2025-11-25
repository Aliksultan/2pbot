import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler
from dotenv import load_dotenv
from database import init_db
from handlers import setup_conv, report_conv, profile, leaderboard, help_command, badges, reading_now
from my_books_handler import my_books_conv
from admin import admin_handlers
from scheduler_tasks import send_daily_checkin, send_reminder, close_questionnaire, send_daily_report, send_weekly_summary
from pytz import timezone

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv('BOT_TOKEN')

def main():
    if not TOKEN:
        print("Error: BOT_TOKEN not found in environment variables.")
        return

    # Initialize DB
    Session = init_db()
    
    # Init Badges
    from gamification import init_badges
    session = Session()
    init_badges(session)
    session.close()
    
    # Build Application
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Add Handlers
    application.add_handler(setup_conv)
    application.add_handler(report_conv)
    application.add_handler(my_books_conv)
    application.add_handler(CommandHandler('profile', profile))
    application.add_handler(CommandHandler('leaderboard', leaderboard))
    application.add_handler(CommandHandler('badges', badges))
    application.add_handler(CommandHandler('reading_now', reading_now))
    application.add_handler(CommandHandler('help', help_command))
    
    for handler in admin_handlers:
        application.add_handler(handler)
        
    # Setup Scheduler
    job_queue = application.job_queue
    
    # UTC+5 Timezone
    tz = timezone('Etc/GMT-5')
    
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
