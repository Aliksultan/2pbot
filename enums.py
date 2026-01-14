"""
Type-safe enumerations for the Reading Club Bot
"""
from enum import Enum

class GoalType(str, Enum):
    """Club goal type - separate PRL/RNK minimums or overall total"""
    SEPARATE = "SEPARATE"
    OVERALL = "OVERALL"

class LogStatus(str, Enum):
    """Daily log status values"""
    PENDING = "pending"
    ACHIEVED = "achieved"
    READ_NOT_ENOUGH = "read_not_enough"
    NOT_READ = "not_read"
    MISSED = "missed"

class BookCategory(str, Enum):
    """Book category types"""
    PRL = "PRL"
    RNK = "RNK"

class ActionType(str, Enum):
    """Action log types for audit trail"""
    REPORT = "REPORT"
    JOIN_CLUB = "JOIN_CLUB"
    CREATE_CLUB = "CREATE_CLUB"
    ADD_BOOK = "ADD_BOOK"
    ADD_USER_BOOK = "ADD_USER_BOOK"
    KICK_USER = "KICK_USER"
    RESET_USER = "RESET_USER"
    DELETE_CLUB = "DELETE_CLUB"
    DELETE_BOOK = "DELETE_BOOK"
