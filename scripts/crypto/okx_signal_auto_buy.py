#!/usr/bin/env python3
"""
OKX Signal -> Solana/Jupiter auto trader.

默认安全模式：不会实盘下单。
只有同时满足：
  1) .env 中 OKX_SIGNAL_LIVE_TRADING=true
  2) 启动参数带 --live
才会签名并广播交易。

策略规则按用户指定：
  - OKX Signal 新 token：买入固定 0.3 SOL
  - 钱包里已有该 token：跳过，不重复买
  - 买入后价格达到 2x：卖出当前持仓的 50%
  - 不做其它 discretionary 策略过滤
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import queue
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import base58
import requests
import websocket
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned

ENV_PATH = Path(os.getenv("OKX_SIGNAL_ENV", "/root/.hermes/.env"))
STATE_PATH = Path(os.getenv("OKX_SIGNAL_STATE", "/root/.hermes/cache/okx-signal-auto-buy/state.json"))
LOG_PATH = Path(os.getenv("OKX_SIGNAL_LOG", "/root/.hermes/cache/okx-signal-auto-buy/events.log"))

SOL_MINT = "So11111111111111111111111111111111111111112"
OKX_SIGNAL_URL = (
    "https://web3.okx.com/priapi/v1/dx/market/v2/smartmoney/signal/gems-list"
    # sortBy=1&isAsc=false = 按 firstSignalTime 倒序，最新信号排最前。
    # 之前误用 sortBy=4（疑似涨幅/榜单维度），会导致“刚进入榜单但 firstSignalTime 很旧”的 token 被当成新信号。
    "?sortBy=1&isAsc=false&signalLabels=1%2C2%2C3&chainId=501"
)
JUP_QUOTE_URL = "https://lite-api.jup.ag/swap/v1/quote"
JUP_SWAP_URL = "https://lite-api.jup.ag/swap/v1/swap"
DEFAULT_RPC = "https://api.mainnet-beta.solana.com"
OKX_WS_URL = "wss://wsdexpri.okx.com:443/ws/v5/iprivate/dex"
OKX_WS_CHANNEL = "dex-market-sm-signal-status"
SPL_TOKEN_PROGRAM="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM="TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"


@dataclass
class Config:
    live_env: bool
    buy_sol: Decimal
    poll_seconds: int
    slippage_bps: int
    tp_multiple: Decimal
    sell_fraction: Decimal
    rpc_url: str
    max_open_positions: int
    min_sol_reserve: Decimal
    dry_run_quote: bool
    tp_check_seconds: int
    tp_top_n: int
    tp_429_cooldown_seconds: int
    max_signal_age_seconds: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_dirs() -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log(msg: str, *, also_print: bool = True) -> None:
    ensure_dirs()
    line = f"{utc_now()} {msg}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    if also_print:
        print(line, flush=True)


def tg_escape(text: Any) -> str:
    """Escape Telegram HTML text."""
    s = str(text)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def notify_telegram(text: str) -> None:
    """Push a Telegram message directly via bot token if configured.

    Uses OKX_SIGNAL_BOT_TOKEN (or falls back to TELEGRAM_BOT_TOKEN) and OKX_SIGNAL_TELEGRAM_CHAT_ID.
    If chat id is not set, falls back to the first TELEGRAM_ALLOWED_USERS entry.
    """
    token = os.getenv("OKX_SIGNAL_BOT_TOKEN", "").strip() or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("OKX_SIGNAL_TELEGRAM_CHAT_ID", "").strip()
    if not chat_id:
        allowed = os.getenv("TELEGRAM_ALLOWED_USERS", "").strip()
        if allowed:
            chat_id = allowed.split(",")[0].strip()
    if not token or not chat_id:
        log("[TG-SKIP] TELEGRAM_BOT_TOKEN or chat_id missing", also_print=True)
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=15,
        )
        if r.status_code != 200:
            log(f"[TG-ERR] HTTP {r.status_code}: {r.text[:300]}")
    except Exception as e:
        log(f"[TG-ERR] {type(e).__name__}: {e}")


# === Manual confirmation mode ===

PENDING_CONFIRMS: Dict[str, Dict[str, Any]] = {}
PENDING_LOCK = threading.Lock()
_SOL_ADDRS = {"So11111111111111111111111111111111111111112", "So11111111111111111111111111111111111111111"}


def _check_twitter_profile(handle: str) -> Dict[str, Any]:
    """Check Twitter profile for follower count and activity."""
    result: Dict[str, Any] = {"handle": handle, "followers": 0, "tweets": 0, "verified": False, "exists": False}
    try:
        r = requests.get(
            f"https://x.com/{handle}",
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            timeout=8, allow_redirects=True,
        )
        if r.status_code == 200:
            text = r.text
            import re
            fc = re.search(r'"followers_count":(\d+)', text)
            sc = re.search(r'"statuses_count":(\d+)', text)
            ver = re.search(r'"verified":(true)', text)
            if fc:
                result["followers"] = int(fc.group(1))
                result["exists"] = True
            if sc:
                result["tweets"] = int(sc.group(1))
            if ver:
                result["verified"] = True
    except Exception as e:
        log(f"[TWITTER-WARN] {handle}: {type(e).__name__}")
    return result


def _check_telegram_group(handle: str) -> Dict[str, Any]:
    """Check if a Telegram group/channel exists and get member count."""
    result: Dict[str, Any] = {"handle": handle, "members": 0, "exists": False}
    try:
        r = requests.get(
            f"https://t.me/{handle}",
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
            timeout=8,
        )
        if r.status_code == 200 and 'tgme_page_title' in r.text:
            result["exists"] = True
            import re
            # Match "74 416 members" or "1,234 members" or "12345 members"
            mc = re.search(r'([\d][\d\s,]*)\s+members?', r.text)
            if mc:
                result["members"] = int(mc.group(1).replace(",", "").replace(" ", ""))
    except Exception:
        pass
    return result


def _search_token_buzz(symbol: str, name: str) -> Dict[str, Any]:
    """Search for token buzz using DuckDuckGo instant answer."""
    result: Dict[str, Any] = {"mentions": 0, "related": []}
    try:
        q = f"{symbol} solana meme coin"
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": q, "format": "json", "no_redirect": "1"},
            headers={"User-Agent": "okx-signal/1.0"},
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            # Check related topics
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and topic.get("Text"):
                    result["related"].append(topic["Text"][:100])
            result["mentions"] = len(result["related"])
    except Exception:
        pass
    return result


def _search_twitter_narrative(symbol: str, name: str, mint: str) -> Dict[str, Any]:
    """Search Twitter for token narrative via web search and DexScreener social data."""
    result: Dict[str, Any] = {
        "tweets": [],
        "narrative": "",
        "kol_mentions": [],
        "heat_score": 0,
        "search_queries": [],
        "twitter_handle": "",
        "has_twitter": False,
    }
    
    # First try to get Twitter handle from DexScreener (more reliable)
    try:
        dex_url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
        r = requests.get(dex_url, timeout=8, headers={"User-Agent": "okx-signal/1.0"})
        if r.status_code == 200:
            data = r.json()
            pairs = data.get("pairs", [])
            if pairs:
                info = pairs[0].get("info", {})
                socials = info.get("socials", [])
                for s in socials:
                    if s.get("type", "").lower() == "twitter":
                        url = s.get("url", "")
                        if url:
                            # Handle both profile URLs and tweet URLs
                            parts = url.rstrip("/").split("/")
                            for i, part in enumerate(parts):
                                if part in ["x.com", "twitter.com"] and i + 1 < len(parts):
                                    candidate = parts[i + 1]
                                    if candidate not in ["status", "i", "search"]:
                                        handle = candidate
                                        result["twitter_handle"] = handle
                                        result["has_twitter"] = True
                                        result["kol_mentions"].append(handle)
                                        log(f"[NARRATIVE] found Twitter handle from DexScreener: @{handle}")
                                        break
                            if result["has_twitter"]:
                                break
    except Exception as e:
        log(f"[NARRATIVE-WARN] DexScreener social fetch failed: {type(e).__name__}")
    
    # Try web search as backup (may fail due to CAPTCHA)
    queries = [
        f'"{symbol}" solana site:x.com',
        f'"{name}" solana site:x.com',
    ]
    
    all_tweets = []
    seen_urls = set()
    
    for q in queries[:2]:
        try:
            log(f"[NARRATIVE] searching: {q[:50]}...")
            r = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": q},
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
                timeout=10,
            )
            if r.status_code != 200:
                continue
                
            result["search_queries"].append(q)
            
            # Extract URLs from DuckDuckGo HTML
            urls = re.findall(r'class="result__url"[^>]*href="([^"]+)"', r.text)
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|span|div)', r.text, re.DOTALL)
            
            for i, url in enumerate(urls[:5]):
                if not any(domain in url for domain in ["x.com", "twitter.com"]):
                    continue
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # Extract author handle from URL
                author = ""
                if "/status/" in url:
                    parts = url.split("/")
                    for j, part in enumerate(parts):
                        if part in ["x.com", "twitter.com"] and j + 1 < len(parts):
                            author = parts[j + 1]
                            break
                
                text = ""
                if i < len(snippets):
                    text = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                
                tweet = {
                    "author": author,
                    "text": text[:300],
                    "url": url,
                    "engagement": 0,
                }
                all_tweets.append(tweet)
                
                if author and author not in result["kol_mentions"]:
                    result["kol_mentions"].append(author)
                    
        except Exception as e:
            log(f"[NARRATIVE-WARN] search failed: {type(e).__name__}")
            continue
    
    result["tweets"] = all_tweets[:10]
    
    # Calculate heat score based on available data
    tweet_count = len(all_tweets)
    kol_count = len(result["kol_mentions"])
    has_twitter = result["has_twitter"]
    
    # Base score for having Twitter presence
    if has_twitter:
        result["heat_score"] = 3  # Base score for having Twitter
        log(f"[NARRATIVE] has Twitter presence, base heat=3")
    
    # Additional score from tweets
    if tweet_count >= 10:
        result["heat_score"] = max(result["heat_score"], 8)
    elif tweet_count >= 5:
        result["heat_score"] = max(result["heat_score"], 6)
    elif tweet_count >= 2:
        result["heat_score"] = max(result["heat_score"], 4)
    elif tweet_count >= 1:
        result["heat_score"] = max(result["heat_score"], 2)
    
    # Bonus for KOL mentions
    if kol_count >= 3:
        result["heat_score"] = min(10, result["heat_score"] + 2)
    elif kol_count >= 1:
        result["heat_score"] = min(10, result["heat_score"] + 1)
    
    log(f"[NARRATIVE] found {tweet_count} tweets, {kol_count} KOLs, has_twitter={has_twitter}, heat={result['heat_score']}")
    
    return result


def _generate_narrative_summary(symbol: str, name: str, narrative_data: Dict[str, Any], dexscreener_data: Dict[str, Any]) -> str:
    """Generate narrative summary from collected data."""
    tweets = narrative_data.get("tweets", [])
    kol_mentions = narrative_data.get("kol_mentions", [])
    heat = narrative_data.get("heat_score", 0)
    has_twitter = narrative_data.get("has_twitter", False)
    twitter_handle = narrative_data.get("twitter_handle", "")
    
    ds = dexscreener_data
    liq = ds.get("liquidity_usd", 0) or 0
    vol24 = ds.get("volume_24h", 0) or 0
    pc_1h = ds.get("price_change_1h", 0) or 0
    
    parts = []
    narrative_types = []
    
    sym_lower = symbol.lower()
    name_lower = name.lower()
    
    # Detect narrative type from name/symbol
    if any(kw in sym_lower or kw in name_lower for kw in ["pepe", "frog", "toad"]):
        narrative_types.append("🐸 Pepe系列")
    if any(kw in sym_lower or kw in name_lower for kw in ["doge", "shib", "dog", "cat"]):
        narrative_types.append("🐕 动物Meme")
    if any(kw in sym_lower or kw in name_lower for kw in ["ai", "gpt", "agent", "bot"]):
        narrative_types.append("🤖 AI叙事")
    if any(kw in sym_lower or kw in name_lower for kw in ["trump", "maga", "biden"]):
        narrative_types.append("🇺🇸 政治Meme")
    
    # Detect from tweets
    tweet_text = " ".join([t.get("text", "") for t in tweets]).lower()
    if "viral" in tweet_text or "moon" in tweet_text or "pump" in tweet_text:
        narrative_types.append("🚀 拉升叙事")
    if "community" in tweet_text or "hold" in tweet_text or "diamond" in tweet_text:
        narrative_types.append("💎 社区叙事")
    
    if not narrative_types:
        narrative_types.append("📌 通用Meme")
    
    parts.append(f"类型: {', '.join(narrative_types[:2])}")
    
    # Twitter presence
    if has_twitter and twitter_handle:
        parts.append(f"🐦 @{twitter_handle}")
    elif tweets:
        parts.append(f"推文: {len(tweets)}条")
        if kol_mentions:
            kol_str = ", ".join([f"@{k}" for k in kol_mentions[:3]])
            parts.append(f"博主: {kol_str}")
    else:
        parts.append("推文: 暂无")
    
    if liq > 0 and pc_1h > 100:
        parts.append(f"🔥 1h暴涨{pc_1h:.0f}%")
    elif liq > 0 and pc_1h > 20:
        parts.append(f"📈 1h+{pc_1h:.0f}%")
    
    if heat >= 8:
        parts.append("热度:🔥🔥🔥")
    elif heat >= 5:
        parts.append("热度:🔥🔥")
    elif heat >= 2:
        parts.append("热度:🔥")
    else:
        parts.append("热度:❓")
    
    return " | ".join(parts)


def gather_token_analysis(token: Dict[str, Any], cfg: Config) -> Dict[str, Any]:
    """Fetch DexScreener data and build token analysis with social verification."""
    mint = token.get("mint", "")
    analysis: Dict[str, Any] = {
        "mint": mint,
        "symbol": token.get("symbol", "?"),
        "name": token.get("name", "?"),
        "signal_label": token.get("signal_label", ""),
        "signal_age": signal_age_seconds(token),
        "current_mcap": token.get("current_mcap", ""),
        "first_signal_mcap": token.get("first_signal_mcap", ""),
    }
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
        r = requests.get(url, timeout=10, headers={"User-Agent": "okx-signal/1.0"})
        if r.status_code == 200:
            data = r.json()
            pairs = data.get("pairs", [])
            if pairs:
                sol_pair = None
                for p in pairs:
                    if p.get("quoteToken", {}).get("address", "") in _SOL_ADDRS:
                        sol_pair = p
                        break
                if not sol_pair:
                    sol_pair = pairs[0]
                liq = sol_pair.get("liquidity", {})
                vol = sol_pair.get("volume", {})
                pc = sol_pair.get("priceChange", {})
                info = sol_pair.get("info", {})
                socials = info.get("socials", [])
                websites = info.get("websites", [])

                # Extract social handles
                twitter_handle = ""
                telegram_handle = ""
                for s in socials:
                    st = s.get("type", "").lower()
                    su = s.get("url", "")
                    if st == "twitter" and su:
                        # Handle both profile URLs and tweet URLs
                        # Profile: https://x.com/username
                        # Tweet: https://x.com/username/status/123456
                        parts = su.rstrip("/").split("/")
                        for i, part in enumerate(parts):
                            if part in ["x.com", "twitter.com"] and i + 1 < len(parts):
                                candidate = parts[i + 1]
                                if candidate not in ["status", "i", "search"]:
                                    twitter_handle = candidate
                                    break
                    elif st == "telegram" and "/" in su:
                        telegram_handle = su.rstrip("/").split("/")[-1]

                analysis["dexscreener"] = {
                    "price_usd": sol_pair.get("priceUsd", ""),
                    "price_native": sol_pair.get("priceNative", ""),
                    "liquidity_usd": liq.get("usd", 0) or 0,
                    "volume_24h": vol.get("h24", 0) or 0,
                    "volume_1h": vol.get("h1", 0) or 0,
                    "volume_5m": vol.get("m5", 0) or 0,
                    "price_change_5m": pc.get("m5", 0) or 0,
                    "price_change_1h": pc.get("h1", 0) or 0,
                    "price_change_24h": pc.get("h24", 0) or 0,
                    "pair_created": sol_pair.get("pairCreatedAt", ""),
                    "dex": sol_pair.get("dexId", ""),
                    "url": sol_pair.get("url", f"https://dexscreener.com/solana/{mint}"),
                    "socials": socials,
                    "websites": websites,
                    "twitter_handle": twitter_handle,
                    "telegram_handle": telegram_handle,
                }

                # Verify social accounts
                if twitter_handle:
                    log(f"[ANALYSIS] checking twitter @{twitter_handle}")
                    analysis["twitter"] = _check_twitter_profile(twitter_handle)
                if telegram_handle:
                    log(f"[ANALYSIS] checking telegram @{telegram_handle}")
                    analysis["telegram"] = _check_telegram_group(telegram_handle)

    except Exception as e:
        log(f"[ANALYSIS-WARN] DexScreener fetch failed: {e}")

    # Search for token buzz
    sym = analysis.get("symbol", "")
    name = analysis.get("name", "")
    mint = analysis.get("mint", "")
    if sym and sym != "?":
        analysis["buzz"] = _search_token_buzz(sym, name)
    
    # Search for Twitter narrative
    if sym and sym != "?":
        try:
            analysis["narrative"] = _search_twitter_narrative(sym, name, mint)
            ds_data = analysis.get("dexscreener", {})
            analysis["narrative_summary"] = _generate_narrative_summary(sym, name, analysis["narrative"], ds_data)
        except Exception as e:
            log(f"[NARRATIVE-WARN] narrative analysis failed: {type(e).__name__}")
            analysis["narrative"] = {"tweets": [], "kol_mentions": [], "heat_score": 0}
            analysis["narrative_summary"] = ""

    return analysis


def calculate_meme_score(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Score the meme coin on multiple dimensions (out of 12) with narrative analysis."""
    scores: Dict[str, int] = {}
    reasons: List[str] = []
    risks: List[str] = []
    ds = analysis.get("dexscreener", {})
    tw = analysis.get("twitter", {})
    tg = analysis.get("telegram", {})
    buzz = analysis.get("buzz", {})
    narrative = analysis.get("narrative", {})

    # 1. Twitter verification (3 pts)
    tw_followers = tw.get("followers", 0)
    tw_exists = tw.get("exists", False)
    if tw_exists and tw_followers >= 50000:
        scores["twitter"] = 3
        reasons.append(f"Twitter @{tw.get('handle','')} 粉丝 {tw_followers:,} 🔥")
    elif tw_exists and tw_followers >= 10000:
        scores["twitter"] = 2
        reasons.append(f"Twitter @{tw.get('handle','')} 粉丝 {tw_followers:,}")
    elif tw_exists and tw_followers >= 1000:
        scores["twitter"] = 1
        reasons.append(f"Twitter @{tw.get('handle','')} 粉丝 {tw_followers:,}")
    elif tw_exists:
        scores["twitter"] = 1
        risks.append(f"Twitter @{tw.get('handle','')} 粉丝仅 {tw_followers:,}")
    else:
        scores["twitter"] = 0
        risks.append("Twitter 账户不存在或无法验证")

    # 2. Telegram community (2 pts)
    tg_members = tg.get("members", 0)
    tg_exists = tg.get("exists", False)
    if tg_exists and tg_members >= 5000:
        scores["telegram"] = 2
        reasons.append(f"Telegram 社区 {tg_members:,} 人 🔥")
    elif tg_exists and tg_members >= 500:
        scores["telegram"] = 1
        reasons.append(f"Telegram 社区 {tg_members:,} 人")
    elif tg_exists:
        scores["telegram"] = 1
        risks.append(f"Telegram 社区仅 {tg_members:,} 人")
    else:
        scores["telegram"] = 0
        risks.append("无 Telegram 社区")

    # 3. Trading activity (2 pts)
    liq = ds.get("liquidity_usd", 0) or 0
    vol24 = ds.get("volume_24h", 0) or 0
    vol5m = ds.get("volume_5m", 0) or 0
    ratio = vol24 / liq if liq > 0 else 0
    # Also check if 5m volume is accelerating
    vol_accel = (vol5m * 288) / vol24 if vol24 > 0 else 0  # 5m extrapolated vs 24h
    if ratio >= 2 or vol_accel >= 1.5:
        scores["activity"] = 2
        reasons.append(f"交易极度活跃 24h量/流={ratio:.1f}x")
    elif ratio >= 0.3:
        scores["activity"] = 1
        reasons.append(f"交易活跃 24h量/流={ratio:.1f}x")
    else:
        scores["activity"] = 0
        risks.append(f"交易冷清 24h量/流={ratio:.2f}x")

    # 4. Price momentum (2 pts)
    c5 = ds.get("price_change_5m", 0) or 0
    c1h = ds.get("price_change_1h", 0) or 0
    if c5 >= 20 and c1h > 0:
        scores["momentum"] = 2
        reasons.append(f"强势拉升 5m+{c5:.1f}% 1h+{c1h:.1f}% 🔥")
    elif c5 >= 5:
        scores["momentum"] = 1
        reasons.append(f"5分钟上涨 +{c5:.1f}%")
    elif c5 >= 0:
        scores["momentum"] = 1
    else:
        scores["momentum"] = 0
        risks.append(f"5分钟下跌 {c5:.1f}%")

    # 5. Signal freshness (1 pt)
    age = analysis.get("signal_age")
    if age is not None and 0 <= age < 60:
        scores["freshness"] = 1
        reasons.append(f"信号极新鲜 ({age:.0f}s)")
    else:
        scores["freshness"] = 0

    # 6. Twitter narrative (2 pts)
    heat = narrative.get("heat_score", 0)
    tweets = narrative.get("tweets", [])
    kol_mentions = narrative.get("kol_mentions", [])
    has_twitter = narrative.get("has_twitter", False)
    twitter_handle = narrative.get("twitter_handle", "")
    
    if heat >= 6 and len(tweets) >= 3:
        scores["narrative"] = 2
        reasons.append(f"Twitter热度高 找到{len(tweets)}条推文 🔥")
        if kol_mentions:
            kol_str = ", ".join([f"@{k}" for k in kol_mentions[:2]])
            reasons.append(f"  相关博主: {kol_str}")
    elif has_twitter and twitter_handle:
        scores["narrative"] = 1
        reasons.append(f"有官方Twitter @{twitter_handle}")
    elif heat >= 3 or len(tweets) >= 1:
        scores["narrative"] = 1
        reasons.append(f"Twitter有提及 ({len(tweets)}条)")
    else:
        scores["narrative"] = 0
        risks.append("Twitter无相关讨论")

    # Buzz bonus (if found in search)
    if buzz.get("mentions", 0) > 0:
        reasons.append(f"网络有相关讨论 ({buzz['mentions']}条)")

    total = sum(scores.values())
    if total >= 10:
        rec = "强烈建议买入 🔥"
    elif total >= 7:
        rec = "可以考虑 ⚡"
    elif total >= 5:
        rec = "谨慎观望 ⚠️"
    else:
        rec = "不建议买入 🚫"

    return {"total": total, "max": 12, "scores": scores, "reasons": reasons, "risks": risks, "recommendation": rec}


def format_analysis_message(analysis: Dict[str, Any], score: Dict[str, Any], cfg: Config) -> str:
    """Build the Telegram message with token analysis and score."""
    ds = analysis.get("dexscreener", {})
    tw = analysis.get("twitter", {})
    tg = analysis.get("telegram", {})
    narrative = analysis.get("narrative", {})
    narrative_summary = analysis.get("narrative_summary", "")
    sym = tg_escape(analysis.get("symbol", "?"))
    name = tg_escape(analysis.get("name", "?"))
    mint = analysis.get("mint", "")
    age = analysis.get("signal_age")
    age_text = f"{age:.0f}秒前" if age is not None else "未知" 

    parts = [
        f"🔔 <b>OKX Signal 新信号</b>\n",
        f"<b>{name}</b> ({sym})",
        f"<code>{tg_escape(mint)}</code>\n",
    ]

    if ds:
        parts.append(f"📊 流动性: <b>${ds.get('liquidity_usd', 0):,.0f}</b>")
        parts.append(f"📈 24h量: ${ds.get('volume_24h', 0):,.0f} | 5m: {ds.get('price_change_5m', 0):+.1f}% | 1h: {ds.get('price_change_1h', 0):+.1f}%")
        parts.append(f"💰 价格: {ds.get('price_usd', '?')}")
        parts.append(f"⏰ 信号: {age_text}")
        parts.append("")

        # Social verification section
        social_parts = []
        if tw.get("exists"):
            tw_icon = "✅" if tw.get("followers", 0) >= 10000 else "⚠️" if tw.get("followers", 0) >= 1000 else "❌"
            social_parts.append(f"🐦 Twitter: @{tg_escape(tw.get('handle',''))} {tw.get('followers',0):,}粉丝 {tw_icon}")
        elif ds.get("twitter_handle"):
            social_parts.append(f"🐦 Twitter: @{tg_escape(ds.get('twitter_handle',''))} (未验证)")

        if tg.get("exists"):
            tg_icon = "✅" if tg.get("members", 0) >= 5000 else "⚠️" if tg.get("members", 0) >= 500 else "❌"
            social_parts.append(f"📱 Telegram: {tg.get('members',0):,}人 {tg_icon}")
        elif ds.get("telegram_handle"):
            social_parts.append(f"📱 Telegram: @{tg_escape(ds.get('telegram_handle',''))} (未验证)")

        if social_parts:
            parts.append("👥 <b>社交验证:</b>")
            parts.extend([f"  {s}" for s in social_parts])
            parts.append("")

        # Links
        link_parts = [f'<a href="{ds.get("url", "")}">DexScreener</a>']
        for s in ds.get("socials", []):
            st = s.get("type", "").lower()
            su = s.get("url", "")
            if st == "twitter" and su:
                link_parts.append(f'<a href="{su}">Twitter</a>')
            elif st == "telegram" and su:
                link_parts.append(f'<a href="{su}">Telegram</a>')
        for w in ds.get("websites", []):
            wu = w.get("url", "")
            if wu:
                link_parts.append(f'<a href="{wu}">Website</a>')
        parts.append("🔗 " + " | ".join(link_parts))
    else:
        parts.append(f"⏰ 信号: {age_text}")
        parts.append("⚠️ DexScreener 数据暂未获取")

    parts.append("")

    # Narrative summary section
    if narrative_summary:
        parts.append("🧠 <b>叙事分析:</b>")
        parts.append(f"  {tg_escape(narrative_summary)}")
        parts.append("")
    
    # Analysis reasons
    if score.get("reasons"):
        parts.append("💡 <b>分析:</b>")
        for r in score["reasons"]:
            parts.append(f"  • {r}")

    if score.get("risks"):
        parts.append("")
        parts.append("⚠️ <b>风险:</b>")
        for r in score["risks"]:
            parts.append(f"  • {r}")

    parts.append("")

    # Score breakdown (updated dimensions)
    labels = [("twitter", "Twitter", 3), ("telegram", "Telegram", 2), ("activity", "活跃度", 2), ("momentum", "动量", 2), ("freshness", "新鲜", 1), ("narrative", "叙事", 2)]
    parts.append(f"⭐ <b>评分: {score['total']}/{score['max']}</b>")
    for key, label, mx in labels:
        v = score.get("scores", {}).get(key, 0)
        icon = "✅" if v == mx else ("⚠️" if v > 0 else "❌")
        parts.append(f"  {label} {v}/{mx} {icon}")

    parts.append("")
    parts.append(f"💰 <b>建议: {score['recommendation']}</b>")
    parts.append(f"买入金额: {cfg.buy_sol} SOL")
    return "\n".join(parts)


def notify_telegram_with_keyboard(text: str, mint: str, name: str = "") -> Optional[int]:
    """Send Telegram message with confirm/reject inline buttons. Returns message_id."""
    token = os.getenv("OKX_SIGNAL_BOT_TOKEN", "").strip() or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("OKX_SIGNAL_TELEGRAM_CHAT_ID", "").strip()
    if not chat_id:
        allowed = os.getenv("TELEGRAM_ALLOWED_USERS", "").strip()
        if allowed:
            chat_id = allowed.split(",")[0].strip()
    if not token or not chat_id:
        log("[TG-SKIP] TELEGRAM_BOT_TOKEN or chat_id missing", also_print=True)
        return None
    # Twitter search links
    twitter_contract_url = f"https://x.com/search?q={mint}"
    twitter_name_url = f"https://x.com/search?q={name}" if name else ""
    keyboard_rows = [
        [
            {"text": "✅ 确认买入", "callback_data": f"confirm:{mint}"},
            {"text": "❌ 放弃", "callback_data": f"reject:{mint}"},
        ],
        [
            {"text": "🔍 Twitter搜合约", "url": twitter_contract_url},
            {"text": "🔍 Twitter搜名称", "url": twitter_name_url},
        ] if name else [
            {"text": "🔍 Twitter搜合约", "url": twitter_contract_url},
        ]
    ]
    keyboard = {"inline_keyboard": keyboard_rows}
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                  "disable_web_page_preview": True, "reply_markup": keyboard},
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("result", {}).get("message_id")
        log(f"[TG-ERR] HTTP {r.status_code}: {r.text[:300]}")
    except Exception as e:
        log(f"[TG-ERR] {type(e).__name__}: {e}")
    return None


def edit_telegram_message(message_id: int, text: str) -> None:
    """Edit a Telegram message (remove buttons, update text)."""
    token = os.getenv("OKX_SIGNAL_BOT_TOKEN", "").strip() or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("OKX_SIGNAL_TELEGRAM_CHAT_ID", "").strip()
    if not chat_id:
        allowed = os.getenv("TELEGRAM_ALLOWED_USERS", "").strip()
        if allowed:
            chat_id = allowed.split(",")[0].strip()
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/editMessageText",
            json={"chat_id": chat_id, "message_id": message_id, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=15,
        )
    except Exception as e:
        log(f"[TG-ERR] edit: {type(e).__name__}: {e}")


def answer_callback_query(callback_id: str) -> None:
    """Answer callback query to dismiss loading spinner."""
    token = os.getenv("OKX_SIGNAL_BOT_TOKEN", "").strip() or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/answerCallbackQuery",
            json={"callback_query_id": callback_id}, timeout=10,
        )
    except Exception:
        pass


def callback_polling_loop(kp: Keypair, cfg: Config, live: bool, state: Dict[str, Any]) -> None:
    """Poll Telegram for inline-button callback queries."""
    tg_token = os.getenv("OKX_SIGNAL_BOT_TOKEN", "").strip() or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not tg_token:
        log("[CALLBACK-SKIP] No TELEGRAM_BOT_TOKEN")
        return
    log("[CALLBACK] 开始监听 Telegram 回调")
    offset = 0
    while True:
        try:
            # Expire old confirmations (>5 min)
            now = time.time()
            expired = []
            with PENDING_LOCK:
                for k, p in PENDING_CONFIRMS.items():
                    if now - p.get("timestamp", 0) > 300:
                        expired.append(k)
                for k in expired:
                    p = PENDING_CONFIRMS.pop(k, {})
                    mid = p.get("msg_id")
                    sym = p.get("token", {}).get("symbol", "?")
                    if mid:
                        edit_telegram_message(mid, f"⏰ <b>确认超时，已自动放弃</b>\n{tg_escape(sym)}")
                    log(f"[TIMEOUT] {sym}")

            r = requests.get(
                f"https://api.telegram.org/bot{tg_token}/getUpdates",
                params={"offset": offset, "timeout": 10, "allowed_updates": '["callback_query"]'},
                timeout=20,
            )
            if r.status_code != 200:
                time.sleep(5); continue
            data = r.json()
            if not data.get("ok"):
                time.sleep(5); continue

            for update in data.get("result", []):
                uid = update.get("update_id", 0)
                if uid >= offset:
                    offset = uid + 1
                cb = update.get("callback_query")
                if not cb:
                    continue
                cb_id = cb.get("id", "")
                cb_data = cb.get("data", "")
                if ":" not in cb_data:
                    answer_callback_query(cb_id); continue
                action, cb_mint = cb_data.split(":", 1)

                # Find matching pending
                with PENDING_LOCK:
                    pending = None
                    pending_key = None
                    for k, p in PENDING_CONFIRMS.items():
                        if p.get("token", {}).get("mint") == cb_mint:
                            pending = p; pending_key = k; break
                if not pending:
                    answer_callback_query(cb_id); continue
                answer_callback_query(cb_id)

                tok = pending.get("token", {})
                mid = pending.get("msg_id")
                sym = tok.get("symbol", "?")

                if action == "confirm":
                    with PENDING_LOCK:
                        PENDING_CONFIRMS.pop(pending_key, None)
                    log(f"[MANUAL-CONFIRM] 用户确认 {sym} {cb_mint[:16]}")
                    def _do_buy(_tok=tok, _mid=mid):
                        try:
                            buy_token(_tok, kp, cfg, live, state, manual=True)
                            if _mid:
                                edit_telegram_message(_mid, f"✅ <b>已买入</b>\n{tg_escape(_tok.get('symbol', '?'))}")
                        except Exception as e:
                            log(f"[MANUAL-BUY-ERR] {_tok.get('symbol')} {type(e).__name__}: {e}")
                            if _mid:
                                edit_telegram_message(_mid, f"❌ <b>买入失败</b>\n{tg_escape(_tok.get('symbol', '?'))}: {tg_escape(str(e)[:80])}")
                    threading.Thread(target=_do_buy, daemon=True).start()

                elif action == "reject":
                    with PENDING_LOCK:
                        PENDING_CONFIRMS.pop(pending_key, None)
                    log(f"[MANUAL-REJECT] 用户拒绝 {sym} {cb_mint[:16]}")
                    if mid:
                        edit_telegram_message(mid, f"❌ <b>已放弃</b>\n{tg_escape(sym)}")

        except Exception as e:
            log(f"[CALLBACK-ERR] {type(e).__name__}: {e}")
            time.sleep(5)


def load_config() -> Config:
    load_dotenv(ENV_PATH, override=True)
    raw_max_open = os.getenv("OKX_SIGNAL_MAX_OPEN_POSITIONS", "0").strip().lower()
    max_open_positions = 0 if raw_max_open in ("", "0", "none", "unlimited", "no_limit") else int(raw_max_open)
    return Config(
        live_env=os.getenv("OKX_SIGNAL_LIVE_TRADING", "false").lower() == "true",
        buy_sol=Decimal(os.getenv("OKX_SIGNAL_BUY_SOL", "0.3")),
        poll_seconds=int(os.getenv("OKX_SIGNAL_POLL_SECONDS", "8")),
        slippage_bps=int(os.getenv("OKX_SIGNAL_SLIPPAGE_BPS", "500")),  # 5%, meme token默认宽一点
        tp_multiple=Decimal(os.getenv("OKX_SIGNAL_TAKE_PROFIT_MULTIPLE", "2")),
        sell_fraction=Decimal(os.getenv("OKX_SIGNAL_SELL_FRACTION_AT_2X", "0.5")),
        rpc_url=os.getenv("SOLANA_RPC_URL", DEFAULT_RPC),
        max_open_positions=max_open_positions,
        min_sol_reserve=Decimal(os.getenv("OKX_SIGNAL_MIN_SOL_RESERVE", "0.05")),
        dry_run_quote=os.getenv("OKX_SIGNAL_DRY_RUN_QUOTE", "true").lower() == "true",
        tp_check_seconds=int(os.getenv("OKX_SIGNAL_TP_CHECK_SECONDS", "60")),
        tp_top_n=int(os.getenv("OKX_SIGNAL_TP_TOP_N", "10")),
        tp_429_cooldown_seconds=int(os.getenv("OKX_SIGNAL_TP_429_COOLDOWN_SECONDS", "180")),
        # 严格只买“刚推送”的信号；默认只接受 firstSignalTime 在最近 120 秒内的 token。
        max_signal_age_seconds=int(os.getenv("OKX_SIGNAL_MAX_SIGNAL_AGE_SECONDS", "120")),
    )


def load_keypair() -> Keypair:
    raw = os.getenv("SOLANA_PRIVATE_KEY", "").strip().strip('"').strip("'")
    if not raw:
        raise RuntimeError(f"SOLANA_PRIVATE_KEY not found in {ENV_PATH}")
    if raw.startswith("["):
        b = bytes(json.loads(raw))
    else:
        b = base58.b58decode(raw)
    if len(b) == 64:
        return Keypair.from_bytes(b)
    if len(b) == 32:
        return Keypair.from_seed(b)
    raise RuntimeError(f"Unsupported SOLANA_PRIVATE_KEY byte length: {len(b)}")


def rpc_call(method: str, params: list, cfg: Config, timeout: int = 20) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    headers = {"Content-Type": "application/json", "User-Agent": "okx-signal-autobuy/1.0"}
    last_err: Optional[Exception] = None
    urls = []
    for u in [cfg.rpc_url, DEFAULT_RPC, "https://solana-rpc.publicnode.com"]:
        if u and u not in urls:
            urls.append(u)
    for url in urls:
        for attempt in range(3):
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=timeout)
                if r.status_code in (403, 429, 500, 502, 503, 504):
                    last_err = requests.HTTPError(f"RPC {url} HTTP {r.status_code}: {r.text[:200]}")
                    time.sleep(0.8 * (attempt + 1))
                    continue
                r.raise_for_status()
                data = r.json()
                if "error" in data:
                    raise RuntimeError(f"RPC {method} error: {data['error']}")
                return data.get("result")
            except Exception as e:
                last_err = e
                time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"RPC {method} failed after retries: {last_err}")


def get_sol_balance_lamports(owner: str, cfg: Config) -> int:
    res = rpc_call("getBalance", [owner], cfg)
    return int(res.get("value", 0))


def _merge_token_accounts_jsonparsed(owner: str, cfg: Config, program_id: str, out: Dict[str, int]) -> None:
    res = rpc_call(
        "getTokenAccountsByOwner",
        [owner, {"programId": program_id}, {"encoding": "jsonParsed"}],
        cfg,
    )
    for item in res.get("value", []):
        try:
            info = item["account"]["data"]["parsed"]["info"]
            mint = str(info["mint"])
            amount = int(info["tokenAmount"]["amount"])
            if amount > 0:
                out[mint] = out.get(mint, 0) + amount
        except Exception:
            continue


def _merge_token_accounts_base64(owner: str, cfg: Config, program_id: str, out: Dict[str, int]) -> None:
    # SPL Token 和 Token-2022 token account 的基础布局前 72 字节一致：mint[0:32], owner[32:64], amount u64 LE[64:72]。
    res = rpc_call(
        "getTokenAccountsByOwner",
        [owner, {"programId": program_id}, {"encoding": "base64"}],
        cfg,
    )
    for item in res.get("value", []):
        try:
            data_field = item["account"]["data"]
            b64 = data_field[0] if isinstance(data_field, list) else data_field
            raw = base64.b64decode(b64)
            if len(raw) < 72:
                continue
            mint = str(Pubkey.from_bytes(raw[0:32]))
            amount = int.from_bytes(raw[64:72], "little")
            if amount > 0:
                out[mint] = out.get(mint, 0) + amount
        except Exception:
            continue


def get_token_accounts(owner: str, cfg: Config) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for program_id in (SPL_TOKEN_PROGRAM, TOKEN_2022_PROGRAM):
        try:
            _merge_token_accounts_jsonparsed(owner, cfg, program_id, out)
            continue
        except Exception as e:
            log(f"[HOLDINGS-WARN] jsonParsed failed program={program_id}: {e}; trying base64 fallback")
            if "429" in str(e) or "Too many requests" in str(e):
                continue
        try:
            _merge_token_accounts_base64(owner, cfg, program_id, out)
        except Exception as e:
            log(f"[HOLDINGS-WARN] base64 fallback failed program={program_id}: {e}")
    return out


def get_token_accounts_with_decimals(owner: str, cfg: Config) -> Dict[str, Tuple[int, int]]:
    """Like get_token_accounts but returns {mint: (raw_amount, decimals)}."""
    out: Dict[str, Tuple[int, int]] = {}
    for program_id in (SPL_TOKEN_PROGRAM, TOKEN_2022_PROGRAM):
        try:
            res = rpc_call(
                "getTokenAccountsByOwner",
                [owner, {"programId": program_id}, {"encoding": "jsonParsed"}],
                cfg,
            )
            for item in res.get("value", []):
                try:
                    info = item["account"]["data"]["parsed"]["info"]
                    mint = str(info["mint"])
                    ta = info["tokenAmount"]
                    amount = int(ta["amount"])
                    dec = int(ta["decimals"])
                    if amount > 0:
                        if mint in out:
                            out[mint] = (out[mint][0] + amount, dec)
                        else:
                            out[mint] = (amount, dec)
                except Exception:
                    continue
        except Exception as e:
            if "429" in str(e) or "Too many requests" in str(e):
                log(f"[HOLDINGS-WARN] 429 on {program_id}, skipping decimals fetch")
            else:
                log(f"[HOLDINGS-WARN] get_token_accounts_with_decimals failed {program_id}: {e}")
    return out


def dexscreener_price_map(mints: List[str]) -> Dict[str, float]:
    """Query DexScreener for priceNative of a list of mints. Returns {mint: priceNative}.

    DexScreener API allows up to 30 addresses per request.
    When multiple pairs exist for the same token, uses the one with highest liquidity
    among pairs whose quote token is SOL (to get true SOL-denominated price).
    """
    SOL_ADDRS = {"So11111111111111111111111111111111111111112", "So11111111111111111111111111111111111111111"}
    # {mint: (priceNative, liquidity_usd)} — keep highest liquidity SOL-pair
    best: Dict[str, Tuple[float, float]] = {}
    batch_size = 30
    for i in range(0, len(mints), batch_size):
        batch = mints[i:i + batch_size]
        try:
            addr_str = ",".join(batch)
            url = f"https://api.dexscreener.com/latest/dex/tokens/{addr_str}"
            r = requests.get(url, timeout=15, headers={"User-Agent": "okx-signal-autobuy/1.0"})
            if r.status_code == 200:
                data = r.json()
                for pair in data.get("pairs", []) or []:
                    # Only consider pairs where quote token is SOL
                    quote_addr = pair.get("quoteToken", {}).get("address", "")
                    if quote_addr not in SOL_ADDRS:
                        continue
                    base_addr = pair.get("baseToken", {}).get("address", "")
                    pn = pair.get("priceNative")
                    liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)
                    if base_addr and pn is not None:
                        try:
                            pn_float = float(pn)
                        except (ValueError, TypeError):
                            continue
                        prev = best.get(base_addr)
                        if prev is None or liq > prev[1]:
                            best[base_addr] = (pn_float, liq)
            else:
                log(f"[DEXSCREENER] HTTP {r.status_code} for batch {i}")
        except Exception as e:
            log(f"[DEXSCREENER] batch {i} error: {e}")
        if i + batch_size < len(mints):
            time.sleep(0.5)
    return {m: v[0] for m, v in best.items()}


def get_sol_usdt_price() -> float:
    """Get current SOL/USDT price from Binance API."""
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": "SOLUSDT"},
            timeout=10,
            headers={"User-Agent": "okx-signal-autobuy/1.0"},
        )
        r.raise_for_status()
        return float(r.json()["price"])
    except Exception as e:
        log(f"[SOL-PRICE-WARN] Failed to get SOL/USDT price: {e}")
        return 0.0


def get_mint_holding(owner: str, mint: str, cfg: Config) -> int:
    """Fast single-mint holding check. Avoid full wallet token scans in realtime buy path.

    Full getTokenAccountsByOwner(programId=...) scans were taking minutes / 429ing on
    public RPC, which made fresh OKX page signals turn stale before execution.
    """
    total = 0
    try:
        res = rpc_call(
            "getTokenAccountsByOwner",
            [owner, {"mint": mint}, {"encoding": "jsonParsed"}],
            cfg,
            timeout=8,
        )
        for item in res.get("value", []):
            try:
                info = item["account"]["data"]["parsed"]["info"]
                amount = int(info["tokenAmount"]["amount"])
                if amount > 0:
                    total += amount
            except Exception:
                continue
        if total > 0:
            return total
    except Exception as e:
        log(f"[HOLDING-MINT-WARN] jsonParsed mint check failed {mint}: {e}; trying base64")
    try:
        res = rpc_call(
            "getTokenAccountsByOwner",
            [owner, {"mint": mint}, {"encoding": "base64"}],
            cfg,
            timeout=8,
        )
        for item in res.get("value", []):
            try:
                data_field = item["account"]["data"]
                b64 = data_field[0] if isinstance(data_field, list) else data_field
                raw = base64.b64decode(b64)
                if len(raw) >= 72:
                    amount = int.from_bytes(raw[64:72], "little")
                    if amount > 0:
                        total += amount
            except Exception:
                continue
    except Exception as e:
        log(f"[HOLDING-MINT-WARN] base64 mint check failed {mint}: {e}; continue with age gate")
    return total


def wait_for_signature(sig: str, cfg: Config, timeout_seconds: int = 60) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            res = rpc_call("getSignatureStatuses", [[sig], {"searchTransactionHistory": True}], cfg, timeout=15)
            status = (res.get("value") or [None])[0]
            if status:
                if status.get("err"):
                    log(f"[TX-ERR] sig={sig} err={status.get('err')}")
                    return False
                if status.get("confirmationStatus") in ("confirmed", "finalized"):
                    return True
        except Exception as e:
            log(f"[TX-WAIT-WARN] {type(e).__name__}: {e}")
        time.sleep(3)
    return False


def wait_for_token_holding(owner: str, mint: str, cfg: Config, min_amount: int = 1, attempts: int = 3) -> int:
    for i in range(attempts):
        held = int(get_mint_holding(owner, mint, cfg))
        if held >= min_amount:
            return held
        time.sleep(1 + i)
    return int(get_mint_holding(owner, mint, cfg))


def load_state() -> Dict[str, Any]:
    ensure_dirs()
    if not STATE_PATH.exists():
        return {"seen": {}, "positions": {}, "skipped_holdings": {}, "txs": []}
    with STATE_PATH.open("r", encoding="utf-8") as f:
        state = json.load(f)
    state.setdefault("seen", {})
    state.setdefault("positions", {})
    state.setdefault("skipped_holdings", {})
    state.setdefault("txs", [])
    return state


def save_state(state: Dict[str, Any]) -> None:
    ensure_dirs()
    tmp = STATE_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
    tmp.replace(STATE_PATH)


def fetch_okx_gems() -> List[Dict[str, Any]]:
    headers = {
        "user-agent": "Mozilla/5.0 OKX-Signal-AutoBuy/1.0",
        "referer": "https://web3.okx.com/zh-hans/signal",
        "accept": "application/json",
    }
    r = requests.get(OKX_SIGNAL_URL, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != 0:
        raise RuntimeError(f"OKX API error: {data}")
    return data.get("data", {}).get("gems", []) or []


def parse_gem(g: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ti = g.get("tokenInfo") or {}
    mint = ti.get("tokenContractAddress")
    chain_id = str(ti.get("chainId", ""))
    if not mint or chain_id != "501":
        return None
    key = f"{chain_id}:{mint}"
    first_signal_time_raw = str(g.get("firstSignalTime") or "")
    first_signal_ms: Optional[int] = None
    try:
        first_signal_ms = int(first_signal_time_raw)
    except Exception:
        first_signal_ms = None
    return {
        "key": key,
        "mint": mint,
        "chain_id": chain_id,
        "symbol": ti.get("tokenSymbol") or "?",
        "name": ti.get("tokenName") or "?",
        "first_signal_time": first_signal_time_raw,
        "first_signal_ms": first_signal_ms,
        "first_signal_mcap": str(g.get("firstSignalMcap") or ""),
        "current_mcap": str(g.get("currentMcap") or ""),
        "signal_label": str(g.get("signalLabel") or ""),
        "raw": g,
    }


def signal_age_seconds(token: Dict[str, Any]) -> Optional[float]:
    ms = token.get("first_signal_ms")
    if not ms:
        return None
    return time.time() - (int(ms) / 1000.0)


def fmt_signal_time(token: Dict[str, Any]) -> str:
    ms = token.get("first_signal_ms")
    if not ms:
        return str(token.get("first_signal_time") or "")
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).isoformat(timespec="seconds")


def jup_quote(input_mint: str, output_mint: str, amount: int, cfg: Config) -> Dict[str, Any]:
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": str(amount),
        "slippageBps": str(cfg.slippage_bps),
    }
    r = requests.get(JUP_QUOTE_URL, params=params, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"Jupiter quote HTTP {r.status_code}: {r.text[:500]}")
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"Jupiter quote error: {data}")
    return data


def jup_swap_tx(quote: Dict[str, Any], user_pubkey: str) -> str:
    payload = {
        "quoteResponse": quote,
        "userPublicKey": user_pubkey,
        "wrapAndUnwrapSol": True,
        "dynamicComputeUnitLimit": True,
        "prioritizationFeeLamports": {"priorityLevelWithMaxLamports": {"maxLamports": 1000000, "priorityLevel": "high"}},
    }
    r = requests.post(JUP_SWAP_URL, json=payload, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Jupiter swap HTTP {r.status_code}: {r.text[:500]}")
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"Jupiter swap error: {data}")
    tx = data.get("swapTransaction")
    if not tx:
        raise RuntimeError(f"No swapTransaction in Jupiter response: {data}")
    return tx


def sign_and_send_swap(swap_tx_b64: str, kp: Keypair, cfg: Config) -> str:
    raw = base64.b64decode(swap_tx_b64)
    tx = VersionedTransaction.from_bytes(raw)
    sig = kp.sign_message(to_bytes_versioned(tx.message))
    signed_tx = VersionedTransaction.populate(tx.message, [sig])
    signed_b64 = base64.b64encode(bytes(signed_tx)).decode()
    res = rpc_call(
        "sendTransaction",
        [signed_b64, {"encoding": "base64", "skipPreflight": False, "maxRetries": 3}],
        cfg,
        timeout=30,
    )
    return str(res)


def swap_with_retry(
    kp: Keypair, cfg: Config, quote: Dict[str, Any],
    symbol: str, mint: str, *, label: str = "swap", max_retries: int = 3,
) -> Tuple[Optional[str], bool]:
    """Execute a Jupiter swap with automatic retry on confirmation failure.

    Returns (sig, confirmed).  Retries up to max_retries times if:
    - sendTransaction raises
    - wait_for_signature returns False (timeout or on-chain error)
    """
    owner = str(kp.pubkey())
    sig = None
    for attempt in range(1, max_retries + 1):
        try:
            tx_b64 = jup_swap_tx(quote, owner)
            sig = sign_and_send_swap(tx_b64, kp, cfg)
        except Exception as e:
            log(f"[{label.upper()}-SEND-ERR] {symbol} attempt={attempt}/{max_retries}: {e}")
            if attempt < max_retries:
                time.sleep(2 * attempt)
                try:
                    in_amount = int(quote.get("inAmount", "0"))
                    if label == "sell":
                        quote = jup_quote(mint, SOL_MINT, in_amount, cfg)
                    else:
                        quote = jup_quote(SOL_MINT, mint, in_amount, cfg)
                except Exception as qe:
                    log(f"[{label.upper()}-REQUOTE-ERR] {symbol} attempt={attempt}: {qe}")
            continue

        confirmed = wait_for_signature(sig, cfg, timeout_seconds=75)
        if confirmed:
            return sig, True

        log(f"[{label.upper()}-CONFIRM-FAIL] {symbol} attempt={attempt}/{max_retries} sig={sig}")
        if attempt < max_retries:
            time.sleep(2 * attempt)
            try:
                in_amount = int(quote.get("inAmount", "0"))
                if label == "sell":
                    quote = jup_quote(mint, SOL_MINT, in_amount, cfg)
                else:
                    quote = jup_quote(SOL_MINT, mint, in_amount, cfg)
            except Exception as qe:
                log(f"[{label.upper()}-REQUOTE-ERR] {symbol} attempt={attempt}: {qe}")

    return sig, False


def decimals_int_ratio(a: Decimal, b: Decimal) -> str:
    return str((a / b).normalize()) if b != 0 else "0"


def buy_token(token: Dict[str, Any], kp: Keypair, cfg: Config, live: bool, state: Dict[str, Any], manual: bool = False) -> None:
    # 下单前必须重新计算一次信号年龄。WS 收到时可能还新鲜，但 RPC/Jupiter/持仓检查可能阻塞数分钟；
    # 如果不在这里二次校验，会出现“19:21 信号，19:31 才成交”的延迟买入。
    age = signal_age_seconds(token)
    age_text = "unknown" if age is None else f"{age:.1f}s"
    if age is None:
        log(f"[SKIP] 下单前信号时间未知，不买入 {token.get('symbol')} {token.get('mint')}")
        return
    if age < -30:
        log(f"[SKIP] 下单前 eventTime 在未来，疑似时间异常，不买入 {token.get('symbol')} age={age_text}")
        return
    if age > cfg.max_signal_age_seconds and not manual:
        log(f"[SKIP] 下单前信号已过期: {token.get('symbol')} eventTime={fmt_signal_time(token)} age={age_text} > {cfg.max_signal_age_seconds}s，不买入")
        return
    elif age > cfg.max_signal_age_seconds and manual:
        log(f"[MANUAL] 信号已过期但用户手动确认，继续买入: {token.get('symbol')} age={age_text}")

    owner = str(kp.pubkey())
    lamports_in = int(cfg.buy_sol * Decimal(1_000_000_000))

    # Safety: re-check mint-level duplicate before spending SOL
    mint = token.get("mint", "")
    if mint:
        for _pk, _pos in state.get("positions", {}).items():
            if _pos.get("mint") == mint and _pos.get("live_bought") and not _pos.get("half_sold") and not _pos.get("sell_sig"):
                log(f"[SKIP] buy_token: 已有活跃持仓，取消买入 {token.get('symbol')} {mint} existing={_pk[:40]}")
                return

    bal = get_sol_balance_lamports(owner, cfg)
    reserve = int(cfg.min_sol_reserve * Decimal(1_000_000_000))
    if bal < lamports_in + reserve:
        log(f"[SKIP] SOL不足: balance={bal/1e9:.9f}, need≈{(lamports_in+reserve)/1e9:.3f} token={token['symbol']} {token['mint']}")
        return

    quote = jup_quote(SOL_MINT, token["mint"], lamports_in, cfg)
    out_amount = int(quote.get("outAmount", "0"))
    if out_amount <= 0:
        log(f"[SKIP] Jupiter报价outAmount=0 token={token['symbol']} {token['mint']}")
        return

    # entry_price_lamports_per_raw_token = SOL lamports / raw token unit.
    # 后续用同等 raw token -> SOL quote 做2x判断，不依赖decimals。
    position = {
        "mint": token["mint"],
        "symbol": token["symbol"],
        "name": token["name"],
        "entry_time": utc_now(),
        "entry_sol_lamports": lamports_in,
        "entry_token_raw_amount": out_amount,
        "tp_multiple": str(cfg.tp_multiple),
        "sell_fraction": str(cfg.sell_fraction),
        "half_sold": False,
        "live_bought": bool(live),
        "okx_first_signal_time": token.get("first_signal_time"),
        "okx_signal_label": token.get("signal_label"),
    }

    if not live:
        log(f"[DRY-BUY] {token['symbol']} {token['mint']} quote: 0.3 SOL -> raw {out_amount}; 未下单")
        # 默认不记录paper position，避免后续实盘启动时被历史dry-run状态干扰。
        # 如需纸面追踪2x，可设置 OKX_SIGNAL_RECORD_PAPER=true。
        if os.getenv("OKX_SIGNAL_RECORD_PAPER", "false").lower() == "true":
            state["positions"][token["key"]] = position
            save_state(state)
        return

    sig, confirmed = swap_with_retry(kp, cfg, quote, token['symbol'], token['mint'], label="buy")
    position["buy_sig"] = sig
    position["buy_confirmed"] = confirmed
    actual_held = wait_for_token_holding(owner, token["mint"], cfg, min_amount=1, attempts=10) if confirmed else 0
    if actual_held > 0:
        position["confirmed_token_raw_amount"] = actual_held
    elif confirmed:
        position["pending_holding_confirmation"] = True
        log(f"[BUY-WARN] tx sent but token holding not confirmed yet {token['symbol']} {token['mint']} sig={sig}")
    else:
        # Buy failed — do NOT create a position entry. Log and return.
        log(f"[BUY-FAIL] 所有重试均失败 {token['symbol']} {token['mint']} sig={sig}")
        state["txs"].append({"time": utc_now(), "type": "buy_failed", "mint": token["mint"], "sig": sig, "sol_lamports": lamports_in, "token_raw": out_amount, "confirmed": False, "held_raw": 0})
        save_state(state)
        return
    state["positions"][token["key"]] = position
    state["txs"].append({"time": utc_now(), "type": "buy", "mint": token["mint"], "sig": sig, "sol_lamports": lamports_in, "token_raw": out_amount, "confirmed": confirmed, "held_raw": actual_held})
    save_state(state)
    log(f"[LIVE-BUY] {token['symbol']} {token['mint']} sig={sig} confirmed={confirmed}")
    notify_telegram(
        "🟢 <b>OKX Signal 实盘买入</b>\n"
        f"Token: <b>{tg_escape(token['symbol'])}</b>\n"
        f"Name: {tg_escape(token['name'])}\n"
        f"Mint: <code>{tg_escape(token['mint'])}</code>\n"
        f"买入金额: <b>{cfg.buy_sol} SOL</b>\n"
        f"预计收到(raw): <code>{out_amount}</code>\n"
        f"Signal Label: {tg_escape(token.get('signal_label'))}\n"
        f"当前MCap: {tg_escape(token.get('current_mcap'))}\n"
        f"TX: <code>{tg_escape(sig)}</code>\n"
        f"确认: {'✅' if confirmed else '❌'}\n"
        f"时间: {utc_now()}"
    )


TP_COOLDOWN_UNTIL = 0.0
TP_COOLDOWN_REASON = ""


def is_jupiter_429_error(e: Exception) -> bool:
    return "Jupiter quote HTTP 429" in str(e) or "Rate limit exceeded" in str(e)


def rank_positions_for_tp(owner: str, cfg: Config, state: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any], int, int]]:
    """Return unsold live positions ranked by current wallet value in USDT (via DexScreener + Binance SOL price).

    Uses fresh DexScreener priceNative (no 429 risk) instead of stale cached
    Jupiter values.  This ensures tokens that pumped 10x since last TP check
    still rank at the top.
    """
    # Step 1: Get on-chain holdings with decimals
    holdings = get_token_accounts_with_decimals(owner, cfg)  # {mint: (raw, dec)}

    # Step 2: Build eligible candidate list, deduplicate by mint (keep highest value)
    by_mint: Dict[str, Tuple[str, Dict[str, Any], int, int]] = {}
    for key, pos in list(state.get("positions", {}).items()):
        # Don't filter half_sold here — include all live positions for ranking.
        # TP sell logic already has its own half_sold safety check.
        if not pos.get("live_bought"):
            continue
        # Skip unconfirmed buys (legacy entries from before the fix)
        if pos.get("buy_confirmed") is False:
            continue
        mint = pos.get("mint")
        if not mint:
            continue
        held_info = holdings.get(mint)
        if not held_info:
            continue
        held_raw, decimals = held_info
        if held_raw <= 0:
            continue
        entry_raw = int(pos.get("entry_token_raw_amount") or pos.get("confirmed_token_raw_amount") or 0)
        entry_sol = int(pos.get("entry_sol_lamports") or 0)
        if entry_raw <= 0 or entry_sol <= 0:
            continue
        # Keep only one entry per mint (the one with most held_raw)
        existing = by_mint.get(mint)
        if existing is None or held_raw > existing[2]:
            by_mint[mint] = (key, pos, held_raw, entry_raw)

    candidates_raw = []
    for mint, (key, pos, held_raw, entry_raw) in by_mint.items():
        candidates_raw.append((key, pos, held_raw, entry_raw, mint))

    if not candidates_raw:
        return []

    # Step 3: Batch-query DexScreener for fresh prices + get SOL/USDT price
    unique_mints = list(set(c[4] for c in candidates_raw))
    price_map = dexscreener_price_map(unique_mints)
    sol_usdt_price = get_sol_usdt_price()
    dex_miss_count = sum(1 for c in candidates_raw if c[4] not in price_map)
    log(f"[TP-RANK] dexscreener got {len(price_map)}/{len(unique_mints)} prices, SOL/USDT={sol_usdt_price:.2f}, dex_miss={dex_miss_count}")

    # Step 4: Compute live value for each candidate in USDT
    # For DexScreener misses that have never been TP-checked, use Jupiter quote as fallback
    jup_fallback_count = 0
    candidates: List[Tuple[str, Dict[str, Any], int, int]] = []
    for key, pos, held_raw, entry_raw, mint in candidates_raw:
        entry_sol = int(pos.get("entry_sol_lamports") or 0)
        # Get decimals from holdings (already fetched)
        _, decimals = holdings.get(mint, (0, 6))
        price_native = price_map.get(mint, 0.0)
        if price_native > 0:
            # value_lamports = held_raw * priceNative / 10^decimals * 10^9
            # Use float to avoid overflow
            current_value_lamports = int(held_raw * price_native / (10 ** decimals) * 1e9)
            # Convert to USDT: lamports -> SOL -> USDT
            current_value_usdt = current_value_lamports / 1e9 * sol_usdt_price if sol_usdt_price > 0 else current_value_lamports
        else:
            # DexScreener miss: try Jupiter quote for accurate ranking
            cached_val = int(pos.get("last_tp_value_lamports") or 0)
            if cached_val > 0:
                current_value_lamports = cached_val
            elif jup_fallback_count < 15:  # Rate limit: max 15 Jupiter quotes per round
                try:
                    q = jup_quote(mint, SOL_MINT, entry_raw, cfg)
                    jup_val = int(q.get("outAmount", "0"))
                    if jup_val > 0:
                        current_value_lamports = int(jup_val * held_raw / entry_raw) if entry_raw > 0 else entry_sol
                        jup_fallback_count += 1
                    else:
                        current_value_lamports = entry_sol
                except Exception:
                    current_value_lamports = entry_sol
            else:
                current_value_lamports = entry_sol
            current_value_usdt = current_value_lamports / 1e9 * sol_usdt_price if sol_usdt_price > 0 else current_value_lamports
        pos["rank_value_lamports"] = current_value_lamports
        pos["rank_value_usdt"] = current_value_usdt
        candidates.append((key, pos, held_raw, entry_raw))

    if jup_fallback_count > 0:
        log(f"[TP-RANK] jupiter fallback used for {jup_fallback_count} positions")

    # Sort by USDT value (desc), then held_raw (desc)
    candidates.sort(key=lambda x: (float(x[1].get("rank_value_usdt") or 0), x[2]), reverse=True)
    save_state(state)
    return candidates


def maybe_take_profit(kp: Keypair, cfg: Config, live: bool, state: Dict[str, Any]) -> None:
    global TP_COOLDOWN_UNTIL, TP_COOLDOWN_REASON
    now = time.time()
    if now < TP_COOLDOWN_UNTIL:
        left = int(TP_COOLDOWN_UNTIL - now)
        log(f"[TP-COOLDOWN] skip left={left}s reason={TP_COOLDOWN_REASON}")
        return
    owner = str(kp.pubkey())
    try:
        candidates = rank_positions_for_tp(owner, cfg, state)
    except Exception as e:
        log(f"[TP-RANK-ERR] 钱包持仓扫描失败，跳过本轮TP检查: {e}")
        if "429" in str(e) or "Too many requests" in str(e):
            TP_COOLDOWN_UNTIL = time.time() + max(30, cfg.tp_429_cooldown_seconds)
            TP_COOLDOWN_REASON = "RPC429 during TP wallet scan"
            log(f"[TP-COOLDOWN-SET] seconds={cfg.tp_429_cooldown_seconds} reason={TP_COOLDOWN_REASON}")
        return
    total_candidates = len(candidates)
    if cfg.tp_top_n > 0:
        candidates = candidates[:cfg.tp_top_n]
    log(f"[TP-RANK] checking_top={len(candidates)} total_eligible={total_candidates} top_n={cfg.tp_top_n}")
    for key, pos, held_raw, entry_raw in candidates:
        mint = pos["mint"]
        entry_sol = int(pos["entry_sol_lamports"])
        # 先只用记录的 entry_raw 做 Jupiter quote 判断是否达到 2x；不要每轮先扫链上持仓，
        # 否则 Solana public RPC 429 会让 TP loop 卡数分钟，并影响页面监听进程资源。
        try:
            q = jup_quote(mint, SOL_MINT, entry_raw, cfg)
            current_sol_for_entry_raw = int(q.get("outAmount", "0"))
        except Exception as e:
            log(f"[TP-CHECK-ERR] {pos.get('symbol')} quote失败: {e}")
            if is_jupiter_429_error(e):
                TP_COOLDOWN_UNTIL = time.time() + max(30, cfg.tp_429_cooldown_seconds)
                TP_COOLDOWN_REASON = f"Jupiter429 during TP check {pos.get('symbol')}"
                log(f"[TP-COOLDOWN-SET] seconds={cfg.tp_429_cooldown_seconds} reason={TP_COOLDOWN_REASON}; stop current TP round")
                return
            continue
        ratio = Decimal(current_sol_for_entry_raw) / Decimal(entry_sol) if entry_sol else Decimal(0)
        current_sol_for_held_raw = int(Decimal(current_sol_for_entry_raw) * Decimal(held_raw) / Decimal(entry_raw)) if entry_raw else 0
        pos["last_tp_value_lamports"] = current_sol_for_held_raw
        pos["last_tp_ratio"] = str(ratio)
        pos["last_tp_check_time"] = utc_now()
        save_state(state)
        log(f"[TP-CHECK] {pos.get('symbol')} ratio={ratio:.3f} value≈{current_sol_for_held_raw/1e9:.6f}SOL target={cfg.tp_multiple}")
        if ratio < cfg.tp_multiple:
            continue

        # Safety: re-check half_sold before selling (may have been set by earlier iteration)
        if pos.get("half_sold") or pos.get("sell_sig"):
            log(f"[TP-SKIP] {pos.get('symbol')} already half_sold or has sell_sig, skipping")
            continue

        # 只有真正达到止盈线时，才查询当前链上持仓来计算卖出50%；RPC失败则用记录数量兜底。
        try:
            held_raw = int(get_mint_holding(owner, mint, cfg) or 0)
        except Exception as e:
            log(f"[TP-HOLDING-WARN] {pos.get('symbol')} 当前持仓查询失败，使用记录数量估算: {e}")
            held_raw = 0
        if held_raw <= 0:
            held_raw = int(pos.get("confirmed_token_raw_amount") or pos.get("entry_token_raw_amount") or 0)
            if held_raw <= 0:
                log(f"[TP-CHECK-SKIP] 钱包无持仓且无记录数量 {pos.get('symbol')} {mint}")
                continue
        sell_amount = int(Decimal(held_raw) * cfg.sell_fraction)
        if sell_amount <= 0:
            continue
        try:
            quote = jup_quote(mint, SOL_MINT, sell_amount, cfg)
            out_sol = int(quote.get("outAmount", "0"))
        except Exception as e:
            log(f"[TP-SELL-QUOTE-ERR] {pos.get('symbol')} quote失败: {e}")
            if is_jupiter_429_error(e):
                TP_COOLDOWN_UNTIL = time.time() + max(30, cfg.tp_429_cooldown_seconds)
                TP_COOLDOWN_REASON = f"Jupiter429 during TP sell quote {pos.get('symbol')}"
                log(f"[TP-COOLDOWN-SET] seconds={cfg.tp_429_cooldown_seconds} reason={TP_COOLDOWN_REASON}; stop current TP round")
                return
            continue
        if not live:
            log(f"[DRY-SELL-50%] {pos.get('symbol')} 已达2x，拟卖 raw={sell_amount} -> {out_sol/1e9:.6f} SOL；未下单")
            pos["half_sold"] = True
            pos["half_sold_time"] = utc_now()
            pos["dry_sell_out_sol_lamports"] = out_sol
            save_state(state)
            continue

        # 先标记 half_sold=True 防止重复卖出，如果失败会重置
        pos["half_sold"] = True
        pos["half_sold_time"] = utc_now()
        pos["sell_confirmed"] = None
        pos["sell_sig"] = None
        pos["sell_raw_amount"] = sell_amount
        pos["sell_out_sol_lamports_quote"] = out_sol
        save_state(state)

        sig, confirmed = swap_with_retry(kp, cfg, quote, pos.get('symbol', ''), mint, label="sell")

        if not confirmed:
            # 所有重试均失败，重置 half_sold 允许下轮重试
            pos["half_sold"] = False
            pos["half_sold_time"] = None
            pos["sell_confirmed"] = False
            pos["sell_sig"] = sig
            save_state(state)
            log(f"[SELL-FAIL] 所有重试均失败 {pos.get('symbol')} {mint} sig={sig}，已重置 half_sold")
            notify_telegram(
                "🔴 <b>OKX Signal 止盈卖出失败</b>\n"
                f"Token: <b>{tg_escape(pos.get('symbol'))}</b>\n"
                f"Mint: <code>{tg_escape(mint)}</code>\n"
                f"已重置，下轮将自动重试\n"
                f"TX: <code>{tg_escape(sig or 'N/A')}</code>\n"
                f"时间: {utc_now()}"
            )
            continue

        # 卖出成功
        pos["sell_confirmed"] = True
        pos["sell_sig"] = sig
        for tx in reversed(state.get("txs", [])):
            if tx.get("type") == "sell50" and tx.get("sig") == sig:
                tx["confirmed"] = True
                break
        state["txs"].append({
            "time": utc_now(),
            "type": "sell50",
            "mint": mint,
            "sig": sig,
            "raw": sell_amount,
            "out_sol_lamports_quote": out_sol,
            "confirmed": True,
        })
        save_state(state)
        log(f"[LIVE-SELL-50%] {pos.get('symbol')} sig={sig} confirmed=True")
        notify_telegram(
            "🔵 <b>OKX Signal 2x止盈卖出50%</b>\n"
            f"Token: <b>{tg_escape(pos.get('symbol'))}</b>\n"
            f"Mint: <code>{tg_escape(mint)}</code>\n"
            f"卖出比例: <b>50%</b>\n"
            f"卖出raw数量: <code>{sell_amount}</code>\n"
            f"预计收到: <b>{out_sol/1e9:.6f} SOL</b>\n"
            f"触发倍数: {ratio:.3f}x\n"
            f"TX: <code>{tg_escape(sig)}</code>\n"
            f"时间: {utc_now()}"
        )



def parse_okx_activity_token(activity: Dict[str, Any], token_infos: Dict[str, Any], fallback_meta: Dict[str, Dict[str, Any]], *, source_prefix: str = "ws", source_name: str = "okx_ws_signalActivity") -> Optional[Dict[str, Any]]:
    """Parse one OKX WS signalActivity item into the token dict used by buy_token().

    OKX 的 signalActivity schema 不是公开 API；前端代码显示 activityList 内字段包含
    batchId/batchIndex/eventTime/id/signalLabel/tokenKey，tokenInfo 是按 tokenKey 索引的 map。
    这里兼容直接字段、tokenKey->tokenInfo，以及 gems-list metadata fallback。
    """
    token_key = str(activity.get("tokenKey") or activity.get("token_key") or activity.get("tokenId") or activity.get("id") or "")
    ti = {}
    if token_key and isinstance(token_infos, dict):
        ti = token_infos.get(token_key) or token_infos.get(str(token_key)) or {}
    mint = (
        activity.get("tokenContractAddress")
        or activity.get("tokenAddress")
        or activity.get("contractAddress")
        or activity.get("mint")
        or ti.get("tokenContractAddress")
        or ti.get("tokenAddress")
        or ti.get("contractAddress")
    )
    if not mint:
        return None
    mint = str(mint)
    meta = fallback_meta.get(mint, {})
    chain_id = str(activity.get("chainId") or ti.get("chainId") or meta.get("chain_id") or "501")
    if chain_id != "501":
        return None
    event_time_raw = activity.get("eventTime") or activity.get("time") or activity.get("timestamp") or activity.get("createdTime")
    event_ms: Optional[int] = None
    try:
        if event_time_raw is not None and str(event_time_raw) != "":
            event_ms = int(float(str(event_time_raw)))
            if event_ms < 10_000_000_000:
                event_ms *= 1000
    except Exception:
        event_ms = None
    event_id = str(
        activity.get("eventId")
        or activity.get("id")
        or (f"{activity.get('batchId')}_{activity.get('batchIndex')}" if activity.get("batchId") is not None else "")
        or f"{mint}:{event_ms or int(time.time()*1000)}:{activity.get('signalLabel') or activity.get('signalType') or ''}"
    )
    key = f"{source_prefix}:{chain_id}:{mint}:{event_id}"
    return {
        "key": key,
        "mint": mint,
        "chain_id": chain_id,
        "symbol": ti.get("tokenSymbol") or ti.get("symbol") or meta.get("symbol") or "?",
        "name": ti.get("tokenName") or ti.get("name") or meta.get("name") or "?",
        "first_signal_time": str(event_time_raw or ""),
        "first_signal_ms": event_ms,
        "first_signal_mcap": str(activity.get("firstSignalMcap") or meta.get("first_signal_mcap") or ""),
        "current_mcap": str(activity.get("mcap") or ti.get("mcap") or meta.get("current_mcap") or ""),
        "signal_label": str(activity.get("signalLabel") or activity.get("signalType") or ""),
        "source": source_name,
        "event_id": event_id,
        "raw": activity,
    }


def build_gems_metadata() -> Dict[str, Dict[str, Any]]:
    meta: Dict[str, Dict[str, Any]] = {}
    try:
        for token in [p for p in (parse_gem(g) for g in fetch_okx_gems()) if p]:
            meta[token["mint"]] = token
    except Exception as e:
        log(f"[META-WARN] gems-list metadata fallback failed: {e}")
    return meta


def tokens_from_okx_signal_message(msg: Dict[str, Any], fallback_meta: Dict[str, Dict[str, Any]], *, source_prefix: str, source_name: str) -> List[Dict[str, Any]]:
    """Extract signalActivity tokens from an OKX Signal WS/browser frame.

    Page mode only feeds this with websocket frames actually received by the
    rendered OKX Signal webpage, so the trigger semantics are "webpage push".
    """
    out: List[Dict[str, Any]] = []
    data = msg.get("data") or []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        typ = item.get("type")
        if typ != "signalActivity":
            continue
        content = item.get("content") or {}
        activity_list = content.get("activityList") or content.get("activities") or []
        token_infos = content.get("tokenInfo") or content.get("tokenInfos") or {}
        log(f"[SIGNAL-FRAME] source={source_name} signalActivity count={len(activity_list)}")
        for act in activity_list:
            if isinstance(act, dict):
                token = parse_okx_activity_token(act, token_infos, fallback_meta, source_prefix=source_prefix, source_name=source_name)
                if token:
                    out.append(token)
                else:
                    log(f"[SIGNAL-SKIP] source={source_name} cannot parse activity: {json.dumps(act, ensure_ascii=False)[:500]}")
    return out


def iter_okx_ws_tokens(cfg: Config, deadline: Optional[float] = None):
    fallback_meta = build_gems_metadata()
    last_meta_refresh = time.time()
    while True:
        if deadline and time.time() >= deadline:
            return
        ws = None
        try:
            ws = websocket.create_connection(
                OKX_WS_URL,
                header=["Origin: https://web3.okx.com", "User-Agent: Mozilla/5.0 OKX-Signal-AutoBuy/1.0"],
                timeout=20,
            )
            ws.settimeout(5)
            sub = {"op": "subscribe", "args": [{"channel": OKX_WS_CHANNEL, "chainId": 501}]}
            ws.send(json.dumps(sub, separators=(",", ":")))
            log(f"[WS] connected url={OKX_WS_URL} channel={OKX_WS_CHANNEL}")
            while True:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    if deadline and time.time() >= deadline:
                        return
                    try:
                        ws.send("ping")
                    except Exception:
                        raise
                    continue
                if not raw:
                    continue
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", "replace")
                if raw in ("pong", "ping"):
                    continue
                try:
                    msg = json.loads(raw)
                except Exception:
                    log(f"[WS-RAW] {str(raw)[:300]}")
                    continue
                if msg.get("event") == "subscribe":
                    log(f"[WS-SUB] {msg.get('arg')}")
                    continue
                if msg.get("event") == "error":
                    log(f"[WS-ERR] {msg}")
                    break
                data = msg.get("data") or []
                if time.time() - last_meta_refresh > 300:
                    fallback_meta = build_gems_metadata()
                    last_meta_refresh = time.time()
                for token in tokens_from_okx_signal_message(msg, fallback_meta, source_prefix="ws", source_name="okx_ws_signalActivity"):
                    yield token
        except Exception as e:
            log(f"[WS-LOOP-ERR] {type(e).__name__}: {e}; reconnect in 5s")
            time.sleep(5)
        finally:
            try:
                if ws is not None:
                    ws.close()
            except Exception:
                pass


def handle_token_signal(token: Dict[str, Any], kp: Keypair, cfg: Config, live: bool, state: Dict[str, Any], holding_amount: int, live_open: int, manual: bool = False) -> int:
    key = token["key"]
    if key in state["seen"]:
        return live_open
    state["seen"][key] = {"first_seen_local": utc_now(), **{k: token.get(k) for k in ["mint", "symbol", "name", "first_signal_time", "signal_label", "source", "event_id"]}}
    save_state(state)
    age = signal_age_seconds(token)
    age_text = "unknown" if age is None else f"{age:.1f}s"
    source = token.get("source") or "okx_signal"
    log(f"[NEW] source={source} {token['symbol']} {token['mint']} label={token.get('signal_label')} event_id={token.get('event_id')} okx_time={fmt_signal_time(token)} age={age_text}")
    if age is None:
        log(f"[SKIP] 信号缺少 eventTime，不买入 {token['symbol']} {token['mint']} source={source}")
        return live_open
    if age < -30:
        log(f"[SKIP] eventTime 在未来，疑似时间异常，不买入 {token['symbol']} age={age_text} source={source}")
        return live_open
    if age > cfg.max_signal_age_seconds:
        log(f"[SKIP] 非实时新信号: {token['symbol']} eventTime={fmt_signal_time(token)} age={age_text} > {cfg.max_signal_age_seconds}s，不买入 source={source}")
        return live_open
    if holding_amount > 0:
        state["skipped_holdings"][key] = {"time": utc_now(), "reason": "already_holding", "raw_amount": holding_amount, "symbol": token["symbol"]}
        save_state(state)
        log(f"[SKIP] 已持仓，不重复买入 {token['symbol']} {token['mint']} raw={holding_amount}")
        return live_open

    # Mint-level duplicate check: skip if we already have an active position
    # for the same mint (different signal events have different keys).
    mint = token.get("mint")
    if mint:
        for _pk, _pos in state.get("positions", {}).items():
            if _pos.get("mint") == mint and _pos.get("live_bought") and not _pos.get("half_sold") and not _pos.get("sell_sig"):
                state["skipped_holdings"][key] = {"time": utc_now(), "reason": "already_in_positions", "existing_key": _pk[:40], "symbol": token["symbol"]}
                save_state(state)
                log(f"[SKIP] 已有活跃持仓，不重复买入 {token['symbol']} {mint} existing={_pk[:40]}")
                return live_open

    if live and cfg.max_open_positions > 0 and live_open >= cfg.max_open_positions:
        log(f"[SKIP] 达到最大实盘持仓数 {cfg.max_open_positions}: {token['symbol']}")
        return live_open

    # Auto-buy disabled: only send analysis to Telegram for manual review
    try:
        analysis = gather_token_analysis(token, cfg)
        score = calculate_meme_score(analysis)
        message = format_analysis_message(analysis, score, cfg)
        msg_id = notify_telegram_with_keyboard(message, mint or "", name=token.get("symbol", ""))
        if msg_id:
            with PENDING_LOCK:
                PENDING_CONFIRMS[key] = {
                    "token": token, "analysis": analysis, "score": score,
                    "msg_id": msg_id, "timestamp": time.time(),
                }
            log(f"[MANUAL-SENT] {token['symbol']} {mint[:16] if mint else '?'} score={score['total']}/{score['max']} msg_id={msg_id}")
        else:
            log(f"[MANUAL-ERR] Telegram发送失败 {token['symbol']}")
    except Exception as e:
        log(f"[MANUAL-ERR] {token['symbol']} {type(e).__name__}: {e}")
    return live_open


def ws_loop(kp: Keypair, cfg: Config, live: bool, state: Dict[str, Any], max_new: int = 20, ws_seconds: int = 0) -> None:
    owner = str(kp.pubkey())
    deadline = time.time() + ws_seconds if ws_seconds > 0 else None
    processed = 0
    while True:
        if deadline and time.time() >= deadline:
            log(f"[WS-EXIT] reached ws_seconds={ws_seconds}")
            return
        live_open = sum(1 for p in state.get("positions", {}).values() if p.get("live_bought") and not p.get("half_sold"))
        try:
            sol_bal = get_sol_balance_lamports(owner, cfg)
            sol_text = f"{sol_bal/1e9:.9f}"
        except Exception as e:
            sol_text = f"unknown({type(e).__name__})"
        # 不在 WS 启动前全量扫 token accounts：公共 RPC 容易 429，且会阻塞实时订阅。
        # 持仓只在真正 signalActivity 到达、准备买入前即时检查。
        log(f"[STATUS] wallet={owner} SOL={sol_text} live_open={live_open} live={live} source=ws")
        for token in iter_okx_ws_tokens(cfg, deadline=deadline):
            holding_amount = 0
            age = signal_age_seconds(token)
            if age is not None and -30 <= age <= cfg.max_signal_age_seconds:
                holding_amount = get_mint_holding(owner, token["mint"], cfg)
            live_open = handle_token_signal(token, kp, cfg, live, state, holding_amount, live_open)
            processed += 1
            maybe_take_profit(kp, cfg, live, state)
            if processed >= max_new:
                log(f"[WS-EXIT] reached max_new={max_new}")
                return
            if deadline and time.time() >= deadline:
                log(f"[WS-EXIT] reached ws_seconds={ws_seconds}")
                return
        if deadline and time.time() >= deadline:
            log(f"[WS-EXIT] reached ws_seconds={ws_seconds}")
            return

def page_loop(kp: Keypair, cfg: Config, live: bool, state: Dict[str, Any], max_new: int = 20, page_seconds: int = 0, manual: bool = False) -> None:
    """Open the real OKX Signal webpage and buy on websocket frames received by that page.

    This is intentionally different from --source ws: the trigger is not our
    standalone anonymous WS client; it is the WebSocket traffic observed from the
    rendered https://web3.okx.com/zh-hans/signal page itself.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError(f"Playwright not available: {type(e).__name__}: {e}")

    owner = str(kp.pubkey())
    deadline = time.time() + page_seconds if page_seconds > 0 else None
    token_q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
    fallback_meta = build_gems_metadata()
    last_meta_refresh = time.time()
    processed = 0

    # Start callback polling thread in manual mode
    if manual:
        threading.Thread(target=callback_polling_loop, args=(kp, cfg, live, state), daemon=True).start()
        log("[MANUAL] 已启动 Telegram 回调监听，等待用户确认买入")

    def on_ws(ws):
        log(f"[PAGE-WS] open url={ws.url}")

        def on_frame(payload: str) -> None:
            nonlocal fallback_meta, last_meta_refresh
            if not payload or payload in ("ping", "pong"):
                return
            s = payload.decode("utf-8", "replace") if isinstance(payload, bytes) else str(payload)
            if "signalActivity" not in s:
                return
            try:
                msg = json.loads(s)
            except Exception:
                log(f"[PAGE-WS-RAW] {s[:500]}")
                return
            if time.time() - last_meta_refresh > 300:
                fallback_meta = build_gems_metadata()
                last_meta_refresh = time.time()
            for token in tokens_from_okx_signal_message(msg, fallback_meta, source_prefix="page", source_name="okx_page_ws_signalActivity"):
                token_q.put(token)

        ws.on("framereceived", on_frame)

    def run_buy_flow(token: Dict[str, Any]) -> None:
        """Run slow RPC/Jupiter work outside Playwright's WS callback loop."""
        nonlocal processed, last_tp_check
        # Fresh signal buy has absolute priority over TP scanning. Move the TP
        # timer forward before doing RPC/Jupiter work so a scheduled TP thread
        # cannot start at the same moment and consume quote quota first.
        last_tp_check = time.time()
        live_open = sum(1 for p0 in state.get("positions", {}).values() if p0.get("live_bought") and not p0.get("half_sold"))
        holding_amount = 0
        age = signal_age_seconds(token)
        if age is not None and -30 <= age <= cfg.max_signal_age_seconds:
            holding_amount = get_mint_holding(owner, token["mint"], cfg)
        handle_token_signal(token, kp, cfg, live, state, holding_amount, live_open, manual=manual)
        processed += 1
        # Do not run full-wallet TP scan after every page signal; public RPC can block the realtime path.
        # TP checks are better handled by a separate slower monitor or a timed non-blocking loop.

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        page.on("websocket", on_ws)
        log(f"[PAGE] opening https://web3.okx.com/zh-hans/signal live={live}")
        page.goto("https://web3.okx.com/zh-hans/signal", wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass
        title = page.title()
        body_text = ""
        try:
            body_text = page.locator("body").inner_text(timeout=10000)[:300]
        except Exception as e:
            body_text = f"body_text_error={type(e).__name__}: {e}"
        log(f"[PAGE] ready title={title!r} text={body_text!r}")
        if "信号" not in title and "金狗" not in body_text and "聪明钱" not in body_text:
            log("[PAGE-WARN] 页面文本未确认 OKX Signal UI，继续监听 websocket，但请检查页面是否被风控/改版")

        last_tp_check = 0.0
        tp_running = False

        def run_tp_check() -> None:
            nonlocal tp_running, last_tp_check
            try:
                maybe_take_profit(kp, cfg, live, state)
            except Exception as e:
                log(f"[TP-LOOP-ERR] {type(e).__name__}: {e}")
            finally:
                last_tp_check = time.time()
                tp_running = False

        while True:
            now = time.time()
            if live and cfg.tp_check_seconds > 0 and not tp_running and now - last_tp_check >= cfg.tp_check_seconds:
                tp_running = True
                threading.Thread(target=run_tp_check, daemon=True).start()
            if deadline and time.time() >= deadline:
                log(f"[PAGE-EXIT] reached page_seconds={page_seconds}")
                return
            try:
                token = token_q.get(timeout=1)
            except queue.Empty:
                page.wait_for_timeout(250)
                continue
            threading.Thread(target=run_buy_flow, args=(token,), daemon=True).start()
            if processed >= max_new:
                log(f"[PAGE-EXIT] reached max_new={max_new}")
                return


def scan_once(kp: Keypair, cfg: Config, live: bool, state: Dict[str, Any], max_new: int = 20) -> None:
    owner = str(kp.pubkey())
    sol_bal = get_sol_balance_lamports(owner, cfg)
    holdings = get_token_accounts(owner, cfg)
    live_open = sum(1 for p in state.get("positions", {}).values() if p.get("live_bought") and not p.get("half_sold"))
    log(f"[STATUS] wallet={owner} SOL={sol_bal/1e9:.9f} token_holdings={len(holdings)} live_open={live_open} live={live}")

    gems = fetch_okx_gems()
    parsed = [p for p in (parse_gem(g) for g in gems) if p]
    log(f"[OKX] fetched_gems={len(gems)} solana_parsed={len(parsed)}")

    new_count = 0
    for token in parsed:
        key = token["key"]
        if key in state["seen"]:
            continue
        state["seen"][key] = {"first_seen_local": utc_now(), **{k: token[k] for k in ["mint", "symbol", "name", "first_signal_time", "signal_label"]}}
        save_state(state)
        new_count += 1
        age = signal_age_seconds(token)
        age_text = "unknown" if age is None else f"{age:.1f}s"
        log(f"[NEW] {token['symbol']} {token['mint']} label={token['signal_label']} mcap={token['current_mcap']} okx_time={fmt_signal_time(token)} age={age_text}")

        if age is None:
            log(f"[SKIP] 缺少OKX firstSignalTime，不买入 {token['symbol']} {token['mint']}")
            continue
        if age < -30:
            log(f"[SKIP] OKX firstSignalTime 在未来，疑似时间异常，不买入 {token['symbol']} age={age_text}")
            continue
        if age > cfg.max_signal_age_seconds:
            log(f"[SKIP] 非实时新信号: {token['symbol']} OKX信号时间={fmt_signal_time(token)} age={age_text} > {cfg.max_signal_age_seconds}s，不买入")
            continue

        if token["mint"] in holdings:
            state["skipped_holdings"][key] = {"time": utc_now(), "reason": "already_holding", "raw_amount": holdings[token["mint"]], "symbol": token["symbol"]}
            save_state(state)
            log(f"[SKIP] 已持仓，不重复买入 {token['symbol']} {token['mint']} raw={holdings[token['mint']]}")
            continue

        # Mint-level duplicate check
        _mint = token.get("mint")
        _already_active = False
        if _mint:
            for _pk, _pos in state.get("positions", {}).items():
                if _pos.get("mint") == _mint and _pos.get("live_bought") and not _pos.get("half_sold") and not _pos.get("sell_sig"):
                    state["skipped_holdings"][key] = {"time": utc_now(), "reason": "already_in_positions", "existing_key": _pk[:40], "symbol": token["symbol"]}
                    save_state(state)
                    log(f"[SKIP] 已有活跃持仓，不重复买入 {token['symbol']} {_mint} existing={_pk[:40]}")
                    _already_active = True
                    break
        if _already_active:
            continue

        if live and cfg.max_open_positions > 0 and live_open >= cfg.max_open_positions:
            log(f"[SKIP] 达到最大实盘持仓数 {cfg.max_open_positions}: {token['symbol']}")
            continue
        try:
            buy_token(token, kp, cfg, live, state)
            if live:
                live_open += 1
        except Exception as e:
            log(f"[BUY-ERR] {token['symbol']} {token['mint']} {type(e).__name__}: {e}")
        if new_count >= max_new:
            break

    maybe_take_profit(kp, cfg, live, state)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="只扫描一次")
    ap.add_argument("--live", action="store_true", help="允许实盘；仍需.env OKX_SIGNAL_LIVE_TRADING=true")
    ap.add_argument("--max-new", type=int, default=20, help="单次最多处理几个新token")
    ap.add_argument("--reset-seen", action="store_true", help="清空seen；危险，仅测试用")
    ap.add_argument("--warmup-seen", action="store_true", help="把当前OKX列表全部标记为已见，不买入；用于开实盘前避免买历史信号")
    ap.add_argument("--source", choices=["page", "ws", "polling"], default=os.getenv("OKX_SIGNAL_SOURCE", "page"), help="信号源：page=打开OKX网页并按页面WS推送触发；ws=匿名WS；polling仅测试/metadata fallback")
    ap.add_argument("--ws-seconds", type=int, default=0, help="WS/page dry-run/测试运行秒数；0表示持续运行")
    ap.add_argument("--manual", action="store_true", help="手动确认模式：信号触发后推送分析到TG，等待用户点击确认/放弃")
    args = ap.parse_args()

    ensure_dirs()
    cfg = load_config()
    kp = load_keypair()
    live = bool(args.live and cfg.live_env)
    if args.live and not cfg.live_env:
        log("[SAFE] 你传了--live，但.env里 OKX_SIGNAL_LIVE_TRADING 不是 true，所以仍然DRY-RUN")
    log(f"[BOOT] pubkey={kp.pubkey()} live={live} manual={args.manual} buy_sol={cfg.buy_sol} poll={cfg.poll_seconds}s slippage_bps={cfg.slippage_bps} max_signal_age={cfg.max_signal_age_seconds}s tp_check={cfg.tp_check_seconds}s tp_top_n={cfg.tp_top_n}")
    state = load_state()
    if args.reset_seen:
        state["seen"] = {}
        save_state(state)
        log("[RESET] seen cleared")
    if args.warmup_seen:
        gems = fetch_okx_gems()
        n = 0
        for token in [p for p in (parse_gem(g) for g in gems) if p]:
            key = token["key"]
            if key not in state["seen"]:
                state["seen"][key] = {"first_seen_local": utc_now(), **{k: token[k] for k in ["mint", "symbol", "name", "first_signal_time", "signal_label"]}}
                n += 1
        save_state(state)
        log(f"[WARMUP] 当前OKX列表已标记为seen: added={n}; 不执行买入")
        if args.once:
            return 0

    if args.source == "page":
        try:
            page_seconds = args.ws_seconds if args.ws_seconds > 0 else (30 if args.once else 0)
            page_loop(kp, cfg, live, state, max_new=args.max_new, page_seconds=page_seconds, manual=args.manual)
            return 0
        except KeyboardInterrupt:
            log("[STOP] KeyboardInterrupt")
            return 0

    if args.source == "ws":
        try:
            ws_seconds = args.ws_seconds if args.ws_seconds > 0 else (30 if args.once else 0)
            ws_loop(kp, cfg, live, state, max_new=args.max_new, ws_seconds=ws_seconds)
            return 0
        except KeyboardInterrupt:
            log("[STOP] KeyboardInterrupt")
            return 0

    if live:
        log("[SAFE] polling/gems-list 不是实时权威信号源，禁止 live 买入；请使用 --source ws")
        live = False
    while True:
        try:
            scan_once(kp, cfg, live, state, max_new=args.max_new)
        except KeyboardInterrupt:
            log("[STOP] KeyboardInterrupt")
            return 0
        except Exception as e:
            log(f"[LOOP-ERR] {type(e).__name__}: {e}")
        if args.once:
            return 0
        time.sleep(cfg.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())




