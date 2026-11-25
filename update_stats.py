"""Update the stats in card.svg with live numbers from GitHub.

Run by the GitHub Action in .github/workflows/update-card.yml.
Needs two environment variables: GITHUB_TOKEN and GH_USER.
"""
import json
import os
import re
import urllib.request

USER = os.environ["GH_USER"]
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection { totalCommitContributions restrictedContributionsCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes { stargazerCount }
    }
  }
}
"""


def fetch_stats():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"GitHub API error: {data['errors']}")
    user = data["data"]["user"]
    contrib = user["contributionsCollection"]
    return {
        "stars": sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
        # includes private commits only if you turned on "private contributions" in your profile settings
        "commits": contrib["totalCommitContributions"] + contrib["restrictedContributionsCount"],
        "followers": user["followers"]["totalCount"],
    }


def update_card(svg, stats):
    svg = re.sub(r'(class="mono stat">)[^<]*stars[^<]*(</text>)',
                 rf'\g<1>{stats["stars"]} stars on my repos\g<2>', svg)
    svg = re.sub(r'(class="mono stat">)[^<]*commits[^<]*(</text>)',
                 rf'\g<1>{stats["commits"]} commits in last year\g<2>', svg)
    svg = re.sub(r'(class="mono stat">)[^<]*followers?[^<]*(</text>)',
                 rf'\g<1>{stats["followers"]} followers\g<2>', svg)
    return svg


if __name__ == "__main__":
    stats = fetch_stats()
    with open("card.svg", encoding="utf-8") as f:
        svg = f.read()
    with open("card.svg", "w", encoding="utf-8") as f:
        f.write(update_card(svg, stats))
    print("Updated card.svg:", stats)
