#!/usr/bin/env python3
"""
学习素材收集器 (Learning Material Scraper)

用于从多种来源收集AI研究、意识研究、记忆系统等学习素材。
支持：网页、RSS、API等来源，内容提取清洗，去重机制，本地存储。

Usage:
    python scraper.py                    # 使用默认配置运行
    python scraper.py --config config.json  # 使用自定义配置
    python scraper.py --source rss       # 只收集RSS源
    python scraper.py --source web       # 只收集网页
"""

import os
import sys
import json
import hashlib
import logging
import argparse
import re
import time
import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict, field
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse

# Third-party imports with fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    import defusedxml.ElementTree as DefusedET
    HAS_DEFUSEDXML = True
except ImportError:
    HAS_DEFUSEDXML = False

# Named logger for this module (fix #5: avoid basicConfig conflicts)
logger = logging.getLogger(__name__)


# ============================================================
# Configuration
# ============================================================

DEFAULT_CONFIG = {
    "storage_path": os.path.expanduser("~/.hermes/cognition/learning/materials"),
    "log_path": os.path.expanduser("~/.hermes/cognition/learning/logs"),
    "dedup_db_path": os.path.expanduser("~/.hermes/cognition/learning/dedup_db.json"),
    "user_agent": "Hermes-LearningBot/1.0 (AGI Evolution Project)",
    "request_timeout": 30,
    "max_retries": 3,
    "max_content_length": 500000,  # 500KB max per article
    "request_delay": 1.0,  # seconds between requests (fix #8: rate limiting)
    "dedup_flush_interval": 10,  # save dedup DB every N mark_seen calls (fix #4)
    "sources": {
        "rss": [
            {
                "name": "ArXiv AI",
                "url": "http://export.arxiv.org/rss/cs.AI",
                "tags": ["ai-research", "arxiv"],
                "enabled": True
            },
            {
                "name": "Hugging Face Blog",
                "url": "https://huggingface.co/blog/feed.xml",
                "tags": ["ml", "huggingface"],
                "enabled": True
            }
        ],
        "web": [
            {
                "name": "AI Alignment Forum",
                "url": "https://www.alignmentforum.org/feed.xml",
                "tags": ["alignment", "ai-safety"],
                "enabled": True
            },
            {
                "name": "Distill.pub",
                "url": "https://distill.pub/rss.xml",
                "tags": ["ml-research", "distill"],
                "enabled": True
            }
        ],
        "api": [
            {
                "name": "Semantic Scholar AI",
                "url": "https://api.semanticscholar.org/graph/v1/paper/search",
                "params": {
                    "query": "artificial intelligence consciousness memory",
                    "limit": 10,
                    "fields": "title,abstract,url,year"
                },
                "tags": ["ai-research", "consciousness", "memory"],
                "enabled": True
            }
        ]
    }
}


# ============================================================
# Utility: Deep Merge (fix #10)
# ============================================================

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


# ============================================================
# Data Models
# ============================================================

@dataclass
class LearningMaterial:
    """Represents a single piece of learning material."""
    id: str                          # Unique identifier (SHA256 hash)
    title: str                       # Title of the material
    content: str                     # Extracted text content
    url: str                         # Source URL
    source_type: str                 # rss, web, api
    source_name: str                 # Human-readable source name
    tags: List[str] = field(default_factory=list)  # Categorization tags
    author: str = ""                 # Author if available
    summary: str = ""                # Brief summary
    published_date: str = ""         # Publication date
    collected_date: str = ""         # When we collected it
    metadata: Dict[str, Any] = field(default_factory=dict)  # Extra metadata
    content_hash: str = ""           # Hash for deduplication

    def __post_init__(self):
        if not self.collected_date:
            self.collected_date = datetime.now(timezone.utc).isoformat()
        # Fix #6: use full SHA-256 (32 hex chars) instead of truncated [:16]
        # Fix #7: handle empty URL/title to avoid collision
        if not self.content_hash and self.content:
            self.content_hash = hashlib.sha256(
                self.content.encode('utf-8')
            ).hexdigest()
        if not self.id:
            id_source = self.url or f"no-url-{self.collected_date}"
            id_source += "::" + (self.title or f"no-title-{self.content[:100]}")
            self.id = hashlib.sha256(
                id_source.encode('utf-8')
            ).hexdigest()[:32]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================
# Deduplication Database (fix #4: batch save)
# ============================================================

class DeduplicationDB:
    """Simple file-based deduplication database."""

    def __init__(self, db_path: str, flush_interval: int = 10):
        self.db_path = db_path
        self.seen_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()
        self.flush_interval = flush_interval
        self._dirty_count = 0
        self._load()

    def _load(self):
        """Load existing dedup database from file."""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.seen_urls = set(data.get('urls', []))
                    self.seen_hashes = set(data.get('hashes', []))
                logger.info(f"Loaded dedup DB: {len(self.seen_urls)} URLs, {len(self.seen_hashes)} hashes")
        except Exception as e:
            logger.warning(f"Failed to load dedup DB: {e}")

    def _save(self):
        """Save dedup database to file."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'urls': list(self.seen_urls),
                    'hashes': list(self.seen_hashes),
                    'updated': datetime.now(timezone.utc).isoformat()
                }, f, ensure_ascii=False, indent=2)
            self._dirty_count = 0
        except Exception as e:
            logger.error(f"Failed to save dedup DB: {e}")

    def is_duplicate(self, material: LearningMaterial) -> bool:
        """Check if material has been seen before."""
        return material.url in self.seen_urls or material.content_hash in self.seen_hashes

    def mark_seen(self, material: LearningMaterial):
        """Mark material as seen. Saves to disk periodically instead of every call."""
        self.seen_urls.add(material.url)
        self.seen_hashes.add(material.content_hash)
        self._dirty_count += 1
        if self._dirty_count >= self.flush_interval:
            self._save()

    def flush(self):
        """Force save to disk (call at end of collection run)."""
        if self._dirty_count > 0:
            self._save()

    @property
    def total_seen(self) -> int:
        return len(self.seen_urls)


# ============================================================
# Content Extractors
# ============================================================

class ContentExtractor:
    """Extract and clean content from HTML pages."""

    @staticmethod
    def clean_html(html: str) -> str:
        """Remove HTML tags and clean text."""
        if not HAS_BS4:
            # Fallback: basic regex cleaning
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()

        soup = BeautifulSoup(html, 'html.parser')

        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
            tag.decompose()

        # Get text
        text = soup.get_text(separator='\n', strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n'.join(lines)

    @staticmethod
    def extract_article_content(html: str, url: str = "") -> Dict[str, str]:
        """Extract article title, content, and summary from HTML."""
        if not HAS_BS4:
            return {
                'title': '',
                'content': ContentExtractor.clean_html(html),
                'summary': ''
            }

        soup = BeautifulSoup(html, 'html.parser')

        # Extract title
        title = ''
        for selector in ['h1', 'title', '[property="og:title"]', '.title', '.article-title']:
            el = soup.select_one(selector)
            if el:
                title = el.get_text(strip=True)
                break

        # Extract main content
        content = ''
        for selector in ['article', '.article-content', '.post-content', '.entry-content',
                         'main', '.content', '[role="main"]']:
            el = soup.select_one(selector)
            if el:
                content = el.get_text(separator='\n', strip=True)
                break

        if not content:
            content = ContentExtractor.clean_html(str(soup.body) if soup.body else html)

        # Extract summary
        summary = ''
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            summary = meta_desc.get('content', '')
        if not summary:
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc:
                summary = og_desc.get('content', '')
        if not summary and content:
            # Take first paragraph as summary
            paragraphs = [p.strip() for p in content.split('\n') if len(p.strip()) > 50]
            summary = paragraphs[0][:500] if paragraphs else ''

        # Truncate content if too long
        max_len = DEFAULT_CONFIG.get('max_content_length', 500000)
        if len(content) > max_len:
            content = content[:max_len] + '\n...[truncated]'

        return {
            'title': title,
            'content': content,
            'summary': summary
        }


# ============================================================
# Source Scrapers (Abstract + Implementations)
# ============================================================

class BaseScraper(ABC):
    """Base class for all scrapers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.session = None
        self._last_request_time = 0.0
        self._request_delay = config.get('request_delay', 1.0)
        if HAS_REQUESTS:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': config.get('user_agent', DEFAULT_CONFIG['user_agent'])
            })

    def close(self):
        """Close the HTTP session (fix #9: resource cleanup)."""
        if self.session:
            self.session.close()
            self.session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def _rate_limit(self):
        """Enforce minimum delay between requests (fix #8: rate limiting)."""
        if self._request_delay > 0:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self._request_delay:
                time.sleep(self._request_delay - elapsed)
            self._last_request_time = time.monotonic()

    @abstractmethod
    def fetch(self, source: Dict[str, Any]) -> List[LearningMaterial]:
        """Fetch materials from a source."""
        pass

    def _request_with_retry(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Unified retry logic for HTTP requests (fix #3: consistent retry).
        Returns the Response object on success, None on failure.
        """
        if not self.session:
            logger.error("requests library not available")
            return None

        max_retries = self.config.get('max_retries', 3)
        timeout = kwargs.pop('timeout', self.config.get('request_timeout', 30))

        for attempt in range(max_retries):
            self._rate_limit()
            try:
                resp = self.session.request(method, url, timeout=timeout, **kwargs)
                resp.raise_for_status()
                return resp
            except Exception as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {url} - {e}")
                if attempt < max_retries - 1:
                    # Exponential back-off
                    backoff = 2 ** attempt
                    time.sleep(backoff)

        logger.error(f"All {max_retries} retries exhausted for {url}")
        return None

    def _get(self, url: str, params: Optional[Dict] = None, **kwargs) -> Optional[str]:
        """HTTP GET with retries, returning text."""
        resp = self._request_with_retry('GET', url, params=params, **kwargs)
        return resp.text if resp else None

    def _get_json(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """HTTP GET returning JSON."""
        resp = self._request_with_retry('GET', url, params=params)
        if resp is None:
            return None
        try:
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to parse JSON from {url}: {e}")
            return None


class RSSScraper(BaseScraper):
    """Scrape materials from RSS feeds."""

    def fetch(self, source: Dict[str, Any]) -> List[LearningMaterial]:
        url = source['url']
        name = source.get('name', 'Unknown RSS')
        tags = source.get('tags', [])
        materials = []

        logger.info(f"Fetching RSS: {name} ({url})")

        if HAS_FEEDPARSER:
            return self._fetch_with_feedparser(source)

        # Fallback: parse RSS XML manually
        raw = self._get(url)
        if not raw:
            return materials

        return self._parse_rss_xml(raw, source)

    def _fetch_with_feedparser(self, source: Dict[str, Any]) -> List[LearningMaterial]:
        """Use feedparser library for RSS parsing."""
        url = source['url']
        name = source.get('name', 'Unknown RSS')
        tags = source.get('tags', [])
        materials = []

        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                # Extract content
                content = ''
                if hasattr(entry, 'content') and entry.content:
                    content = entry.content[0].get('value', '')
                elif hasattr(entry, 'summary'):
                    content = entry.get('summary', '')
                elif hasattr(entry, 'description'):
                    content = entry.get('description', '')

                # Clean HTML content
                cleaned = ContentExtractor.clean_html(content)

                # Get link
                link = entry.get('link', '')

                mat = LearningMaterial(
                    id='',
                    title=entry.get('title', 'Untitled'),
                    content=cleaned,
                    url=link,
                    source_type='rss',
                    source_name=name,
                    tags=tags,
                    author=entry.get('author', ''),
                    summary=entry.get('summary', '')[:500] if entry.get('summary') else '',
                    published_date=entry.get('published', '')
                )
                materials.append(mat)

        except Exception as e:
            logger.error(f"Feedparser error for {name}: {e}")

        logger.info(f"Collected {len(materials)} items from RSS: {name}")
        return materials

    def _parse_rss_xml(self, xml: str, source: Dict[str, Any]) -> List[LearningMaterial]:
        """Fallback RSS XML parser without feedparser.
        Fix #1: Uses defusedxml to prevent XXE attacks.
        """
        name = source.get('name', 'Unknown RSS')
        tags = source.get('tags', [])
        materials = []

        try:
            # Fix #1: Use defusedxml to prevent XXE / XML injection
            if HAS_DEFUSEDXML:
                root = DefusedET.fromstring(xml)
            else:
                # Fallback: standard library but with external entities disabled
                import xml.etree.ElementTree as ET
                # DefusedXML not available; warn and use stdlib
                logger.warning("defusedxml not installed; using stdlib xml (XXE risk). "
                               "Install with: pip install defusedxml")
                root = ET.fromstring(xml)

            # Handle common RSS/Atom namespaces
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            # RSS 2.0
            for item in root.iter('item'):
                title = item.findtext('title', '')
                link = item.findtext('link', '')
                desc = item.findtext('description', '')
                author = item.findtext('author', '')
                pub_date = item.findtext('pubDate', '')

                cleaned = ContentExtractor.clean_html(desc)

                mat = LearningMaterial(
                    id='',
                    title=title,
                    content=cleaned,
                    url=link,
                    source_type='rss',
                    source_name=name,
                    tags=tags,
                    author=author,
                    summary=cleaned[:500],
                    published_date=pub_date
                )
                materials.append(mat)

            # Atom
            for entry in root.findall('.//atom:entry', ns):
                title = entry.findtext('atom:title', '', ns)
                link_el = entry.find('atom:link', ns)
                link = link_el.get('href', '') if link_el is not None else ''
                content_el = entry.find('atom:content', ns)
                summary_el = entry.find('atom:summary', ns)

                content = ''
                if content_el is not None and content_el.text:
                    content = content_el.text
                elif summary_el is not None and summary_el.text:
                    content = summary_el.text

                cleaned = ContentExtractor.clean_html(content)
                summary = cleaned[:500]

                mat = LearningMaterial(
                    id='',
                    title=title,
                    content=cleaned,
                    url=link,
                    source_type='rss',
                    source_name=name,
                    tags=tags,
                    summary=summary
                )
                materials.append(mat)

        except Exception as e:
            logger.error(f"XML parse error for {name}: {e}")

        logger.info(f"Parsed {len(materials)} items from RSS XML: {name}")
        return materials


class WebScraper(BaseScraper):
    """Scrape materials from web pages."""

    def fetch(self, source: Dict[str, Any]) -> List[LearningMaterial]:
        url = source['url']
        name = source.get('name', 'Unknown Web')
        tags = source.get('tags', [])

        logger.info(f"Fetching Web: {name} ({url})")

        raw = self._get(url)
        if not raw:
            return []

        # Try as RSS/Atom feed first (many blog feeds end in /feed.xml)
        if '<rss' in raw[:500].lower() or '<feed' in raw[:500].lower():
            rss_scraper = RSSScraper(self.config)
            try:
                return rss_scraper._parse_rss_xml(raw, source)
            finally:
                rss_scraper.close()

        # Extract as regular web page
        extracted = ContentExtractor.extract_article_content(raw, url)

        if not extracted['content']:
            logger.warning(f"No content extracted from {name}")
            return []

        mat = LearningMaterial(
            id='',
            title=extracted['title'] or name,
            content=extracted['content'],
            url=url,
            source_type='web',
            source_name=name,
            tags=tags,
            summary=extracted['summary']
        )

        logger.info(f"Collected 1 item from Web: {name}")
        return [mat]


class APIScraper(BaseScraper):
    """Scrape materials from REST APIs."""

    def fetch(self, source: Dict[str, Any]) -> List[LearningMaterial]:
        url = source['url']
        name = source.get('name', 'Unknown API')
        tags = source.get('tags', [])
        params = source.get('params', {})

        logger.info(f"Fetching API: {name} ({url})")

        data = self._get_json(url, params=params)
        if not data:
            return []

        return self._parse_api_response(data, source)

    def _parse_api_response(self, data: Dict, source: Dict[str, Any]) -> List[LearningMaterial]:
        """Parse API response - supports Semantic Scholar format by default."""
        name = source.get('name', 'Unknown API')
        tags = source.get('tags', [])
        materials = []

        # Semantic Scholar format
        papers = data.get('data', data.get('papers', data.get('results', [])))
        if isinstance(papers, list):
            for paper in papers:
                title = paper.get('title', 'Untitled')
                abstract = paper.get('abstract', paper.get('content', ''))
                paper_url = paper.get('url', paper.get('link', ''))
                year = paper.get('year', '')
                authors = ', '.join(
                    a.get('name', '') for a in paper.get('authors', [])
                    if isinstance(a, dict)
                ) if isinstance(paper.get('authors'), list) else ''

                mat = LearningMaterial(
                    id='',
                    title=title,
                    content=abstract or '',
                    url=paper_url,
                    source_type='api',
                    source_name=name,
                    tags=tags,
                    author=authors,
                    summary=abstract[:500] if abstract else '',
                    published_date=str(year) if year else '',
                    metadata={'year': year}
                )
                materials.append(mat)

        logger.info(f"Collected {len(materials)} items from API: {name}")
        return materials


# ============================================================
# Storage Manager
# ============================================================

class StorageManager:
    """Manage storage of learning materials to local filesystem."""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        # Create subdirectories
        for subdir in ['rss', 'web', 'api', 'index']:
            os.makedirs(os.path.join(storage_path, subdir), exist_ok=True)

    def save(self, material: LearningMaterial) -> str:
        """Save a learning material to disk."""
        subdir = material.source_type
        safe_name = self._safe_filename(material.title)[:80]
        filename = f"{material.id}_{safe_name}.json"
        filepath = os.path.join(self.storage_path, subdir, filename)

        # Save material
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(material.to_json())

        # Update index
        self._update_index(material)

        logger.debug(f"Saved: {filepath}")
        return filepath

    def _update_index(self, material: LearningMaterial):
        """Update the material index file."""
        index_path = os.path.join(self.storage_path, 'index', 'materials_index.jsonl')
        index_entry = {
            'id': material.id,
            'title': material.title,
            'url': material.url,
            'source_type': material.source_type,
            'source_name': material.source_name,
            'tags': material.tags,
            'content_hash': material.content_hash,
            'collected_date': material.collected_date,
            'file_path': os.path.join(material.source_type,
                                      f"{material.id}_{self._safe_filename(material.title)[:80]}.json")
        }
        with open(index_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(index_entry, ensure_ascii=False) + '\n')

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Convert string to safe filename."""
        safe = re.sub(r'[^\w\s-]', '', name)
        safe = re.sub(r'[-\s]+', '_', safe)
        return safe.strip('_')


# ============================================================
# Main Scraper Orchestrator
# ============================================================

class LearningScraper:
    """Main orchestrator for learning material collection."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or DEFAULT_CONFIG
        self._setup_logging()

        self.storage = StorageManager(self.config['storage_path'])
        self.dedup = DeduplicationDB(
            self.config['dedup_db_path'],
            flush_interval=self.config.get('dedup_flush_interval', 10),
        )

        # Initialize scrapers
        self.scrapers = {
            'rss': RSSScraper(self.config),
            'web': WebScraper(self.config),
            'api': APIScraper(self.config),
        }

        # Statistics
        self.stats = {
            'fetched': 0,
            'new': 0,
            'duplicates': 0,
            'errors': 0,
            'saved': 0,
        }

    def _setup_logging(self):
        """Configure logging using a named logger (fix #5)."""
        log_path = self.config.get('log_path', DEFAULT_CONFIG['log_path'])
        os.makedirs(log_path, exist_ok=True)

        log_file = os.path.join(log_path, f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

        # Configure the module-level logger (not root) to avoid duplicate handlers
        # on repeated instantiation.
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setFormatter(formatter)
            logger.addHandler(fh)

            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(formatter)
            logger.addHandler(sh)

            # Prevent propagation to root logger to avoid double-logging
            logger.propagate = False

        self.log_file = log_file

    def close(self):
        """Close all scrapers and flush dedup DB (fix #9: resource cleanup)."""
        for scraper in self.scrapers.values():
            scraper.close()
        self.dedup.flush()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def collect(self, source_types: Optional[List[str]] = None) -> List[LearningMaterial]:
        """
        Collect materials from all configured sources.

        Args:
            source_types: Optional list of source types to collect from (rss, web, api).
                         If None, collect from all enabled sources.

        Returns:
            List of newly collected (non-duplicate) materials.
        """
        all_materials = []
        sources = self.config.get('sources', {})

        for source_type in ['rss', 'web', 'api']:
            if source_types and source_type not in source_types:
                continue

            scraper = self.scrapers.get(source_type)
            if not scraper:
                continue

            source_list = sources.get(source_type, [])
            for source in source_list:
                if not source.get('enabled', True):
                    logger.info(f"Skipping disabled source: {source.get('name')}")
                    continue

                try:
                    materials = scraper.fetch(source)
                    self.stats['fetched'] += len(materials)

                    for mat in materials:
                        if self.dedup.is_duplicate(mat):
                            self.stats['duplicates'] += 1
                            logger.debug(f"Duplicate skipped: {mat.title}")
                            continue

                        # Save new material
                        self.storage.save(mat)
                        self.dedup.mark_seen(mat)
                        self.stats['new'] += 1
                        self.stats['saved'] += 1
                        all_materials.append(mat)

                except Exception as e:
                    self.stats['errors'] += 1
                    logger.error(f"Error collecting from {source.get('name')}: {e}")

        # Flush any remaining dedup changes (fix #4)
        self.dedup.flush()

        self._print_summary()
        return all_materials

    def _print_summary(self):
        """Print collection summary."""
        s = self.stats
        logger.info("=" * 60)
        logger.info("Collection Summary:")
        logger.info(f"  Fetched:     {s['fetched']}")
        logger.info(f"  New:         {s['new']}")
        logger.info(f"  Duplicates:  {s['duplicates']}")
        logger.info(f"  Errors:      {s['errors']}")
        logger.info(f"  Saved:       {s['saved']}")
        logger.info(f"  Log file:    {self.log_file}")
        logger.info("=" * 60)

    def search(self, query: str, tags: Optional[List[str]] = None) -> List[Dict]:
        """Search collected materials by query and/or tags."""
        index_path = os.path.join(self.config['storage_path'], 'index', 'materials_index.jsonl')
        results = []

        if not os.path.exists(index_path):
            return results

        query_lower = query.lower() if query else ''

        with open(index_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())

                    # Tag filter
                    if tags and not any(t in entry.get('tags', []) for t in tags):
                        continue

                    # Query filter
                    if query_lower and query_lower not in entry.get('title', '').lower():
                        continue

                    results.append(entry)
                except json.JSONDecodeError:
                    continue

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        index_path = os.path.join(self.config['storage_path'], 'index', 'materials_index.jsonl')
        total_stored = 0
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                total_stored = sum(1 for _ in f)

        return {
            'total_stored': total_stored,
            'total_dedup_seen': self.dedup.total_seen,
            'last_run_stats': self.stats.copy(),
            'storage_path': self.config['storage_path'],
            'log_file': self.log_file,
        }


# ============================================================
# CLI Entry Point
# ============================================================

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file or use defaults.
    Fix #10: proper recursive deep merge instead of shallow update.
    """
    config = copy.deepcopy(DEFAULT_CONFIG)

    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            config = _deep_merge(config, user_config)
            logger.info(f"Loaded config from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")

    return config


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Hermes Learning Material Scraper - Collect AI research materials'
    )
    parser.add_argument('--config', '-c', type=str, help='Path to config JSON file')
    parser.add_argument('--source', '-s', type=str, choices=['rss', 'web', 'api', 'all'],
                        default='all', help='Source type to collect from')
    parser.add_argument('--search', type=str, help='Search collected materials')
    parser.add_argument('--tags', type=str, help='Filter by tags (comma-separated)')
    parser.add_argument('--stats', action='store_true', help='Show collection statistics')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress output')

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Initialize scraper with context manager for cleanup (fix #9)
    with LearningScraper(config) as scraper:

        # Search mode
        if args.search:
            tags = args.tags.split(',') if args.tags else None
            results = scraper.search(args.search, tags)
            print(f"\nFound {len(results)} materials matching '{args.search}':")
            for r in results[:20]:
                print(f"  [{r.get('source_type')}] {r.get('title')}")
                print(f"    URL: {r.get('url')}")
                print(f"    Tags: {', '.join(r.get('tags', []))}")
                print()
            return

        # Stats mode
        if args.stats:
            stats = scraper.get_stats()
            print(json.dumps(stats, indent=2, ensure_ascii=False))
            return

        # Collect mode
        source_types = None if args.source == 'all' else [args.source]
        materials = scraper.collect(source_types)

        # Print collected materials
        if not args.quiet and materials:
            print(f"\n{'='*60}")
            print(f"Collected {len(materials)} new learning materials:")
            print(f"{'='*60}")
            for mat in materials:
                print(f"\n📄 {mat.title}")
                print(f"   Source: {mat.source_name} ({mat.source_type})")
                print(f"   URL: {mat.url}")
                if mat.tags:
                    print(f"   Tags: {', '.join(mat.tags)}")
                if mat.summary:
                    summary = mat.summary[:200] + ('...' if len(mat.summary) > 200 else '')
                    print(f"   Summary: {summary}")
            print(f"\n{'='*60}")
            print(f"Storage: {config['storage_path']}")

        return materials


if __name__ == '__main__':
    main()
