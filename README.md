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
- Username, password and event URL saved in cred.txt file for easy re-run (delete this after you are done!)
- Event files downloaded into folders with session name and speaker names
- Downloads all session attachments into a subfolder named after the event
- Progress bar for downloads
- User-friendly terminal output

---

If you encounter any issues with Edge WebDriver, ensure Edge is up to date. For questions or feature requests, let me know!
Tested on MacOS
