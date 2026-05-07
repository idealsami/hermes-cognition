#!/usr/bin/env python3
"""Binance USD-M current position fluctuation monitor.

Polls real futures positions and sends Telegram alerts when existing positions
move materially in PnL/ROE/price or when positions open/close.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE_URL = "https://fapi.binance.com"
CACHE_DIR = Path("/root/.hermes/cache/binance-position-monitor")
STATE_PATH = CACHE_DIR / "state.json"
LOG_PATH = CACHE_DIR / "monitor.log"
PID_PATH = CACHE_DIR / "monitor.pid"

POLL_SECONDS = 10
# Alert thresholds. These are intentionally moderate to avoid Telegram spam.
PRICE_MOVE_PCT = 0.8          # price move since last alert snapshot
PNL_MOVE_USDT = 8.0           # unrealized PnL move since last alert snapshot
ROE_MOVE_PCT = 10.0           # margin ROE move since last alert snapshot
ABS_LOSS_ROE_PCT = -30.0      # absolute danger threshold
ABS_PROFIT_ROE_PCT = 25.0     # absolute profit threshold
COOLDOWN_SECONDS = 300        # per symbol+reason


def now_ts() -> int:
    return int(time.time())


def log(msg: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    line = time.strftime("[%Y-%m-%d %H:%M:%S UTC] ", time.gmtime()) + msg
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    env_path = Path("/root/.hermes/.env")
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.strip())
    return env


def load_credentials() -> tuple[str, str]:
    env = load_env()
    key = env.get("BINANCE_API_KEY") or env.get("BINANCE_FUTURES_API_KEY") or ""
    secret = env.get("BINANCE_API_SECRET") or env.get("BINANCE_FUTURES_API_SECRET") or ""
    if not key or not secret:
        raise RuntimeError("missing Binance API credentials in /root/.hermes/.env")
    return key, secret


def signed_request(method: str, path: str, params: dict[str, Any], api_key: str, secret: str) -> Any:
    p = dict(params)
    p["timestamp"] = int(time.time() * 1000)
    p.setdefault("recvWindow", 5000)
    qs = urllib.parse.urlencode(p, doseq=True)
    sig = hmac.new(secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
    url = BASE_URL + path + "?" + qs + "&signature=" + sig
    req = urllib.request.Request(url, method=method, headers={"X-MBX-APIKEY": api_key, "User-Agent": "HermesPositionMonitor/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else None


def send_telegram(text: str, env: dict[str, str]) -> None:
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = next((x.strip() for x in env.get("TELEGRAM_ALLOWED_USERS", "").split(",") if x.strip()), "")
    if not token or not chat_id:
        raise RuntimeError("missing Telegram env")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(STATE_PATH)


def fmt(x: float, n: int = 4) -> str:
    return f"{x:.{n}f}"


def normalize_position(p: dict[str, Any]) -> dict[str, Any] | None:
    amt = float(p.get("positionAmt") or 0)
    if abs(amt) < 1e-12:
        return None
    symbol = p["symbol"]
    entry = float(p.get("entryPrice") or 0)
    mark = float(p.get("markPrice") or 0)
    upnl = float(p.get("unRealizedProfit") or 0)
    lev = float(p.get("leverage") or 1)
    notional = abs(float(p.get("notional") or (amt * mark)))
    side = "LONG" if amt > 0 else "SHORT"
    margin = notional / lev if lev else 0.0
    roe = (upnl / margin * 100) if margin else 0.0
    price_chg = ((mark - entry) / entry * 100 * (1 if amt > 0 else -1)) if entry else 0.0
    return {
        "symbol": symbol,
        "side": side,
        "amt": amt,
        "entry": entry,
        "mark": mark,
        "upnl": upnl,
        "lev": lev,
        "notional": notional,
        "margin": margin,
        "roe": roe,
        "price_chg": price_chg,
    }


def render_position(pos: dict[str, Any]) -> str:
    pnl = pos["upnl"]
    icon = "🟢" if pnl >= 0 else "🔴"
    return (
        f"{icon} **{pos['symbol']} {pos['side']}**\n"
        f"数量: `{pos['amt']}` | 杠杆: `{pos['lev']:.0f}x`\n"
        f"入场: `{fmt(pos['entry'])}` → 标记: `{fmt(pos['mark'])}`\n"
        f"价格变动: **{pos['price_chg']:+.2f}%** | ROE: **{pos['roe']:+.2f}%**\n"
        f"未实现盈亏: **{pnl:+.2f} USDT** | 名义: `{pos['notional']:.2f}U`"
    )


def can_alert(state: dict[str, Any], key: str) -> bool:
    last = state.setdefault("last_alert", {}).get(key, 0)
    return now_ts() - float(last or 0) >= COOLDOWN_SECONDS


def mark_alert(state: dict[str, Any], key: str) -> None:
    state.setdefault("last_alert", {})[key] = now_ts()


def build_alerts(positions: dict[str, dict[str, Any]], state: dict[str, Any], first_run: bool) -> list[tuple[str, str]]:
    alerts: list[tuple[str, str]] = []
    prev = state.get("positions", {})
    current_symbols = set(positions)
    prev_symbols = set(prev)

    if first_run:
        sorted_positions = sorted(positions.values(), key=lambda p: abs(p.get("notional", 0)), reverse=True)
        body = "## 📌 Binance 当前持仓监控已启动\n" + ("\n\n".join(render_position(p) for p in sorted_positions) if sorted_positions else "当前无持仓。")
        alerts.append(("startup", body))
        return alerts

    for sym in sorted(current_symbols - prev_symbols):
        key = f"{sym}:opened"
        if can_alert(state, key):
            alerts.append((key, "## 🆕 Binance 新持仓\n" + render_position(positions[sym])))
            mark_alert(state, key)

    for sym in sorted(prev_symbols - current_symbols):
        key = f"{sym}:closed"
        if can_alert(state, key):
            old = prev[sym]
            alerts.append((key, f"## ✅ Binance 持仓已关闭\n**{sym} {old.get('side','')}** 已不在当前持仓中\n上次记录未实现盈亏: **{float(old.get('upnl',0)):+.2f} USDT** | ROE: **{float(old.get('roe',0)):+.2f}%**"))
            mark_alert(state, key)

    for sym in sorted(current_symbols & prev_symbols):
        cur = positions[sym]
        old = prev[sym]
        reasons = []
        d_price = cur["price_chg"] - float(old.get("price_chg", 0))
        d_pnl = cur["upnl"] - float(old.get("upnl", 0))
        d_roe = cur["roe"] - float(old.get("roe", 0))
        if abs(d_price) >= PRICE_MOVE_PCT:
            reasons.append(f"价格较上次提醒变动 {d_price:+.2f}pct")
        if abs(d_pnl) >= PNL_MOVE_USDT:
            reasons.append(f"盈亏变动 {d_pnl:+.2f}U")
        if abs(d_roe) >= ROE_MOVE_PCT:
            reasons.append(f"ROE变动 {d_roe:+.2f}pct")
        if cur["roe"] <= ABS_LOSS_ROE_PCT and float(old.get("roe", 0)) > ABS_LOSS_ROE_PCT:
            reasons.append(f"ROE跌破风险线 {ABS_LOSS_ROE_PCT:.0f}%")
        if cur["roe"] >= ABS_PROFIT_ROE_PCT and float(old.get("roe", 0)) < ABS_PROFIT_ROE_PCT:
            reasons.append(f"ROE突破盈利线 +{ABS_PROFIT_ROE_PCT:.0f}%")
        if reasons:
            key = f"{sym}:move"
            if can_alert(state, key):
                text = "## ⚠️ Binance 持仓波动提醒\n" + "\n".join(f"- {r}" for r in reasons) + "\n\n" + render_position(cur)
                alerts.append((key, text))
                mark_alert(state, key)

    return alerts


def fetch_positions(api_key: str, secret: str) -> dict[str, dict[str, Any]]:
    raw = signed_request("GET", "/fapi/v2/positionRisk", {}, api_key, secret)
    out = {}
    for p in raw:
        n = normalize_position(p)
        if n:
            out[n["symbol"]] = n
    return out


def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
    env = load_env()
    api_key, secret = load_credentials()
    state = load_state()
    first_run = not bool(state.get("initialized"))
    log(f"position monitor started pid={os.getpid()} poll={POLL_SECONDS}s thresholds price={PRICE_MOVE_PCT}% pnl={PNL_MOVE_USDT}U roe={ROE_MOVE_PCT}%")

    while True:
        try:
            positions = fetch_positions(api_key, secret)
            alerts = build_alerts(positions, state, first_run=first_run)
            for key, text in alerts:
                try:
                    send_telegram(text, env)
                    log(f"alert sent key={key}")
                except Exception as e:
                    log(f"telegram failed key={key}: {e}")
            state["positions"] = positions
            state["initialized"] = True
            state["last_scan_ts"] = now_ts()
            save_state(state)
            log(f"scan ok positions={len(positions)} alerts={len(alerts)}")
            first_run = False
        except Exception as e:
            log(f"scan failed: {type(e).__name__}: {e}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
