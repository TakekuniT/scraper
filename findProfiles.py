import instaloader
import time

CREATOR_SIGNALS = [
    "creator", "content creator", "youtuber", "youtube", "tiktok",
    "video", "collab", "influencer", "ugc", "podcast", "streamer",
    "link in bio", "new video", "filmmaker", "educator"
]

def findFollowers(username, L, max_results=500):
    # We scrape who the seed follows (followees), not their followers.
    # Creators tend to follow others in their niche, making this a reliable discovery signal.
    try:
        profile = instaloader.Profile.from_username(L.context, username)
    except instaloader.exceptions.ProfileNotExistsException:
        print(f"  Profile @{username} not found, skipping.")
        return []

    results = []
    try:
        for followee in profile.get_followees():
            results.append(followee)
            if len(results) >= max_results:
                break
            time.sleep(0.3)
    except instaloader.exceptions.LoginRequiredException:
        print("  Login required to fetch followees. Make sure you're logged in.")
    except Exception as e:
        print(f"  Error fetching followees for @{username}: {e}")

    return results


def findCreators(profiles):
    creators = []
    for profile in profiles:
        bio = (profile.biography or "").lower()
        has_signal = any(signal in bio for signal in CREATOR_SIGNALS)
        has_link = bool(profile.external_url)
        has_posts = profile.mediacount > 5

        if (has_signal or has_link) and has_posts:
            creators.append(profile)

    return creators
