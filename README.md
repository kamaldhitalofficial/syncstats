# SyncStats

Automatically sync your GitHub stats to your profile README with a simple GitHub Action.

## Features

- Profile overview (followers, repos, gists, contributions)
- 7-day contribution calendar
- Language statistics with visual bars
- Organizations list
- Contribution summary (stars, forks)
- Automatic hourly updates
- **Customizable sections** - Choose what stats to display

## Usage

Add this to your workflow file (e.g., `.github/workflows/update-stats.yml`):

```yaml
name: Update GitHub Stats

on:
  schedule:
    - cron: '0 * * * *'
  workflow_dispatch:

jobs:
  update-stats:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Update stats
        uses: kamaldhitalofficial/syncstats@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Configuration

Create a `config.json` file in your repository root to customize which stats to display:

```json
{
  "profile": {
    "name": true,
    "joined_date": true,
    "followers": true,
    "available_for_hire": true
  },
  "calendar": {
    "enabled": true
  },
  "activity_stats": {
    "commits": true,
    "pr_reviews": true,
    "prs_opened": true,
    "issues_open": true,
    "issue_comments": true
  },
  "community_stats": {
    "organizations": true,
    "following": true,
    "starred": true,
    "watching": true
  },
  "repository_stats": {
    "total_repos": true,
    "license": true,
    "releases": true,
    "packages": true,
    "disk_usage": true
  },
  "metadata": {
    "stargazers": true,
    "forkers": true,
    "watchers": true
  }
}
```

If no `config.json` is provided, all stats will be displayed by default.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github_token` | GitHub token for API access | Yes | - |
| `commit_message` | Commit message for updates | No | `Update GitHub stats` |

## Setup

1. Create the workflow file `.github/workflows/update-stats.yml` as shown above
2. (Optional) Create `config.json` to customize displayed stats
3. The action will automatically create or replace your README.md with generated stats
4. Stats update every hour automatically

## License

MIT
