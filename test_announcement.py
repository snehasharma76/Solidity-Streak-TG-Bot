#!/usr/bin/env python3
"""
Test script to simulate challenge announcements with sideTrack content.
This script allows testing the announcement formatting for any day.
"""

import sys
import asyncio
from datetime import datetime
import pytz
import argparse
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Import from the project
sys.path.append('/home/sethuraman/Documents/Projects/Solidity-Streak-TG-Bot')
from scheduler import get_challenge_details

class MockApplication:
    """Mock Telegram application for testing"""
    class MockBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            print(f'\n===== MOCK MESSAGE TO CHAT {chat_id} =====\n')
            print(f'Parse mode: {parse_mode}')
            print(f'\n{text}\n')
            return True
    
    def __init__(self):
        self.bot = self.MockBot()

async def test_challenge_announcement(day):
    """Test the challenge announcement for a specific day"""
    print(f'\n===== TESTING CHALLENGE ANNOUNCEMENT FOR DAY {day} =====\n')
    
    # Get challenge details
    challenge = get_challenge_details(day)
    
    if not challenge:
        print(f"No challenge found for day {day}")
        return
    
    print(f"Challenge details for day {day}:")
    print(f"Contract Name: {challenge.get('contractName', 'Not found')}")
    print(f"Week: {challenge.get('week', 'Not found')}")
    
    # Check for sideTrack
    if 'sideTrack' in challenge:
        print("\nSideTrack found:")
        sidetrack = challenge['sideTrack']
        print(f"Title: {sidetrack.get('title', 'Not found')}")
        print(f"Concepts: {sidetrack.get('conceptsTaught', [])}")
    else:
        print("\nNo sideTrack found for this day")
    
    # Format the announcement message
    
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
    
    # Check for sideTrack content
    sidetrack_text = ""
    if 'sideTrack' in challenge and challenge['sideTrack']:
        sidetrack = challenge['sideTrack']
        sidetrack_text = f"\n🔄 *SIDE TRACK: {sidetrack.get('title', 'Special Topic')}*\n\n"
        
        # Add sideTrack concepts if available
        if 'conceptsTaught' in sidetrack and sidetrack['conceptsTaught']:
            sidetrack_text += "🧠 *Key Points:*\n"
            for concept in sidetrack['conceptsTaught']:
                sidetrack_text += f"• {concept}\n"
            sidetrack_text += "\n"
        
        # Add sideTrack example if available
        if 'exampleApplication' in sidetrack and sidetrack['exampleApplication']:
            sidetrack_text += f"🛠️ *Practical Example:*\n{sidetrack['exampleApplication']}\n\n"
    
    # Build the message
    message = f"💥 *DAY {day} CHALLENGE IS LIVE!* 💥\n\n"
    message += week_text
    message += f"📌 *Today's Challenge:* {challenge.get('contractName', f'Day {day} Challenge')}\n\n"
    message += example_text
    message += concepts_text
    message += progression_text
    message += sidetrack_text
    message += f"🔗 *Full Details:* [Web3 Compass Challenge Calendar](https://web3compass.xyz/challenge-calendar)\n\n"
    message += f"👉 Submit your solution using `/submit <GitHub_PR_link>`\n\n"
    message += f"💪 Let's crush this challenge together, builders!"
    
    print("\n===== FORMATTED ANNOUNCEMENT =====\n")
    print(message)
    
    # Mock sending to a chat
    mock_app = MockApplication()
    await mock_app.bot.send_message(chat_id=123456789, text=message, parse_mode="Markdown")

async def test_solution_announcement(day):
    """Test the solution announcement for a specific day"""
    print(f'\n===== TESTING SOLUTION ANNOUNCEMENT FOR DAY {day} =====\n')
    
    # Get challenge details
    challenge = get_challenge_details(day)
    
    if not challenge:
        print(f"No challenge found for day {day}")
        return
    
    youtube_link = challenge.get("youtubeLink", "[Link coming soon]")
    solution_link = challenge.get("solutionLink", "https://web3compass.xyz/challenge-calendar")
    
    # Build the message
    contract_name = challenge.get('contractName', f'Day {day} Challenge')
    message = f"📣 *SOLUTION REVEAL: DAY {day}* 📣\n\n"
    message += f"The official solution for yesterday's challenge is now live!\n\n"
    message += f"📜 *Challenge:* `{contract_name}`\n\n"
    message += f"🧠 *Solution Link:* [View Solution]({solution_link})\n"
    message += f"📺 *Video Walkthrough:* [Watch Here]({youtube_link})\n\n"
    message += f"🎯 Compare your approach with the official one and level up!"
    
    print("\n===== FORMATTED SOLUTION ANNOUNCEMENT =====\n")
    print(message)
    
    # Mock sending to a chat
    mock_app = MockApplication()
    await mock_app.bot.send_message(chat_id=123456789, text=message, parse_mode="Markdown")

async def main():
    """Main function to run tests"""
    parser = argparse.ArgumentParser(description='Test challenge announcements')
    parser.add_argument('day', type=int, help='Day number to test (1-30)')
    parser.add_argument('--solution', action='store_true', help='Test solution announcement instead of challenge')
    args = parser.parse_args()
    
    if args.day < 1 or args.day > 30:
        print("Day must be between 1 and 30")
        return
    
    if args.solution:
        await test_solution_announcement(args.day)
    else:
        await test_challenge_announcement(args.day)

if __name__ == '__main__':
    asyncio.run(main())
