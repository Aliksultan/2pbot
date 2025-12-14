import pytest
from handlers import start, enter_key, select_books_prl, report_start, report_book_progress, finish_report
from database import User, Club, Book, UserBook, DailyLog
import handlers

# Patch the Session in handlers to use our test session
# This is tricky because handlers imports Session from database.py
# We will patch get_session_scope instead or just mock the Session object in handlers

@pytest.fixture(autouse=True)
def patch_session(db_session, monkeypatch):
    """Patch the Session object in handlers.py to return our test session."""
    # We need to patch get_session_scope to yield our db_session
    from contextlib import contextmanager
    
    @contextmanager
    def mock_get_session_scope(SessionFactory):
        yield db_session
        # No commit/close here as it's handled by the fixture
        
    monkeypatch.setattr(handlers, "get_session_scope", mock_get_session_scope)
    monkeypatch.setattr(handlers, "Session", lambda: db_session)

@pytest.mark.asyncio
async def test_start_new_user(mock_update, mock_context, db_session):
    update = mock_update(user_id=1)
    state = await start(update, mock_context)
    
    assert state == 0 # ENTER_KEY
    user = db_session.query(User).filter_by(telegram_id=1).first()
    assert user is not None
    assert user.username == "user_1"

@pytest.mark.asyncio
async def test_enter_key_valid(mock_update, mock_context, db_session):
    # Setup club
    club = Club(name="Test Club", key="TESTKEY", daily_min_prl=10, daily_min_rnk=10)
    db_session.add(club)
    db_session.commit()
    
    # Setup user
    user = User(telegram_id=2, username="user_2")
    db_session.add(user)
    db_session.commit()
    
    update = mock_update(user_id=2, text="TESTKEY")
    state = await enter_key(update, mock_context)
    
    assert state == 1 # SELECT_BOOKS_PRL
    
    # Refresh user
    db_session.expire_all()
    user = db_session.query(User).filter_by(telegram_id=2).first()
    assert user.club_id == club.id

@pytest.mark.asyncio
async def test_report_flow(mock_update, mock_context, db_session):
    # Setup
    club = Club(name="Test Club", key="TESTKEY", daily_min_prl=10, daily_min_rnk=10)
    db_session.add(club)
    db_session.flush()
    
    book = Book(title="Test Book", category="PRL", total_pages=100, club_id=club.id)
    db_session.add(book)
    db_session.flush()
    
    user = User(telegram_id=3, username="user_3", club_id=club.id)
    db_session.add(user)
    db_session.flush()
    
    ub = UserBook(user_id=user.id, book_id=book.id, total_pages=100, current_page=0)
    db_session.add(ub)
    db_session.commit()
    
    # Start Report
    update = mock_update(user_id=3)
    state = await report_start(update, mock_context)
    
    assert "report_queue" in mock_context.user_data
    assert mock_context.user_data["report_queue"][0] == ub.id
    
    # Report Pages
    update.message.text = "10"
    await report_book_progress(update, mock_context)
    
    # Verify progress
    db_session.expire_all()
    ub = db_session.query(UserBook).get(ub.id)
    assert ub.current_page == 10
    assert mock_context.user_data["report_results"]["PRL"] == 10
    
    # Finish Report is called automatically when queue is empty
    # await finish_report(update, mock_context)
    
    # Verify Log
    log = db_session.query(DailyLog).filter_by(user_id=user.id).first()
    assert log is not None
    assert log.pages_read_prl == 10
    assert log.status == 'read_not_enough' # Goal is 10 PRL + 10 RNK, read 10 PRL only
