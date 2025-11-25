from datetime import datetime, timedelta
import pytz
import matplotlib.pyplot as plt
import io

TIMEZONE = pytz.timezone('Etc/GMT-5') # UTC+5

def get_current_time():
    return datetime.now(TIMEZONE)

def get_today_date():
    return get_current_time().date()

def generate_contribution_graph(daily_logs):
    # Calendar View (Monthly)
    import matplotlib.pyplot as plt
    import calendar
    
    # Configuration
    today = get_today_date()
    year = today.year
    month = today.month
    
    # Create calendar grid
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    # Map logs
    log_map = {l.date.day: l for l in daily_logs if l.date.year == year and l.date.month == month}
    
    # Plotting
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.set_facecolor('#2c3e50') # Dark blue-grey background
    fig.patch.set_facecolor('#2c3e50')
    
    # Grid settings
    rows = len(cal)
    cols = 7
    
    ax.set_xlim(0, cols)
    ax.set_ylim(0, rows + 1) # +1 for header
    ax.axis('off')
    
    # Draw Header (Month Year)
    ax.text(3.5, rows + 0.5, f"{month_name} {year}", 
            ha='center', va='center', color='white', fontsize=16, weight='bold')
            
    # Draw Day Names
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for i, day in enumerate(days):
        ax.text(i + 0.5, rows - 0.2, day, 
                ha='center', va='center', color='#bdc3c7', fontsize=10)
                
    # Draw Days
    for r, week in enumerate(cal):
        for c, day in enumerate(week):
            if day == 0:
                continue
                
            # Coordinates (row 0 is top, so we invert y)
            y = rows - 1 - r
            x = c
            
            # Draw Box
            # Determine status
            status_color = '#34495e' # Default greyish
            status_text = ""
            
            if day in log_map:
                log = log_map[day]
                if log.status == 'achieved':
                    status_color = '#27ae60' # Green
                    status_text = "✓"
                elif log.status == 'read_not_enough':
                    status_color = '#f39c12' # Orange
                    status_text = "~"
                elif log.status == 'missed':
                    status_color = '#c0392b' # Red
                    status_text = "✕"
            elif day < today.day:
                # Past day with no log -> Missed (or just empty if we want to be lenient)
                # Let's assume empty means missed if it's in the past
                status_color = '#c0392b'
                status_text = "✕"
            elif day == today.day:
                 status_color = '#34495e' # Today pending
            
            # Draw Rectangle
            rect = plt.Rectangle((x + 0.05, y + 0.05), 0.9, 0.9, 
                               color=status_color, ec='none', alpha=0.8)
            # Using basic rectangle for now. FancyBboxPatch could do rounded.
            import matplotlib.patches as mpatches
            # box = mpatches.FancyBboxPatch((x + 0.1, y + 0.1), 0.8, 0.8, boxstyle="round,pad=0.02", color=status_color)
            # ax.add_patch(box)
            # Stick to simple rectangle for reliability
            ax.add_patch(rect)
            
            # Draw Day Number
            ax.text(x + 0.5, y + 0.5, str(day), 
                    ha='center', va='center', color='white', fontsize=12, weight='bold')
            
            # Draw Status Icon (small)
            if status_text:
                ax.text(x + 0.8, y + 0.2, status_text, 
                        ha='center', va='center', color='white', fontsize=10, weight='bold')

    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    buf.seek(0)
    plt.close()
    return buf

def calculate_reading_stats(user):
    """Calculate comprehensive reading statistics for a user"""
    from datetime import timedelta
    from collections import Counter
    
    stats = {
        'avg_pages_week': 0,
        'avg_pages_month': 0,
        'avg_pages_all_time': 0,
        'best_streak': user.best_streak,
        'current_streak': user.streak,
        'most_productive_day': 'N/A',
        'total_books_finished': 0,
        'total_pages_read': 0,
        'days_active': 0,
        'reading_speed': {}  # book_id: days_to_finish
    }
    
    logs = user.logs
    if not logs:
        return stats
        
    # Sort logs by date
    sorted_logs = sorted(logs, key=lambda x: x.date)
    
    # Total stats
    stats['total_pages_read'] = sum((l.pages_read_prl or 0) + (l.pages_read_rnk or 0) for l in logs)
    stats['days_active'] = len([l for l in logs if l.status in ['achieved', 'read_not_enough']])
    stats['total_books_finished'] = len([ub for ub in user.readings if ub.finished])
    
    # Average calculations
    today = get_today_date()
    
    # Last 7 days
    week_ago = today - timedelta(days=7)
    week_logs = [l for l in logs if l.date >= week_ago]
    if week_logs:
        week_pages = sum((l.pages_read_prl or 0) + (l.pages_read_rnk or 0) for l in week_logs)
        stats['avg_pages_week'] = round(week_pages / 7, 1)
    
    # This month
    month_start = today.replace(day=1)
    month_logs = [l for l in logs if l.date >= month_start]
    if month_logs:
        days_in_month = (today - month_start).days + 1
        month_pages = sum((l.pages_read_prl or 0) + (l.pages_read_rnk or 0) for l in month_logs)
        stats['avg_pages_month'] = round(month_pages / days_in_month, 1)
    
    # All time
    if sorted_logs:
        first_log = sorted_logs[0].date
        total_days = (today - first_log).days + 1
        stats['avg_pages_all_time'] = round(stats['total_pages_read'] / total_days, 1)
    
    # Most productive day of week (0=Monday, 6=Sunday)
    day_counter = Counter()
    for log in logs:
        if log.status in ['achieved', 'read_not_enough']:
            pages = (log.pages_read_prl or 0) + (log.pages_read_rnk or 0)
            day_counter[log.date.weekday()] += pages
            
    if day_counter:
        most_productive_day_num = day_counter.most_common(1)[0][0]
        days_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        stats['most_productive_day'] = days_names[most_productive_day_num]
    
    # Reading speed prediction for current books
    for ub in user.readings:
        if not ub.finished and ub.current_page > 0:
            # Find first log for this book
            # This is a simplified calculation - we assume linear reading speed
            pages_remaining = ub.total_pages - ub.current_page
            if stats['avg_pages_week'] > 0:
                days_to_finish = int(pages_remaining / (stats['avg_pages_week'] / 7))
                stats['reading_speed'][ub.book.title] = days_to_finish
    
    return stats
