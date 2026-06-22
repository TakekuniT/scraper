from playwright.sync_api import Page
from collections import deque
from findEmail import extractEmails
import time
import re

CREATOR_SIGNALS = [
    "creator", "content creator", "youtuber", "youtube", "tiktok",
    "video", "collab", "influencer", "ugc", "podcast", "streamer",
    "link in bio", "new video", "filmmaker", "educator"
]

def dismissPopups(page):
    for label in ["Not Now", "Not now", "Later"]:
        try:
            page.locator(f'button:text("{label}")').first.click(timeout=1500)
        except:
            pass

def login(page, username, password):
    page.goto('https://www.instagram.com/accounts/login/')
    page.wait_for_selector('input[name="username"]')
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    print("  Complete any 2FA or verification in the browser window...")
    # Wait up to 90 seconds so you can handle 2FA/CAPTCHA manually
    try:
        page.wait_for_url(re.compile(r'instagram\.com/(?!accounts/)'), timeout=90000)
    except Exception:
        print("  Login timed out — check the browser window.")
        return
    time.sleep(3)
    dismissPopups(page)
    time.sleep(1)
    dismissPopups(page)

def getFollowees(page, username, max_results=300):
    page.goto(f'https://www.instagram.com/{username}/')
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    if 'accounts/login' in page.url:
        print(f"  Session expired — redirected to login")
        return []

    # Print all hrefs so we can see what Instagram's DOM actually has
    all_hrefs = page.evaluate('''() =>
        Array.from(document.querySelectorAll('a'))
            .map(a => a.getAttribute('href'))
            .filter(Boolean)
    ''')
    following_hrefs = [h for h in all_hrefs if 'following' in h.lower()]
    print(f"  {len(all_hrefs)} links on page, following-related: {following_hrefs}")

    clicked = page.evaluate('''(username) => {
        // Strategy 1: <a> tag with /following in href
        for (const a of document.querySelectorAll('a')) {
            const href = a.getAttribute('href') || '';
            if (href.includes('/following')) {
                a.click();
                return 'a-href';
            }
        }
        // Strategy 2: any button/li/span whose visible text ends with "following"
        for (const el of document.querySelectorAll('button, [role="button"], li, span')) {
            const text = (el.innerText || '').toLowerCase().trim();
            if (text.endsWith('following') && /\\d/.test(text)) {
                el.click();
                return 'text-match:' + el.tagName;
            }
        }
        return null;
    }''', username)

    print(f"  Click strategy used: {clicked}")

    if not clicked:
        return []

    try:
        page.wait_for_selector('div[role="dialog"]', timeout=8000)
    except:
        print(f"  Following dialog did not open after click")
        return []

    time.sleep(1.5)
    dialog = page.locator('div[role="dialog"]')
    found = set()
    stale = 0

    # Get dialog center for mouse wheel scrolling (works with React virtual lists)
    box = dialog.bounding_box()
    scroll_x = box['x'] + box['width'] / 2 if box else 640
    scroll_y = box['y'] + box['height'] / 2 if box else 400

    while len(found) < max_results and stale < 5:
        prev = len(found)
        for link in dialog.locator('a').all():
            href = link.get_attribute('href') or ''
            m = re.match(r'^/([A-Za-z0-9._]+)/?$', href)
            if m and m.group(1) not in {'explore', 'reels', 'stories', 'direct', 'accounts'}:
                found.add(m.group(1))

        stale = stale + 1 if len(found) == prev else 0

        # Mouse wheel scroll — triggers React's virtual list to load more items
        page.mouse.move(scroll_x, scroll_y)
        page.mouse.wheel(0, 1200)
        time.sleep(1.5)

    return list(found)[:max_results]


def checkProfile(page, username):
    """Returns (is_creator, emails) by visiting the profile page."""
    try:
        page.goto(f'https://www.instagram.com/{username}/', timeout=12000)
        page.wait_for_load_state('domcontentloaded')
        time.sleep(1)
        body = page.inner_text('body')
        html = page.content()
        emails = extractEmails(html)
        # A public email in a bio is itself a creator signal — skip the keyword check
        is_creator = bool(emails) or any(s in body.lower() for s in CREATOR_SIGNALS)
        return is_creator, emails
    except:
        return False, []


def discoverCreators(seeds, page, target_emails, max_followees_per_node=300):
    queue = deque(seeds)
    visited = set(seeds)
    found = []
    email_count = 0

    while queue and email_count < target_emails:
        username = queue.popleft()
        print(f"Exploring @{username} | Emails found: {email_count}/{target_emails}")

        followees = getFollowees(page, username, max_results=max_followees_per_node)
        print(f"  {len(followees)} followees, scanning profiles...")

        for uname in followees:
            if uname in visited:
                continue
            visited.add(uname)

            is_creator, emails = checkProfile(page, uname)

            if is_creator:
                found.append({
                    'username': uname,
                    'emails': emails,
                    'profile_url': f'https://www.instagram.com/{uname}/'
                })
                email_count += len(emails)
                # Only expand from creators who have a public email — they're
                # professional creators whose following lists stay niche-relevant
                if emails:
                    queue.append(uname)
                label = ', '.join(emails) if emails else 'no email'
                print(f"  + @{uname} — {label} (total emails: {email_count}/{target_emails})")

            if email_count >= target_emails:
                break

            time.sleep(0.8)

    return found
