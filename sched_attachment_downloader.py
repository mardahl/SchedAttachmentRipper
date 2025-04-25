import os
import sys
import time
import getpass
from pathlib import Path
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# Configurable constants
SCHED_LOGIN_URL = "https://sched.com/login/"
SCHED_DASHBOARD_URL = "https://sched.com/dashboard/"
ATTACHMENT_EXTENSIONS = [".pdf", ".pptx", ".ppt", ".docx", ".doc"]


def get_credentials_and_event_url():
    creds_path = Path(__file__).parent / "creds.txt"
    username = password = event_url = None
    if creds_path.exists():
        with open(creds_path, "r") as f:
            lines = f.read().splitlines()
            if len(lines) >= 2:
                username, password = lines[0], lines[1]
                if len(lines) >= 3:
                    event_url = lines[2]
    if not username or not password:
        print("\nPlease enter your Sched.com credentials (they will be saved in creds.txt):")
        username = input("Email/Username: ")
        password = getpass.getpass("Password: ")
    if not event_url:
        event_url = input("\nPaste the full URL of the Sched.com event you want to scrape: ").strip()
    # Save/overwrite creds.txt with all three lines
    with open(creds_path, "w") as f:
        f.write(username + "\n" + password + "\n" + event_url + "\n")
    print("Credentials and event URL saved to creds.txt.")
    return username, password, event_url


def setup_driver():
    print("\nSetting up Edge WebDriver...")
    options = webdriver.EdgeOptions()
    options.add_argument("--start-maximized")
    service = EdgeService(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=options)
    return driver


def login_sched(driver, username, password):
    driver.get(SCHED_LOGIN_URL)
    # Wait for either username or email field
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        user_field = driver.find_element(By.NAME, "username")
    except Exception:
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            user_field = driver.find_element(By.NAME, "email")
        except Exception:
            print("Could not find username or email field on login page. The page structure may have changed.")
            return False
    user_field.send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)
    # Try to close cookie banner if present (common class/id patterns)
    try:
        cookie_buttons = driver.find_elements(By.XPATH, "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept') or contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'agree') or contains(@id,'cookie') or contains(@class,'cookie')]")
        for btn in cookie_buttons:
            try:
                btn.click()
                time.sleep(0.5)
            except Exception:
                continue
    except Exception:
        pass
    # Find the login button by name
    try:
        login_btn = driver.find_element(By.NAME, "login")
        driver.execute_script("arguments[0].scrollIntoView(true);", login_btn)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.NAME, "login")))
        login_btn.click()
    except Exception:
        print("Could not find or click the login button. The page structure may have changed.")
        return False
    # Wait for login to complete: check for disappearance of login form or presence of 'my-events' link
    try:
        WebDriverWait(driver, 20).until(
            lambda d: not d.find_elements(By.NAME, "username") and not d.find_elements(By.NAME, "password")
        )
        # Also check for 'my-events' link or user profile
        if driver.find_elements(By.XPATH, "//a[contains(@href, '/my-events')]"):
            print("Login successful!\n")
            return True
    except Exception:
        pass
    # If login form is still present, warn user
    if driver.find_elements(By.NAME, "username") or driver.find_elements(By.NAME, "password"):
        print("Login failed. Login form is still present. Please check your credentials or if there is a CAPTCHA.")
        return False
    print("Login may have succeeded, but could not confirm. Continuing...")
    return True


def list_events(driver):
    # Go to the user's events page
    driver.get("https://sched.com/my-events?1#speaking")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "event_title")))
    event_divs = driver.find_elements(By.CLASS_NAME, "event_title")
    events = []
    for div in event_divs:
        try:
            link = div.find_element(By.TAG_NAME, "a")
            href = link.get_attribute("href")
            name = link.text.strip()
            if href and name:
                events.append({"name": name, "url": href})
        except Exception:
            continue
    if not events:
        print("No events found on your speaking page.")
        sys.exit(1)
    print("Available events:")
    for idx, event in enumerate(events, 1):
        print(f"  [{idx}] {event['name']}")
    while True:
        try:
            choice = int(input("\nSelect an event by number: "))
            if 1 <= choice <= len(events):
                return events[choice - 1]
        except ValueError:
            pass
        print("Invalid selection. Try again.")

def get_event_days(driver, event_url):
    # Always include the current event_url as the first day to scrape
    driver.get(event_url)
    time.sleep(1)
    day_hrefs = [event_url]  # current day first
    # Find the sched-dates-menu div and extract all day hrefs (other days only)
    try:
        dates_menu = driver.find_element(By.CLASS_NAME, "sched-dates-menu")
        links = dates_menu.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href")
            if href and href != event_url:
                day_hrefs.append(href)
    except Exception:
        pass  # It's fine if there are no other days
    return day_hrefs

import re

def sanitize_filename(name):
    # Replace forbidden/special characters for folders/files
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()

def get_sessions_for_day(driver, day_url):
    driver.get(day_url)
    time.sleep(1)
    sessions = []
    # Find all <span class="event"> and get their <a> child, title, and speakers
    event_spans = driver.find_elements(By.CSS_SELECTOR, "span.event")
    for event_span in event_spans:
        try:
            link = event_span.find_element(By.TAG_NAME, "a")
            href = link.get_attribute("href")
            title = link.text.split('\n')[0].strip()
            # Try to get speakers from <span class="sched-event-evpeople"> inside <a>
            try:
                speakers_span = link.find_element(By.CLASS_NAME, "sched-event-evpeople")
                speakers = speakers_span.text.strip()
            except Exception:
                speakers = "Unknown Speaker"
            if href:
                sessions.append({
                    "href": href,
                    "title": title,
                    "speakers": speakers
                })
        except Exception:
            continue
    return sessions

def get_attachments_for_session(driver, session_url, session_folder):
    driver.get(session_url)
    time.sleep(1)
    found = False
    # Find all <a> tags with class containing 'file-uploaded' (even if there are other classes)
    links = driver.find_elements(By.XPATH, "//a[contains(@class, 'file-uploaded')]")
    for link in links:
        href = link.get_attribute("href")
        text = link.text.strip() or os.path.basename(href)
        # Try to find the extension from the nearby .sched-file-extension span
        extension = None
        try:
            parent = link.find_element(By.XPATH, "..")
            ext_span = parent.find_element(By.CLASS_NAME, "sched-file-extension")
            extension = ext_span.text.strip()
        except Exception:
            pass
        if href:
            # Build filename: use anchor text, append extension if not present
            filename = text
            if extension and not filename.lower().endswith(extension.lower()):
                filename = f"{filename}.{extension}"
            filename = sanitize_filename(filename)
            dest_path = session_folder / filename
            if dest_path.exists():
                print(f"    Skipping (already exists): {filename}")
                continue
            try:
                print(f"    Downloading: {filename}")
                download_file(href, dest_path)
                found = True
            except Exception as e:
                print(f"    Failed to download {filename}: {e}")
    if not links:
        print(f"    No files found in session.")
    return found


def find_attachments_on_session(driver, session_url):
    driver.get(session_url)
    time.sleep(1)
    attachments = []
    # Look for links to files with known extensions
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        href = link.get_attribute("href")
        if href and any(href.lower().endswith(ext) for ext in ATTACHMENT_EXTENSIONS):
            text = link.text.strip() or os.path.basename(href)
            attachments.append({"url": href, "name": text})
    return attachments


def download_file(url, dest_path):
    import requests
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        with open(dest_path, 'wb') as f, tqdm(
            desc=os.path.basename(dest_path),
            total=total,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            leave=False
        ) as bar:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))


def main():
    username, password, event_url = get_credentials_and_event_url()
    driver = setup_driver()
    try:
        if not login_sched(driver, username, password):
            driver.quit()
            sys.exit(1)
        # Use event_url directly, and name the folder after the event (last part of URL)
        event_name = event_url.rstrip('/').split('/')[-1]
        event_dir = Path.cwd() / event_name.replace('/', '_')
        event_dir.mkdir(exist_ok=True)
        day_links = get_event_days(driver, event_url)
        print(f"\nFound {len(day_links)} event day(s). Gathering sessions and attachments...")
        for day_url in tqdm(day_links, desc="Event Days", unit="day"):
            sessions = get_sessions_for_day(driver, day_url)
            for session in tqdm(sessions, desc="Sessions", unit="session", leave=False):
                session_title = sanitize_filename(session['title'])
                speakers = sanitize_filename(session['speakers'])
                session_folder = event_dir / f"{session_title} - {speakers}"
                session_folder.mkdir(exist_ok=True)
                print(f"  Session: {session['title']} | Speakers: {session['speakers']}")
                get_attachments_for_session(driver, session['href'], session_folder)
        print(f"\nAll available attachments downloaded to: {event_dir}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
