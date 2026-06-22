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

    while len(found) < max_results and stale < 4:
        prev = len(found)
        for link in dialog.locator('a').all():
            href = link.get_attribute('href') or ''
            m = re.match(r'^/([A-Za-z0-9._]+)/?$', href)
            if m and m.group(1) not in {'explore', 'reels', 'stories', 'direct', 'accounts'}:
                found.add(m.group(1))

        stale = stale + 1 if len(found) == prev else 0

        page.evaluate('''() => {
            const d = document.querySelector('[role="dialog"]');
            if (d) { const s = d.querySelector("ul") || d; s.scrollTop += 800; }
        }''')
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
        is_creator = any(s in body.lower() for s in CREATOR_SIGNALS)
        emails = extractEmails(html)
        return is_creator, emails
    except:
        return False, []


def discoverCreators(seeds, page, target_count, max_followees_per_node=300):
    queue = deque(seeds)
    visited = set(seeds)
    found = []

    while queue and len(found) < target_count:
        username = queue.popleft()
        print(f"Exploring @{username} | Found: {len(found)}/{target_count}")

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
                queue.append(uname)
                label = ', '.join(emails) if emails else 'no email'
                print(f"  + @{uname} ({len(found)}/{target_count}) — {label}")

            if len(found) >= target_count:
                break

            time.sleep(0.8)

    return found
