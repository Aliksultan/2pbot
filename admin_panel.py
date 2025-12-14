"""
Interactive Admin Panel for Reading Club Bot
Uses inline keyboards for easy navigation
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, 
    CallbackQueryHandler, MessageHandler, filters
)
from database import init_db, Club, Book, User, DailyLog, UserBook, get_session_scope
from utils import get_admin_ids
import uuid

Session = init_db()

# Conversation states
MAIN_MENU, CLUB_MENU, BOOK_MENU, USER_MENU, STATS_MENU = range(5)
CREATE_CLUB_NAME, CREATE_CLUB_TYPE, CREATE_CLUB_GOALS_PRL, CREATE_CLUB_GOALS_RNK, CREATE_CLUB_GOALS_TOTAL = range(5, 10)
ADD_BOOK_CLUB, ADD_BOOK_TITLE, ADD_BOOK_PAGES = range(10, 13)
BROADCAST_CLUB, BROADCAST_MESSAGE = range(13, 15)
SELECT_USER, CONFIRM_ACTION = range(15, 17)


def admin_only_callback(func):
    """Decorator to check admin access for callback queries"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        admin_ids = get_admin_ids()
        user_id = update.effective_user.id
        if user_id not in admin_ids:
            if update.callback_query:
                await update.callback_query.answer("Admin access only.", show_alert=True)
            return ConversationHandler.END
        return await func(update, context, *args, **kwargs)
    return wrapper


# ==================== KEYBOARD BUILDERS ====================

def build_main_menu():
    """Build the main admin menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("📋 Clubs", callback_data="menu_clubs"),
            InlineKeyboardButton("📚 Books", callback_data="menu_books"),
        ],
        [
            InlineKeyboardButton("👥 Users", callback_data="menu_users"),
            InlineKeyboardButton("📊 Stats", callback_data="menu_stats"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="menu_broadcast"),
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="close_panel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_club_menu():
    """Build the club management menu"""
    keyboard = [
        [InlineKeyboardButton("➕ Create Club", callback_data="club_create")],
        [InlineKeyboardButton("📋 List All Clubs", callback_data="club_list")],
        [InlineKeyboardButton("🗑️ Delete Club", callback_data="club_delete")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_book_menu():
    """Build the book management menu"""
    keyboard = [
        [InlineKeyboardButton("➕ Add Book", callback_data="book_add")],
        [InlineKeyboardButton("📋 List Books", callback_data="book_list")],
        [InlineKeyboardButton("🗑️ Delete Book", callback_data="book_delete")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_user_menu():
    """Build the user management menu"""
    keyboard = [
        [InlineKeyboardButton("📋 List Users", callback_data="user_list")],
        [InlineKeyboardButton("🚫 Kick User", callback_data="user_kick")],
        [InlineKeyboardButton("🔄 Reset User", callback_data="user_reset")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_stats_menu():
    """Build the statistics menu"""
    keyboard = [
        [InlineKeyboardButton("📊 Club Stats", callback_data="stats_club")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="stats_leaderboard")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_club_selector(clubs, action_prefix):
    """Build a club selector keyboard"""
    keyboard = []
    for club in clubs:
        keyboard.append([
            InlineKeyboardButton(
                f"{club.name} ({len(club.users)} members)",
                callback_data=f"{action_prefix}_{club.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def build_back_button(callback_data="back_main"):
    """Build a simple back button"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=callback_data)]])


def build_cancel_button():
    """Build a cancel button"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")]])


def build_club_type_selector():
    """Build club type selector"""
    keyboard = [
        [InlineKeyboardButton("📊 Separate Goals (PRL + RNK)", callback_data="type_SEPARATE")],
        [InlineKeyboardButton("📈 Overall Goal (Total)", callback_data="type_OVERALL")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== MAIN HANDLERS ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for the admin panel"""
    admin_ids = get_admin_ids()
    if update.effective_user.id not in admin_ids:
        await update.message.reply_text("🚫 Admin access only.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🛡️ <b>Admin Panel</b>\n\n"
        "Select an action:",
        parse_mode='HTML',
        reply_markup=build_main_menu()
    )
    return MAIN_MENU


@admin_only_callback
async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "menu_clubs":
        await query.edit_message_text(
            "📋 <b>Club Management</b>\n\nSelect an action:",
            parse_mode='HTML',
            reply_markup=build_club_menu()
        )
        return CLUB_MENU
    
    elif data == "menu_books":
        await query.edit_message_text(
            "📚 <b>Book Management</b>\n\nSelect an action:",
            parse_mode='HTML',
            reply_markup=build_book_menu()
        )
        return BOOK_MENU
    
    elif data == "menu_users":
        await query.edit_message_text(
            "👥 <b>User Management</b>\n\nSelect an action:",
            parse_mode='HTML',
            reply_markup=build_user_menu()
        )
        return USER_MENU
    
    elif data == "menu_stats":
        await query.edit_message_text(
            "📊 <b>Statistics</b>\n\nSelect an action:",
            parse_mode='HTML',
            reply_markup=build_stats_menu()
        )
        return STATS_MENU
    
    elif data == "menu_broadcast":
        # Show broadcast options: all users or by club
        with get_session_scope(Session) as session:
            clubs = session.query(Club).all()
            user_count = session.query(User).count()
            
            keyboard = [
                [InlineKeyboardButton(f"📢 All Users ({user_count})", callback_data="broadcast_all")],
            ]
            for club in clubs:
                club_user_count = len(club.users)
                keyboard.append([
                    InlineKeyboardButton(
                        f"📋 {club.name} ({club_user_count})",
                        callback_data=f"broadcast_{club.id}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_main")])
            
            await query.edit_message_text(
                "📢 <b>Broadcast Message</b>\n\nSelect target:",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return BROADCAST_CLUB
    
    elif data == "close_panel":
        await query.edit_message_text("Admin panel closed.")
        return ConversationHandler.END
    
    return MAIN_MENU


@admin_only_callback
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to main menu"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🛡️ <b>Admin Panel</b>\n\nSelect an action:",
        parse_mode='HTML',
        reply_markup=build_main_menu()
    )
    return MAIN_MENU


# ==================== CLUB HANDLERS ====================

@admin_only_callback
async def club_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle club menu button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "club_create":
        await query.edit_message_text(
            "➕ <b>Create New Club</b>\n\n"
            "Enter the club name:",
            parse_mode='HTML',
            reply_markup=build_cancel_button()
        )
        return CREATE_CLUB_NAME
    
    elif data == "club_list":
        with get_session_scope(Session) as session:
            clubs = session.query(Club).all()
            
            if not clubs:
                await query.edit_message_text(
                    "📋 <b>All Clubs</b>\n\nNo clubs found.",
                    parse_mode='HTML',
                    reply_markup=build_back_button("back_clubs")
                )
                return CLUB_MENU
            
            keyboard = []
            for club in clubs:
                user_count = len(club.users)
                keyboard.append([
                    InlineKeyboardButton(
                        f"{club.name} ({user_count} members)",
                        callback_data=f"viewclub_{club.id}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_clubs")])
            
            await query.edit_message_text(
                "📋 <b>All Clubs</b>\n\nSelect a club to view details:",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return CLUB_MENU
    
    elif data.startswith("viewclub_"):
        club_id = int(data.split("_")[1])
        with get_session_scope(Session) as session:
            from sqlalchemy import func
            from datetime import date
            
            club = session.query(Club).filter_by(id=club_id).first()
            users = session.query(User).filter_by(club_id=club_id).all()
            books = session.query(Book).filter_by(club_id=club_id).all()
            
            goal_info = f"{club.daily_min_prl}p PRL + {club.daily_min_rnk}p RNK" if club.goal_type == 'SEPARATE' else f"{club.daily_min_total}p total"
            
            # Calculate total pages read in club
            user_ids = [u.id for u in users]
            total_pages = 0
            if user_ids:
                total_pages = session.query(
                    func.sum(DailyLog.pages_read_prl + DailyLog.pages_read_rnk)
                ).filter(DailyLog.user_id.in_(user_ids)).scalar() or 0
            
            # Today's reports
            today = date.today()
            today_reports = 0
            if user_ids:
                today_reports = session.query(DailyLog).filter(
                    DailyLog.user_id.in_(user_ids),
                    func.date(DailyLog.date) == today
                ).count()
            
            # Top readers
            top_users = sorted(users, key=lambda u: u.xp, reverse=True)[:3]
            
            text = (
                f"📋 <b>{club.name}</b>\n\n"
                f"<b>📌 Info</b>\n"
                f"├ Key: <code>{club.key}</code>\n"
                f"├ Type: {club.goal_type}\n"
                f"└ Daily Goal: {goal_info}\n\n"
                f"<b>📊 Stats</b>\n"
                f"├ Members: {len(users)}\n"
                f"├ Books: {len(books)}\n"
                f"├ Total Pages: {total_pages:,}\n"
                f"└ Today's Reports: {today_reports}/{len(users)}\n\n"
            )
            
            # Top readers
            if top_users:
                text += "<b>🏆 Top Readers</b>\n"
                medals = ["🥇", "🥈", "🥉"]
                for i, user in enumerate(top_users):
                    text += f"{medals[i]} {user.full_name} - {user.xp} XP\n"
                text += "\n"
            
            # Top 5 popular books (most users reading/finished)
            if books:
                # Count how many users are reading each book
                book_popularity = []
                for book in books:
                    reader_count = session.query(UserBook).filter_by(book_id=book.id).count()
                    book_popularity.append((book, reader_count))
                
                # Sort by popularity (most readers first)
                book_popularity.sort(key=lambda x: x[1], reverse=True)
                
                text += "<b>📚 Top Books</b>\n"
                for book, count in book_popularity[:5]:
                    text += f"• {book.title} ({count} readers)\n"
                text += "\n"
            
            # Member list
            if users:
                text += "<b>👥 Members</b>\n"
                for user in users:
                    text += f"• {user.full_name} (<code>{user.telegram_id}</code>) Lvl {user.level} 🔥{user.streak}\n"
            else:
                text += "<i>No members yet</i>\n"
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=build_back_button("club_list")
        )
        return CLUB_MENU
    
    elif data == "club_delete":
        with get_session_scope(Session) as session:
            clubs = session.query(Club).all()
            if not clubs:
                await query.edit_message_text(
                    "No clubs to delete.",
                    reply_markup=build_back_button("back_clubs")
                )
                return CLUB_MENU
            
            await query.edit_message_text(
                "🗑️ <b>Delete Club</b>\n\nSelect a club to delete:\n\n⚠️ This will remove all club data!",
                parse_mode='HTML',
                reply_markup=build_club_selector(clubs, "delete_club")
            )
        return CLUB_MENU
    
    elif data == "back_clubs":
        await query.edit_message_text(
            "📋 <b>Club Management</b>\n\nSelect an action:",
            parse_mode='HTML',
            reply_markup=build_club_menu()
        )
        return CLUB_MENU
    
    elif data.startswith("delete_club_"):
        club_id = int(data.split("_")[2])
        with get_session_scope(Session) as session:
            club = session.query(Club).filter_by(id=club_id).first()
            if club:
                club_name = club.name
                # Delete related data
                session.query(UserBook).filter(UserBook.user_id.in_(
                    session.query(User.id).filter_by(club_id=club_id)
                )).delete(synchronize_session=False)
                session.query(DailyLog).filter(DailyLog.user_id.in_(
                    session.query(User.id).filter_by(club_id=club_id)
                )).delete(synchronize_session=False)
                session.query(User).filter_by(club_id=club_id).delete()
                session.query(Book).filter_by(club_id=club_id).delete()
                session.delete(club)
                
                await query.edit_message_text(
                    f"✅ Club <b>{club_name}</b> deleted successfully.",
                    parse_mode='HTML',
                    reply_markup=build_back_button("back_clubs")
                )
            else:
                await query.edit_message_text(
                    "Club not found.",
                    reply_markup=build_back_button("back_clubs")
                )
        return CLUB_MENU
    
    return CLUB_MENU


async def create_club_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: Get club name"""
    context.user_data['new_club_name'] = update.message.text
    
    await update.message.reply_text(
        "Select the goal type for this club:",
        reply_markup=build_club_type_selector()
    )
    return CREATE_CLUB_TYPE


@admin_only_callback
async def create_club_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2: Get club goal type"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_action":
        await query.edit_message_text("Club creation cancelled.")
        return ConversationHandler.END
    
    goal_type = query.data.split("_")[1]  # SEPARATE or OVERALL
    context.user_data['new_club_type'] = goal_type
    
    if goal_type == "SEPARATE":
        await query.edit_message_text(
            "Enter the <b>minimum daily pages for PRL</b> (Personal Reading List):\n\n"
            "Example: <code>5</code>",
            parse_mode='HTML',
            reply_markup=build_cancel_button()
        )
        return CREATE_CLUB_GOALS_PRL
    else:
        await query.edit_message_text(
            "Enter the <b>minimum total daily pages</b>:\n\n"
            "Example: <code>10</code>",
            parse_mode='HTML',
            reply_markup=build_cancel_button()
        )
        return CREATE_CLUB_GOALS_TOTAL


async def create_club_goals_prl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3a: Get PRL goal"""
    try:
        prl_goal = int(update.message.text)
        context.user_data['new_club_prl'] = prl_goal
        
        await update.message.reply_text(
            "Enter the <b>minimum daily pages for RNK</b> (Ranked/Challenge books):\n\n"
            "Example: <code>5</code>",
            parse_mode='HTML',
            reply_markup=build_cancel_button()
        )
        return CREATE_CLUB_GOALS_RNK
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return CREATE_CLUB_GOALS_PRL


async def create_club_goals_rnk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3b: Get RNK goal and create club"""
    try:
        rnk_goal = int(update.message.text)
        
        # Create the club
        with get_session_scope(Session) as session:
            club = Club(
                name=context.user_data['new_club_name'],
                key=str(uuid.uuid4())[:8].upper(),
                goal_type='SEPARATE',
                daily_min_prl=context.user_data['new_club_prl'],
                daily_min_rnk=rnk_goal,
                daily_min_total=0
            )
            session.add(club)
            session.flush()
            
            await update.message.reply_text(
                f"✅ <b>Club Created Successfully!</b>\n\n"
                f"<b>Name:</b> {club.name}\n"
                f"<b>Key:</b> <code>{club.key}</code>\n"
                f"<b>Type:</b> Separate Goals\n"
                f"<b>PRL Goal:</b> {club.daily_min_prl} pages/day\n"
                f"<b>RNK Goal:</b> {club.daily_min_rnk} pages/day\n\n"
                f"Share the key with members to join!",
                parse_mode='HTML'
            )
        
        # Clear user data
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return CREATE_CLUB_GOALS_RNK


async def create_club_goals_total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3c: Get total goal and create club"""
    try:
        total_goal = int(update.message.text)
        
        # Create the club
        with get_session_scope(Session) as session:
            club = Club(
                name=context.user_data['new_club_name'],
                key=str(uuid.uuid4())[:8].upper(),
                goal_type='OVERALL',
                daily_min_prl=0,
                daily_min_rnk=0,
                daily_min_total=total_goal
            )
            session.add(club)
            session.flush()
            
            await update.message.reply_text(
                f"✅ <b>Club Created Successfully!</b>\n\n"
                f"<b>Name:</b> {club.name}\n"
                f"<b>Key:</b> <code>{club.key}</code>\n"
                f"<b>Type:</b> Overall Goal\n"
                f"<b>Daily Goal:</b> {club.daily_min_total} pages/day\n\n"
                f"Share the key with members to join!",
                parse_mode='HTML'
            )
        
        # Clear user data
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return CREATE_CLUB_GOALS_TOTAL


async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current action"""
    query = update.callback_query
    await query.answer()
    
    context.user_data.clear()
    await query.edit_message_text("Action cancelled.")
    return ConversationHandler.END


# ==================== BOOK HANDLERS ====================

@admin_only_callback
async def book_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle book menu button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "book_add":
        # Show club selector for adding book
        with get_session_scope(Session) as session:
            clubs = session.query(Club).all()
            if not clubs:
                await query.edit_message_text(
                    "No clubs found. Create a club first.",
                    reply_markup=build_back_button("back_books")
                )
                return BOOK_MENU
            
            await query.edit_message_text(
                "➕ <b>Add Book</b>\n\nSelect a club:",
                parse_mode='HTML',
                reply_markup=build_club_selector(clubs, "addbook")
            )
        return BOOK_MENU
    
    elif data.startswith("addbook_"):
        club_id = int(data.split("_")[1])
        context.user_data['book_club_id'] = club_id
        
        await query.edit_message_text(
            "Enter the <b>book title</b>:",
            parse_mode='HTML',
            reply_markup=build_cancel_button()
        )
        return ADD_BOOK_TITLE
    
    elif data == "book_list":
        with get_session_scope(Session) as session:
            clubs = session.query(Club).all()
            if not clubs:
                await query.edit_message_text(
                    "No clubs found.",
                    reply_markup=build_back_button("back_books")
                )
                return BOOK_MENU
            
            await query.edit_message_text(
                "📋 <b>List Books</b>\n\nSelect a club:",
                parse_mode='HTML',
                reply_markup=build_club_selector(clubs, "listbooks")
            )
        return BOOK_MENU
    
    elif data.startswith("listbooks_"):
        club_id = int(data.split("_")[1])
        with get_session_scope(Session) as session:
            club = session.query(Club).filter_by(id=club_id).first()
            books = session.query(Book).filter_by(club_id=club_id).all()
            
            if not books:
                text = f"📚 <b>Books in {club.name}</b>\n\nNo books found."
            else:
                text = f"📚 <b>Books in {club.name}</b>\n\n"
                for book in books:
                    text += f"#{book.id} <b>{book.title}</b> ({book.total_pages}p)\n"
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=build_back_button("back_books")
        )
        return BOOK_MENU
    
    elif data == "book_delete":
        with get_session_scope(Session) as session:
            clubs = session.query(Club).all()
            if not clubs:
                await query.edit_message_text(
                    "No clubs found.",
                    reply_markup=build_back_button("back_books")
                )
                return BOOK_MENU
            
            await query.edit_message_text(
                "🗑️ <b>Delete Book</b>\n\nSelect a club:",
                parse_mode='HTML',
                reply_markup=build_club_selector(clubs, "delbook_club")
            )
        return BOOK_MENU
    
    elif data.startswith("delbook_club_"):
        club_id = int(data.split("_")[2])
        with get_session_scope(Session) as session:
            books = session.query(Book).filter_by(club_id=club_id).all()
            
            if not books:
                await query.edit_message_text(
                    "No books in this club.",
                    reply_markup=build_back_button("back_books")
                )
                return BOOK_MENU
            
            keyboard = []
            for book in books:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🗑️ {book.title} ({book.total_pages}p)",
                        callback_data=f"delbook_{book.id}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_books")])
            
            await query.edit_message_text(
                "🗑️ <b>Delete Book</b>\n\nSelect a book to delete:",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return BOOK_MENU
    
    elif data.startswith("delbook_") and not data.startswith("delbook_club"):
        book_id = int(data.split("_")[1])
        with get_session_scope(Session) as session:
            book = session.query(Book).filter_by(id=book_id).first()
            if book:
                title = book.title
                session.query(UserBook).filter_by(book_id=book_id).delete()
                session.delete(book)
                
                await query.edit_message_text(
                    f"✅ Book <b>{title}</b> deleted.",
                    parse_mode='HTML',
                    reply_markup=build_back_button("back_books")
                )
            else:
                await query.edit_message_text(
                    "Book not found.",
                    reply_markup=build_back_button("back_books")
                )
        return BOOK_MENU
    
    elif data == "back_books":
        await query.edit_message_text(
            "📚 <b>Book Management</b>\n\nSelect an action:",
            parse_mode='HTML',
            reply_markup=build_book_menu()
        )
        return BOOK_MENU
    
    return BOOK_MENU


async def add_book_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get book title"""
    context.user_data['book_title'] = update.message.text
    
    await update.message.reply_text(
        "Enter the <b>total number of pages</b>:",
        parse_mode='HTML',
        reply_markup=build_cancel_button()
    )
    return ADD_BOOK_PAGES


async def add_book_pages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get book pages and create book"""
    try:
        pages = int(update.message.text)
        
        with get_session_scope(Session) as session:
            book = Book(
                title=context.user_data['book_title'],
                total_pages=pages,
                club_id=context.user_data['book_club_id']
            )
            session.add(book)
            session.flush()
            
            await update.message.reply_text(
                f"✅ <b>Book Added!</b>\n\n"
                f"<b>Title:</b> {book.title}\n"
                f"<b>Pages:</b> {book.total_pages}\n"
                f"<b>ID:</b> #{book.id}",
                parse_mode='HTML'
            )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return ADD_BOOK_PAGES


# ==================== USER HANDLERS ====================

@admin_only_callback
async def user_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user menu button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "user_list":
        with get_session_scope(Session) as session:
            users = session.query(User).all()
            
            if not users:
                await query.edit_message_text(
                    "👥 <b>All Users</b>\n\nNo users found.",
                    parse_mode='HTML',
                    reply_markup=build_back_button("back_users")
                )
                return USER_MENU
            
            keyboard = []
            for user in users:
                club_name = user.club.name if user.club else "No Club"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{user.full_name} ({club_name})",
                        callback_data=f"viewuser_{user.id}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_users")])
            
            await query.edit_message_text(
                f"👥 <b>All Users</b> ({len(users)} total)\n\nSelect a user to view profile:",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return USER_MENU
    
    elif data.startswith("viewuser_"):
        user_id = int(data.split("_")[1])
        with get_session_scope(Session) as session:
            from utils import calculate_reading_stats, generate_contribution_graph
            from gamification import get_xp_for_next_level
            import html
            
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                await query.edit_message_text(
                    "User not found.",
                    reply_markup=build_back_button("user_list")
                )
                return USER_MENU
            
            logs = user.logs
            
            # Generate graph
            graph_buf = generate_contribution_graph(logs)
            
            # Calculate stats
            stats = calculate_reading_stats(user)
            
            # Progress Bar for Level
            next_level_xp = get_xp_for_next_level(user.level)
            prev_level_xp = get_xp_for_next_level(user.level - 1)
            level_range = next_level_xp - prev_level_xp
            current_progress = user.xp - prev_level_xp
            percent = min(1.0, max(0.0, current_progress / level_range)) if level_range > 0 else 0
            bar_len = 10
            filled = int(bar_len * percent)
            bar = "█" * filled + "░" * (bar_len - filled)
            
            badges_str = " ".join([b.badge.icon for b in user.badges]) if user.badges else "None"
            
            safe_name = html.escape(user.full_name)
            club_info = f"{user.club.name}" if user.club else "No Club"
            
            # Build reading speed info
            speed_info = ""
            if stats['reading_speed']:
                speed_info = "\n\n📈 <b>Reading Speed:</b>\n"
                for book_title, days in list(stats['reading_speed'].items())[:2]:
                    speed_info += f"• <i>{book_title}</i>: ~{days} days to finish\n"
            
            caption = (
                f"👤 <b>{safe_name}</b>\n"
                f"🏢 {club_info}\n"
                f"🆔 <code>{user.telegram_id}</code>\n\n"
                
                f"<b>📊 Level & Progress</b>\n"
                f"🏆 Level {user.level} ({user.xp} XP)\n"
                f"<code>[{bar}]</code> {int(percent*100)}%\n\n"
                
                f"<b>🔥 Streak Info</b>\n"
                f"Current: {user.streak} days | Best: {stats['best_streak']} days\n\n"
                
                f"<b>📚 Reading Stats</b>\n"
                f"📖 Books Finished: {stats['total_books_finished']}\n"
                f"📄 Total Pages: {stats['total_pages_read']:,}\n"
                f"📅 Active Days: {stats['days_active']}\n\n"
                
                f"<b>📈 Averages</b>\n"
                f"Last 7 days: {stats['avg_pages_week']} pages/day\n"
                f"This month: {stats['avg_pages_month']} pages/day\n"
                f"All time: {stats['avg_pages_all_time']} pages/day\n"
                f"Most productive: {stats['most_productive_day']}"
                f"{speed_info}\n"
                f"🏅 <b>Badges:</b> {badges_str}"
            )
            
            # Delete the callback message and send photo
            await query.message.delete()
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=graph_buf,
                caption=caption,
                parse_mode='HTML'
            )
        return ConversationHandler.END
    
    elif data == "user_kick":
        with get_session_scope(Session) as session:
            clubs = session.query(Club).all()
            if not clubs:
                await query.edit_message_text(
                    "No clubs found.",
                    reply_markup=build_back_button("back_users")
                )
                return USER_MENU
            
            await query.edit_message_text(
                "🚫 <b>Kick User</b>\n\nSelect a club:",
                parse_mode='HTML',
                reply_markup=build_club_selector(clubs, "kickuser_club")
            )
        return USER_MENU
    
    elif data.startswith("kickuser_club_"):
        club_id = int(data.split("_")[2])
        with get_session_scope(Session) as session:
            users = session.query(User).filter_by(club_id=club_id).all()
            
            if not users:
                await query.edit_message_text(
                    "No users in this club.",
                    reply_markup=build_back_button("back_users")
                )
                return USER_MENU
            
            keyboard = []
            for user in users:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🚫 {user.full_name}",
                        callback_data=f"kickuser_{user.id}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_users")])
            
            await query.edit_message_text(
                "🚫 <b>Kick User</b>\n\nSelect a user to remove:",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return USER_MENU
    
    elif data.startswith("kickuser_") and not data.startswith("kickuser_club"):
        user_id = int(data.split("_")[1])
        with get_session_scope(Session) as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                name = user.full_name
                session.query(UserBook).filter_by(user_id=user_id).delete()
                session.query(DailyLog).filter_by(user_id=user_id).delete()
                session.delete(user)
                
                await query.edit_message_text(
                    f"✅ User <b>{name}</b> removed.",
                    parse_mode='HTML',
                    reply_markup=build_back_button("back_users")
                )
            else:
                await query.edit_message_text(
                    "User not found.",
                    reply_markup=build_back_button("back_users")
                )
        return USER_MENU
    
    elif data == "user_reset":
        with get_session_scope(Session) as session:
            clubs = session.query(Club).all()
            if not clubs:
                await query.edit_message_text(
                    "No clubs found.",
                    reply_markup=build_back_button("back_users")
                )
                return USER_MENU
            
            await query.edit_message_text(
                "🔄 <b>Reset User</b>\n\nSelect a club:",
                parse_mode='HTML',
                reply_markup=build_club_selector(clubs, "resetuser_club")
            )
        return USER_MENU
    
    elif data.startswith("resetuser_club_"):
        club_id = int(data.split("_")[2])
        with get_session_scope(Session) as session:
            users = session.query(User).filter_by(club_id=club_id).all()
            
            if not users:
                await query.edit_message_text(
                    "No users in this club.",
                    reply_markup=build_back_button("back_users")
                )
                return USER_MENU
            
            keyboard = []
            for user in users:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🔄 {user.full_name}",
                        callback_data=f"resetuser_{user.id}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_users")])
            
            await query.edit_message_text(
                "🔄 <b>Reset User</b>\n\nSelect a user to reset (keeps account, clears progress):",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return USER_MENU
    
    elif data.startswith("resetuser_") and not data.startswith("resetuser_club"):
        user_id = int(data.split("_")[1])
        with get_session_scope(Session) as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                name = user.full_name
                user.xp = 0
                user.level = 1
                user.streak = 0
                user.best_streak = 0
                session.query(DailyLog).filter_by(user_id=user_id).delete()
                
                await query.edit_message_text(
                    f"✅ User <b>{name}</b> progress reset.",
                    parse_mode='HTML',
                    reply_markup=build_back_button("back_users")
                )
            else:
                await query.edit_message_text(
                    "User not found.",
                    reply_markup=build_back_button("back_users")
                )
        return USER_MENU
    
    elif data == "user_profile":
        await query.edit_message_text(
            "👤 <b>View Profile</b>\n\nEnter the user's Telegram ID:",
            parse_mode='HTML',
            reply_markup=build_cancel_button()
        )
        return SELECT_USER
    
    elif data == "back_users":
        await query.edit_message_text(
            "👥 <b>User Management</b>\n\nSelect an action:",
            parse_mode='HTML',
            reply_markup=build_user_menu()
        )
        return USER_MENU
    
    return USER_MENU


async def view_user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View a user's profile by Telegram ID"""
    try:
        telegram_id = int(update.message.text)
        
        with get_session_scope(Session) as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            
            if not user:
                await update.message.reply_text(
                    "User not found.",
                    reply_markup=build_back_button("back_users")
                )
                return ConversationHandler.END
            
            club_name = user.club.name if user.club else "None"
            
            text = (
                f"👤 <b>{user.full_name}</b>\n\n"
                f"<b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
                f"<b>Club:</b> {club_name}\n"
                f"<b>Level:</b> {user.level}\n"
                f"<b>XP:</b> {user.xp}\n"
                f"<b>Streak:</b> {user.streak} days\n"
                f"<b>Best Streak:</b> {user.best_streak} days\n"
                f"<b>Books:</b> {len(user.readings)}\n"
                f"<b>Logs:</b> {len(user.logs)}\n"
            )
            
            await update.message.reply_text(text, parse_mode='HTML')
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("Please enter a valid Telegram ID (numbers only).")
        return SELECT_USER


# ==================== STATS HANDLERS ====================

@admin_only_callback
async def stats_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stats menu button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "stats_club":
        with get_session_scope(Session) as session:
            clubs = session.query(Club).all()
            if not clubs:
                await query.edit_message_text(
                    "No clubs found.",
                    reply_markup=build_back_button("back_stats")
                )
                return STATS_MENU
            
            await query.edit_message_text(
                "📊 <b>Club Statistics</b>\n\nSelect a club:",
                parse_mode='HTML',
                reply_markup=build_club_selector(clubs, "clubstats")
            )
        return STATS_MENU
    
    elif data.startswith("clubstats_"):
        club_id = int(data.split("_")[1])
        with get_session_scope(Session) as session:
            from sqlalchemy import func
            from datetime import date
            
            club = session.query(Club).filter_by(id=club_id).first()
            users = session.query(User).filter_by(club_id=club_id).all()
            books = session.query(Book).filter_by(club_id=club_id).all()
            
            today = date.today()
            today_logs = session.query(DailyLog).filter(
                DailyLog.user_id.in_([u.id for u in users]),
                func.date(DailyLog.date) == today
            ).all()
            
            total_pages = session.query(
                func.sum(DailyLog.pages_read_prl + DailyLog.pages_read_rnk)
            ).filter(DailyLog.user_id.in_([u.id for u in users])).scalar() or 0
            
            text = (
                f"📊 <b>{club.name} Statistics</b>\n\n"
                f"<b>Members:</b> {len(users)}\n"
                f"<b>Books:</b> {len(books)}\n"
                f"<b>Total Pages Read:</b> {total_pages}\n"
                f"<b>Today's Reports:</b> {len(today_logs)}/{len(users)}\n\n"
                f"<b>Goal Type:</b> {club.goal_type}\n"
            )
            
            if club.goal_type == 'SEPARATE':
                text += f"<b>Daily Goal:</b> {club.daily_min_prl}p PRL + {club.daily_min_rnk}p RNK\n"
            else:
                text += f"<b>Daily Goal:</b> {club.daily_min_total}p total\n"
            
            # Top readers
            if users:
                top_users = sorted(users, key=lambda u: u.xp, reverse=True)[:5]
                text += "\n<b>🏆 Top Readers:</b>\n"
                for i, user in enumerate(top_users, 1):
                    text += f"{i}. {user.full_name} - {user.xp} XP\n"
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=build_back_button("back_stats")
        )
        return STATS_MENU
    
    elif data == "stats_leaderboard":
        with get_session_scope(Session) as session:
            clubs = session.query(Club).all()
            if not clubs:
                await query.edit_message_text(
                    "No clubs found.",
                    reply_markup=build_back_button("back_stats")
                )
                return STATS_MENU
            
            await query.edit_message_text(
                "🏆 <b>Leaderboard</b>\n\nSelect a club:",
                parse_mode='HTML',
                reply_markup=build_club_selector(clubs, "leaderboard")
            )
        return STATS_MENU
    
    elif data.startswith("leaderboard_"):
        club_id = int(data.split("_")[1])
        with get_session_scope(Session) as session:
            club = session.query(Club).filter_by(id=club_id).first()
            users = session.query(User).filter_by(club_id=club_id).order_by(User.xp.desc()).all()
            
            if not users:
                text = f"🏆 <b>Leaderboard - {club.name}</b>\n\nNo users yet."
            else:
                text = f"🏆 <b>Leaderboard - {club.name}</b>\n\n"
                medals = ["🥇", "🥈", "🥉"]
                for i, user in enumerate(users, 1):
                    medal = medals[i-1] if i <= 3 else f"{i}."
                    text += f"{medal} <b>{user.full_name}</b>\n   Level {user.level} | {user.xp} XP | 🔥{user.streak}\n\n"
        
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=build_back_button("back_stats")
        )
        return STATS_MENU
    
    elif data == "back_stats":
        await query.edit_message_text(
            "📊 <b>Statistics</b>\n\nSelect an action:",
            parse_mode='HTML',
            reply_markup=build_stats_menu()
        )
        return STATS_MENU
    
    return STATS_MENU


# ==================== BROADCAST HANDLERS ====================

@admin_only_callback
async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast target selection"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "broadcast_all":
        context.user_data['broadcast_target'] = 'all'
        await query.edit_message_text(
            "📢 <b>Broadcast to ALL Users</b>\n\n"
            "Enter the message to send:",
            parse_mode='HTML',
            reply_markup=build_cancel_button()
        )
        return BROADCAST_MESSAGE
    
    elif data.startswith("broadcast_"):
        club_id = int(data.split("_")[1])
        context.user_data['broadcast_target'] = 'club'
        context.user_data['broadcast_club_id'] = club_id
        
        await query.edit_message_text(
            "📢 <b>Broadcast to Club</b>\n\n"
            "Enter the message to send:",
            parse_mode='HTML',
            reply_markup=build_cancel_button()
        )
        return BROADCAST_MESSAGE
    
    return BROADCAST_CLUB


async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast message to selected target"""
    message = update.message.text
    target = context.user_data.get('broadcast_target', 'all')
    
    with get_session_scope(Session) as session:
        if target == 'all':
            users = session.query(User).all()
            header = "📢 <b>Announcement</b>"
        else:
            club_id = context.user_data.get('broadcast_club_id')
            club = session.query(Club).filter_by(id=club_id).first()
            users = session.query(User).filter_by(club_id=club_id).all()
            header = f"📢 <b>Announcement from {club.name}</b>"
        
        if not users:
            await update.message.reply_text("No users to send to.")
            return ConversationHandler.END
        
        sent_count = 0
        failed_count = 0
        
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"{header}\n\n{message}",
                    parse_mode='HTML'
                )
                sent_count += 1
            except Exception:
                failed_count += 1
        
        await update.message.reply_text(
            f"✅ Broadcast sent!\n\n"
            f"<b>Sent:</b> {sent_count}\n"
            f"<b>Failed:</b> {failed_count}",
            parse_mode='HTML'
        )
    
    context.user_data.clear()
    return ConversationHandler.END

admin_panel_conv = ConversationHandler(
    entry_points=[CommandHandler('admin', admin_panel)],
    states={
        MAIN_MENU: [
            CallbackQueryHandler(main_menu_handler),
        ],
        CLUB_MENU: [
            CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            CallbackQueryHandler(club_menu_handler),
        ],
        BOOK_MENU: [
            CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            CallbackQueryHandler(book_menu_handler),
        ],
        USER_MENU: [
            CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            CallbackQueryHandler(user_menu_handler),
        ],
        STATS_MENU: [
            CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            CallbackQueryHandler(stats_menu_handler),
        ],
        BROADCAST_CLUB: [
            CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            CallbackQueryHandler(broadcast_handler),
        ],
        BROADCAST_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast),
            CallbackQueryHandler(cancel_action, pattern="^cancel_action$"),
        ],
        CREATE_CLUB_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_club_name),
            CallbackQueryHandler(cancel_action, pattern="^cancel_action$"),
        ],
        CREATE_CLUB_TYPE: [
            CallbackQueryHandler(create_club_type),
        ],
        CREATE_CLUB_GOALS_PRL: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_club_goals_prl),
            CallbackQueryHandler(cancel_action, pattern="^cancel_action$"),
        ],
        CREATE_CLUB_GOALS_RNK: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_club_goals_rnk),
            CallbackQueryHandler(cancel_action, pattern="^cancel_action$"),
        ],
        CREATE_CLUB_GOALS_TOTAL: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_club_goals_total),
            CallbackQueryHandler(cancel_action, pattern="^cancel_action$"),
        ],
        ADD_BOOK_TITLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_book_title),
            CallbackQueryHandler(cancel_action, pattern="^cancel_action$"),
        ],
        ADD_BOOK_PAGES: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_book_pages),
            CallbackQueryHandler(cancel_action, pattern="^cancel_action$"),
        ],
        SELECT_USER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, view_user_profile),
            CallbackQueryHandler(cancel_action, pattern="^cancel_action$"),
        ],
    },
    fallbacks=[
        CommandHandler('cancel', lambda u, c: ConversationHandler.END),
        CallbackQueryHandler(cancel_action, pattern="^cancel_action$"),
    ],
    per_message=False,
)
