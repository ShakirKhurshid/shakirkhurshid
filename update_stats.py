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
      nodes { nameWithOwner stargazerCount }
    }
    repositoriesContributedTo(first: 100, privacy: PUBLIC, includeUserRepositories: true,
        contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) {
      nodes { nameWithOwner stargazerCount }
    }
    pullRequests(first: 100, states: MERGED, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes { repository { nameWithOwner stargazerCount isPrivate } }
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

    # Every public repo you own, recently contributed to, or got a PR merged into.
    # Each repo is counted once, even if it shows up in more than one list.
    repos = {}
    for r in user["repositories"]["nodes"] + user["repositoriesContributedTo"]["nodes"]:
        repos[r["nameWithOwner"]] = r["stargazerCount"]
    for pr in user["pullRequests"]["nodes"]:
        r = pr["repository"]
        if not r["isPrivate"]:
            repos[r["nameWithOwner"]] = r["stargazerCount"]

    return {
        "stars": sum(repos.values()),
        # includes private commits only if you turned on "private contributions" in your profile settings
        "commits": contrib["totalCommitContributions"] + contrib["restrictedContributionsCount"],
        "followers": user["followers"]["totalCount"],
    }


def update_card(svg, stats):
    svg = re.sub(r'(class="mono stat">)[^<]*stars[^<]*(</text>)',
                 rf'\g<1>{stats["stars"]} stars contributed to\g<2>', svg)
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
