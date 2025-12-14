import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, User, Club, Book, DailyLog
from unittest.mock import MagicMock, AsyncMock
import datetime

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    return create_engine(TEST_DB_URL)

@pytest.fixture(scope="session")
def tables(engine):
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(engine, tables):
    """Returns a sqlalchemy session, and after the test tears down everything properly."""
    connection = engine.connect()
    # begin the nested transaction
    transaction = connection.begin()
    # use the connection with the already started transaction
    Session = sessionmaker(bind=connection, expire_on_commit=False)
    session = Session()

    yield session

    session.close()
    # roll back the broader transaction
    transaction.rollback()
    connection.close()

@pytest.fixture
def mock_update():
    def _create_update(user_id=123, text="/start"):
        update = MagicMock()
        update.effective_user.id = user_id
        update.effective_user.username = f"user_{user_id}"
        update.effective_user.full_name = f"User {user_id}"
        update.message.text = text
        update.message.reply_text = AsyncMock()
        update.message.reply_photo = AsyncMock()
        update.callback_query = None
        return update
    return _create_update

@pytest.fixture
def mock_context():
    context = MagicMock()
    context.user_data = {}
    context.bot.send_message = AsyncMock()
    return context
