"""AI Dev Digest Fetchers Package."""

from src.fetchers.blog_fetcher import fetch_blog_posts
from src.fetchers.github_fetcher import fetch_github_releases
from src.fetchers.hackernews_fetcher import fetch_hackernews_stories
from src.fetchers.huggingface_fetcher import fetch_huggingface_papers

__all__ = [
    "fetch_blog_posts",
    "fetch_github_releases",
    "fetch_hackernews_stories",
    "fetch_huggingface_papers",
]
