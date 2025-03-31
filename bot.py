from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import logging
import random
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

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

# Constants
CHALLENGE_URL = "https://web3compass.xyz/challenge-calendar"
utc = pytz.UTC

# Database setup
conn = sqlite3.connect('submissions.db')
c = conn.cursor()

# Create submissions table with PR link and username
c.execute('''CREATE TABLE IF NOT EXISTS submissions
             (user_id INTEGER, username TEXT, submission_date TEXT, streak INTEGER, pr_link TEXT)''')

# Create daily challenges table
c.execute('''CREATE TABLE IF NOT EXISTS daily_challenges
             (day INTEGER PRIMARY KEY, title TEXT, description TEXT, youtube_link TEXT)''')
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "🚀 *Welcome to the 30-Day Solidity Challenge by Web3 Compass!* 🚀\n\n"
        "Ready to level up your blockchain skills? Here's how to participate:\n\n"
        "🔹 `/submit <github_pr_link>` - Submit your daily solution\n"
        "🔹 `/streak` - Check your current streak\n"
        "🔹 `/leaderboard` - See the top builders\n\n"
        "Let's build the decentralized future together! 💪",
        parse_mode="Markdown"
    )

async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle solution submissions with GitHub PR links."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ *Oops!* You forgot to include your GitHub PR link!\n\n"
            "*Correct Format:* `/submit <PR_link>`\n\n"
            "Example: `/submit https://github.com/user/repo/pull/123`",
            parse_mode="Markdown"
        )
        return

    pr_link = context.args[0]
    if not pr_link.startswith('https://github.com'):
        await update.message.reply_text(
            "❌ *Invalid Link Detected!*\n\n"
            "Please provide a valid GitHub PR link starting with `https://github.com`",
            parse_mode="Markdown"
        )
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

    # Get username (or first name if username is not available)
    username = update.message.from_user.username
    if not username:
        username = update.message.from_user.first_name
    
    # Save submission with PR link and username
    c.execute("INSERT INTO submissions (user_id, username, submission_date, streak, pr_link) VALUES (?, ?, ?, ?, ?)",
              (user_id, username, today.strftime('%Y-%m-%d'), streak, pr_link))
    conn.commit()

    # Add milestone badges
    if streak == 5:
        await update.message.reply_text(
            f"🎯 *PR SUBMITTED SUCCESSFULLY!* 🎯\n\n"
            f"🔥 *Streak: {streak} days* 🔥\n\n"
            f"🏆 Achievement Unlocked: *SOLIDITY NOVICE* 🏆\n\n"
            f"Keep building! You're on your way to greatness!",
            parse_mode="Markdown"
        )
    elif streak == 15:
        await update.message.reply_text(
            f"🎯 *PR SUBMITTED SUCCESSFULLY!* 🎯\n\n"
            f"🔥 *Streak: {streak} days* 🔥\n\n"
            f"🏆 Achievement Unlocked: *SOLIDITY ENTHUSIAST* 🏆\n\n"
            f"Amazing progress! You're becoming a true blockchain builder!",
            parse_mode="Markdown"
        )
    elif streak == 30:
        await update.message.reply_text(
            f"🎯 *PR SUBMITTED SUCCESSFULLY!* 🎯\n\n"
            f"🔥 *LEGENDARY STREAK: {streak} days* 🔥\n\n"
            f"🏆 ULTIMATE Achievement Unlocked: *SOLIDITY MASTER* 🏆\n\n"
            f"INCREDIBLE WORK! You've completed the entire challenge! 🚀",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"🎯 *PR SUBMITTED SUCCESSFULLY!* 🎯\n\n"
            f"🔥 *Current Streak: {streak} days* 🔥\n\n"
            f"Keep up the great work! Building consistently is the key to mastery.",
            parse_mode="Markdown"
        )

async def streak(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check user's current streak."""
    user_id = update.message.from_user.id
    
    # Get username (or first name if username is not available)
    username = update.message.from_user.username
    if not username:
        username = update.message.from_user.first_name
    
    c.execute("SELECT streak, username FROM submissions WHERE user_id=? ORDER BY submission_date DESC LIMIT 1", (user_id,))
    result = c.fetchone()
    if result:
        streak_days = result[0]
        stored_username = result[1] if len(result) > 1 else None
        
        # Update username if it has changed
        if stored_username != username:
            c.execute("UPDATE submissions SET username=? WHERE user_id=?", (username, user_id))
            conn.commit()
        
        if streak_days >= 20:
            emoji = "🔥🔥🔥"
            message = "LEGENDARY STATUS!"
        elif streak_days >= 10:
            emoji = "🔥🔥"
            message = "You're on fire!"
        else:
            emoji = "🔥"
            message = "Great start!"
            
        user_display = f"@{username}" if username else "Your"
        
        await update.message.reply_text(
            f"{emoji} *STREAK STATS* {emoji}\n\n"
            f"{user_display} current streak is *{streak_days} days*!\n\n"
            f"{message}",
            parse_mode="Markdown"
        )
    else:
        user_display = f"@{username}" if username else "You"
        await update.message.reply_text(
            f"😢 *No Submissions Yet*\n\n"
            f"{user_display} haven't submitted any solutions yet. \n"
            f"Submit your first solution with `/submit <github_pr_link>` to start your streak!",
            parse_mode="Markdown"
        )

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show top 10 users by streak."""
    c.execute("""
        SELECT username, MAX(streak) as max_streak 
        FROM submissions 
        GROUP BY user_id 
        ORDER BY max_streak DESC 
        LIMIT 10
    """)
    leaders = c.fetchall()
    if leaders:
        message = "🏆 *SOLIDITY CHALLENGE LEADERBOARD* 🏆\n\n"
        
        # Emoji medals for top 3
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (username, streak) in enumerate(leaders, 1):
            user_display = f"@{username}" if username else "Anonymous"
            if i <= 3:
                # Top 3 get special formatting
                message += f"{medals[i-1]} *{streak} days* - {user_display}\n"
            else:
                # Others get regular formatting
                message += f"{i}. *{streak} days* - {user_display}\n"
                
        message += "\n💪 Keep building to climb the ranks! 💪"
        await update.message.reply_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "📊 *LEADERBOARD EMPTY* 📊\n\n"
            "Be the first to submit and claim the top spot!",
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all messages and check for GM."""
    if update.message and update.message.text:
        text = update.message.text.lower()
        if text in ["gm", "gm gm"]:
            # Get a random fun GM response
            responses = [
                # Motivational
                "*GM Builders!* 🚀 Let's build something amazing today!",
                "*GM!* Ready to crush some Solidity code today? 💪",
                "*GM fam!* Another day, another smart contract! 🧠",
                "*GM!* Coffee + Solidity = Perfect morning! ☕",
                "*GM!* Let's keep that streak going! 🔥",
                
                # Web3 themed
                "*GM!* 🔗 Time to build those blockchain skills!",
                "*GM Solidity Builders!* 💸 Gas fees are high, but your potential is higher!",
                "*GM!* 💎 Diamonds are formed under pressure, just like great smart contracts!",
                "*GM!* 👨‍💻 Today's a great day to avoid reentrancy bugs!",
                "*GM!* 🤖 Building the future, one function at a time!",
                
                # Fun/Meme-y
                "*gm gm!* 🚀🚀 Double the gm, double the productivity!",
                "*GM!* 🤯 Solidity doesn't sleep and neither do we!",
                "*GM!* 💡 Is your brain fully charged for some big brain smart contract energy?",
                "*GM!* 👊 WAGMI - We're All Gonna Make Incredible contracts!",
                "*GM!* 👀 Eyes on the code, mind on the blockchain!",
                
                # Inspirational
                "*GM Builder!* 🌟 Remember: every expert was once a beginner.",
                "*GM!* 💪 Small consistent steps lead to giant achievements in Solidity.",
                "*GM!* 💰 Building wealth through building smart contracts!",
                "*GM!* 📈 Your streak is your most valuable NFT - don't break it!",
                "*GM!* 🎉 Every day you code is a day you grow!",
                
                # Seasonal/Time-based (can expand these based on time of year)
                "*GM Early Bird!* 🐦 Catching the blockchain worm today?",
                "*GM Night Owl!* 🦉 Coding through the night again?",
                "*GM!* 🐱 Don't let curiosity kill your cat... or your smart contract!",
                "*GM!* 🌞 Rise and shine! The blockchain never sleeps, but you should!",
                "*GM!* 🌙 Whether it's day or night where you are, it's always a good time to code!"
            ]
            await update.message.reply_text(random.choice(responses), parse_mode="Markdown")

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get the current chat ID."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"📱 *CHAT INFORMATION* 📱\n\n"
        f"Chat ID: `{chat_id}`\n\n"
        f"Use this ID in your .env file to configure the bot.",
        parse_mode="Markdown"
    )

def get_challenge_details(day):
    """Fetch challenge details from the website"""
    try:
        # First check if we already have it in the database
        c.execute("SELECT title, description FROM daily_challenges WHERE day=?", (day,))
        result = c.fetchone()
        if result:
            return {"title": result[0], "description": result[1]}
            
        # If not in database, try to fetch from website
        response = requests.get(CHALLENGE_URL)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # This is a placeholder - you'll need to adjust the selectors based on the actual website structure
            challenge_element = soup.select_one(f'#day-{day}')
            if challenge_element:
                title = challenge_element.select_one('.title').text
                description = challenge_element.select_one('.description').text
                
                # Save to database for future use
                c.execute("INSERT INTO daily_challenges (day, title, description) VALUES (?, ?, ?)",
                          (day, title, description))
                conn.commit()
                
                return {"title": title, "description": description}
        
        # If we couldn't get specific details, return generic info
        return {"title": f"Day {day} Challenge", "description": "Check the website for details!"}
    except Exception as e:
        logging.error(f"Error fetching challenge details: {e}")
        return {"title": f"Day {day} Challenge", "description": "Check the website for details!"}

async def announce_daily_challenge(application):
    """Announce the daily challenge at 12 AM UTC"""
    # Calculate current day (assuming challenge starts April 1st)
    current_day = (datetime.now(utc).date() - datetime(2025, 4, 1, tzinfo=utc).date()).days + 1
    
    if 1 <= current_day <= 30:
        challenge = get_challenge_details(current_day)
        if challenge:
            message = (f"🎯 Day {current_day} Challenge is LIVE! 🎯\n\n"
                      f"Today's Challenge: {challenge['title']}\n\n"
                      f"Description: {challenge['description']}\n\n"
                      f"Submit your solution using /submit <GitHub_PR_link>")
            
            # Send to all configured groups
            for chat_id in GROUP_CHAT_IDS:
                await application.bot.send_message(chat_id=chat_id, text=message)

async def send_reminder(application):
    """Send reminder 3 hours before deadline"""
    message = ("⏰ Only 3 hours left to submit today's challenge!\n"
               "Don't forget to submit your solution using /submit <GitHub_PR_link>")
    
    # Send to all configured groups
    for chat_id in GROUP_CHAT_IDS:
        await application.bot.send_message(chat_id=chat_id, text=message)

async def announce_solution(application):
    """Announce that solution is live"""
    # Calculate previous day (assuming challenge starts April 1st)
    current_day = (datetime.now(utc).date() - datetime(2025, 4, 1, tzinfo=utc).date()).days
    
    if 1 <= current_day <= 30:
        c.execute("SELECT youtube_link FROM daily_challenges WHERE day=?", (current_day,))
        result = c.fetchone()
        youtube_link = result[0] if result and result[0] else "[Link coming soon]"
        
        message = (f"📢 Solution for Day {current_day} is now LIVE!\n\n"
                  f"🌐 Check the solution on our website: {CHALLENGE_URL}\n"
                  f"📺 Watch the explanation: {youtube_link}")
        
        # Send to all configured groups
        for chat_id in GROUP_CHAT_IDS:
            await application.bot.send_message(chat_id=chat_id, text=message)

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
    
    # Add a command to manually trigger announcements (for testing)
    application.add_handler(CommandHandler("announce", lambda update, context: announce_daily_challenge(application)))
    application.add_handler(CommandHandler("reminder", lambda update, context: send_reminder(application)))
    application.add_handler(CommandHandler("solution", lambda update, context: announce_solution(application)))
    
    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
