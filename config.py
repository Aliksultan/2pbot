"""
Centralized configuration constants for the Reading Club Bot
"""
import os

# ==================== XP CONSTANTS ====================
XP_PER_PAGE = 1
XP_STREAK_BONUS = 10  # Per day of streak
XP_BOOK_FINISHED = 100
XP_SELECTION_BONUS = 50  # For selecting recommended book
XP_COMPLETION_BONUS = 100  # For completing recommended book

# ==================== SCHEDULER TIMES ====================
CHECKIN_HOUR = 18
REMINDER_HOURS = [20, 22]
CLOSE_HOUR = 0
REPORT_HOUR = 0
REPORT_MINUTE = 1
WEEKLY_SUMMARY_HOUR = 20
WEEKLY_SUMMARY_DAY = 6  # Sunday

# ==================== LIMITS ====================
MAX_MESSAGE_LENGTH = 4000
MAX_BUTTONS_PER_MESSAGE = 50
LEADERBOARD_LIMIT = 10

# ==================== BADGE THRESHOLDS ====================
STREAK_THRESHOLDS = [3, 7, 30]
PAGE_THRESHOLDS = [100, 500, 1000]
LEVEL_THRESHOLDS = [5, 10]
SPEED_READER_DAYS = 7
DIVERSE_READER_CATEGORIES = 3
CLUB_CHAMPION_DAYS = 7

# ==================== TIMEZONE ====================
DEFAULT_TIMEZONE = os.getenv('TIMEZONE', 'Etc/GMT-5')

# ==================== DATABASE ====================
DATABASE_PATH = 'sqlite:///reading_club.db'
