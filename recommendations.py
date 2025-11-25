"""Book recommendation engine for the reading club bot"""
import random
from database import init_db, User, Book, UserBook

Session = init_db()

# Priority tier mappings
PRIORITY_BOOKS = {
    1: [
        "iNANCIN GOLGESINDE",
        "SONSUZ NUR 1",
        "SONSUZ NUR 2",
        "OLUM OTESI HAYAT",
        "KURANDAN iDRAKE YANSIYANLAR",
        "YUSUF SURESI",
        "KURANIN ALTIN iKLiMiNDE",
        "FATiHA UZERiNE MULAHAZALAR",
        "VARLIGIN METAFiZiK BOYUTU"
    ],
    2: [
        "ZEKAT",
        "ORUC",
        "ENGiNLiGiYLE BiZiM DUNYAMIZ",
        "MiRAC ENGiNLiKLi iBADET NAMAZ"
    ],
    3: [
        "iRSAD EKSENi",
        "iLAYI KELIMETULLAH veya CiHAD",
        "CEKIRDEKTEN CINARA",
        "YARATILIS GERCEGi ve EVRiM"
    ],
    4: [
        "CAG ve NESIL",
        "BUHRANLAR ANAFORUNDA iNSAN",
        "YiTiRiLMiS CENNETE DOGRU",
        "ZAMANIN ALTIN DiLiMi",
        "GUNLER BAHARI SOLUKLARKEN",
        "YESEREN DUSUNCELER",
        "ISIGIN GORUNDUGU UFUK",
        "ORNEKLERI KENDINDEN BIR HAREKET",
        "SUKUTUN CIGLIKLARI",
        "HAKKA ADANMISLAR YOLU",
        "RUHUMUZUN HEYKELiNi DiKERKEN",
        "KENDİ DÜNYAMIZA DOĞRU",
        "BEYAN"
    ],
    5: [
        "KALBiN ZUMRUT TEPELERi 1",
        "KALBiN ZUMRUT TEPELERi 2",
        "KALBiN ZUMRUT TEPELERi 3",
        "KALBiN ZUMRUT TEPELERi 4"
    ],
    6: [
        "ASRIN GETiRDiGi TEREDDUTLER 1-4",
        "FASILDAN FASILA 1-5",
        "PRiZMA 1-9",
        "SOHBET ATMOSFERi",
        "KIRIK TESTi 1-21"
    ],
    7: [
        "KIRIK MIZRAP",
        "OLCU veya YOLDAKi ISIKLAR"
    ]
}

# XP Bonuses
XP_SELECTION_BONUS = 50
XP_COMPLETION_BONUS = 100

def get_book_priority(book_title):
    """Get priority level for a book title"""
    title_upper = book_title.upper()
    for priority, books in PRIORITY_BOOKS.items():
        for book in books:
            if book.upper() in title_upper or title_upper in book.upper():
                return priority
    return 8  # Default to lowest priority

def get_recommended_book(user, session):
    """
    Get the next recommended book for a user based on their reading progress.
    Returns (book, priority_level) or (None, None) if no recommendation available.
    """
    # Get all completed books by user
    completed_books = session.query(UserBook).filter(
        UserBook.user_id == user.id,
        UserBook.finished == True
    ).all()
    
    completed_titles = {ub.book.title for ub in completed_books}
    
    # Get all books in user's current reading list (including completed)
    user_book_ids = {ub.book_id for ub in user.readings}
    
    # Find lowest priority tier with incomplete books
    for priority in range(1, 9):  # 1 to 8
        if priority in PRIORITY_BOOKS:
            priority_books = PRIORITY_BOOKS[priority]
            
            # Find books in this tier that user hasn't completed
            available_books = []
            for book_name in priority_books:
                # Check if this book exists in the club and is not completed
                club_books = session.query(Book).filter(
                    Book.club_id == user.club_id,
                    Book.title.like(f"%{book_name}%")
                ).all()
                
                for club_book in club_books:
                    # Skip if already completed or already in user's list
                    if club_book.title not in completed_titles and club_book.id not in user_book_ids:
                        available_books.append(club_book)
            
            # If there are available books in this tier, randomly select one
            if available_books:
                recommended = random.choice(available_books)
                return recommended, priority
    
    # No recommendations available (completed all tiers)
    return None, None

def set_book_priorities(session):
    """Set priority levels for all books based on the priority mappings"""
    for priority, book_names in PRIORITY_BOOKS.items():
        for book_name in book_names:
            books = session.query(Book).filter(Book.title.like(f"%{book_name}%")).all()
            for book in books:
                book.priority_level = priority
    
    session.commit()
