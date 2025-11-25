from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Date, DateTime
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

Base = declarative_base()

class Club(Base):
    __tablename__ = 'clubs'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    key = Column(String, unique=True, nullable=False)
    daily_min_prl = Column(Integer, default=0)
    daily_min_rnk = Column(Integer, default=0)
    
    # New Fields for Flexible Goals
    goal_type = Column(String, default='SEPARATE') # 'SEPARATE' or 'OVERALL'
    daily_min_total = Column(Integer, default=0)
    
    books = relationship("Book", back_populates="club")
    users = relationship("User", back_populates="club")

class Book(Base):
    __tablename__ = 'books'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False) # 'PRL' or 'RNK'
    total_pages = Column(Integer, nullable=False)
    club_id = Column(Integer, ForeignKey('clubs.id'))
    priority_level = Column(Integer, default=8)  # 1-8, lower is higher priority
    
    club = relationship("Club", back_populates="books")


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    full_name = Column(String)
    club_id = Column(Integer, ForeignKey('clubs.id'), nullable=True)
    streak = Column(Integer, default=0)
    joined_at = Column(DateTime, default=datetime.now)
    
    club = relationship("Club", back_populates="users")
    readings = relationship("UserBook", back_populates="user")
    logs = relationship("DailyLog", back_populates="user")
    badges = relationship("UserBadge", back_populates="user")
    
    # Gamification & Settings
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    
    # Streak & Grace Period
    best_streak = Column(Integer, default=0)
    grace_period_active = Column(Boolean, default=False)  # True if user missed yesterday and can make it up today
    
class UserBook(Base):
    __tablename__ = 'user_books'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    book_id = Column(Integer, ForeignKey('books.id'))
    current_page = Column(Integer, default=0)
    total_pages = Column(Integer, default=0)
    finished = Column(Boolean, default=False)
    finished_date = Column(Date, nullable=True)
    is_recommended = Column(Boolean, default=False)  # Was this book recommended?
    recommendation_bonus_claimed = Column(Boolean, default=False)  # Did user get selection bonus?
    
    user = relationship("User", back_populates="readings")
    book = relationship("Book")

class Badge(Base):
    __tablename__ = 'badges'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    icon = Column(String) # Emoji

class UserBadge(Base):
    __tablename__ = 'user_badges'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    badge_id = Column(Integer, ForeignKey('badges.id'))
    awarded_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="badges")
    badge = relationship("Badge")

class DailyLog(Base):
    __tablename__ = 'daily_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    date = Column(Date, nullable=False)
    pages_read_prl = Column(Integer, default=0)
    pages_read_rnk = Column(Integer, default=0)
    status = Column(String, default='pending') # achieved, read_not_enough, not_read, missed
    
    user = relationship("User", back_populates="logs")

def init_db(db_path='sqlite:///reading_club.db'):
    engine = create_engine(db_path)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
