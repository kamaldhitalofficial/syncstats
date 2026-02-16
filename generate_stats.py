import os
import re
import json
import requests
from typing import Dict, List, Any, Tuple
from datetime import datetime, timezone, timedelta
from collections import Counter


class GitHubStatsGenerator:
    def __init__(self, token: str, config_path: str = "config.json"):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = "https://api.github.com"
        self.username = self._get_authenticated_user()
        self.config = self._load_config(config_path)
    
    def _load_config(self, config_path: str) -> Dict:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict:
        return {
            'profile': {'name': True, 'joined_date': True, 'followers': True, 'available_for_hire': True},
            'calendar': {'enabled': True},
            'activity_stats': {'commits': True, 'pr_reviews': True, 'prs_opened': True, 'issues_open': True, 'issue_comments': True},
            'community_stats': {'organizations': True, 'following': True, 'starred': True, 'watching': True},
            'repository_stats': {'total_repos': True, 'license': True, 'releases': True, 'packages': True, 'disk_usage': True},
            'metadata': {'stargazers': True, 'forkers': True, 'watchers': True}
        }
    
    def _get_authenticated_user(self) -> str:
        response = requests.get(f"{self.base_url}/user", headers=self.headers)
        response.raise_for_status()
        return response.json()["login"]
    
    def get_user_profile(self) -> Dict[str, Any]:
        # Fetch user profile
        response = requests.get(f"{self.base_url}/users/{self.username}", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_user_repos(self) -> List[Dict[str, Any]]:
        # Get all repos
        repos = []
        page = 1
        while True:
            response = requests.get(
                f"{self.base_url}/user/repos",
                headers=self.headers,
                params={"per_page": 100, "page": page, "affiliation": "owner"}
            )
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            repos.extend(data)
            page += 1
        return repos
    
    def get_user_events(self, days: int = 7) -> List[Dict[str, Any]]:
        # Get recent events
        events = []
        page = 1
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        while page <= 10:
            response = requests.get(
                f"{self.base_url}/users/{self.username}/events",
                headers=self.headers,
                params={"per_page": 100, "page": page}
            )
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            
            for event in data:
                event_date = datetime.strptime(event["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if event_date < cutoff_date:
                    return events
                events.append(event)
            page += 1
        
        return events
    
    def get_organizations(self) -> List[Dict[str, Any]]:
        # Get orgs
        response = requests.get(f"{self.base_url}/user/orgs", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_starred_count(self) -> int:
        # Count starred repos
        response = requests.get(
            f"{self.base_url}/users/{self.username}/starred",
            headers=self.headers,
            params={"per_page": 1}
        )
        response.raise_for_status()
        link_header = response.headers.get("Link", "")
        if "last" in link_header:
            match = re.search(r'page=(\d+)>; rel="last"', link_header)
            if match:
                return int(match.group(1))
        return len(response.json())
    
    def get_watching_count(self) -> int:
        # Count watched repos
        response = requests.get(
            f"{self.base_url}/users/{self.username}/subscriptions",
            headers=self.headers,
            params={"per_page": 1}
        )
        response.raise_for_status()
        link_header = response.headers.get("Link", "")
        if "last" in link_header:
            match = re.search(r'page=(\d+)>; rel="last"', link_header)
            if match:
                return int(match.group(1))
        return len(response.json())
    
    def get_issues_stats(self) -> Tuple[int, int]:
        # Get issues stats
        issues_response = requests.get(
            f"{self.base_url}/search/issues",
            headers=self.headers,
            params={"q": f"author:{self.username} type:issue is:open", "per_page": 1}
        )
        issues_response.raise_for_status()
        open_issues = issues_response.json().get("total_count", 0)
        
        comments_response = requests.get(
            f"{self.base_url}/search/issues",
            headers=self.headers,
            params={"q": f"commenter:{self.username}", "per_page": 1}
        )
        comments_response.raise_for_status()
        comments = comments_response.json().get("total_count", 0)
        
        return open_issues, comments
    
    def get_contributed_repos(self) -> int:
        # Count contributed repos
        response = requests.get(
            f"{self.base_url}/search/commits",
            headers=self.headers,
            params={"q": f"author:{self.username}", "per_page": 1}
        )
        response.raise_for_status()
        return response.json().get("total_count", 0)
    
    def get_gists_count(self) -> int:
        # Count gists
        response = requests.get(
            f"{self.base_url}/users/{self.username}/gists",
            headers=self.headers,
            params={"per_page": 1}
        )
        response.raise_for_status()
        link_header = response.headers.get("Link", "")
        if "last" in link_header:
            match = re.search(r'page=(\d+)>; rel="last"', link_header)
            if match:
                return int(match.group(1))
        return len(response.json())
    
    def analyze_repos(self, repos: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Analyze repos
        licenses = [r.get("license", {}).get("key") for r in repos if r.get("license")]
        most_common_license = Counter(licenses).most_common(1)[0][0] if licenses else "None"
        
        total_stars = sum(r.get("stargazers_count", 0) for r in repos)
        total_forks = sum(r.get("forks_count", 0) for r in repos)
        total_watchers = sum(r.get("watchers_count", 0) for r in repos)
        total_size = sum(r.get("size", 0) for r in repos)
        
        releases_count = 0
        packages_count = 0
        
        for repo in repos[:10]:
            try:
                rel_response = requests.get(repo["releases_url"].replace("{/id}", ""), headers=self.headers, timeout=2)
                if rel_response.status_code == 200:
                    releases_count += len(rel_response.json())
            except:
                pass
        
        return {
            "license": most_common_license,
            "releases": releases_count,
            "packages": packages_count,
            "disk_usage": total_size,
            "total_stars": total_stars,
            "total_forks": total_forks,
            "total_watchers": total_watchers
        }
    
    def analyze_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Analyze activity
        commits = sum(1 for e in events if e["type"] == "PushEvent")
        prs_opened = sum(1 for e in events if e["type"] == "PullRequestEvent" and e.get("payload", {}).get("action") == "opened")
        pr_reviews = sum(1 for e in events if e["type"] == "PullRequestReviewEvent")
        
        daily_contributions = {}
        for event in events:
            date = event["created_at"][:10]
            daily_contributions[date] = daily_contributions.get(date, 0) + 1
        
        return {
            "commits": commits,
            "prs_opened": prs_opened,
            "pr_reviews": pr_reviews,
            "daily_contributions": daily_contributions
        }
    
    def generate_contribution_calendar(self, daily_contributions: Dict[str, int]) -> str:
        # Build calendar
        today = datetime.now(timezone.utc)
        calendar = "<table><tr>"
        
        for i in range(6, -1, -1):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            count = daily_contributions.get(date, 0)
            
            if count == 0:
                color = "#ebedf0"
            elif count <= 3:
                color = "#9be9a8"
            elif count <= 6:
                color = "#40c463"
            elif count <= 9:
                color = "#30a14e"
            else:
                color = "#216e39"
            
            day_name = (today - timedelta(days=i)).strftime("%a")
            calendar += f"<td align='center' style='padding: 5px;'><div style='background-color: {color}; width: 30px; height: 30px; border-radius: 3px;'></div><small>{day_name}</small></td>"
        
        calendar += "</tr></table>"
        return calendar
    
    def generate_contribution_summary(self, daily_contributions: Dict[str, int]) -> str:
        # Summarize contributions
        total = sum(daily_contributions.values())
        if total == 0:
            return "No contributions in the last 7 days"
        elif total <= 5:
            return f"{total} contributions - Light activity this week"
        elif total <= 15:
            return f"{total} contributions - Moderate activity this week"
        else:
            return f"{total} contributions - High activity this week"
    
    def generate_profile_section(self, profile: Dict[str, Any], stats: Dict[str, Any]) -> str:
        # Build SVG
        name = profile.get("name", self.username)
        hireable = profile.get("hireable", False)
        created_at = datetime.strptime(profile["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%B %d, %Y")
        followers = profile.get("followers", 0)
        following = profile.get("following", 0)
        public_repos = profile.get("public_repos", 0)
        
        # Get config
        cfg = self.config
        profile_cfg = cfg.get('profile', {})
        calendar_cfg = cfg.get('calendar', {})
        activity_cfg = cfg.get('activity_stats', {})
        community_cfg = cfg.get('community_stats', {})
        repos_cfg = cfg.get('repository_stats', {})
        metadata_cfg = cfg.get('metadata', {})
        
        # Generate SVG content
        svg_content = f"""<svg width="900" height="450" xmlns="http://www.w3.org/2000/svg">
  <defs>

    <g id="calendar-icon">
      <rect x="0" y="1.5" width="10.5" height="9" rx="1.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <line x1="2.25" y1="0" x2="2.25" y2="3" stroke="#c9d1d9" stroke-width="1"/>
      <line x1="8.25" y1="0" x2="8.25" y2="3" stroke="#c9d1d9" stroke-width="1"/>
      <line x1="0" y1="4.5" x2="10.5" y2="4.5" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="users-icon">
      <circle cx="3.75" cy="3" r="2.25" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <path d="M0,10.5 Q0,7.5 3.75,7.5 Q7.5,7.5 7.5,10.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <circle cx="8.25" cy="3.75" r="1.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <path d="M7.5,10.5 Q7.5,8.25 9.75,8.25 Q12,8.25 12,10.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="briefcase-icon">
      <rect x="0.75" y="3.75" width="10.5" height="6.75" rx="1.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <path d="M3.75,3.75 L3.75,2.25 Q3.75,1.5 4.5,1.5 L7.5,1.5 Q8.25,1.5 8.25,2.25 L8.25,3.75" fill="none" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="activity-icon">
      <polyline points="0,6 3,6 4.5,1.5 7.5,10.5 9,6 12,6" fill="none" stroke="#c9d1d9" stroke-width="1.5"/>
    </g>
    <g id="zap-icon">
      <polygon points="6,0 1.5,6.75 6,6.75 4.5,12 10.5,5.25 6,5.25" fill="none" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="building-icon">
      <rect x="1.5" y="1.5" width="9" height="9" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <rect x="3.75" y="3.75" width="1.5" height="1.5" fill="#c9d1d9"/>
      <rect x="6.75" y="3.75" width="1.5" height="1.5" fill="#c9d1d9"/>
      <rect x="3.75" y="6.75" width="1.5" height="1.5" fill="#c9d1d9"/>
      <rect x="6.75" y="6.75" width="1.5" height="1.5" fill="#c9d1d9"/>
    </g>
    <g id="folder-icon">
      <path d="M1.5,2.25 L4.5,2.25 L6,3.75 L10.5,3.75 L10.5,9.75 L1.5,9.75 Z" fill="none" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="star-icon">
      <polygon points="6,0.75 7.5,4.5 11.25,4.5 8.25,6.75 9.75,10.5 6,8.25 2.25,10.5 3.75,6.75 0.75,4.5 4.5,4.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="git-commit-icon">
      <circle cx="6" cy="6" r="2.25" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <line x1="0" y1="6" x2="3.75" y2="6" stroke="#c9d1d9" stroke-width="1"/>
      <line x1="8.25" y1="6" x2="12" y2="6" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="eye-icon">
      <ellipse cx="6" cy="6" rx="5.25" ry="3" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <circle cx="6" cy="6" r="1.5" fill="#c9d1d9"/>
    </g>
    <g id="git-pr-icon">
      <circle cx="2.25" cy="2.25" r="1.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <circle cx="2.25" cy="9.75" r="1.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <circle cx="9.75" cy="6" r="1.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <line x1="2.25" y1="3.75" x2="2.25" y2="8.25" stroke="#c9d1d9" stroke-width="1"/>
      <path d="M8.25,6 L6,6 L6,2.25 L2.25,2.25" fill="none" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="alert-icon">
      <circle cx="6" cy="6" r="5.25" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <line x1="6" y1="3" x2="6" y2="6.75" stroke="#c9d1d9" stroke-width="1"/>
      <circle cx="6" cy="9" r="0.375" fill="#c9d1d9"/>
    </g>
    <g id="message-icon">
      <rect x="0.75" y="2.25" width="10.5" height="7.5" rx="1.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <polyline points="0.75,2.25 6,6 11.25,2.25" fill="none" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="user-plus-icon">
      <circle cx="4.5" cy="3.75" r="2.25" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <path d="M0,10.5 Q0,7.5 4.5,7.5 Q9,7.5 9,10.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <line x1="9.75" y1="3.75" x2="12" y2="3.75" stroke="#c9d1d9" stroke-width="1"/>
      <line x1="10.875" y1="2.625" x2="10.875" y2="4.875" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="star-outline-icon">
      <polygon points="6,0.75 7.5,4.5 11.25,4.5 8.25,6.75 9.75,10.5 6,8.25 2.25,10.5 3.75,6.75 0.75,4.5 4.5,4.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="scale-icon">
      <line x1="6" y1="1.5" x2="6" y2="10.5" stroke="#c9d1d9" stroke-width="1"/>
      <path d="M1.5,4.5 L6,1.5 L10.5,4.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <path d="M1.5,4.5 L1.5,6 L4.5,6 L4.5,4.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <path d="M7.5,4.5 L7.5,6 L10.5,6 L10.5,4.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="rocket-icon">
      <path d="M6,1.5 Q9,1.5 10.5,4.5 L10.5,7.5 L9,9 L7.5,7.5 L4.5,7.5 L3,9 L1.5,7.5 L1.5,4.5 Q3,1.5 6,1.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <circle cx="6.75" cy="4.5" r="0.75" fill="#c9d1d9"/>
      <path d="M4.5,7.5 L3,10.5 L4.5,9" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <path d="M7.5,7.5 L9,10.5 L7.5,9" fill="none" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="package-icon">
      <path d="M1.5,3 L6,0.75 L10.5,3 L10.5,9 L6,11.25 L1.5,9 Z" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <polyline points="1.5,3 6,5.25 10.5,3" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <line x1="6" y1="5.25" x2="6" y2="11.25" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="database-icon">
      <ellipse cx="6" cy="2.25" rx="4.5" ry="1.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <path d="M1.5,2.25 L1.5,9.75 Q1.5,11.25 6,11.25 Q10.5,11.25 10.5,9.75 L10.5,2.25" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <ellipse cx="6" cy="6" rx="4.5" ry="1.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
    </g>
    <g id="fork-icon">
      <circle cx="6" cy="1.5" r="1.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <circle cx="2.25" cy="10.5" r="1.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <circle cx="9.75" cy="10.5" r="1.5" fill="none" stroke="#c9d1d9" stroke-width="1"/>
      <path d="M6,3 L6,6 M3.75,6 Q3.75,7.5 2.25,9 M8.25,6 Q8.25,7.5 9.75,9" fill="none" stroke="#c9d1d9" stroke-width="1"/>
    </g>
  </defs>
  
  <rect width="900" height="450" fill="#0d1117"/>
  
"""
        
        # Profile name
        if profile_cfg.get('name', True):
            svg_content += f"""
  <text x="20" y="40" font-family="Arial" font-size="24" font-weight="bold" fill="#c9d1d9">{name}</text>"""
        
        # Profile details
        y_pos = 58
        if profile_cfg.get('joined_date', True):
            svg_content += f"""
  
  <use href="#calendar-icon" x="20" y="{y_pos}"/>
  <text x="42" y="{y_pos + 12}" font-family="Arial" font-size="14" fill="#c9d1d9">Joined: {created_at}</text>"""
            y_pos += 25
        
        if profile_cfg.get('followers', True):
            svg_content += f"""
  
  <use href="#users-icon" x="20" y="{y_pos}"/>
  <text x="42" y="{y_pos + 12}" font-family="Arial" font-size="14" fill="#c9d1d9">Followers: {followers}</text>"""
            y_pos += 25
        
        if profile_cfg.get('available_for_hire', True):
            svg_content += f"""
  
  <use href="#briefcase-icon" x="20" y="{y_pos}"/>
  <text x="42" y="{y_pos + 12}" font-family="Arial" font-size="14" fill="#c9d1d9">Available for hire: {"Yes" if hireable else "No"}</text>"""
        
        # Calendar section
        if calendar_cfg.get('enabled', True):
            svg_content += """
  

  <text x="550" y="40" font-family="Arial" font-size="18" font-weight="bold" fill="#c9d1d9">Last 7 Days</text>
"""
        
        # Add contribution calendar
        if calendar_cfg.get('enabled', True):
            today = datetime.now(timezone.utc)
            x_start = 550
            y_start = 60
            
            for i in range(6, -1, -1):
                date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                day_name = (today - timedelta(days=i)).strftime("%a")
                count = stats.get('daily_contributions', {}).get(date, 0)
                
                if count == 0:
                    color = "#ebedf0"
                elif count <= 3:
                    color = "#9be9a8"
                elif count <= 6:
                    color = "#40c463"
                elif count <= 9:
                    color = "#30a14e"
                else:
                    color = "#216e39"
                
                x_pos = x_start + (6 - i) * 45
                svg_content += f'  <rect x="{x_pos}" y="{y_start}" width="35" height="35" fill="{color}" rx="3"/>\n'
                svg_content += f'  <text x="{x_pos + 17}" y="{y_start + 55}" font-family="Arial" font-size="10" fill="#8b949e" text-anchor="middle">{day_name}</text>\n'
        
        svg_content += f"""
  <text x="700" y="130" font-family="Arial" font-size="12" fill="#8b949e" text-anchor="middle">{stats['summary']}</text>
  
"""
        
        # Check if any activity stats are enabled
        has_activity = any([
            activity_cfg.get('commits', True),
            activity_cfg.get('pr_reviews', True),
            activity_cfg.get('prs_opened', True),
            activity_cfg.get('issues_open', True),
            activity_cfg.get('issue_comments', True)
        ])
        
        # Check if any community stats are enabled
        has_community = any([
            community_cfg.get('organizations', True),
            community_cfg.get('following', True),
            community_cfg.get('starred', True),
            community_cfg.get('watching', True)
        ])
        
        # Check if any repository stats are enabled
        has_repos = any([
            repos_cfg.get('total_repos', True),
            repos_cfg.get('license', True),
            repos_cfg.get('releases', True),
            repos_cfg.get('packages', True),
            repos_cfg.get('disk_usage', True)
        ])
        
        # Check if any metadata stats are enabled
        has_metadata = any([
            metadata_cfg.get('stargazers', True),
            metadata_cfg.get('forkers', True),
            metadata_cfg.get('watchers', True)
        ])
        
        # Add headers only if section has enabled stats
        if has_activity:
            svg_content += """
  <text x="20" y="190" font-family="Arial" font-size="16" font-weight="bold" fill="#c9d1d9">Activity Stats</text>"""
        
        if has_community:
            svg_content += """
  
  <text x="240" y="190" font-family="Arial" font-size="16" font-weight="bold" fill="#c9d1d9">Community Stats</text>"""
        
        if has_repos:
            svg_content += """
  
  <text x="460" y="190" font-family="Arial" font-size="16" font-weight="bold" fill="#c9d1d9">Repository Stats</text>"""
        
        if has_metadata:
            svg_content += """
  
  <text x="680" y="190" font-family="Arial" font-size="16" font-weight="bold" fill="#c9d1d9">Metadata</text>"""
        
        svg_content += """
  
"""
        
        # Activity stats
        y_pos = 210
        if activity_cfg.get('commits', True):
            svg_content += f"""
  <use href="#git-commit-icon" x="20" y="{y_pos}"/>
  <text x="38" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Commits (7d): {stats['activity']['commits']}</text>"""
            y_pos += 25
        
        if activity_cfg.get('pr_reviews', True):
            svg_content += f"""
  
  <use href="#eye-icon" x="20" y="{y_pos}"/>
  <text x="38" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">PR Reviews: {stats['activity']['pr_reviews']}</text>"""
            y_pos += 25
        
        if activity_cfg.get('prs_opened', True):
            svg_content += f"""
  
  <use href="#git-pr-icon" x="20" y="{y_pos}"/>
  <text x="38" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">PRs Opened: {stats['activity']['prs_opened']}</text>"""
            y_pos += 25
        
        if activity_cfg.get('issues_open', True):
            svg_content += f"""
  
  <use href="#alert-icon" x="20" y="{y_pos}"/>
  <text x="38" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Issues Open: {stats['issues']['open']}</text>"""
            y_pos += 25
        
        if activity_cfg.get('issue_comments', True):
            svg_content += f"""
  
  <use href="#message-icon" x="20" y="{y_pos}"/>
  <text x="38" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Issue Comments: {stats['issues']['comments']}</text>"""
        
        svg_content += """
  
"""
        
        # Community stats
        y_pos = 210
        if community_cfg.get('organizations', True):
            svg_content += f"""
  <use href="#building-icon" x="240" y="{y_pos}"/>
  <text x="258" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Organizations: {stats['community']['orgs']}</text>"""
            y_pos += 25
        
        if community_cfg.get('following', True):
            svg_content += f"""
  
  <use href="#user-plus-icon" x="240" y="{y_pos}"/>
  <text x="258" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Following: {following}</text>"""
            y_pos += 25
        
        if community_cfg.get('starred', True):
            svg_content += f"""
  
  <use href="#star-outline-icon" x="240" y="{y_pos}"/>
  <text x="258" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Starred: {stats['community']['starred']}</text>"""
            y_pos += 25
        
        if community_cfg.get('watching', True):
            svg_content += f"""
  
  <use href="#eye-icon" x="240" y="{y_pos}"/>
  <text x="258" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Watching: {stats['community']['watching']}</text>"""
        
        svg_content += """
  
"""
        
        # Repository stats
        y_pos = 210
        if repos_cfg.get('total_repos', True):
            svg_content += f"""
  <use href="#folder-icon" x="460" y="{y_pos}"/>
  <text x="478" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Total Repos: {public_repos}</text>"""
            y_pos += 25
        
        if repos_cfg.get('license', True):
            svg_content += f"""
  
  <use href="#scale-icon" x="460" y="{y_pos}"/>
  <text x="478" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">License: {stats['repos']['license']}</text>"""
            y_pos += 25
        
        if repos_cfg.get('releases', True):
            svg_content += f"""
  
  <use href="#rocket-icon" x="460" y="{y_pos}"/>
  <text x="478" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Releases: {stats['repos']['releases']}</text>"""
            y_pos += 25
        
        if repos_cfg.get('packages', True):
            svg_content += f"""
  
  <use href="#package-icon" x="460" y="{y_pos}"/>
  <text x="478" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Packages: {stats['repos']['packages']}</text>"""
            y_pos += 25
        
        if repos_cfg.get('disk_usage', True):
            svg_content += f"""
  
  <use href="#database-icon" x="460" y="{y_pos}"/>
  <text x="478" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Disk: {stats['repos']['disk_usage'] / 1024:.2f} MB</text>"""
        
        svg_content += """
  
"""
        
        # Metadata
        y_pos = 210
        if metadata_cfg.get('stargazers', True):
            svg_content += f"""
  <use href="#star-icon" x="680" y="{y_pos}"/>
  <text x="698" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Stargazers: {stats['repos']['total_stars']}</text>"""
            y_pos += 25
        
        if metadata_cfg.get('forkers', True):
            svg_content += f"""
  
  <use href="#fork-icon" x="680" y="{y_pos}"/>
  <text x="698" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Forkers: {stats['repos']['total_forks']}</text>"""
            y_pos += 25
        
        if metadata_cfg.get('watchers', True):
            svg_content += f"""
  
  <use href="#eye-icon" x="680" y="{y_pos}"/>
  <text x="698" y="{y_pos + 10}" font-family="Arial" font-size="13" fill="#c9d1d9">Watchers: {stats['repos']['total_watchers']}</text>"""
        
        svg_content += """
</svg>"""
        
        return svg_content
        """Generate comprehensive profile section"""
        name = profile.get("name", self.username)
        hireable = profile.get("hireable", False)
        created_at = datetime.strptime(profile["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%B %d, %Y")
        followers = profile.get("followers", 0)
        following = profile.get("following", 0)
        public_repos = profile.get("public_repos", 0)
        
        section = f"""<table width="100%" cellspacing="0" cellpadding="0" style="border: 0; border-collapse: collapse; background-color: #0d1117;">
<tr>
<td valign="top" width="60%" style="border: 0; padding: 20px; color: #c9d1d9;">

### <span style="color: #58a6ff;">{name}</span>

<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/calendar.svg" width="16" height="16" style="filter: invert(1);" /> **Joined:** {created_at}  
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/users.svg" width="16" height="16" style="filter: invert(1);" /> **Followers:** {followers}  
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/briefcase.svg" width="16" height="16" style="filter: invert(1);" /> **Available for hire:** {"Yes" if hireable else "No"}

</td>
<td valign="top" width="360" style="border: 0; padding: 20px; color: #c9d1d9;">

### <img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/activity.svg" width="20" height="20" style="filter: invert(1);" /> Last 7 Days

{stats['calendar']}

<p align="center"><em>{stats['summary']}</em></p>

</td>
</tr>
</table>

<table width="100%" cellspacing="0" cellpadding="0" style="border: 0; border-collapse: collapse; background-color: #0d1117;">
<tr>
<th width="25%" style="border: 0; padding: 15px; color: #58a6ff; text-align: left;"><img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/zap.svg" width="16" height="16" style="filter: invert(1);" /> Activity Stats</th>
<th width="25%" style="border: 0; padding: 15px; color: #58a6ff; text-align: left;"><img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/users.svg" width="16" height="16" style="filter: invert(1);" /> Community Stats</th>
<th width="25%" style="border: 0; padding: 15px; color: #58a6ff; text-align: left;"><img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/folder.svg" width="16" height="16" style="filter: invert(1);" /> Repository Stats</th>
<th width="25%" style="border: 0; padding: 15px; color: #58a6ff; text-align: left;"><img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/award.svg" width="16" height="16" style="filter: invert(1);" /> Metadata</th>
</tr>
<tr>
<td valign="top" style="border: 0; padding: 15px; color: #c9d1d9;">

<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/git-commit.svg" width="14" height="14" style="filter: invert(1);" /> **Commits (7d):** {stats['activity']['commits']}<br>
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/eye.svg" width="14" height="14" style="filter: invert(1);" /> **PR Reviews:** {stats['activity']['pr_reviews']}<br>
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/git-pull-request.svg" width="14" height="14" style="filter: invert(1);" /> **PRs Opened:** {stats['activity']['prs_opened']}<br>
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/alert-circle.svg" width="14" height="14" style="filter: invert(1);" /> **Issues Open:** {stats['issues']['open']}<br>
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/message-circle.svg" width="14" height="14" style="filter: invert(1);" /> **Issue Comments:** {stats['issues']['comments']}

</td>
<td valign="top" style="border: 0; padding: 15px; color: #c9d1d9;">

<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/building.svg" width="14" height="14" style="filter: invert(1);" /> **Organizations:** {stats['community']['orgs']}<br>
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/user-plus.svg" width="14" height="14" style="filter: invert(1);" /> **Following:** {following}<br>
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/star.svg" width="14" height="14" style="filter: invert(1);" /> **Starred:** {stats['community']['starred']}<br>
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/eye.svg" width="14" height="14" style="filter: invert(1);" /> **Watching:** {stats['community']['watching']}

</td>
<td valign="top" style="border: 0; padding: 15px; color: #c9d1d9;">

<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/folder-git.svg" width="14" height="14" style="filter: invert(1);" /> **Total Repos:** {public_repos}<br>
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/scale.svg" width="14" height="14" style="filter: invert(1);" /> **License:** {stats['repos']['license']}<br>
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/rocket.svg" width="14" height="14" style="filter: invert(1);" /> **Releases:** {stats['repos']['releases']}<br>
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/package.svg" width="14" height="14" style="filter: invert(1);" /> **Packages:** {stats['repos']['packages']}<br>
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/hard-drive.svg" width="14" height="14" style="filter: invert(1);" /> **Disk:** {stats['repos']['disk_usage'] / 1024:.2f} MB

</td>
<td valign="top" style="border: 0; padding: 15px; color: #c9d1d9;">

<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/star.svg" width="14" height="14" style="filter: invert(1);" /> **Stargazers:** {stats['repos']['total_stars']}<br>
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/git-fork.svg" width="14" height="14" style="filter: invert(1);" /> **Forkers:** {stats['repos']['total_forks']}<br>
<img src="https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/eye.svg" width="14" height="14" style="filter: invert(1);" /> **Watchers:** {stats['repos']['total_watchers']}

</td>
</tr>
</table>
"""
        return section
    
    def generate_stats(self, sections: List[str]) -> str:
        # Generate stats
        print(f"Fetching stats for {self.username}...")
        
        profile = self.get_user_profile()
        repos = self.get_user_repos()
        events = self.get_user_events(7)
        orgs = self.get_organizations()
        
        print("Analyzing repositories...")
        repo_stats = self.analyze_repos(repos)
        
        print("Analyzing activity...")
        activity_stats = self.analyze_events(events)
        
        print("Fetching community stats...")
        starred = self.get_starred_count()
        watching = self.get_watching_count()
        open_issues, issue_comments = self.get_issues_stats()
        
        stats = {
            'activity': {
                'commits': activity_stats['commits'],
                'pr_reviews': activity_stats['pr_reviews'],
                'prs_opened': activity_stats['prs_opened']
            },
            'issues': {
                'open': open_issues,
                'comments': issue_comments
            },
            'community': {
                'orgs': len(orgs),
                'starred': starred,
                'watching': watching
            },
            'repos': repo_stats,
            'daily_contributions': activity_stats['daily_contributions'],
            'summary': self.generate_contribution_summary(activity_stats['daily_contributions'])
        }
        
        svg_content = self.generate_profile_section(profile, stats)
        
        return svg_content
    
    def update_readme(self, readme_path: str, svg_content: str):
        """Update README and SVG files"""
        svg_path = "github-stats.svg"
        
        # Check if SVG content changed
        svg_changed = True
        if os.path.exists(svg_path):
            with open(svg_path, "r") as f:
                old_svg = f.read()
            if old_svg == svg_content:
                svg_changed = False
                print("SVG unchanged, skipping update")
        
        if svg_changed:
            # Write SVG file
            with open(svg_path, "w") as f:
                f.write(svg_content)
            print(f"Updated {svg_path}")
        
        # Create or check README
        readme_content = f'<img src="https://raw.githubusercontent.com/{self.username}/{self.username}/main/github-stats.svg" alt="GitHub Stats" />\n'
        
        readme_changed = True
        if os.path.exists(readme_path):
            with open(readme_path, "r") as f:
                old_readme = f.read()
            if old_readme == readme_content:
                readme_changed = False
                print("README unchanged")
        
        if readme_changed or not os.path.exists(readme_path):
            with open(readme_path, "w") as f:
                f.write(readme_content)
            print(f"Updated {readme_path}")


def main():
    token = os.environ.get("GITHUB_TOKEN")
    readme_path = "README.md"
    sections = os.environ.get("SECTIONS", "profile").split(",")
    
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    
    generator = GitHubStatsGenerator(token)
    svg_content = generator.generate_stats(sections)
    generator.update_readme(readme_path, svg_content)


if __name__ == "__main__":
    main()
