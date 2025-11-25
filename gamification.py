from database import User, UserBadge, Badge, DailyLog
from sqlalchemy import func

# XP Constants
XP_PER_PAGE = 1
XP_STREAK_BONUS = 10 # Per day of streak
XP_BOOK_FINISHED = 100

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
    # Need to calculate total pages from logs
    total_pages = session.query(
        func.sum(DailyLog.pages_read_prl + DailyLog.pages_read_rnk)
    ).filter_by(user_id=user.id).scalar() or 0
    
    if total_pages >= 100: award("100 Pages")
    if total_pages >= 500: award("500 Pages")
    if total_pages >= 1000: award("1000 Pages")
    
    # 3. Level Badges
    if user.level >= 5: award("Level 5")
    if user.level >= 10: award("Level 10")
    
    return new_badges

def init_badges(session):
    badges = [
        ("3 Day Streak", "Maintained a 3-day reading streak", "🔥"),
        ("7 Day Streak", "Maintained a 7-day reading streak", "🔥🔥"),
        ("30 Day Streak", "Maintained a 30-day reading streak", "🔥🔥🔥"),
        ("100 Pages", "Read 100 pages total", "📖"),
        ("500 Pages", "Read 500 pages total", "📚"),
        ("1000 Pages", "Read 1000 pages total", "🧙‍♂️"),
        ("Level 5", "Reached Level 5", "⭐"),
        ("Level 10", "Reached Level 10", "🌟"),
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
                    progress = f"{user.streak}/{target}"
                    progress_pct = min(100, int((user.streak / target) * 100))
                elif "7 Day" in badge.name:
                    target = 7
                    progress = f"{user.streak}/{target}"
                    progress_pct = min(100, int((user.streak / target) * 100))
                elif "30 Day" in badge.name:
                    target = 30
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
                    progress = f"{total_pages}/{target}"
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
        
        badge_info.append({
            'badge': badge,
            'earned': earned,
            'progress': progress,
            'progress_pct': progress_pct
        })
    
    return badge_info
