#!/bin/bash

# Start the bot in the background
echo "Starting Solidity Streak Bot..."
python3 bot.py &
BOT_PID=$!

# Start the scheduler in the background
echo "Starting scheduler..."
python3 scheduler.py &
SCHEDULER_PID=$!

# Function to handle script termination
cleanup() {
    echo "Stopping bot and scheduler..."
    kill $BOT_PID $SCHEDULER_PID
    exit 0
}

# Register the cleanup function for when the script is terminated
trap cleanup SIGINT SIGTERM

echo "Both bot and scheduler are running!"
echo "Press Ctrl+C to stop both processes."

# Wait for both processes
wait
