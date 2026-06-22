import re

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE)

def extractEmails(bio):
    if not bio:
        return []
    return EMAIL_RE.findall(bio)


def scrapeEmails(profiles):
    results = []
    for profile in profiles:
        emails = extractEmails(profile.biography or "")
        for email in emails:
            results.append({
                'username': profile.username,
                'full_name': profile.full_name,
                'followers': profile.followers,
                'email': email,
                'profile_url': f'https://www.instagram.com/{profile.username}/'
            })
    return results
