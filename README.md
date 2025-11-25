# Reading Club Telegram Bot

A feature-rich Telegram bot for managing reading clubs with gamification, progress tracking, and social features.

## ✨ Features

### Core Functionality
- 📚 Book tracking & progress management
- 📊 Daily reading reports with club statistics
- 🔥 Streak system with grace period
- ⭐ XP & leveling with achievement badges
- 🗺️ Personalized reading roadmap (8-tier priority system)

### Social Features
- 🏆 Anonymous leaderboard & daily rankings
- 📖 See what others are reading (anonymized)
- 📊 Real-time club participation stats
- 🏅 Comprehensive achievement system

### Automation
- 🔔 Daily check-ins (8:00 AM)
- ⏰ Reading reminders (4:00 PM, 7:00 PM)
- 📧 Daily summaries (10:00 PM)
- 📅 Weekly recaps (Sunday 8:00 PM)
- 🤖 Auto-close reports at midnight

### Gamification
- **+50 XP** - Select recommended book
- **+100 XP** - Complete recommended book
- **+100 XP** - Finish any book
- **+1 XP** - Per page read
- **+10 XP** - Daily streak bonus

## 🚀 Quick Start with Docker

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd readingclub
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   nano .env  # Add your BOT_TOKEN from @BotFather
   ```

3. **Update admin IDs** in `admin.py`:
   ```python
   ADMIN_IDS = [YOUR_TELEGRAM_ID]
   ```

4. **Start with Docker**:
   ```bash
   docker-compose up -d
   ```

5. **View logs**:
   ```bash
   docker-compose logs -f bot
   ```

That's it! Your bot is now running. 🎉

## 📋 Manual Installation (Without Docker)

### Prerequisites
- Python 3.9+
- pip

### Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your BOT_TOKEN
   ```

3. **Update admin IDs** in `admin.py`

4. **Run the bot**:
   ```bash
   python3 main.py
   ```

## 🎮 User Commands

| Command | Description |
|---------|-------------|
| `/start` | Join the reading club |
| `/change_club` | Switch to a different club |
| `/report` | Submit daily reading |
| `/my_books` | Manage your books |
| `/profile` | View stats & achievements |
| `/badges` | View badge collection |
| `/leaderboard` | Club rankings (anonymous) |
| `/reading_now` | Currently reading books |
| `/help` | Show all commands |

## 👑 Admin Commands

| Command | Description |
|---------|-------------|
| `/create_club <name> <key> <type> [goals...]` | Create new club |
| `/delete_club <key>` | Delete a club |
| `/add_book <key> <title> <cat> <pages>` | Add book to library |
| `/delete_book <id>` | Remove book |
| `/club_stats <key>` | Detailed analytics |
| `/admin_leaderboard <key>` | De-anonymized rankings |
| `/view_profile <telegram_id>` | View any user's profile |
| `/admin_users <key>` | List members |
| `/kick_user <id>` | Remove user |
| `/reset_user <id>` | Reset progress |
| `/broadcast <msg>` | Message all users |

## 🏗️ Project Structure

```
readingclub/
├── main.py                 # Entry point
├── handlers.py             # Command handlers
├── admin.py               # Admin commands
├── database.py            # Database models
├── gamification.py        # XP & badges system
├── recommendations.py     # Reading roadmap logic
├── my_books_handler.py    # Book management
├── scheduler_tasks.py     # Automated tasks
├── utils.py               # Helper functions
├── requirements.txt       # Dependencies
├── Dockerfile            # Docker image
├── docker-compose.yml    # Docker orchestration
└── .env.example          # Environment template
```

## 📊 Technology Stack

- **Python 3.9**
- **python-telegram-bot v20+** - Telegram bot framework
- **SQLAlchemy** - ORM for SQLite database
- **APScheduler** - Task scheduling
- **Matplotlib** - Reading activity graphs
- **Docker** - Containerization

## ⚙️ Configuration

### Environment Variables

Create a `.env` file:
```
BOT_TOKEN=your_bot_token_here
```

### Admin Setup

Edit `admin.py`:
```python
ADMIN_IDS = [123456789, 987654321]  # Your Telegram IDs
```

Get your Telegram ID from [@userinfobot](https://t.me/userinfobot)

### Timezone

Default: UTC+5

To change, edit `utils.py`:
```python
TIMEZONE = pytz.timezone('Your/Timezone')  # e.g., 'Asia/Karachi'
```

## 🗺️ Reading Roadmap

The bot includes an 8-tier reading priority system:

1. **Foundation** - Core essential books
2. **Worship** - Prayer & religious practice
3. **Guidance** - Spiritual direction
4. **Contemporary** - Modern issues
5. **Heart Series** - Spiritual development
6. **Collections** - Multi-volume works
7. **Poetry & Lights** - Literary works
8. **Others** - General library

Books are recommended based on completion of each tier.

## 🔧 Common Docker Commands

```bash
# Start bot
docker-compose up -d

# Stop bot
docker-compose down

# View logs
docker-compose logs -f bot

# Restart after code changes
docker-compose restart bot

# Rebuild after major changes
docker-compose build --no-cache
docker-compose up -d

# Backup database
cp reading_club.db reading_club.db.backup
```

## 📝 First-Time Setup

1. Get bot token from [@BotFather](https://t.me/BotFather)
2. Add token to `.env`
3. Update `ADMIN_IDS` in `admin.py`
4. Start the bot
5. Create a club:
   ```
   /create_club "My Club" myclub123 OVERALL 20
   ```
6. Add books:
   ```
   /add_book myclub123 "Book Title" PRL 300
   ```

## 🐛 Troubleshooting

### Bot not responding
- Check logs: `docker-compose logs bot`
- Verify BOT_TOKEN is correct in `.env`
- Ensure server has internet access

### Database errors
- Stop bot: `docker-compose down`
- Check file permissions on `reading_club.db`
- Restart: `docker-compose up -d`

### Scheduled tasks not running
- Verify timezone configuration
- Check scheduler logs in console output

## 📈 Monitoring

```bash
# Check if bot is running
docker ps | grep reading_club_bot

# View resource usage
docker stats reading_club_bot

# Inspect health
docker inspect reading_club_bot
```

## 🔒 Security

- ✅ `.env` is gitignored (never commit tokens!)
- ✅ Admin commands protected by ID check
- ✅ Input validation and HTML escaping
- ✅ Database is local SQLite (no external access)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - feel free to use and modify.

## 🙏 Acknowledgments

Built with ❤️ for reading enthusiasts

---

**Need help?** Check the logs or open an issue!
