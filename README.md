# Sched.com Attachment Downloader

This script logs into Sched.com, lists your events, and downloads all session attachments (PDF, PPTX, etc.) for a selected event using Microsoft Edge and Selenium.

## Prerequisites
- Python 3.8+
- Microsoft Edge browser (already installed)

## Setup
1. Create and activate a Python virtual environment:
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Run the script:
   ```sh
   python sched_attachment_downloader.py
   ```

The script will automatically download and manage the correct Edge WebDriver for you.

## Features
- Secure login prompt (credentials not stored)
- Event selection
- Downloads all session attachments into a subfolder named after the event
- Progress bar for downloads
- Sleek, user-friendly terminal output

---

If you encounter any issues with Edge WebDriver, ensure Edge is up to date. For questions or feature requests, let me know!
