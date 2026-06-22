import re

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE)

def extractEmails(text):
    if not text:
        return []
    return list(set(EMAIL_RE.findall(text)))

def scrapeEmails(creators):
    rows = []
    for creator in creators:
        if creator['emails']:
            for email in creator['emails']:
                rows.append({
                    'username': creator['username'],
                    'email': email,
                    'profile_url': creator['profile_url']
                })
    return rows
