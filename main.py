import instaloader
import csv
import os
import getpass
from findProfiles import findFollowers, findCreators
from findEmail import scrapeEmails


def load_seeds(niche):
    seed_file = os.path.join('seeds', f'{niche}.txt')
    if not os.path.exists(seed_file):
        raise FileNotFoundError(
            f"No seed file found for niche '{niche}'. Create seeds/{niche}.txt with one Instagram URL or username per line."
        )
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
        fieldnames = ['username', 'full_name', 'followers', 'email', 'profile_url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    return path


def main():
    niche = input("Enter niche (e.g. cs, fitness, fashion): ").strip()
    seeds = load_seeds(niche)
    print(f"Loaded {len(seeds)} seed(s) for niche '{niche}'")

    L = instaloader.Instaloader()
    ig_username = input("Instagram username: ").strip()
    ig_password = getpass.getpass("Instagram password: ")

    try:
        L.login(ig_username, ig_password)
        print("Logged in successfully.\n")
    except instaloader.exceptions.BadCredentialsException:
        print("Login failed: bad credentials.")
        return
    except instaloader.exceptions.TwoFactorAuthRequiredException:
        code = input("2FA code: ").strip()
        L.two_factor_login(code)
        print("Logged in with 2FA.\n")

    all_profiles = []
    seen = set()

    for seed in seeds:
        print(f"Scraping following list of @{seed}...")
        profiles = findFollowers(seed, L)
        print(f"  {len(profiles)} accounts found in following list")

        creators = findCreators(profiles)
        print(f"  {len(creators)} creator candidates after filtering")

        for c in creators:
            if c.username not in seen:
                seen.add(c.username)
                all_profiles.append(c)

    print(f"\nTotal unique creator candidates: {len(all_profiles)}")

    results = scrapeEmails(all_profiles)
    print(f"Gmail addresses found: {len(results)}")

    if results:
        path = save_results(results, niche)
        print(f"Saved to {path}")
    else:
        print("No Gmail addresses found in bios.")


if __name__ == '__main__':
    main()
