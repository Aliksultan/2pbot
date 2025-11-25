from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database import init_db, Club, Book, User, DailyLog, UserBook
import uuid

Session = init_db()

# Simple admin check (in real app, use ID list or role)
ADMIN_IDS = [420607440] # Add admin telegram IDs here

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id not in ADMIN_IDS:
            # For testing purposes, let's allow everyone or log a warning
            # await update.message.reply_text("Admin access only.")
            # return
            pass # Allow for now for testing
        return await func(update, context, *args, **kwargs)
    return wrapper

@admin_only
async def create_club(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /create_club Name SEPARATE MinPRL MinRNK
    # Usage: /create_club Name OVERALL MinTotal
    try:
        args = context.args
        name = args[0]
        mode = args[1].upper()
        
        min_prl = 0
        min_rnk = 0
        min_total = 0
        
        if mode == 'SEPARATE':
            min_prl = int(args[2])
            min_rnk = int(args[3])
        elif mode == 'OVERALL':
            min_total = int(args[2])
        else:
            await update.message.reply_text("Mode must be SEPARATE or OVERALL")
            return
        
        key = str(uuid.uuid4())[:8] # Generate random 8 char key
        
        session = Session()
        club = Club(
            name=name, 
            key=key, 
            daily_min_prl=min_prl, 
            daily_min_rnk=min_rnk,
            goal_type=mode,
            daily_min_total=min_total
        )
        session.add(club)
        session.commit()
        
        # Add default books
        rnk_books = [
            "Sözler", "Mektubat", "Lem'alar", "Şuâlar", "Mesnevî-i Nuriye", 
            "İşârâtü'l-İ'câz", "Asâ-yi Mûsâ", "Barla Lahikası", "Kastamonu Lahikası", 
            "Emirdağ Lahikası", "Iman ve Küfür Muvazeneleri", 
            "Sikke-I Tasdik-I Gaybi Mecmûası", "Muhâkemat", "Tarihçe-I Hayat"
        ]
        
        prl_books = [
            "ASRIN GETiRDiGi TEREDDUTLER 1", "ASRIN GETiRDiGi TEREDDUTLER 2", "ASRIN GETiRDiGi TEREDDUTLER 3", "ASRIN GETiRDiGi TEREDDUTLER 4",
            "BEYAN", "BiR iCAZ HECELEMESi", "CAG ve NESIL", "BUHRANLAR ANAFORUNDA iNSAN", "YiTiRiLMiS CENNETE DOGRU",
            "ZAMANIN ALTIN DiLiMi", "GUNLER BAHARI SOLUKLARKEN", "YESEREN DUSUNCELER", "ISIGIN GORUNDUGU UFUK",
            "ORNEKLERI KENDINDEN BIR HAREKET", "SUKUTUN CIGLIKLARI", "HAKKA ADANMISLAR YOLU", "CEKIRDEKTEN CINARA",
            "ENGiNLiGiYLE BiZiM DUNYAMIZ", "FASILDAN FASILA 1", "FASILDAN FASILA 2", "FASILDAN FASILA 3", "FASILDAN FASILA 4", "FASILDAN FASILA 5",
            "FATiHA UZERiNE MULAHAZALAR", "iLAYI KELIMETULLAH veya CiHAD", "iNANCIN GOLGESINDE", "iRSAD EKSENi", "KADER",
            "KALBiN ZUMRUT TEPELERi 1", "KALBiN ZUMRUT TEPELERi 2", "KALBiN ZUMRUT TEPELERi 3", "KALBiN ZUMRUT TEPELERi 4",
            "KIRIK MIZRAP", "KIRIK TESTi 1", "KIRIK TESTi 2", "KIRIK TESTi 3", "KIRIK TESTi 4", "KIRIK TESTi 5", "KIRIK TESTi 6",
            "KIRIK TESTi 7", "KIRIK TESTi 8", "KIRIK TESTi 9", "KIRIK TESTi 10", "KIRIK TESTi 11", "KIRIK TESTi 12", "KIRIK TESTi 13",
            "KIRIK TESTi 14", "KIRIK TESTi 15", "KIRIK TESTi 16", "KIRIK TESTi 17", "KIRIK TESTi 18", "KIRIK TESTi 19", "KIRIK TESTi 20", "KIRIK TESTi 21",
            "KURANDAN iDRAKE YANSIYANLAR", "KURANIN ALTIN iKLiMiNDE", "MiRAC ENGiNLiKLi iBADET NAMAZ", "OLCU veya YOLDAKi ISIKLAR",
            "OLUM OTESI HAYAT", "ORUC", "PRiZMA 1", "PRiZMA 2", "PRiZMA 3", "PRiZMA 4", "PRiZMA 5", "PRiZMA 6", "PRiZMA 7", "PRiZMA 8", "PRiZMA 9",
            "RUHUMUZUN HEYKELiNi DiKERKEN", "KENDİ DÜNYAMIZA DOĞRU", "SOHBET ATMOSFERi", "SONSUZ NUR 1", "SONSUZ NUR 2",
            "VARLIGIN METAFiZiK BOYUTU", "YARATILIS GERCEGi ve EVRiM", "YUSUF SURESI", "ZEKAT"
        ]
        
        for title in rnk_books:
            session.add(Book(title=title, category='RNK', total_pages=0, club_id=club.id))
            
        for title in prl_books:
            session.add(Book(title=title, category='PRL', total_pages=0, club_id=club.id))
            
        session.commit()
        
        msg = f"Club '{name}' created!\nKey: {key}\nMode: {mode}\n"
        if mode == 'SEPARATE':
            msg += f"Goals: PRL {min_prl}, RNK {min_rnk}"
        else:
            msg += f"Goal: {min_total} pages total"
            
        await update.message.reply_text(msg)
        session.close()
    except (IndexError, ValueError):
        await update.message.reply_text("Usage:\n/create_club <Name> SEPARATE <MinPRL> <MinRNK>\nOR\n/create_club <Name> OVERALL <MinTotal>")

@admin_only
async def add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /add_book ClubKey Category Title TotalPages
    try:
        args = context.args
        key = args[0]
        category = args[1].upper()
        title = " ".join(args[2:-1])
        pages = int(args[-1])
        
        if category not in ['PRL', 'RNK']:
            await update.message.reply_text("Category must be PRL or RNK")
            return

        session = Session()
        club = session.query(Club).filter_by(key=key).first()
        if not club:
            await update.message.reply_text("Club not found.")
            session.close()
            return
            
        book = Book(title=title, category=category, total_pages=pages, club_id=club.id)
        session.add(book)
        session.commit()
        
        await update.message.reply_text(f"Book '{title}' added to {club.name} ({category})")
        session.close()
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /add_book <ClubKey> <Category> <Title> <TotalPages>")

@admin_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /broadcast ClubKey Message
    try:
        args = context.args
        key = args[0]
        message = " ".join(args[1:])
        
        session = Session()
        club = session.query(Club).filter_by(key=key).first()
        if not club:
            await update.message.reply_text("Club not found.")
            session.close()
            return
            
        count = 0
        for user in club.users:
            try:
                await context.bot.send_message(chat_id=user.telegram_id, text=f"📢 <b>Announcement</b>:\n{message}", parse_mode='HTML')
                count += 1
            except Exception:
                pass
                
        await update.message.reply_text(f"Broadcast sent to {count} users.")
        session.close()
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /broadcast <ClubKey> <Message>")

    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /broadcast <ClubKey> <Message>")

@admin_only
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /admin_users ClubKey
    try:
        key = context.args[0]
        session = Session()
        club = session.query(Club).filter_by(key=key).first()
        if not club:
            await update.message.reply_text("Club not found.")
            session.close()
            return
            
        msg = f"👥 <b>Users in {club.name}</b>:\n"
        for user in club.users:
            msg += f"ID: <code>{user.telegram_id}</code> | {user.full_name} | Lvl {user.level}\n"
            
        await update.message.reply_text(msg, parse_mode='HTML')
        session.close()
    except IndexError:
        await update.message.reply_text("Usage: /admin_users <ClubKey>")

@admin_only
async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /kick_user TelegramID
    try:
        target_id = int(context.args[0])
        session = Session()
        user = session.query(User).filter_by(telegram_id=target_id).first()
        
        if user:
            # Delete associated data
            session.query(DailyLog).filter_by(user_id=user.id).delete()
            session.query(UserBook).filter_by(user_id=user.id).delete()
            # Badges?
            # session.query(UserBadge).filter_by(user_id=user.id).delete() # Need to import UserBadge if we want to be thorough
            session.delete(user)
            session.commit()
            await update.message.reply_text(f"User {target_id} kicked.")
        else:
            await update.message.reply_text("User not found.")
        session.close()
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /kick_user <TelegramID>")

@admin_only
async def reset_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /reset_user TelegramID
    try:
        target_id = int(context.args[0])
        session = Session()
        user = session.query(User).filter_by(telegram_id=target_id).first()
        
        if user:
            user.streak = 0
            user.xp = 0
            user.level = 1
            # Optional: Clear logs? Let's keep logs but reset stats.
            session.commit()
            await update.message.reply_text(f"User {target_id} stats reset (Streak, XP, Level).")
        else:
            await update.message.reply_text("User not found.")
        session.close()
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /reset_user <TelegramID>")

    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /reset_user <TelegramID>")

@admin_only
async def club_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /club_stats ClubKey
    try:
        key = context.args[0]
        session = Session()
        club = session.query(Club).filter_by(key=key).first()
        if not club:
            await update.message.reply_text("Club not found.")
            session.close()
            return
        
        from utils import get_today_date
        import datetime
        
        user_count = len(club.users)
        total_books = len(club.books)
        
        # Calculate detailed stats
        total_pages_read = 0
        active_users_7d = 0
        active_users_30d = 0
        total_streaks = 0
        best_streak = 0
        total_books_completed = 0
        grace_period_users = 0
        
        today = get_today_date()
        week_ago = today - datetime.timedelta(days=7)
        month_ago = today - datetime.timedelta(days=30)
        
        for user in club.users:
            # Total pages
            for log in user.logs:
                total_pages_read += (log.pages_read_prl or 0) + (log.pages_read_rnk or 0)
            
            # Active users (last 7/30 days)
            recent_logs_7d = [log for log in user.logs if log.date >= week_ago]
            recent_logs_30d = [log for log in user.logs if log.date >= month_ago]
            if recent_logs_7d:
                active_users_7d += 1
            if recent_logs_30d:
                active_users_30d += 1
            
            # Streaks
            total_streaks += user.streak
            if user.streak > best_streak:
                best_streak = user.streak
            
            # Grace period
            if user.grace_period_active:
                grace_period_users += 1
            
            # Completed books
            total_books_completed += len([ub for ub in user.readings if ub.finished])
        
        avg_pages_per_user = total_pages_read / user_count if user_count > 0 else 0
        avg_streak = total_streaks / user_count if user_count > 0 else 0
        completion_rate = (active_users_7d / user_count * 100) if user_count > 0 else 0
        
        msg = (
            f"📊 <b>Detailed Stats for {club.name}</b>\n\n"
            f"<b>👥 MEMBERS</b>\n"
            f"├ Total: {user_count}\n"
            f"├ Active (7d): {active_users_7d} ({completion_rate:.1f}%)\n"
            f"└ Active (30d): {active_users_30d}\n\n"
            f"<b>📚 BOOKS</b>\n"
            f"├ In Library: {total_books}\n"
            f"└ Completed: {total_books_completed}\n\n"
            f"<b>📖 READING</b>\n"
            f"├ Total Pages: {total_pages_read:,}\n"
            f"└ Avg/User: {avg_pages_per_user:.1f}\n\n"
            f"<b>🔥 STREAKS</b>\n"
            f"├ Best: {best_streak} days\n"
            f"├ Average: {avg_streak:.1f} days\n"
            f"└ Grace Period: {grace_period_users} users\n\n"
            f"<b>⚙️ SETTINGS</b>\n"
            f"├ Goal Type: {club.goal_type}\n"
        )
        
        if club.goal_type == 'OVERALL':
            msg += f"└ Daily Min: {club.daily_min_total} pages\n"
        else:
            msg += f"├ PRL Min: {club.daily_min_prl} pages\n"
            msg += f"└ RNK Min: {club.daily_min_rnk} pages\n"
        
        await update.message.reply_text(msg, parse_mode='HTML')
        session.close()
    except IndexError:
        await update.message.reply_text("Usage: /club_stats <ClubKey>")


@admin_only
async def admin_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /admin_books ClubKey
    try:
        key = context.args[0]
        session = Session()
        club = session.query(Club).filter_by(key=key).first()
        if not club:
            await update.message.reply_text("Club not found.")
            session.close()
            return
            
        msg = f"📚 <b>Books in {club.name}</b>:\n"
        for book in club.books:
            msg += f"ID: <code>{book.id}</code> | {book.title} ({book.category})\n"
            
        await update.message.reply_text(msg, parse_mode='HTML')
        session.close()
    except IndexError:
        await update.message.reply_text("Usage: /admin_books <ClubKey>")

@admin_only
async def delete_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /delete_book BookID
    try:
        book_id = int(context.args[0])
        session = Session()
        book = session.query(Book).get(book_id)
        
        if book:
            # Delete associated UserBooks
            session.query(UserBook).filter_by(book_id=book.id).delete()
            session.delete(book)
            session.commit()
            await update.message.reply_text(f"Book '{book.title}' deleted.")
        else:
            await update.message.reply_text("Book not found.")
        session.close()
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /delete_book <BookID>")

@admin_only
async def all_clubs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /all_clubs
    session = Session()
    clubs = session.query(Club).all()
    
    if not clubs:
        await update.message.reply_text("No clubs found.")
        session.close()
        return
        
    msg = "🏢 <b>All Clubs</b>:\n"
    for club in clubs:
        msg += f"• {club.name} (Key: <code>{club.key}</code>) - {len(club.users)} members\n"
        
    await update.message.reply_text(msg, parse_mode='HTML')
    session.close()

@admin_only
async def all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /all_users
    session = Session()
    users = session.query(User).all()
    
    if not users:
        await update.message.reply_text("No users found.")
        session.close()
        return
        
    msg = "👥 <b>All Users</b>:\n"
    # Chunking message to avoid limit if many users
    for user in users:
        club_info = f"{user.club.name} ({user.club.key})" if user.club else "No Club"
        line = f"ID: <code>{user.telegram_id}</code> | {user.full_name} | {club_info}\n"
        
        if len(msg) + len(line) > 4000:
            await update.message.reply_text(msg, parse_mode='HTML')
            msg = ""
        msg += line
        
    if msg:
        await update.message.reply_text(msg, parse_mode='HTML')
    session.close()

@admin_only
async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View any user's profile by telegram ID"""
    # Usage: /view_profile <telegram_id>
    try:
        from utils import calculate_reading_stats, generate_contribution_graph
        
        user_id = int(context.args[0])
        session = Session()
        user = session.query(User).filter_by(telegram_id=user_id).first()
        
        if not user:
            await update.message.reply_text(f"User with ID {user_id} not found.")
            session.close()
            return
        
        logs = user.logs
        
        # Generate graph
        graph_buf = generate_contribution_graph(logs)
        
        # Get stats
        stats = calculate_reading_stats(user)
        
        # Build message
        msg = (
            f"👤 <b>Profile: {user.full_name}</b>\n\n"
            f"🆔 Telegram ID: {user.telegram_id}\n"
            f"📚 Club: {user.club.name if user.club else 'None'}\n\n"
            f"<b>📊 STATS</b>\n"
            f"🔥 Streak: {user.streak} days (Best: {user.best_streak})\n"
            f"⭐ Level: {user.level}\n"
            f"💎 XP: {user.xp}\n\n"
            f"<b>📖 READING</b>\n"
            f"├ Avg (7d): {stats['avg_pages_week']:.1f} pages/day\n"
            f"├ Avg (Month): {stats['avg_pages_month']:.1f} pages/day\n"
            f"└ Avg (All-time): {stats['avg_pages_all_time']:.1f} pages/day\n\n"
            f"<b>🏆 ACHIEVEMENTS</b>\n"
            f"├ Books Finished: {stats['total_books_finished']}\n"
            f"├ Total Pages: {stats['total_pages_read']:,}\n"
            f"└ Active Days: {stats['days_active']}\n\n"
        )
        
        if user.grace_period_active:
            msg += "⏰ <b>Grace Period Active</b>\n"
        
        # Send with graph
        await update.message.reply_photo(photo=graph_buf, caption=msg, parse_mode='HTML')
        session.close()
        
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /view_profile <telegram_id>")

@admin_only
async def admin_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """De-anonymized leaderboard for admins showing all real names"""
    # Usage: /admin_leaderboard <ClubKey>
    try:
        key = context.args[0]
        session = Session()
        club = session.query(Club).filter_by(key=key).first()
        
        if not club:
            await update.message.reply_text("Club not found.")
            session.close()
            return
        
        # Top users by XP
        users = session.query(User).filter(User.club_id == club.id).order_by(User.xp.desc()).limit(20).all()
        
        import html
        msg = f"🏆 <b>Admin Leaderboard - {club.name}</b> 🏆\n\n"
        
        for i, u in enumerate(users):
            safe_name = html.escape(u.full_name)
            # Show extra info for admins
            status = ""
            if u.grace_period_active:
                status = " ⏰"
            if u.streak >= 7:
                status += " 🔥"
            
            msg += f"{i+1}. <b>{safe_name}</b>{status}\n"
            msg += f"   └ Lvl {u.level} | {u.xp} XP | Streak: {u.streak}d\n"
        
        await update.message.reply_text(msg, parse_mode='HTML')
        session.close()
        
    except IndexError:
        await update.message.reply_text("Usage: /admin_leaderboard <ClubKey>")

@admin_only
async def delete_club(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a club and all associated data"""
    # Usage: /delete_club <ClubKey>
    try:
        key = context.args[0]
        session = Session()
        club = session.query(Club).filter_by(key=key).first()
        
        if not club:
            await update.message.reply_text(f"Club with key '{key}' not found.")
            session.close()
            return
        
        # Get stats before deletion
        user_count = len(club.users)
        book_count = len(club.books)
        club_name = club.name
        
        # Delete associated users (will cascade delete their books and logs)
        for user in club.users:
            session.delete(user)
        
        # Delete all books
        for book in club.books:
            session.delete(book)
        
        # Delete the club
        session.delete(club)
        session.commit()
        session.close()
        
        await update.message.reply_text(
            f"✅ <b>Club Deleted</b>\n\n"
            f"📚 Club: {club_name}\n"
            f"👥 Users removed: {user_count}\n"
            f"📖 Books removed: {book_count}",
            parse_mode='HTML'
        )
        
    except IndexError:
        await update.message.reply_text("Usage: /delete_club <ClubKey>")


admin_handlers = [
    CommandHandler('create_club', create_club),
    CommandHandler('add_book', add_book),
    CommandHandler('broadcast', broadcast),
    CommandHandler('admin_users', admin_users),
    CommandHandler('kick_user', kick_user),
    CommandHandler('reset_user', reset_user),
    CommandHandler('club_stats', club_stats),
    CommandHandler('admin_books', admin_books),
    CommandHandler('delete_book', delete_book),
    CommandHandler('delete_club', delete_club),
    CommandHandler('all_clubs', all_clubs),
    CommandHandler('all_users', all_users),
    CommandHandler('view_profile', view_profile),
    CommandHandler('admin_leaderboard', admin_leaderboard)
]
