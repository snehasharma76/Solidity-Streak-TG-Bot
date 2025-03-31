from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import logging
import random

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")

# Support for multiple group chat IDs (comma-separated in .env)
group_chat_ids_str = os.getenv("GROUP_CHAT_ID", "")
GROUP_CHAT_IDS = [int(chat_id.strip()) for chat_id in group_chat_ids_str.split(",") if chat_id.strip()]

# Database setup
conn = sqlite3.connect('submissions.db')
c = conn.cursor()

# Create submissions table with PR link
c.execute('''CREATE TABLE IF NOT EXISTS submissions
             (user_id INTEGER, submission_date TEXT, streak INTEGER, pr_link TEXT)''')
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to the 30-Day Solidity Challenge by Web3 Compass!\n"
        "Use /submit <github_pr_link> to submit your solution each day,\n"
        "/streak to check your streak,\n"
        "/chatid to get the current chat ID,\n"
        "and /leaderboard to see the top participants."
    )

async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle solution submissions with GitHub PR links."""
    if not context.args:
        await update.message.reply_text(
            "Please provide your GitHub PR link with the submission!\n"
            "Format: /submit <PR_link>"
        )
        return

    pr_link = context.args[0]
    if not pr_link.startswith('https://github.com'):
        await update.message.reply_text("Please provide a valid GitHub PR link!")
        return

    user_id = update.message.from_user.id
    today = datetime.now().date()

    # Check last submission
    c.execute("SELECT submission_date, streak FROM submissions WHERE user_id=? ORDER BY submission_date DESC LIMIT 1", (user_id,))
    last_submission = c.fetchone()

    if last_submission:
        last_date = datetime.strptime(last_submission[0], '%Y-%m-%d').date()
        if last_date == today:
            await update.message.reply_text("You've already submitted today!")
            return
        elif last_date == today - timedelta(days=1):
            streak = last_submission[1] + 1
        else:
            streak = 1
    else:
        streak = 1

    # Save submission with PR link
    c.execute("INSERT INTO submissions (user_id, submission_date, streak, pr_link) VALUES (?, ?, ?, ?)",
              (user_id, today.strftime('%Y-%m-%d'), streak, pr_link))
    conn.commit()

    # Add milestone badges
    if streak == 5:
        await update.message.reply_text(f"🎉 PR submitted! Streak: {streak} days. You're a Solidity Novice!")
    elif streak == 15:
        await update.message.reply_text(f"🎉 PR submitted! Streak: {streak} days. You're a Solidity Enthusiast!")
    elif streak == 30:
        await update.message.reply_text(f"🎉 PR submitted! Streak: {streak} days. You're a Solidity Master!")
    else:
        await update.message.reply_text(f"PR submitted! Your streak is {streak} days.")

async def streak(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check user's current streak."""
    user_id = update.message.from_user.id
    c.execute("SELECT streak FROM submissions WHERE user_id=? ORDER BY submission_date DESC LIMIT 1", (user_id,))
    result = c.fetchone()
    if result:
        await update.message.reply_text(f"Your current streak is {result[0]} days.")
    else:
        await update.message.reply_text("You haven't submitted any solutions yet.")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show top 10 users by streak."""
    c.execute("SELECT user_id, streak FROM submissions GROUP BY user_id ORDER BY streak DESC LIMIT 10")
    leaders = c.fetchall()
    if leaders:
        message = "🏆 Top 10 Streaks:\n"
        for i, (user_id, streak) in enumerate(leaders, 1):
            message += f"{i}. User {user_id}: {streak} days\n"
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("No submissions yet.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all messages and check for GM."""
    if update.message and update.message.text:
        text = update.message.text.lower()
        if text in ["gm", "gm gm"]:
            # Get a random fun GM response
            responses = [
                "GM Builders! 🚀 Let's build something amazing today!",
                "GM! Ready to crush some Solidity code today? 💪",
                "GM fam! Another day, another smart contract! 🧠",
                "GM! Coffee + Solidity = Perfect morning! ☕",
                "GM! Let's keep that streak going! 🔥"
            ]
            await update.message.reply_text(random.choice(responses))

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get the current chat ID."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Chat ID: {chat_id}")

def main() -> None:
    """Start the bot."""
    # Initialize the application
    application = Application.builder().token(API_KEY).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("submit", submit))
    application.add_handler(CommandHandler("streak", streak))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("chatid", get_chat_id))

    # Add message handler for all messages (including GM)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
