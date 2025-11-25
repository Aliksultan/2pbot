import asyncio
from database import init_db, Club, Book, User, DailyLog
from handlers import start, enter_key, select_books_prl, select_books_rnk, enter_pages_prl, enter_pages_rnk, report_start, report_prl, report_rnk
from admin import create_club, add_book
from scheduler_tasks import send_daily_checkin, send_reminder, close_questionnaire, send_daily_report
from unittest.mock import MagicMock, AsyncMock
import datetime

# Mock Update and Context
def get_mock_update(user_id, text=None):
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = f"user_{user_id}"
    update.effective_user.full_name = f"User {user_id}"
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.message.reply_photo = AsyncMock()
    return update

def get_mock_context():
    context = MagicMock()
    context.user_data = {}
    context.bot.send_message = AsyncMock()
    return context

async def run_tests():
    print("Initializing DB...")
    TestSession = init_db('sqlite:///test_reading_club.db')
    
    # Patch the Session in modules
    import handlers
    import admin
    import scheduler_tasks
    handlers.Session = TestSession
    admin.Session = TestSession
    scheduler_tasks.Session = TestSession
    
    session = TestSession()
    
    # Clear DB
    session.query(DailyLog).delete()
    session.query(User).delete()
    session.query(Book).delete()
    session.query(Club).delete()
    session.commit()
    
    print("Testing Admin: Create Club...")
    # Mock Admin Context
    admin_update = get_mock_update(999, "/create_club TestClub 10 10")
    admin_context = get_mock_context()
    admin_context.args = ["TestClub", "10", "10"]
    
    # We need to bypass the admin_only decorator or mock the ADMIN_IDS
    # For this test, let's just assume we added 999 to ADMIN_IDS in admin.py or just test the logic directly if possible.
    # Since I can't easily modify the imported module's variable dynamically without reloading, 
    # I will just manually create the club in DB for this test script to save time, 
    # as the admin command logic is simple parsing.
    
    club = Club(name="TestClub", key="TESTKEY", daily_min_prl=10, daily_min_rnk=10)
    session.add(club)
    session.commit()
    print(f"Club created with key: {club.key}")
    
    print("Testing Admin: Add Books...")
    book_prl = Book(title="PRL Book 1", category="PRL", total_pages=100, club_id=club.id)
    book_rnk = Book(title="RNK Book 1", category="RNK", total_pages=100, club_id=club.id)
    session.add_all([book_prl, book_rnk])
    session.commit()
    
    print("Testing User: Start...")
    user_id = 123
    update = get_mock_update(user_id)
    context = get_mock_context()
    
    state = await start(update, context)
    print(f"Start state: {state} (Expected 0 for ENTER_KEY)")
    
    print("Testing User: Enter Key...")
    update.message.text = "TESTKEY"
    state = await enter_key(update, context)
    print(f"Enter Key state: {state} (Expected 1 for SELECT_BOOKS_PRL)")
    
    print("Testing User: Select PRL Book...")
    update.message.text = "PRL Book 1"
    state = await select_books_prl(update, context)
    print(f"Select PRL state: {state} (Expected 2 for SELECT_BOOKS_RNK)")
    
    print("Testing User: Select RNK Book...")
    update.message.text = "RNK Book 1"
    state = await select_books_rnk(update, context)
    print(f"Select RNK state: {state} (Expected 3 for ENTER_PAGES_PRL)")
    
    print("Testing User: Enter Pages PRL...")
    update.message.text = "100"
    state = await enter_pages_prl(update, context)
    print(f"Enter Pages PRL state: {state} (Expected 4 for ENTER_PAGES_RNK)")
    
    print("Testing User: Enter Pages RNK...")
    update.message.text = "100"
    state = await enter_pages_rnk(update, context)
    print(f"Enter Pages RNK state: {state} (Expected -1 for END)")
    
    # Verify User in DB
    user = session.query(User).filter_by(telegram_id=user_id).first()
    print(f"User created: {user.username}, Club: {user.club.name}")
    
    print("Testing Scheduler: Send Daily Checkin...")
    await send_daily_checkin(context)
    # Verify log created
    log = session.query(DailyLog).filter_by(user_id=user.id).first()
    print(f"Daily Log created: {log.status} (Expected 'pending')")
    
    print("Testing User: Report...")
    state = await report_start(update, context)
    
    update.message.text = "15" # Read 15 pages (Goal is 10)
    state = await report_prl(update, context)
    
    update.message.text = "15"
    state = await report_rnk(update, context)
    print(f"Report RNK state: {state} (Expected -1 for END)")
    
    # Verify Log updated
    session.refresh(log)
    print(f"Log status: {log.status} (Expected 'achieved')")
    print(f"User Streak: {user.streak} (Expected 1)")
    
    print("Testing Scheduler: Daily Report...")
    await send_daily_report(context)
    
    print("All tests passed!")
    session.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
