from telegram.ext import ContextTypes
from database import init_db, User, DailyLog, Club, Book, UserBook
from utils import get_current_time, get_today_date, generate_contribution_graph
from sqlalchemy import func
import datetime

Session = init_db()

async def send_daily_checkin(context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    users = session.query(User).all()
    today = get_today_date()
    
    for user in users:

                
        # Check if log already exists (maybe they filled it early?)
        log = session.query(DailyLog).filter_by(user_id=user.id, date=today).first()
        if not log:
            # Create a pending log
            log = DailyLog(user_id=user.id, date=today, status='pending')
            session.add(log)
            session.commit()
            
            try:
                await context.bot.send_message(chat_id=user.telegram_id, text="👋 Good evening! Did you do your reading today?\nUse /report to log your progress and keep your streak alive! 🔥")
            except Exception as e:
                print(f"Failed to send to {user.telegram_id}: {e}")
    session.close()

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    users = session.query(User).all()
    today = get_today_date()
    
    for user in users:
        log = session.query(DailyLog).filter_by(user_id=user.id, date=today).first()
        if log and log.status == 'pending':
            try:
                await context.bot.send_message(chat_id=user.telegram_id, text="⏰ <b>Reminder:</b> The day is almost over! Don't forget to /report your reading.", parse_mode='HTML')
            except Exception as e:
                print(f"Failed to send reminder to {user.telegram_id}: {e}")
    session.close()

async def close_questionnaire(context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    users = session.query(User).all()
    today = get_today_date()
    
    for user in users:
        log = session.query(DailyLog).filter_by(user_id=user.id, date=today).first()
        
        # If no log or status is NOT achieved
        if not log or log.status != 'achieved':
            # Check if user has an active grace period
            if user.grace_period_active:
                # Grace period was active but they still didn't achieve - reset streak
                user.streak = 0
                user.grace_period_active = False
                session.commit()
                
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text="⏰ <b>Grace Period Expired</b>\n\n"
                             "You had 24 hours to make up yesterday's reading by reading double today, but didn't achieve it.\n"
                             "🔥 Streak reset to 0. 😢\n\n"
                             "<i>Don't give up! Start a new streak tomorrow!</i>",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"Failed to send grace expired msg to {user.telegram_id}: {e}")
            else:
                # No grace period - activate it for tomorrow
                user.grace_period_active = True
                
                if log and log.status == 'pending':
                    log.status = 'missed'
                    
                session.commit()
                
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text="⏰ <b>Grace Period Activated!</b>\n\n"
                             "You missed today's reading goal. ⚠️\n\n"
                             "📚 <b>Good news:</b> You have 24 hours to make it up!\n"
                             "Read <b>DOUBLE</b> your daily goal tomorrow to preserve your streak.\n\n"
                             f"🔥 Current streak: {user.streak} days (at risk)",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"Failed to send grace period msg to {user.telegram_id}: {e}")
    session.close()

async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    users = session.query(User).all()
    today = get_today_date()
    yesterday = today - datetime.timedelta(days=1)
    
    # Calculate ranking (simplified: total pages read ever)
    # In a real app, this might be "pages read today" or "pages read this month"
    # The prompt says "ranking of the most pages read from the reading club"
    
    # Let's do ranking based on total pages read
    ranking_query = session.query(
        User.id, 
        func.sum(DailyLog.pages_read_prl + DailyLog.pages_read_rnk).label('total_pages')
    ).join(DailyLog).group_by(User.id).order_by(func.sum(DailyLog.pages_read_prl + DailyLog.pages_read_rnk).desc()).all()
    
    ranking_map = {r.id: i+1 for i, r in enumerate(ranking_query)}
    
    for user in users:
        log = session.query(DailyLog).filter_by(user_id=user.id, date=yesterday).first()
        status_msg = "Keep it up!"
        if log and log.status == 'missed':
            status_msg = "Don't give up, try again today!"
        
        rank = ranking_map.get(user.id, "N/A")
        
        msg = f"Daily Report:\nStreak: {user.streak} days\n{status_msg}\nYour Rank: #{rank}"
        
        # Stats
        # Week/Month/Year stats would be queries here
        
        try:
            await context.bot.send_message(chat_id=user.telegram_id, text=msg)
        except Exception as e:
            print(f"Failed to send report to {user.telegram_id}: {e}")
            
    session.close()

async def send_weekly_summary(context: ContextTypes.DEFAULT_TYPE):
    """Send weekly reading summary every Sunday"""
    import datetime
    
    session = Session()
    users = session.query(User).all()
    today = get_today_date()
    
    # Get start of week (7 days ago)
    week_start = today - datetime.timedelta(days=7)
    
    for user in users:
        # Get logs for the past week
        week_logs = session.query(DailyLog).filter(
            DailyLog.user_id == user.id,
            DailyLog.date >= week_start,
            DailyLog.date < today
        ).all()
        
        if not week_logs:
            continue  # Skip users with no activity
        
        # Calculate weekly stats
        total_pages = sum((log.pages_read_prl or 0) + (log.pages_read_rnk or 0) for log in week_logs)
        days_achieved = len([log for log in week_logs if log.status == 'achieved'])
        days_active = len([log for log in week_logs if log.status in ['achieved', 'read_not_enough']])
        
        # Determine streak status
        streak_status = "🔥 Active" if user.streak > 0 else "💤 Broken"
        if user.grace_period_active:
            streak_status = "⏰ At Risk (Grace Period)"
        
        # Build message
        msg = (
            f"📊 <b>Weekly Reading Summary</b> 📊\n\n"
            f"📅 <b>Week of {week_start.strftime('%b %d')} - {today.strftime('%b %d')}</b>\n\n"
            f"📖 <b>Total Pages Read:</b> {total_pages}\n"
            f"✅ <b>Goals Achieved:</b> {days_achieved}/7 days\n"
            f"📚 <b>Days Active:</b> {days_active}/7 days\n"
            f"🔥 <b>Streak:</b> {user.streak} days ({streak_status})\n\n"
        )
        
        # Add encouragement based on performance
        if days_achieved >= 6:
            msg += "🌟 <b>Excellent work!</b> You're crushing it! Keep up the amazing consistency! 💪"
        elif days_achieved >= 4:
            msg += "👍 <b>Great effort!</b> You're doing well! Try to hit all 7 days next week! 📚"
        elif days_achieved >= 2:
            msg += "📖 <b>Good start!</b> You can do better! Let's aim higher next week! 🎯"
        else:
            msg += "💪 <b>New week, new you!</b> Don't give up! Every day is a chance to read! 🌱"
        
        try:
            await context.bot.send_message(chat_id=user.telegram_id, text=msg, parse_mode='HTML')
        except Exception as e:
            print(f"Failed to send weekly summary to {user.telegram_id}: {e}")
    
    session.close()
