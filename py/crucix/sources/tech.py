"""Tech News Sources - Hacker News, GitHub, AI"""
from __future__ import annotations
import asyncio
from .base import SourceResult, safe_fetch
from ..config import HACKERNEWS_API_KEY, GITHUB_TOKEN


async def hackernews_top() -> SourceResult:
    import time
    start = time.time()
    try:
        data = await safe_fetch("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15.0)
        if isinstance(data, list):
            stories = data[:30]
            tasks = []
            for story_id in stories[:10]:
                tasks.append(safe_fetch(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=10.0))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            articles = []
            for r in results:
                if isinstance(r, dict) and r.get("title"):
                    articles.append({
                        "title": r.get("title"),
                        "url": r.get("url"),
                        "score": r.get("score", 0),
                        "by": r.get("by"),
                        "time": r.get("time"),
                    })
            
            return SourceResult(
                name="HackerNews",
                status="ok",
                duration_ms=(time.time() - start) * 1000,
                data={"articles": articles, "count": len(articles)}
            )
        return SourceResult(name="HackerNews", status="error", duration_ms=(time.time() - start) * 1000, error="Invalid data")
    except Exception as e:
        return SourceResult(name="HackerNews", status="error", duration_ms=(time.time() - start) * 1000, error=str(e))


async def github_trending() -> SourceResult:
    import time
    start = time.time()
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        
        data = await safe_fetch(
            "https://api.github.com/search/repositories",
            params={"q": "created:>2024-01-01", "sort": "stars", "order": "desc", "per_page": 15},
            headers=headers,
            timeout=15.0
        )
        
        if isinstance(data, dict) and data.get("items"):
            repos = []
            for item in data["items"][:15]:
                repos.append({
                    "name": item.get("full_name"),
                    "description": item.get("description"),
                    "stars": item.get("stargazers_count", 0),
                    "language": item.get("language"),
                    "url": item.get("html_url"),
                    "created": item.get("created_at"),
                })
            
            return SourceResult(
                name="GitHub",
                status="ok",
                duration_ms=(time.time() - start) * 1000,
                data={"repos": repos, "count": len(repos)}
            )
        return SourceResult(name="GitHub", status="error", duration_ms=(time.time() - start) * 1000, error="No data")
    except Exception as e:
        return SourceResult(name="GitHub", status="error", duration_ms=(time.time() - start) * 1000, error=str(e))


async def ai_news() -> SourceResult:
    import time
    start = time.time()
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        
        queries = ["llm", "gpt", "AI", "machine-learning", "transformer"]
        results = []
        
        for query in queries[:3]:
            data = await safe_fetch(
                "https://api.github.com/search/repositories",
                params={"q": f"{query} created:>2024-06-01", "sort": "stars", "order": "desc", "per_page": 5},
                headers=headers,
                timeout=12.0
            )
            if isinstance(data, dict) and data.get("items"):
                for item in data["items"][:5]:
                    results.append({
                        "name": item.get("full_name"),
                        "stars": item.get("stargazers_count", 0),
                        "description": item.get("description", "")[:100],
                        "language": item.get("language"),
                    })
        
        results.sort(key=lambda x: x.get("stars", 0), reverse=True)
        results = results[:15]
        
        return SourceResult(
            name="AI-Projects",
            status="ok",
            duration_ms=(time.time() - start) * 1000,
            data={"projects": results, "count": len(results)}
        )
    except Exception as e:
        return SourceResult(name="AI-Projects", status="error", duration_ms=(time.time() - start) * 1000, error=str(e))


async def autonomous_news() -> SourceResult:
    import time
    start = time.time()
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        
        data = await safe_fetch(
            "https://api.github.com/search/repositories",
            params={"q": "autonomous self-driving ROS robotics created:>2024-01-01", "sort": "stars", "order": "desc", "per_page": 10},
            headers=headers,
            timeout=15.0
        )
        
        if isinstance(data, dict) and data.get("items"):
            repos = []
            for item in data["items"][:10]:
                repos.append({
                    "name": item.get("full_name"),
                    "stars": item.get("stargazers_count", 0),
                    "description": item.get("description", "")[:100],
                    "url": item.get("html_url"),
                })
            
            return SourceResult(
                name="Autonomous",
                status="ok",
                duration_ms=(time.time() - start) * 1000,
                data={"projects": repos, "count": len(repos)}
            )
        return SourceResult(name="Autonomous", status="error", duration_ms=(time.time() - start) * 1000, error="No data")
    except Exception as e:
        return SourceResult(name="Autonomous", status="error", duration_ms=(time.time() - start) * 1000, error=str(e))


async def new_energy_news() -> SourceResult:
    import time
    start = time.time()
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        
        data = await safe_fetch(
            "https://api.github.com/search/repositories",
            params={"q": "solar battery electric-vehicle EV renewable-energy created:>2024-01-01", "sort": "stars", "order": "desc", "per_page": 10},
            headers=headers,
            timeout=15.0
        )
        
        if isinstance(data, dict) and data.get("items"):
            repos = []
            for item in data["items"][:10]:
                repos.append({
                    "name": item.get("full_name"),
                    "stars": item.get("stargazers_count", 0),
                    "description": item.get("description", "")[:100],
                    "url": item.get("html_url"),
                })
            
            return SourceResult(
                name="NewEnergy",
                status="ok",
                duration_ms=(time.time() - start) * 1000,
                data={"projects": repos, "count": len(repos)}
            )
        return SourceResult(name="NewEnergy", status="error", duration_ms=(time.time() - start) * 1000, error="No data")
    except Exception as e:
        return SourceResult(name="NewEnergy", status="error", duration_ms=(time.time() - start) * 1000, error=str(e))


async def tech_reddit() -> SourceResult:
    import time
    start = time.time()
    try:
        data = await safe_fetch(
            "https://www.reddit.com/r/technology+artificial+MachineLearning+autonomous+hacking.json",
            headers={"User-Agent": "Crucix/2.0"},
            timeout=15.0
        )
        
        if isinstance(data, dict) and data.get("data"):
            posts = []
            for child in data["data"].get("children", [])[:15]:
                post = child.get("data", {})
                posts.append({
                    "title": post.get("title"),
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "url": post.get("url"),
                    "subreddit": post.get("subreddit"),
                })
            
            return SourceResult(
                name="TechReddit",
                status="ok",
                duration_ms=(time.time() - start) * 1000,
                data={"posts": posts, "count": len(posts)}
            )
        return SourceResult(name="TechReddit", status="error", duration_ms=(time.time() - start) * 1000, error="No data")
    except Exception as e:
        return SourceResult(name="TechReddit", status="error", duration_ms=(time.time() - start) * 1000, error=str(e))


async def briefing() -> dict:
    results = await asyncio.gather(
        hackernews_top(),
        github_trending(),
        ai_news(),
        autonomous_news(),
        new_energy_news(),
        tech_reddit(),
    )
    
    data = {}
    for r in results:
        if r.ok:
            data[r.name] = r.data
    
    return data


briefing = briefing