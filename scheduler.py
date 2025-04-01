import asyncio
import logging
import os
import json
from datetime import datetime
import pytz
import requests
from bs4 import BeautifulSoup
import sqlite3
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application
from dotenv import load_dotenv

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
# Replace this with your GitHub raw content URL once you've uploaded the file
CHALLENGES_JSON_URL = "https://raw.githubusercontent.com/SethuRamanOmanakuttan/challenge-data-solution/refs/heads/main/challenges.json"
# Local fallback file
LOCAL_CHALLENGES_FILE = "challenges.json"
utc = pytz.UTC

# Predefined challenges as a fallback if both GitHub and local file fail
PREDEFINED_CHALLENGES = {
    1: {
        "contractName": "ClickCounter.sol",
        "week": "Week 1: Solidity Fundamentals",
        "exampleApplication": "A simple counter contract to learn variable declaration, function creation, and basic arithmetic. Like a YouTube view counter, tracking how many times a button is clicked.",
        "conceptsTaught": ["Basic Solidity syntax", "Variables (uint)", "Increment/Decrement functions"],
        "logicalProgression": "Foundational syntax and basic contract structure."
    },
    2: {
        "contractName": "SaveMyName.sol",
        "week": "Week 1: Solidity Fundamentals",
        "exampleApplication": "A contract that stores and retrieves a user's name and status, teaching basic data storage. Like Instagram profiles, where users can store and retrieve their names.",
        "conceptsTaught": ["State variables (string, bool)", "Storage and retrieval"],
        "logicalProgression": "Introduces data types and state management."
    },
    3: {
        "contractName": "PollStation.sol",
        "week": "Week 1: Solidity Fundamentals",
        "exampleApplication": "A simple voting contract where users can vote, demonstrating arrays and mappings. Like Twitter/X polls, where users vote for their favorite option.",
        "conceptsTaught": ["Arrays (uint[])", "Mappings (mapping(address => uint))", "Simple voting logic"],
        "logicalProgression": "Introduces complex data structures (arrays, mappings) and logic."
    }
    # These are only used as a last resort
}

# Database setup
conn = sqlite3.connect('submissions.db')
c = conn.cursor()

# Create daily challenges table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS daily_challenges
             (day INTEGER PRIMARY KEY, contract_name TEXT, week TEXT, example_application TEXT, 
              concepts_taught TEXT, logical_progression TEXT, youtube_link TEXT)''')
conn.commit()

def load_challenges_from_json():
    """Load challenges from GitHub or local JSON file"""
    challenges_by_day = {}
    
    #Try to fetch from GitHub first
    try:
        logging.info(f"Attempting to fetch challenges from GitHub: {CHALLENGES_JSON_URL}")
        response = requests.get(CHALLENGES_JSON_URL, timeout=10)
        if response.status_code == 200:
            challenges_data = response.json()
            logging.info(f"Successfully loaded challenges from GitHub")
            
            # Convert to dictionary by day for easy lookup
            for challenge in challenges_data.get("schedule", []):
                day = challenge.get("day")
                if day:
                    challenges_by_day[day] = challenge
            
            return challenges_by_day
    except Exception as e:
        logging.error(f"Error fetching challenges from GitHub: {e}")
    
    # If GitHub fails, try local file
    # try:
    #     logging.info(f"Attempting to load challenges from local file: {LOCAL_CHALLENGES_FILE}")
    #     with open(LOCAL_CHALLENGES_FILE, 'r') as f:
    #         challenges_data = json.load(f)
    #         logging.info(f"Successfully loaded challenges from local file")
            
    #         # Convert to dictionary by day for easy lookup
    #         for challenge in challenges_data.get("schedule", []):
    #             day = challenge.get("day")
    #             if day:
    #                 challenges_by_day[day] = challenge
            
    #         return challenges_by_day
    # except Exception as e:
    #     logging.error(f"Error loading challenges from local file: {e}")
    
    # If all else fails, return predefined challenges
    logging.warning("Using predefined challenges as fallback")
    return PREDEFINED_CHALLENGES

# Load challenges when the module is imported
ALL_CHALLENGES = load_challenges_from_json()

def get_challenge_details(day):
    """Fetch challenge details from JSON, database, or website"""
    try:
        # First check if we already have it in the database
        c.execute("SELECT contract_name, week, example_application, concepts_taught, logical_progression FROM daily_challenges WHERE day=?", (day,))
        result = c.fetchone()
        if result:
            logging.info(f"Found challenge for day {day} in database")
            challenge = {
                "contractName": result[0],
                "week": result[1],
                "exampleApplication": result[2]
            }
            if result[3]:  # If concepts are stored
                challenge["conceptsTaught"] = result[3].split(",")
            if result[4]:
                challenge["logicalProgression"] = result[4]
            return challenge
        
        # Check if we have the challenge in our loaded challenges
        if day in ALL_CHALLENGES:
            logging.info(f"Using challenge from JSON for day {day}")
            challenge = ALL_CHALLENGES[day]
            
            # Store in database for future use
            concepts_str = ",".join(challenge.get("conceptsTaught", []))
            c.execute("INSERT INTO daily_challenges (day, contract_name, week, example_application, concepts_taught, logical_progression) VALUES (?, ?, ?, ?, ?, ?)",
                    (day, challenge.get("contractName", ""), challenge.get("week", ""), challenge.get("exampleApplication", ""), 
                     concepts_str, challenge.get("logicalProgression", "")))
            conn.commit()
            logging.info(f"Saved JSON challenge for day {day} to database")
            
            return challenge
        
        # If not in database or JSON, try to fetch from website as a last resort
        logging.info(f"Challenge for day {day} not found in database or JSON, fetching from website")
        
        try:
            logging.info(f"Attempting to fetch challenge details for day {day} from website")
            response = requests.get(CHALLENGE_URL, timeout=15)
            
            if response.status_code == 200:
                logging.info("Website accessible, parsing content")
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try multiple strategies to find the challenge
                # Strategy 1: Look for day-specific sections
                day_sections = []
                
                # Look for headings with day number
                day_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                for heading in day_headings:
                    if f"Day {day}" in heading.text or f"DAY {day}" in heading.text:
                        logging.info(f"Found heading: {heading.text}")
                        day_sections.append(heading)
                
                # Look for sections or divs with day info
                sections = soup.find_all(['section', 'div', 'article'])
                for section in sections:
                    if f"Day {day}" in section.text or f"DAY {day}" in section.text:
                        if len(section.text) > 100:  # Only consider substantial sections
                            logging.info(f"Found section containing Day {day}")
                            day_sections.append(section)
                
                # If we found any day-specific sections, try to extract title and description
                if day_sections:
                    for section in day_sections:
                        # Try to extract title
                        title_elem = None
                        if section.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            title_elem = section
                        else:
                            title_elem = section.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                        
                        title = f"Day {day} Challenge"
                        if title_elem:
                            title = title_elem.text.strip()
                            logging.info(f"Extracted title: {title}")
                        
                        # Try to extract description
                        description = ""
                        desc_elems = []
                        
                        if section.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            # If section is a heading, look at siblings
                            next_elem = section.find_next_sibling()
                            while next_elem and next_elem.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                if next_elem.name in ['p', 'div', 'span', 'ul', 'ol'] and len(next_elem.text.strip()) > 10:
                                    desc_elems.append(next_elem)
                                next_elem = next_elem.find_next_sibling()
                        else:
                            # If section is a container, look at children
                            desc_elems = section.find_all(['p', 'div', 'span', 'ul', 'ol'])
                        
                        # Combine description elements
                        for elem in desc_elems:
                            if len(elem.text.strip()) > 10:  # Only include non-empty elements
                                description += elem.text.strip() + "\n\n"
                        
                        description = description.strip()
                        if description:
                            logging.info(f"Extracted description (first 100 chars): {description[:100]}...")
                            
                            # Try to extract concepts
                            concepts = []
                            concepts_section = section.find(string=lambda text: "concepts" in text.lower() if text else False)
                            if concepts_section:
                                # Try to find nearby list items
                                concept_list = concepts_section.find_parent().find_all(['li', 'ul', 'ol'])
                                for item in concept_list:
                                    if len(item.text.strip()) > 3:  # Avoid empty items
                                        concepts.append(item.text.strip())
                            
                            # Save to database
                            concepts_str = ",".join(concepts)
                            c.execute("INSERT INTO daily_challenges (day, title, description, concepts) VALUES (?, ?, ?, ?)",
                                    (day, title, description, concepts_str))
                            conn.commit()
                            logging.info(f"Saved challenge for day {day} to database")
                            
                            return {"title": title, "description": description, "concepts": concepts}
        
        except Exception as web_error:
            logging.error(f"Error fetching from website: {web_error}")
        
        # If we couldn't extract from the website, return a message directing to the website
        logging.warning(f"Could not extract challenge details for day {day} from website")
        return {
            "title": f"Day {day} Challenge", 
            "description": f"Today's challenge is now live! Visit {CHALLENGE_URL} to view the full details.\n\nSubmit your solution using /submit <GitHub_PR_link> when you're done!"
        }
    except Exception as e:
        logging.error(f"Unexpected error in get_challenge_details: {e}")
        return {
            "title": f"Day {day} Challenge", 
            "description": f"Today's challenge is now live! Visit {CHALLENGE_URL} to view the full details.\n\nSubmit your solution using /submit <GitHub_PR_link> when you're done!"
        }

async def announce_daily_challenge(application):
    """Announce the daily challenge at 12 AM UTC"""
    # Calculate current day (assuming challenge starts April 1st)
    current_day = (datetime.now(utc).date() - datetime(2025, 4, 1, tzinfo=utc).date()).days + 1
    
    if 1 <= current_day <= 30:
        challenge = get_challenge_details(current_day)
        if challenge:
            # Format concepts if available
            concepts_text = ""
            if 'conceptsTaught' in challenge and challenge['conceptsTaught']:
                concepts_text = "🔍 *Concepts You'll Master:*\n"
                for concept in challenge['conceptsTaught']:
                    concepts_text += f"• {concept}\n"
                concepts_text += "\n"
            
            # Get week information
            week_text = f"📅 *{challenge.get('week', '')}*\n\n" if 'week' in challenge else ""
            
            # Get example application
            example_text = ""
            if 'exampleApplication' in challenge and challenge['exampleApplication']:
                example_text = f"🔎 *Example Application:*\n{challenge['exampleApplication']}\n\n"
            
            # Get logical progression
            progression_text = ""
            if 'logicalProgression' in challenge and challenge['logicalProgression']:
                progression_text = f"📈 *Learning Progression:*\n{challenge['logicalProgression']}\n\n"
            
            message = (f"💥 *DAY {current_day} CHALLENGE IS LIVE!* 💥\n\n"
                      f"{week_text}"
                      f"📌 *Today's Challenge:* {challenge.get('contractName', f'Day {current_day} Challenge')}\n\n"
                      f"{example_text}"
                      f"{concepts_text}"
                      f"{progression_text}"
                      f"🔗 *Full Details:* [Web3 Compass Challenge Calendar]({CHALLENGE_URL})\n\n"
                      f"👉 Submit your solution using `/submit <GitHub_PR_link>`\n\n"
                      f"💪 Let's crush this challenge together, builders!")
            
            # Send to all configured groups
            for chat_id in GROUP_CHAT_IDS:
                try:
                    await application.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                    logging.info(f"Sent daily challenge announcement to chat {chat_id}")
                except Exception as e:
                    logging.error(f"Failed to send announcement to chat {chat_id}: {e}")

async def send_reminder(application):
    """Send reminder 3 hours before deadline"""
    message = ("⏰ *FINAL COUNTDOWN: 3 HOURS LEFT!* ⏰\n\n"
               "🔥 Time is running out for today's challenge!\n\n"
               "💻 Don't break your streak! Submit your solution using `/submit <GitHub_PR_link>`\n\n"
               "💡 Tip: Even a simple solution is better than missing a day!")
    
    # Send to all configured groups
    for chat_id in GROUP_CHAT_IDS:
        try:
            await application.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
            logging.info(f"Sent reminder to chat {chat_id}")
        except Exception as e:
            logging.error(f"Failed to send reminder to chat {chat_id}: {e}")


async def Web3ResourceMessage(application):
    """Send reminder 3 hours before deadline"""
    # message = ("⏰ *FINAL COUNTDOWN: 3 HOURS LEFT!* ⏰\n\n"
    #            "🔥 Time is running out for today's challenge!\n\n"
    #            "💻 Don't break your streak! Submit your solution using `/submit <GitHub_PR_link>`\n\n"
    #            "💡 Tip: Even a simple solution is better than missing a day!")
    message = ("📚 *JUST LAUNCHED: THE WEB3 RESOURCE VAULT* 🧠💥\n\n"
           "We've opened up a brand new GitHub repo full of 🔥 Web3 learning resources — tutorials, blogs, videos, and more!\n\n"
           "🌍 Dive in here: [Web3 Resource Vault](https://github.com/The-Web3-Compass/Web3-Resources)\n\n"
           "✨ If you find it helpful, don’t forget to ⭐ star the repo and hit that 'Follow' button to stay in the loop.\n\n"
           "🛠️ Got a cool link or hidden gem? PRs are open — come contribute and help the community grow smarter, faster, and more decentralized 🧙‍♂️🚀")

    current_day = (datetime.now(utc).date() - datetime(2025, 4, 1, tzinfo=utc).date()).days + 1
    if current_day == 1:
    # Send to all configured groups
        for chat_id in GROUP_CHAT_IDS:
            try:
                await application.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                logging.info(f"Sent reminder to chat {chat_id}")
            except Exception as e:
                logging.error(f"Failed to send reminder to chat {chat_id}: {e}")

# async def announce_solution(application):
#     """Announce that solution is live"""
#     # Calculate previous day (assuming challenge starts April 1st)
#     current_day = (datetime.now(utc).date() - datetime(2025, 4, 1, tzinfo=utc).date()).days
    
#     if 1 <= current_day <= 30:
#         challenge = get_challenge_details(current_day)
#         print(challenge)
#         # c.execute("SELECT youtube_link FROM daily_challenges WHERE day=?", (current_day,))
#         # result = c.fetchone()
#         # youtube_link = result[0] if result and result[0] else "[Link coming soon]"
        
#         # message = (f"📣 *SOLUTION REVEAL: DAY {current_day}* 📣\n\n"
#         #           f"The official solution for yesterday's challenge is now available!\n\n"
#         #           f"🌐 *Website Solution:* [Web3 Compass]({CHALLENGE_URL})\n"
#         #           f"📺 *Video Walkthrough:* [Watch Here]({youtube_link})\n\n"
#         #           f"📚 Compare your approach with the official solution to level up your skills!")
        
#         # # Send to all configured groups
#         # for chat_id in GROUP_CHAT_IDS:
#         #     try:
#         #         await application.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
#         #         logging.info(f"Sent solution announcement to chat {chat_id}")
#         #     except Exception as e:
#         #         logging.error(f"Failed to send solution announcement to chat {chat_id}: {e}")

async def announce_solution(application):
    """Announce that solution is live"""
    # Calculate previous day (assuming challenge starts April 1st)
    current_day = (datetime.now(utc).date() - datetime(2025, 4, 1, tzinfo=utc).date()).days+1
    print(current_day)
    if 1 <= current_day <= 30:
        challenge = ALL_CHALLENGES.get(current_day, {})
        if not challenge:
            logging.warning(f"No challenge found for Day {current_day}")
            return

        youtube_link = challenge.get("youtubeLink", "[Link coming soon]")
        solution_link = challenge.get("solutionLink", CHALLENGE_URL)

        if youtube_link != "[Link coming soon]" and solution_link != CHALLENGE_URL:
            message = (f"📣 *SOLUTION REVEAL: DAY {current_day}* 📣\n\n"
                       f"The official solution for today's challenge is now live!\n\n"
                       f"📜 *Challenge:* `{challenge.get('contractName', f'Day {current_day} Challenge')}`\n\n"
                       f"🧠 *Solution Link:* [View Solution]({solution_link})\n"
                       f"📺 *Video Walkthrough:* [Watch Here]({youtube_link})\n\n"
                       f"🎯 Compare your approach with the official one and level up!")
        else:
            message = (f"📣 *DAY {current_day} SOLUTION UPDATE* 📣\n\n"
                       f"The solution for yesterday's challenge is not live yet.\n\n"
                       f"🎬 Video and GitHub links dropping soon 👀 Stay tuned!\n"
                       f"In the meantime, feel free to share your approach with the community!")

        for chat_id in GROUP_CHAT_IDS:
            try:
                await application.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                logging.info(f"Sent solution update for Day {current_day} to chat {chat_id}")
            except Exception as e:
                logging.error(f"Failed to send solution message to chat {chat_id}: {e}")


async def main():
    """Run the scheduler"""
    # Initialize the application
    application = Application.builder().token(API_KEY).build()
    await application.initialize()
    await application.start()
    
    # Set up scheduler
    scheduler = AsyncIOScheduler(timezone=utc)
    
    # Schedule daily challenge announcement at 12 AM UTC
    scheduler.add_job(announce_daily_challenge, 'cron', hour=0, minute=0, args=[application])

    # scheduler.add_job(announce_daily_challenge, 'cron', hour=7, minute=13, args=[application])


    # Schedule reminder 3 hours before deadline (9 PM UTC)
    scheduler.add_job(send_reminder, 'cron', hour=21, minute=0, args=[application])

    # scheduler.add_job(send_reminder, 'cron', hour=6, minute=53, args=[application])

    
    # Schedule solution announcement at 12:05 AM UTC (just after next day's challenge)
    scheduler.add_job(announce_solution, 'cron', hour=23, minute=55, args=[application])

    # scheduler.add_job(announce_solution, 'cron', hour=7, minute=46, args=[application])

    scheduler.add_job(Web3ResourceMessage, 'cron', hour=9, minute=30, args=[application])

    
    # Start the scheduler
    scheduler.start()
    
    logging.info("Scheduler started. Press Ctrl+C to exit.")
    
    # Keep the script running
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
