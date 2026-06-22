import time
import csv
import os
import re
import shutil
from playwright.sync_api import sync_playwright
from findProfiles import discoverCreators
from findEmail import scrapeEmails


def load_seeds(niche):
    seed_file = os.path.join('seeds', f'{niche}.txt')
    if not os.path.exists(seed_file):
        raise FileNotFoundError(f"No seed file for niche '{niche}'. Create seeds/{niche}.txt")
    usernames = []
    with open(seed_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if 'instagram.com/' in line:
                username = line.rstrip('/').split('/')[-1]
            else:
                username = line
            usernames.append(username)
    return usernames


def save_results(results, niche):
    os.makedirs('output', exist_ok=True)
    path = os.path.join('output', f'{niche}_emails.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['username', 'email', 'profile_url'])
        writer.writeheader()
        writer.writerows(results)
    return path


def ensure_logged_in(page):
    # Use /direct/inbox/ as the auth test — it always redirects to login if not authenticated
    page.goto('https://www.instagram.com/direct/inbox/')
    page.wait_for_load_state('networkidle')
    time.sleep(2)

    if 'accounts/login' not in page.url:
        print("Already logged in via saved session.\n")
        return

    print("Browser is open — log in to Instagram manually in the window.")
    print("Waiting up to 2 minutes for you to complete login...\n")

    try:
        page.wait_for_url(
            re.compile(r'instagram\.com/(?!accounts/login)'),
            timeout=120000
        )
    except Exception:
        print("Login timed out. Exiting.")
        raise SystemExit(1)

    time.sleep(3)
    # Dismiss any post-login popups
    for label in ["Not Now", "Not now", "Later"]:
        try:
            page.locator(f'button:text("{label}")').first.click(timeout=1500)
        except:
            pass
    print("Logged in!\n")


def main():
    niche = input("Enter niche (e.g. cs, fitness, fashion): ").strip()
    seeds = load_seeds(niche)
    print(f"Loaded {len(seeds)} seed(s)")

    target_count = int(input("How many creator profiles to find? ").strip())

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir='.browser_data',
            headless=False,
            ignore_default_args=['--enable-automation'],
            args=['--disable-blink-features=AutomationControlled'],
            viewport={'width': 1280, 'height': 800},
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
        )
        page = browser.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        ensure_logged_in(page)

        print(f"Starting BFS, targeting {target_count} creators...\n")
        creators = discoverCreators(seeds, page, target_count)
        print(f"\nDiscovered {len(creators)} creator profiles")

        results = scrapeEmails(creators)
        print(f"Email addresses found: {len(results)}")

        if results:
            path = save_results(results, niche)
            print(f"Saved to {path}")
        else:
            print("No emails found in bios.")

        browser.close()


if __name__ == '__main__':
    main()
