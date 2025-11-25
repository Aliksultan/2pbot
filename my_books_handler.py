from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from database import init_db, User, Book, UserBook

Session = init_db()

# States for My Books conversation
MB_MENU = 0
MB_ADD_SELECT_CAT = 1
MB_ADD_SELECT_BOOK = 2
MB_ADD_ENTER_PAGES = 3
MB_ADD_ALREADY_READ = 4
MB_ADD_CURRENT_PAGE = 5

async def my_books_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from recommendations import get_recommended_book, XP_SELECTION_BONUS
    
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user or not user.club_id:
        await update.message.reply_text("You are not in a club yet.")
        session.close()
        return ConversationHandler.END
    
    # Get recommended book
    recommended_book, priority = get_recommended_book(user, session)
    
    msg = "📚 <b>Your Books:</b>\n\n"
    
    # Show recommended book at top if available
    if recommended_book:
        msg += f"⭐ <b>RECOMMENDED NEXT by Emine Eroglu path:</b>\n"
        msg += f"📕 <i>{recommended_book.title}</i> ({recommended_book.category})\n"
        msg += f"🎁 <b>+{XP_SELECTION_BONUS} XP bonus</b> if you add this book!\n\n"
        msg += "─" * 30 + "\n\n"
        
        # Store recommendation in context for later
        context.user_data['current_recommendation'] = {
            'book_id': recommended_book.id,
            'book_title': recommended_book.title
        }
    
    # Get in-progress books
    in_progress = [ub for ub in user.readings if not ub.finished]
    # Get finished books sorted by date (most recent first)
    finished = sorted([ub for ub in user.readings if ub.finished], key=lambda x: x.finished_date, reverse=True)
    
    # Show all in-progress books
    for ub in in_progress:
        progress = int((ub.current_page / ub.total_pages) * 100) if ub.total_pages > 0 else 0
        msg += f"📖 <b>{ub.book.title}</b> ({ub.book.category}): {ub.current_page}/{ub.total_pages} ({progress}%)\n"
    
    # Show only the most recent completed book
    if finished:
        latest = finished[0]
        msg += f"\n✅ <b>Last Completed:</b> <i>{latest.book.title}</i> ({latest.book.category}) 🎉\n"
        
    msg += "\n<b>What would you like to do?</b>"
    keyboard = [["Add Book", "Cancel"]]
    
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True), parse_mode='HTML')
    session.close()
    return MB_MENU

async def mb_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Add Book":
        keyboard = [["PRL", "RNK"]]
        await update.message.reply_text("Which category?", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return MB_ADD_SELECT_CAT
    else:
        await update.message.reply_text("Done.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

async def mb_add_select_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    if category not in ['PRL', 'RNK']:
        await update.message.reply_text("Invalid category.")
        return ConversationHandler.END
        
    context.user_data['mb_category'] = category
    
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    # Get available books
    all_books = session.query(Book).filter_by(club_id=user.club_id, category=category).all()
    user_book_ids = [ub.book_id for ub in user.readings]
    available = [b for b in all_books if b.id not in user_book_ids]
    
    if not available:
        await update.message.reply_text("You have added all available books in this category.", reply_markup=ReplyKeyboardRemove())
        session.close()
        return ConversationHandler.END
        
    book_titles = [[b.title] for b in available]
    await update.message.reply_text("Select a book:", reply_markup=ReplyKeyboardMarkup(book_titles, one_time_keyboard=True))
    session.close()
    return MB_ADD_SELECT_BOOK

async def mb_add_select_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    book = session.query(Book).filter_by(title=title, club_id=user.club_id, category=context.user_data['mb_category']).first()
    
    if book:
        context.user_data['mb_book_id'] = book.id
        await update.message.reply_text(f"How many pages does '{title}' have?", reply_markup=ReplyKeyboardRemove())
        session.close()
        return MB_ADD_ENTER_PAGES
    else:
        await update.message.reply_text("Invalid book.")
        session.close()
        return ConversationHandler.END

async def mb_add_enter_pages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pages = int(update.message.text)
        context.user_data['mb_total_pages'] = pages
        
        # Ask if they've already read this book
        keyboard = [["✅ Already finished", "📖 In progress", "🆕 Starting fresh"]]
        await update.message.reply_text(
            f"📚 <b>Book Status:</b>\n\n"
            f"Choose one:\n"
            f"✅ <b>Already finished</b> - Mark as completed\n"
            f"📖 <b>In progress</b> - Continue from where you stopped\n"
            f"🆕 <b>Starting fresh</b> - Begin from page 0",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
            parse_mode='HTML'
        )
        return MB_ADD_ALREADY_READ
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number.")
        return MB_ADD_ENTER_PAGES

async def mb_add_already_read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from utils import get_today_date
    
    choice = update.message.text
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    total_pages = context.user_data['mb_total_pages']
    book_id = context.user_data['mb_book_id']
    
    # Check if this is the recommended book
    is_recommended_selection = False
    if 'current_recommendation' in context.user_data:
        if context.user_data['current_recommendation']['book_id'] == book_id:
            is_recommended_selection = True
    
    if "finished" in choice.lower():
        # Mark as already finished
        ub = UserBook(
            user_id=user.id,
            book_id=book_id,
            total_pages=total_pages,
            current_page=total_pages,
            finished=True,
            finished_date=get_today_date(),
            is_recommended=is_recommended_selection
        )
        session.add(ub)
        
        # Award selection bonus if recommended
        bonus_msg = ""
        if is_recommended_selection:
            from recommendations import XP_SELECTION_BONUS
            from gamification import award_xp
            leveled_up = award_xp(user, XP_SELECTION_BONUS, session)
            ub.recommendation_bonus_claimed = True
            bonus_msg = f"\n\n🎁 <b>+{XP_SELECTION_BONUS} XP</b> for choosing the recommended book!"
            if leveled_up:
                bonus_msg += f"\n🌟 <b>LEVEL UP!</b> You are now Level {user.level}!"
        
        session.commit()
        session.close()
        
        await update.message.reply_text(
            f"✅ <b>Book added as completed!</b> 🎉\n\n"
            f"The book is marked as finished and will appear in your reading history.{bonus_msg}",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
        
    elif "progress" in choice.lower():

        # Ask for current page
        await update.message.reply_text(
            f"📖 <b>What page are you on?</b>\n\n"
            f"Enter the page number where you stopped (1-{total_pages}):",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        return MB_ADD_CURRENT_PAGE
        
    else:
        # Starting fresh
        ub = UserBook(
            user_id=user.id,
            book_id=book_id,
            total_pages=total_pages,
            is_recommended=is_recommended_selection
        )
        session.add(ub)
        
        # Award selection bonus if recommended
        bonus_msg = ""
        if is_recommended_selection:
            from recommendations import XP_SELECTION_BONUS
            from gamification import award_xp
            leveled_up = award_xp(user, XP_SELECTION_BONUS, session)
            ub.recommendation_bonus_claimed = True
            bonus_msg = f"\n\n🎁 <b>+{XP_SELECTION_BONUS} XP</b> for choosing the recommended book!"
            if leveled_up:
                bonus_msg += f"\n🌟 <b>LEVEL UP!</b> You are now Level {user.level}!"
        
        session.commit()
        session.close()
        
        await update.message.reply_text(
            f"✅ <b>Book added successfully!</b>\n\n"
            f"You can start tracking your progress with /report.{bonus_msg}",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        return ConversationHandler.END

async def mb_add_current_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        current_page = int(update.message.text)
        total_pages = context.user_data['mb_total_pages']
        
        if current_page < 0 or current_page > total_pages:
            await update.message.reply_text(
                f"❌ Invalid page number!\n\n"
                f"Please enter a number between 0 and {total_pages}:"
            )
            return MB_ADD_CURRENT_PAGE
        
        session = Session()
        user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
        book_id = context.user_data['mb_book_id']
        
        # Check if this is the recommended book
        is_recommended_selection = False
        if 'current_recommendation' in context.user_data:
            if context.user_data['current_recommendation']['book_id'] == book_id:
                is_recommended_selection = True
        
        ub = UserBook(
            user_id=user.id,
            book_id=book_id,
            total_pages=total_pages,
            current_page=current_page,
            is_recommended=is_recommended_selection
        )
        session.add(ub)
        
        # Award selection bonus if recommended
        bonus_msg = ""
        if is_recommended_selection:
            from recommendations import XP_SELECTION_BONUS
            from gamification import award_xp
            leveled_up = award_xp(user, XP_SELECTION_BONUS, session)
            ub.recommendation_bonus_claimed = True
            bonus_msg = f"\n\n🎁 <b>+{XP_SELECTION_BONUS} XP</b> for choosing the recommended book!"
            if leveled_up:
                bonus_msg += f"\n🌟 <b>LEVEL UP!</b> You are now Level {user.level}!"
        
        session.commit()
        session.close()
        
        progress_pct = int((current_page / total_pages) * 100) if total_pages > 0 else 0
        
        await update.message.reply_text(
            f"✅ <b>Book added successfully!</b>\n\n"
            f"📖 Current progress: {current_page}/{total_pages} ({progress_pct}%)\n"
            f"📚 Pages remaining: {total_pages - current_page}\n\n"
            f"Keep reading and use /report to track your progress!{bonus_msg}",
            parse_mode='HTML'
        )
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid page number.")
        return MB_ADD_CURRENT_PAGE

async def mb_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

my_books_conv = ConversationHandler(
    entry_points=[CommandHandler('my_books', my_books_start)],
    states={
        MB_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, mb_menu)],
        MB_ADD_SELECT_CAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, mb_add_select_cat)],
        MB_ADD_SELECT_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, mb_add_select_book)],
        MB_ADD_ENTER_PAGES: [MessageHandler(filters.TEXT & ~filters.COMMAND, mb_add_enter_pages)],
        MB_ADD_ALREADY_READ: [MessageHandler(filters.TEXT & ~filters.COMMAND, mb_add_already_read)],
        MB_ADD_CURRENT_PAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, mb_add_current_page)],
    },
    fallbacks=[CommandHandler('cancel', mb_cancel)]
)
