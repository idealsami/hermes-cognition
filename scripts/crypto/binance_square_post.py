#!/usr/bin/env python3
"""Binance Square auto-poster cron script.
Collects market data, generates analysis, posts to Binance Square.
Output is injected into the cron prompt as context.
"""
import json
import sys
import os

sys.path.insert(0, "/root/scripts/binance_square_poster")

from collector import collect_all
from content_generator_v7 import generate_post

def main():
    # Collect
    data = collect_all()
    
    # Generate
    post = generate_post(data)
    
    # Post
    api_key = os.environ.get("BINANCE_SQUARE_API_KEY", "").strip()
    
    result = {
        "chars": len(post),
        "fear_greed": data.get("fear_greed_index", {}).get("value"),
        "top_gainer": data.get("top_gainers", [{}])[0].get("symbol") if data.get("top_gainers") else None,
        "top_loser": data.get("top_losers", [{}])[0].get("symbol") if data.get("top_losers") else None,
        "has_api_key": bool(api_key),
    }
    
    if not api_key:
        result["status"] = "NO_API_KEY"
        result["message"] = "BINANCE_SQUARE_API_KEY not set. User needs to get API key from Binance Square Creator Center."
        print(json.dumps(result, ensure_ascii=False))
        return
    
    # Try to post
    try:
        from binance_square.client import post_text
        post_result = post_text(post, api_key=api_key)
        result["status"] = "SUCCESS" if post_result.success else "FAILED"
        result["post_url"] = post_result.post_url
        result["error"] = post_result.error_msg if not post_result.success else None
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)
    
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
