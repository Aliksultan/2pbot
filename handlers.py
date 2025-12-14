from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from database import init_db, User, Club, Book, UserBook, DailyLog, get_session_scope
from utils import get_today_date, generate_contribution_graph
from gamification import award_xp, check_badges, XP_PER_PAGE, XP_STREAK_BONUS, XP_BOOK_FINISHED, get_xp_for_next_level

Session = init_db()

# States
ENTER_KEY = 0
SELECT_BOOKS_PRL = 1
SELECT_BOOKS_RNK = 2
ENTER_PAGES_PRL = 3
ENTER_PAGES_RNK = 4
REPORT_PRL = 5
REPORT_RNK = 6
SELECT_STATUS_PRL = 7
SELECT_STATUS_RNK = 8
ENTER_CURRENT_PAGE_PRL = 9
ENTER_CURRENT_PAGE_RNK = 10

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name
    
    with get_session_scope(Session) as session:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        
        if not user:
            user = User(telegram_id=user_id, username=username, full_name=full_name)
            session.add(user)
            await update.message.reply_text(
                "👋 <b>Welcome to the Reading Club Bot!</b>\n\n"
                "To join your club, please enter the <b>Club Key</b> provided by your admin.\n"
                "<i>(If you don't have one, ask your club administrator!)</i>",
                parse_mode='HTML'
            )
            return ENTER_KEY
        else:
            if user.club_id:
                club_name = user.club.name if user.club else "Unknown"
                await update.message.reply_text(
                    f"📚 You are already in <b>{club_name}</b>.\n\n"
                    f"Use /report to log your reading.\n"
                    f"Use /change_club to switch to a different club.",
                    parse_mode='HTML'
                )
                return ConversationHandler.END
            else:
                await update.message.reply_text("Please enter your <b>Club Key</b> to join:", parse_mode='HTML')
                return ENTER_KEY

async def enter_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text
    with get_session_scope(Session) as session:
        club = session.query(Club).filter_by(key=key).first()
        
        if club:
            user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
            old_club_id = user.club_id
            
            # Check if this is a club change
            is_club_change = old_club_id is not None
            
            user.club_id = club.id
            
            context.user_data['club_id'] = club.id
            
            if is_club_change:
                # User is changing clubs - preserve all their data
                await update.message.reply_text(
                    f"✅ <b>Club Changed!</b>\n\n"
                    f"You've successfully joined <b>{club.name}</b>!\n\n"
                    f"📊 Your stats, streak, and progress have been preserved.\n"
                    f"📚 Use /my_books to add books from the new club library.\n"
                    f"📖 Use /report to continue your reading journey!",
                    parse_mode='HTML',
                    reply_markup=ReplyKeyboardRemove()
                )
                return ConversationHandler.END
            else:
                # New user joining for first time
                context.user_data['selected_prl'] = []
                context.user_data['selected_rnk'] = []
                
                await show_prl_selection(update, context, session)
                return SELECT_BOOKS_PRL
        else:
            await update.message.reply_text("❌ <b>Invalid Key</b>. Please check with your admin and try again.", parse_mode='HTML')
            return ENTER_KEY

async def show_prl_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, session):
    prl_books = session.query(Book).filter_by(club_id=context.user_data['club_id'], category='PRL').all()
    # Filter out already selected
    selected_ids = [b['id'] for b in context.user_data.get('selected_prl', [])]
    available_books = [b for b in prl_books if b.id not in selected_ids]
    
    buttons = [[InlineKeyboardButton(b.title, callback_data=f"prl_{b.id}")] for b in available_books]
    if context.user_data.get('selected_prl'):
        buttons.append([InlineKeyboardButton("✅ Done", callback_data="prl_done")])
        
    await update.message.reply_text(
        "Choose a book from the PRL category (Select multiple, click Done when finished):",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def select_books_prl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "prl_done":
        if not context.user_data.get('selected_prl'):
            await query.edit_message_text("Please select at least one PRL book.")
            return SELECT_BOOKS_PRL
            
        with get_session_scope(Session) as session:
            await show_rnk_selection(query, context, session)
        return SELECT_BOOKS_RNK
        
    with get_session_scope(Session) as session:
        book_id = int(query.data.split('_')[1])
        book = session.query(Book).get(book_id)
        
        if book:
            context.user_data['current_book_id'] = book.id
            context.user_data['current_category'] = 'PRL'
            await query.edit_message_text(
                f"How many pages does '{book.title}' have?"
            )
            return ENTER_PAGES_PRL
        else:
            await query.edit_message_text("Invalid book. Please try again.")
            return SELECT_BOOKS_PRL

async def enter_pages_prl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pages = int(update.message.text)
        book_id = context.user_data['current_book_id']
        
        # Store total pages temporarily
        context.user_data['temp_total_pages'] = pages
        context.user_data['temp_book_id'] = book_id
        
        # Get book title for display
        with get_session_scope(Session) as session:
            book = session.query(Book).get(book_id)
            book_title = book.title if book else "this book"
        
        # Ask for book status
        keyboard = [
            [InlineKeyboardButton("🆕 Starting fresh (page 0)", callback_data="status_prl_fresh")],
            [InlineKeyboardButton("📖 Continue from page", callback_data="status_prl_continue")]
        ]
        await update.message.reply_text(
            f"📚 <b>{book_title}</b>\n\n"
            f"Are you starting fresh or continuing?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return SELECT_STATUS_PRL
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return ENTER_PAGES_PRL

async def select_status_prl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    book_id = context.user_data['temp_book_id']
    total_pages = context.user_data['temp_total_pages']
    
    if query.data == "status_prl_fresh":
        # Starting fresh - save with current_page = 0
        context.user_data.setdefault('selected_prl', []).append({
            'id': book_id,
            'total_pages': total_pages,
            'current_page': 0
        })
        
        await query.edit_message_text("✅ Book added (starting from page 0)")
        
        with get_session_scope(Session) as session:
            await show_prl_selection(query, context, session)
        return SELECT_BOOKS_PRL
        
    else:  # Continue from page
        await query.edit_message_text(
            f"📖 <b>What page are you on?</b>\n\n"
            f"Enter the page number (1-{total_pages}):",
            parse_mode='HTML'
        )
        return ENTER_CURRENT_PAGE_PRL

async def enter_current_page_prl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        current_page = int(update.message.text)
        total_pages = context.user_data['temp_total_pages']
        book_id = context.user_data['temp_book_id']
        
        if current_page < 0 or current_page > total_pages:
            await update.message.reply_text(
                f"❌ Invalid page number!\n\n"
                f"Please enter a number between 0 and {total_pages}:"
            )
            return ENTER_CURRENT_PAGE_PRL
        
        # Save with current page
        context.user_data.setdefault('selected_prl', []).append({
            'id': book_id,
            'total_pages': total_pages,
            'current_page': current_page
        })
        
        progress_pct = int((current_page / total_pages) * 100) if total_pages > 0 else 0
        await update.message.reply_text(
            f"✅ Book added!\n"
            f"📖 Progress: {current_page}/{total_pages} ({progress_pct}%)"
        )
        
        with get_session_scope(Session) as session:
            await show_prl_selection(update, context, session)
        return SELECT_BOOKS_PRL
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid page number.")
        return ENTER_CURRENT_PAGE_PRL

async def show_rnk_selection(update_or_query, context: ContextTypes.DEFAULT_TYPE, session):
    rnk_books = session.query(Book).filter_by(club_id=context.user_data['club_id'], category='RNK').all()
    # Filter out already selected
    selected_ids = [b['id'] for b in context.user_data.get('selected_rnk', [])]
    available_books = [b for b in rnk_books if b.id not in selected_ids]
    
    buttons = [[InlineKeyboardButton(b.title, callback_data=f"rnk_{b.id}")] for b in available_books]
    if context.user_data.get('selected_rnk'):
        buttons.append([InlineKeyboardButton("✅ Done", callback_data="rnk_done")])
    
    text = "Choose a book from the RNK category (Select multiple, click Done when finished):"
    # Handle both message and callback query
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update_or_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def select_books_rnk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "rnk_done":
        if not context.user_data.get('selected_rnk'):
            await query.edit_message_text("Please select at least one RNK book.")
            return SELECT_BOOKS_RNK
            
        # Save all books
        with get_session_scope(Session) as session:
            user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
            
            for b in context.user_data['selected_prl']:
                ub = UserBook(
                    user_id=user.id, 
                    book_id=b['id'], 
                    total_pages=b['total_pages'],
                    current_page=b.get('current_page', 0)
                )
                session.add(ub)
                
            for b in context.user_data['selected_rnk']:
                ub = UserBook(
                    user_id=user.id, 
                    book_id=b['id'], 
                    total_pages=b['total_pages'],
                    current_page=b.get('current_page', 0)
                )
                session.add(ub)
            
        await query.edit_message_text("✅ Setup complete! You will receive daily check-ins at 18:00.")
        return ConversationHandler.END
        
    with get_session_scope(Session) as session:
        book_id = int(query.data.split('_')[1])
        book = session.query(Book).get(book_id)
        
        if book:
            context.user_data['current_book_id'] = book.id
            context.user_data['current_category'] = 'RNK'
            await query.edit_message_text(
                f"How many pages does '{book.title}' have?"
            )
            return ENTER_PAGES_RNK
        else:
            await query.edit_message_text("Invalid book. Please try again.")
            return SELECT_BOOKS_RNK

async def enter_pages_rnk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pages = int(update.message.text)
        book_id = context.user_data['current_book_id']
        
        # Store total pages temporarily
        context.user_data['temp_total_pages'] = pages
        context.user_data['temp_book_id'] = book_id
        
        # Get book title for display
        with get_session_scope(Session) as session:
            book = session.query(Book).get(book_id)
            book_title = book.title if book else "this book"
        
        # Ask for book status
        keyboard = [
            [InlineKeyboardButton("🆕 Starting fresh (page 0)", callback_data="status_rnk_fresh")],
            [InlineKeyboardButton("📖 Continue from page", callback_data="status_rnk_continue")]
        ]
        await update.message.reply_text(
            f"📚 <b>{book_title}</b>\n\n"
            f"Are you starting fresh or continuing?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return SELECT_STATUS_RNK
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return ENTER_PAGES_RNK

async def select_status_rnk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    book_id = context.user_data['temp_book_id']
    total_pages = context.user_data['temp_total_pages']
    
    if query.data == "status_rnk_fresh":
        # Starting fresh - save with current_page = 0
        context.user_data.setdefault('selected_rnk', []).append({
            'id': book_id,
            'total_pages': total_pages,
            'current_page': 0
        })
        
        await query.edit_message_text("✅ Book added (starting from page 0)")
        
        with get_session_scope(Session) as session:
            await show_rnk_selection(query, context, session)
        return SELECT_BOOKS_RNK
        
    else:  # Continue from page
        await query.edit_message_text(
            f"📖 <b>What page are you on?</b>\n\n"
            f"Enter the page number (1-{total_pages}):",
            parse_mode='HTML'
        )
        return ENTER_CURRENT_PAGE_RNK

async def enter_current_page_rnk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        current_page = int(update.message.text)
        total_pages = context.user_data['temp_total_pages']
        book_id = context.user_data['temp_book_id']
        
        if current_page < 0 or current_page > total_pages:
            await update.message.reply_text(
                f"❌ Invalid page number!\n\n"
                f"Please enter a number between 0 and {total_pages}:"
            )
            return ENTER_CURRENT_PAGE_RNK
        
        # Save with current page
        context.user_data.setdefault('selected_rnk', []).append({
            'id': book_id,
            'total_pages': total_pages,
            'current_page': current_page
        })
        
        progress_pct = int((current_page / total_pages) * 100) if total_pages > 0 else 0
        await update.message.reply_text(
            f"✅ Book added!\n"
            f"📖 Progress: {current_page}/{total_pages} ({progress_pct}%)"
        )
        
        with get_session_scope(Session) as session:
            await show_rnk_selection(update, context, session)
        return SELECT_BOOKS_RNK
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid page number.")
        return ENTER_CURRENT_PAGE_RNK

# Reporting Flow
async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_session_scope(Session) as session:
        user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
        
        # Only include books that are NOT finished
        active_books = [ub for ub in user.readings if not ub.finished]
        
        if not active_books:
            await update.message.reply_text(
                "📚 You have no active books to report!\n\n"
                "Use /my_books to add books you're currently reading.",
                parse_mode='HTML'
            )
            return ConversationHandler.END
            
        context.user_data['report_queue'] = [ub.id for ub in active_books]
        context.user_data['report_results'] = {'PRL': 0, 'RNK': 0}
    
    return await ask_next_book_report(update, context)

async def ask_next_book_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data['report_queue']:
        return await finish_report(update, context)
        
    ub_id = context.user_data['report_queue'][0]
    with get_session_scope(Session) as session:
        ub = session.query(UserBook).get(ub_id)
        book_title = ub.book.title
    
    await update.message.reply_text(
        f"📖 How many pages of <b>'{book_title}'</b> did you read?\n<i>(This will be added to your total for today)</i>",
        parse_mode='HTML'
    )
    return REPORT_PRL

async def report_book_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pages = int(update.message.text)
        
        if pages < 0:
            await update.message.reply_text("❌ Please enter a positive number.")
            return REPORT_PRL
        
        ub_id = context.user_data['report_queue'].pop(0)
        
        with get_session_scope(Session) as session:
            ub = session.query(UserBook).get(ub_id)
            
            # Calculate how many pages we can actually add (cap at total)
            pages_remaining = max(0, ub.total_pages - ub.current_page)
            actual_pages = min(pages, pages_remaining)
            
            if pages > pages_remaining and pages_remaining > 0:
                await update.message.reply_text(
                    f"⚠️ You only have {pages_remaining} pages left in this book!\n"
                    f"Adding {actual_pages} pages instead."
                )
            elif pages_remaining == 0:
                await update.message.reply_text(f"✅ You've already finished '{ub.book.title}'! No pages added.")
                return await ask_next_book_report(update, context)
            
            # Update current page
            ub.current_page += actual_pages
            
            # Add to category total
            cat = ub.book.category
            context.user_data['report_results'][cat] += actual_pages
            
            # Check if finished
            if ub.current_page >= ub.total_pages:
                ub.finished = True
                ub.finished_date = get_today_date()
                ub.current_page = ub.total_pages # Cap at total
                
                # Check if this was a recommended book for extra bonus
                completion_bonus_msg = ""
                if ub.is_recommended:
                    from recommendations import XP_COMPLETION_BONUS
                    completion_xp = 100 + XP_COMPLETION_BONUS  # Base 100 + recommended bonus
                    completion_bonus_msg = f"\n🌟 <b>RECOMMENDED BOOK COMPLETED!</b>\n🎁 <b>+{XP_COMPLETION_BONUS} XP BONUS!</b>"
                else:
                    completion_xp = 100  # Base completion XP
                
                await update.message.reply_text(
                    f"🎉🎊 <b>CONGRATULATIONS!</b> 🎊🎉\n\n"
                    f"You finished <b>'{ub.book.title}'</b>!\n"
                    f"📚 {ub.total_pages} pages completed!\n\n"
                    f"🏆 <b>+{completion_xp} XP Bonus!</b>{completion_bonus_msg}",
                    parse_mode='HTML'
                )
                context.user_data.setdefault('finished_books_count', 0)
                context.user_data['finished_books_count'] += 1
        
        return await ask_next_book_report(update, context)
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number.")
        return REPORT_PRL

async def finish_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_session_scope(Session) as session:
        user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
        club = user.club
        
        # Get current session report
        prl_read_now = context.user_data['report_results']['PRL']
        rnk_read_now = context.user_data['report_results']['RNK']
        
        # Get existing log to accumulate
        today = get_today_date()
        log = session.query(DailyLog).filter_by(user_id=user.id, date=today).first()
        
        if not log:
            log = DailyLog(user_id=user.id, date=today, status='pending')
            session.add(log)
            
        # Accumulate
        log.pages_read_prl = (log.pages_read_prl or 0) + prl_read_now
        log.pages_read_rnk = (log.pages_read_rnk or 0) + rnk_read_now
        
        # Check status based on TOTAL
        total_prl = log.pages_read_prl
        total_rnk = log.pages_read_rnk
        total_all = total_prl + total_rnk
        
        old_status = log.status
        new_status = 'not_read'
        
        # If grace period is active, user needs to read DOUBLE to achieve goal
        multiplier = 2 if user.grace_period_active else 1
        
        if club.goal_type == 'OVERALL':
            required_total = club.daily_min_total * multiplier
            if total_all >= required_total:
                new_status = 'achieved'
            elif total_all > 0:
                new_status = 'read_not_enough'
            else:
                new_status = 'not_read'
        else: # SEPARATE
            required_prl = club.daily_min_prl * multiplier
            required_rnk = club.daily_min_rnk * multiplier
            if total_prl >= required_prl and total_rnk >= required_rnk:
                new_status = 'achieved'
            elif total_prl > 0 or total_rnk > 0:
                new_status = 'read_not_enough'
            else:
                new_status = 'not_read'
            
        # Update Streak ONLY if newly achieved
        if new_status == 'achieved' and old_status != 'achieved':
            user.streak += 1
            
            # If grace period was active and user achieved, clear it
            if user.grace_period_active:
                user.grace_period_active = False
        
        log.status = new_status
        
        # XP calculation
        xp_gained = prl_read_now * XP_PER_PAGE + rnk_read_now * XP_PER_PAGE
        
        # Finished books bonus
        finished_books_count = context.user_data.get('finished_books_count', 0)
        xp_gained += finished_books_count * XP_BOOK_FINISHED
        
        leveled_up = award_xp(user, xp_gained, session)
        new_badges = check_badges(user, session)
        
        # Store values before closing session
        user_level = user.level
        badge_list = [(b.icon, b.name) for b in new_badges] if new_badges else []
        
        # Check if grace period was needed and achieved
        grace_saved = user.grace_period_active and new_status == 'achieved'
        
        # Feedback on remaining pages
        remaining_msg = ""
        if new_status != 'achieved':
            if club.goal_type == 'OVERALL':
                remaining = max(0, club.daily_min_total - total_all)
                remaining_msg = f"\n💪 <b>Keep going!</b> You need {remaining} more pages to reach your daily goal."
            else:
                rem_prl = max(0, club.daily_min_prl - total_prl)
                rem_rnk = max(0, club.daily_min_rnk - total_rnk)
                remaining_msg = f"\n💪 <b>Keep going!</b> Remaining: {rem_prl} PRL, {rem_rnk} RNK."
        else:
            remaining_msg = "\n🎉 <b>Daily Goal Achieved!</b> Great work!"

        # Calculate club statistics for today
        from datetime import timedelta
        today = get_today_date()
        
        # Get all club members
        club_members = session.query(User).filter(User.club_id == club.id).all()
        total_members = len(club_members)
        
        # Get today's stats for all members
        achieved_count = 0
        read_not_enough_count = 0
        not_read_count = 0
        skipped_count = 0
        
        today_pages = {}  # user_id -> total_pages_today
        
        for member in club_members:
            today_log = session.query(DailyLog).filter(
                DailyLog.user_id == member.id,
                DailyLog.date == today
            ).first()
            
            if today_log:
                total_pages_member = (today_log.pages_read_prl or 0) + (today_log.pages_read_rnk or 0)
                today_pages[member.id] = total_pages_member
                
                if today_log.status == 'achieved':
                    achieved_count += 1
                elif today_log.status == 'read_not_enough':
                    read_not_enough_count += 1
                elif today_log.status == 'not_read':
                    not_read_count += 1
            else:
                # No log = skipped
                skipped_count += 1
                today_pages[member.id] = 0
        
        # Calculate percentages
        achieved_pct = (achieved_count / total_members * 100) if total_members > 0 else 0
        read_not_enough_pct = (read_not_enough_count / total_members * 100) if total_members > 0 else 0
        not_read_pct = (not_read_count / total_members * 100) if total_members > 0 else 0
        skipped_pct = (skipped_count / total_members * 100) if total_members > 0 else 0
        
        # Get user's ranking for today (by pages read)
        sorted_users = sorted(today_pages.items(), key=lambda x: x[1], reverse=True)
        user_rank = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == user.id), None)
        
        # Calculate days since club creation
        club_age_days = (today - club.created_at.date()).days + 1 if hasattr(club, 'created_at') and club.created_at else 1
        
        # Build main message
        msg = (
            f"✅ <b>Report Saved!</b>\n"
            f"📖 <b>Today's Total:</b> PRL: {total_prl}, RNK: {total_rnk}\n"
            f"📊 <b>Status:</b> {new_status.replace('_', ' ').title()}\n"
            f"{remaining_msg}\n\n"
            f"+ {xp_gained} XP\n"
        )

        if leveled_up:
            msg += f"\n🌟 <b>LEVEL UP!</b> You are now Level {user_level}!"
        
        if grace_saved:
            msg += "\n\n⏰ <b>Grace Period Used!</b> You made up yesterday's missed reading! Streak preserved! 🔥"
        
        if badge_list:
            msg += "\n\n🏅 <b>New Badges Unlocked:</b>"
            for icon, name in badge_list:
                msg += f"\n{icon} {name}"
        
        # Add club statistics
        msg += f"\n\n📊 <b>Club Stats (Day {club_age_days})</b>\n"
        msg += f"👥 Members: {total_members}\n"
        msg += f"✅ Achieved: {achieved_count} ({achieved_pct:.0f}%)\n"
        msg += f"📖 Read (not enough): {read_not_enough_count} ({read_not_enough_pct:.0f}%)\n"
        msg += f"❌ Didn't read: {not_read_count} ({not_read_pct:.0f}%)\n"
        msg += f"⏭ Skipped: {skipped_count} ({skipped_pct:.0f}%)\n"
        
        # Add user's ranking
        if user_rank:
            msg += f"\n🏆 <b>Your Today's Rank: #{user_rank}</b>"
                
        await update.message.reply_text(msg, parse_mode='HTML')
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from utils import calculate_reading_stats
    
    with get_session_scope(Session) as session:
        user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
        if not user:
            await update.message.reply_text("You are not registered yet. Use /start to join.")
            return
            
        logs = user.logs
        
        # Generate graph
        graph_buf = generate_contribution_graph(logs)
        
        # Calculate stats
        stats = calculate_reading_stats(user)
        
        # Update best streak if current is higher
        if user.streak > user.best_streak:
            user.best_streak = user.streak
            # session.commit() # Handled by context manager
        
        # Progress Bar for Level
        next_level_xp = get_xp_for_next_level(user.level)
        prev_level_xp = get_xp_for_next_level(user.level - 1)
        level_range = next_level_xp - prev_level_xp
        current_progress = user.xp - prev_level_xp
        percent = min(1.0, max(0.0, current_progress / level_range))
        bar_len = 10
        filled = int(bar_len * percent)
        bar = "█" * filled + "░" * (bar_len - filled)
        
        badges_str = " ".join([b.badge.icon for b in user.badges]) if user.badges else "None"
        
        # Escape HTML special chars in name
        import html
        safe_name = html.escape(user.full_name)
        club_info = f"{user.club.name} (Key: <code>{user.club.key}</code>)" if user.club else "No Club"
        
        # Build reading speed info
        speed_info = ""
        if stats['reading_speed']:
            speed_info = "\n\n📈 <b>Reading Speed:</b>\n"
            for book_title, days in list(stats['reading_speed'].items())[:2]:  # Show max 2 books
                speed_info += f"• <i>{book_title}</i>: ~{days} days to finish\n"
        
        caption = (
            f"👤 <b>{safe_name}</b>\n"
            f"🏢 {club_info}\n\n"
            
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
        
        await update.message.reply_photo(photo=graph_buf, caption=caption, parse_mode='HTML')

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_session_scope(Session) as session:
        # Get current user
        current_user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
        
        # Top 10 by XP
        users = session.query(User).filter(User.club_id == context.user_data.get('club_id')).order_by(User.xp.desc()).limit(10).all()
        
        # If club_id not in context (e.g. restart), try to get from user
        if not users and current_user and current_user.club_id:
            users = session.query(User).filter(User.club_id == current_user.club_id).order_by(User.xp.desc()).limit(10).all()
        
        import html
        msg = "🏆 <b>Leaderboard</b> 🏆\n\n"
        for i, u in enumerate(users):
            # Show real name only for current user, otherwise show XXX
            if current_user and u.id == current_user.id:
                safe_name = html.escape(u.full_name)
            else:
                safe_name = "XXX"
            msg += f"{i+1}. {safe_name} - Lvl {u.level} ({u.xp} XP)\n"
            
        await update.message.reply_text(msg, parse_mode='HTML')

async def badges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from gamification import get_all_badges_with_progress
    
    with get_session_scope(Session) as session:
        user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
        
        if not user:
            await update.message.reply_text("Please join a club first with /start")
            return
        
        badge_info = get_all_badges_with_progress(user, session)
        
        msg = "🏅 <b>Badge Collection</b> 🏅\n\n"
        
        # Group by type
        earned = [b for b in badge_info if b['earned']]
        locked = [b for b in badge_info if not b['earned']]
        
        if earned:
            msg += "<b>✅ Earned Badges:</b>\n"
            for info in earned:
                badge = info['badge']
                msg += f"{badge.icon} <b>{badge.name}</b>\n<i>{badge.description}</i>\n\n"
        
        if locked:
            msg += "<b>🔒 Locked Badges:</b>\n"
            for info in locked:
                badge = info['badge']
                progress_bar = ""
                if info['progress']:
                    pct = info['progress_pct']
                    filled = int(pct / 10)
                    progress_bar = f"\n<code>[{'█' * filled}{'░' * (10 - filled)}]</code> {info['progress']}"
                msg += f"{badge.icon} <b>{badge.name}</b>\n<i>{badge.description}</i>{progress_bar}\n\n"
        
        msg += f"\n📊 <b>Progress:</b> {len(earned)}/{len(badge_info)} badges earned"
        
        await update.message.reply_text(msg, parse_mode='HTML')

async def reading_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show what books club members are currently reading"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user or not user.club_id:
        await update.message.reply_text("Please join a club first with /start")
        session.close()
        return
    
    # Get all users in the club
    club_users = session.query(User).filter_by(club_id=user.club_id).all()
    
    # Collect all in-progress books
    book_reader_counts = {}  # book_title -> count
    
    for club_user in club_users:
        for ub in club_user.readings:
            if not ub.finished:
                if ub.book.title not in book_reader_counts:
                    book_reader_counts[ub.book.title] = 0
                book_reader_counts[ub.book.title] += 1
    
    if not book_reader_counts:
        await update.message.reply_text(
            "📚 No one is currently reading any books in this club.\n"
            "Be the first to start!",
            parse_mode='HTML'
        )
        session.close()
        return
    
    # Sort by popularity (most readers first)
    sorted_books = sorted(book_reader_counts.items(), key=lambda x: x[1], reverse=True)
    
    msg = f"📖 <b>Currently Reading in {user.club.name}</b> 📖\n\n"
    
    for book_title, reader_count in sorted_books[:10]:  # Show top 10
        if reader_count == 1:
            msg += f"📕 <b>{book_title}</b> - 1 reader\n\n"
        else:
            msg += f"📕 <b>{book_title}</b> - {reader_count} readers\n\n"
    
    await update.message.reply_text(msg, parse_mode='HTML')
    session.close()

async def change_club(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow users to change clubs while preserving their progress"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user or not user.club_id:
        await update.message.reply_text(
            "You are not in any club yet. Use /start to join one.",
            parse_mode='HTML'
        )
        session.close()
        return ConversationHandler.END
    
    old_club_name = user.club.name
    
    # Store user's progress data before changing
    user_stats = {
        'xp': user.xp,
        'level': user.level,
        'streak': user.streak,
        'best_streak': user.best_streak,
        'books_count': len(user.readings),
        'total_logs': len(user.logs)
    }
    
    await update.message.reply_text(
        f"📚 <b>Change Club</b>\n\n"
        f"Current club: <b>{old_club_name}</b>\n\n"
        f"✅ <b>Your progress will be preserved:</b>\n"
        f"⭐ Level {user_stats['level']} ({user_stats['xp']} XP)\n"
        f"🔥 Streak: {user_stats['streak']} days\n"
        f"📚 Books: {user_stats['books_count']}\n"
        f"📊 Reading logs: {user_stats['total_logs']}\n\n"
        f"Please enter the <b>new Club Key</b>:",
        parse_mode='HTML'
    )
    session.close()
    return ENTER_KEY

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Check if user is admin
    from utils import get_admin_ids
    admin_ids = get_admin_ids()
    
    help_text = (
        "📚 <b>Reading Club Bot - Help Guide</b> 📚\n\n"
        "<b>📖 Main Commands:</b>\n"
        "/start - Join a reading club\n"
        "/change_club - Switch to a different club\n"
        "/report - Submit your daily reading report\n"
        "/my_books - Manage your books (add, update progress)\n"
        "/profile - View your stats, streaks & achievements\n"
        "/badges - See your badge collection & progress\n"
        "/leaderboard - View club rankings\n"
        "/reading_now - See what others are reading\n"
        "/help - Show this help message\n"
        "/cancel - Cancel current operation\n\n"
        "<b>✨ Features:</b>\n"
        "🔥 Streak tracking with 24-hour grace period\n"
        "⭐ XP & leveling system\n"
        "🏅 Achievement badges\n"
        "📊 Club statistics & rankings\n"
        "📈 Progress tracking & analytics\n\n"
        "<b>🎁 XP Bonuses:</b>\n"
        "+1 XP per page read\n"
        "+10 XP for maintaining daily streak\n"
        "+100 XP for finishing a book\n\n"
        "<b>⏰ Daily Schedule:</b>\n"
        "• 20:00 - Daily check-in\n"
        "• 22:00 - First reminder\n"
        "• 23:00 - Second reminder\n"
        "• 00:00 - Reports close (grace period starts)\n"
        "• 08:00 - Daily summary\n"
        "• Sunday 20:00 - Weekly summary\n"
    )
    
    if user_id in admin_ids:
        help_text += (
            "\n<b>🛡️ Admin Commands:</b>\n"
            "/create_club <code>&lt;Name&gt; &lt;Type&gt; &lt;Goals&gt;</code> - Create club\n"
            "/add_book <code>&lt;ClubKey&gt; &lt;Title&gt; &lt;Pages&gt;</code> - Add book\n"
            "/broadcast <code>&lt;ClubKey&gt; &lt;Message&gt;</code> - Send to all\n"
            "/club_stats <code>&lt;ClubKey&gt;</code> - View club statistics\n"
            "/admin_users <code>&lt;ClubKey&gt;</code> - List club members\n"
            "/admin_books <code>&lt;ClubKey&gt;</code> - List club books\n"
            "/admin_leaderboard <code>&lt;ClubKey&gt;</code> - Full rankings\n"
            "/view_profile <code>&lt;TelegramID&gt;</code> - View user profile\n"
            "/kick_user <code>&lt;TelegramID&gt;</code> - Remove user\n"
            "/reset_user <code>&lt;TelegramID&gt;</code> - Reset user progress\n"
            "/delete_book <code>&lt;BookID&gt;</code> - Delete a book\n"
            "/delete_club <code>&lt;ClubKey&gt;</code> - Delete club\n"
            "/all_clubs - List all clubs\n"
            "/all_users - List all users\n"
        )
    
    await update.message.reply_text(help_text, parse_mode='HTML')



# Handlers definition
setup_conv = ConversationHandler(
    entry_points=[
        CommandHandler('start', start),
        CommandHandler('change_club', change_club)
    ],
    states={
        ENTER_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_key)],
        SELECT_BOOKS_PRL: [CallbackQueryHandler(select_books_prl)],
        SELECT_BOOKS_RNK: [CallbackQueryHandler(select_books_rnk)],
        ENTER_PAGES_PRL: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_pages_prl)],
        ENTER_PAGES_RNK: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_pages_rnk)],
        SELECT_STATUS_PRL: [CallbackQueryHandler(select_status_prl)],
        SELECT_STATUS_RNK: [CallbackQueryHandler(select_status_rnk)],
        ENTER_CURRENT_PAGE_PRL: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_current_page_prl)],
        ENTER_CURRENT_PAGE_RNK: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_current_page_rnk)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    per_message=False
)

report_conv = ConversationHandler(
    entry_points=[CommandHandler('report', report_start)],
    states={
        REPORT_PRL: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_book_progress)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    per_message=False
)
