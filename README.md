# 2pbot - Reading Club Telegram Bot

A Telegram bot for managing reading clubs, tracking daily reading progress, and gamifying the experience with XP, levels, and badges.

## Features

-   **Reading Clubs**: Create and manage multiple reading clubs with different goals (Separate PRL/RNK or Overall).
-   **Daily Reporting**: Users report pages read daily.
-   **Gamification**: XP, Levels, Streaks, and Badges.
-   **Statistics**: Detailed user and club statistics with graphs.
-   **Reminders**: Automated daily reminders and check-ins.
-   **Admin Tools**: Manage users, books, and clubs.

## Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd 2pbot
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration**:
    Copy `.env.example` to `.env` and fill in your details:
    ```bash
    cp .env.example .env
    ```
    -   `BOT_TOKEN`: Your Telegram Bot Token.
    -   `ADMIN_IDS`: Your Telegram User ID (comma-separated for multiple).
    -   `TIMEZONE`: Your desired timezone (e.g., `Etc/GMT-5`).

4.  **Run the Bot**:
    ```bash
    python main.py
    ```

## Deployment

See [deployment_guide.md](deployment_guide.md) for detailed instructions on deploying to Digital Ocean using Docker.

## Testing

Run automated tests with:
```bash
pytest tests/
```
