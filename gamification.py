from database import User, UserBadge, Badge, DailyLog, UserBook
from sqlalchemy import func
from config import (
    XP_PER_PAGE, XP_STREAK_BONUS, XP_BOOK_FINISHED,
    STREAK_THRESHOLDS, PAGE_THRESHOLDS, LEVEL_THRESHOLDS,
    SPEED_READER_DAYS, DIVERSE_READER_CATEGORIES, CLUB_CHAMPION_DAYS
)
from datetime import datetime, timedelta

# Leveling
# Level N requires 100 * N^2 XP total? Or simple linear?
# Let's do: Level = 1 + sqrt(XP / 100) -> XP = 100 * (Level - 1)^2
# Level 2: 100 XP
# Level 3: 400 XP
# Level 4: 900 XP

def calculate_level(xp):
    if xp < 0: return 1
    return 1 + int((xp / 100) ** 0.5)

def get_xp_for_next_level(level):
    return 100 * (level) ** 2

def award_xp(user, amount, session):
    user.xp += amount
    new_level = calculate_level(user.xp)
    
    leveled_up = False
    if new_level > user.level:
        user.level = new_level
        leveled_up = True
        
    return leveled_up

def check_badges(user, session):
    """Check and award badges based on user stats"""
    new_badges = []
    
    # Helper to check and award
    def award(name):
        badge = session.query(Badge).filter_by(name=name).first()
        if badge:
            has_badge = session.query(UserBadge).filter_by(user_id=user.id, badge_id=badge.id).first()
            if not has_badge:
                ub = UserBadge(user_id=user.id, badge_id=badge.id)
                session.add(ub)
                new_badges.append(badge)
    
    # 1. Streak Badges
    if user.streak >= 3: award("3 Day Streak")
    if user.streak >= 7: award("7 Day Streak")
    if user.streak >= 30: award("30 Day Streak")
    
    # 2. Page Badges (Total pages read)
    total_pages = session.query(
        func.sum(DailyLog.pages_read_prl + DailyLog.pages_read_rnk)
    ).filter_by(user_id=user.id).scalar() or 0
    
    if total_pages >= 100: award("100 Pages")
    if total_pages >= 500: award("500 Pages")
    if total_pages >= 1000: award("1000 Pages")
    
    # 3. Level Badges
    if user.level >= 5: award("Level 5")
    if user.level >= 10: award("Level 10")
    
    # 4. First Finish - Complete first book
    finished_books = session.query(UserBook).filter_by(
        user_id=user.id, finished=True
    ).count()
    if finished_books >= 1: award("First Finish")
    
    # 5. Speed Reader - Finish a book in 7 days or less
    speed_reader_books = session.query(UserBook).filter(
        UserBook.user_id == user.id,
        UserBook.finished == True,
        UserBook.finished_date != None
    ).all()
    
    for ub in speed_reader_books:
        if ub.finished_date:
            # Check if book was added and finished within 7 days
            # We'll use finished_date - assume they started when added
            # For more accuracy, we'd need a started_date field
            days_to_finish = 7  # Default assumption
            if hasattr(ub, 'started_date') and ub.started_date:
                days_to_finish = (ub.finished_date - ub.started_date).days
            if days_to_finish <= SPEED_READER_DAYS:
                award("Speed Reader")
                break
    
    # 6. Diverse Reader - Read from both PRL and RNK categories
    categories_read = set()
    finished_user_books = session.query(UserBook).filter_by(
        user_id=user.id, finished=True
    ).all()
    for ub in finished_user_books:
        if ub.book:
            categories_read.add(ub.book.category)
    
    if len(categories_read) >= 2:  # Both PRL and RNK
        award("Diverse Reader")
    
    # 7. Comeback King - Had a streak, lost it, rebuilt it to 3+
    # Check if best_streak > 0 and current streak >= 3 (meaning they recovered)
    if user.best_streak > 0 and user.streak >= 3 and user.streak < user.best_streak:
        award("Comeback King")
    
    return new_badges

def init_badges(session):
    """Initialize all badge definitions in the database"""
    badges = [
        # Streak Badges
        ("3 Day Streak", "Maintained a 3-day reading streak", "🔥"),
        ("7 Day Streak", "Maintained a 7-day reading streak", "🔥🔥"),
        ("30 Day Streak", "Maintained a 30-day reading streak", "🔥🔥🔥"),
        # Page Badges
        ("100 Pages", "Read 100 pages total", "📖"),
        ("500 Pages", "Read 500 pages total", "📚"),
        ("1000 Pages", "Read 1000 pages total", "🧙‍♂️"),
        # Level Badges
        ("Level 5", "Reached Level 5", "⭐"),
        ("Level 10", "Reached Level 10", "🌟"),
        # NEW: Achievement Badges
        ("First Finish", "Completed your first book", "📗"),
        ("Speed Reader", "Finished a book in 7 days or less", "⚡"),
        ("Diverse Reader", "Read books from both PRL and RNK categories", "🎨"),
        ("Comeback King", "Recovered your reading streak after losing it", "💪"),
    ]
    
    for name, desc, icon in badges:
        if not session.query(Badge).filter_by(name=name).first():
            session.add(Badge(name=name, description=desc, icon=icon))
    session.commit()

def get_all_badges_with_progress(user, session):
    """Get all badges with user's progress toward unlocking them"""
    all_badges = session.query(Badge).all()
    user_badge_ids = [ub.badge_id for ub in user.badges]
    
    # Calculate current stats
    total_pages = session.query(
        func.sum(DailyLog.pages_read_prl + DailyLog.pages_read_rnk)
    ).filter_by(user_id=user.id).scalar() or 0
    
    finished_books_count = session.query(UserBook).filter_by(
        user_id=user.id, finished=True
    ).count()
    
    # Categories read
    categories_read = set()
    finished_user_books = session.query(UserBook).filter_by(
        user_id=user.id, finished=True
    ).all()
    for ub in finished_user_books:
        if ub.book:
            categories_read.add(ub.book.category)
    
    badge_info = []
    
    for badge in all_badges:
        earned = badge.id in user_badge_ids
        progress = None
        progress_pct = 100 if earned else 0
        
        # Calculate progress for each badge type
        if not earned:
            if "Streak" in badge.name:
                if "3 Day" in badge.name:
                    target = 3
                elif "7 Day" in badge.name:
                    target = 7
                elif "30 Day" in badge.name:
                    target = 30
                else:
                    target = 0
                if target > 0:
                    progress = f"{user.streak}/{target}"
                    progress_pct = min(100, int((user.streak / target) * 100))
                    
            elif "Pages" in badge.name:
                if "100 Pages" in badge.name:
                    target = 100
                elif "500 Pages" in badge.name:
                    target = 500
                elif "1000 Pages" in badge.name:
                    target = 1000
                else:
                    target = 0
                if target > 0:
                    progress = f"{int(total_pages)}/{target}"
                    progress_pct = min(100, int((total_pages / target) * 100))
                    
            elif "Level" in badge.name:
                if "Level 5" in badge.name:
                    target = 5
                elif "Level 10" in badge.name:
                    target = 10
                else:
                    target = 0
                if target > 0:
                    progress = f"{user.level}/{target}"
                    progress_pct = min(100, int((user.level / target) * 100))
            
            # NEW: Progress for new badges
            elif badge.name == "First Finish":
                progress = f"{finished_books_count}/1"
                progress_pct = 100 if finished_books_count >= 1 else 0
                
            elif badge.name == "Speed Reader":
                progress = "Finish a book in ≤7 days"
                progress_pct = 0
                
            elif badge.name == "Diverse Reader":
                progress = f"{len(categories_read)}/2 categories"
                progress_pct = min(100, int((len(categories_read) / 2) * 100))
                
            elif badge.name == "Comeback King":
                if user.best_streak > 0:
                    progress = f"Rebuild to 3+ days"
                    progress_pct = min(100, int((user.streak / 3) * 100)) if user.streak < user.best_streak else 0
                else:
                    progress = "Keep your streak!"
                    progress_pct = 0
        
        badge_info.append({
            'badge': badge,
            'earned': earned,
            'progress': progress,
            'progress_pct': progress_pct
        })
    
    return badge_info

