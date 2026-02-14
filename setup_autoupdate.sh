#!/bin/bash
# Install dependencies and setup auto-update for CSOH news page

echo "Setting up CSOH News Page Auto-Updater..."
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

echo "Installing required Python packages..."
pip3 install requests beautifulsoup4

echo ""
echo "Setup complete!"
echo ""
echo "To run the updater manually:"
echo "  python3 update_news.py"
echo ""
echo "To auto-update every day at 2 AM (macOS/Linux):"
echo "  1. Open crontab editor: crontab -e"
echo "  2. Add this line:"
echo "     0 2 * * * cd $(pwd) && python3 update_news.py"
echo ""
echo "To auto-update every day at 2 AM (Windows):"
echo "  1. Open Task Scheduler"
echo "  2. Create Basic Task with trigger: Daily at 2:00 AM"
echo "  3. Action: python3 C:\\path\\to\\update_news.py"
