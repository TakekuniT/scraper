import re

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE)

def extractEmails(text):
    if not text:
        return []
    return list(set(EMAIL_RE.findall(text)))

def scrapeEmails(creators):
    rows = []
    seen = set()
    for creator in creators:
        for email in creator['emails']:
            key = email.lower()
            if key not in seen:
                seen.add(key)
                rows.append({
                    'username': creator['username'],
                    'email': email,
                    'profile_url': creator['profile_url']
                })
    return rows
