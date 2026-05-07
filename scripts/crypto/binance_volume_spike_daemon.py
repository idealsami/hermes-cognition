#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_URL = "https://fapi.binance.com"
POLL_SECONDS = 5
MIN_QUOTE_VOLUME_24H = 1_000_000.0    # 24h成交额>=1M过滤垃圾币（从5M降至1M，捕捉冷门币启动早期）
COOLDOWN_SECONDS = 900                 # 15分钟推送冷却
KLINES_WORKERS = 5
REQUEST_DELAY = 0.08
STATE_PATH = Path("/root/.hermes/cache/binance-volume-monitor/state.json")
LOG_PATH = Path("/root/.hermes/cache/binance-volume-monitor/monitor.log")
PID_PATH = Path("/root/.hermes/cache/binance-volume-monitor/monitor.pid")

# ── 自动交易（只对"连续倍量"触发）──────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
TRADER_ENABLED = False
_trader_err = ''
try:
    from binance_trader import execute_long_for_spike, load_credentials
    TRADER_ENABLED = False  # 用户要求: 禁止交易，只监控/推送信号，不调用下单 API
except Exception as _e:
    _trader_err = str(_e)


@dataclass
class VolumeSignal:
    symbol: str
    price_now: float
    vol_current: float      # 当前bar成交额（未完整）
    vol_prev1: float        # 前一根完整bar
    vol_prev2: float        # 前二根完整bar
    vol_prev3: float        # 前三根完整bar
    quote_volume_24h: float
    price_change_24h_pct: float
    price_change_15m_pct: float  # 当前bar涨幅（bar_open → 现价）
    bar_open_time_ms: int
    trigger_type: str       # "连续倍量" | "单根爆量"

    @property
    def ratio_current_vs_prev1(self) -> float:
        return self.vol_current / self.vol_prev1 if self.vol_prev1 > 0 else 0.0

    @property
    def ratio_prev1_vs_prev2(self) -> float:
        return self.vol_prev1 / self.vol_prev2 if self.vol_prev2 > 0 else 0.0

    @property
    def ratio_current_vs_prev3(self) -> float:
        return self.vol_current / self.vol_prev3 if self.vol_prev3 > 0 else 0.0


def log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    line = f"[{ts}] {message}"
    with LOG_PATH.open('a', encoding='utf-8') as f:
        f.write(line + "\n")


def fetch_json(path: str, params: dict[str, Any] | None = None, _retries: int = 4) -> Any:
    url = BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "hermes-binance-volume-monitor/1.0", "Accept": "application/json"})
    for attempt in range(_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** attempt * 5
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"fetch_json: exceeded retries for {path}")


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    env_path = Path('/root/.hermes/.env')
    if env_path.exists():
        for raw in env_path.read_text(encoding='utf-8').splitlines():
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env.setdefault(k.strip(), v.strip())
    return env


def build_universe() -> list[str]:
    exchange_info = fetch_json('/fapi/v1/exchangeInfo')
    tradable = []
    for s in exchange_info.get('symbols', []):
        if s.get('quoteAsset') == 'USDT' and s.get('contractType') == 'PERPETUAL' and s.get('status') == 'TRADING':
            tradable.append(s['symbol'])
    return tradable


def check_volume_spike(symbol: str, ticker_map: dict[str, Any]) -> VolumeSignal | None:
    ticker = ticker_map.get(symbol)
    if not isinstance(ticker, dict):
        return None
    price_now = float(ticker.get('lastPrice') or 0.0)
    quote_volume_24h = float(ticker.get('quoteVolume') or 0.0)
    price_change_24h_pct = float(ticker.get('priceChangePercent') or 0.0)

    if quote_volume_24h < MIN_QUOTE_VOLUME_24H:
        return None

    time.sleep(REQUEST_DELAY)
    klines = fetch_json('/fapi/v1/klines', {'symbol': symbol, 'interval': '15m', 'limit': 4})
    if not isinstance(klines, list) or len(klines) < 4:
        return None

    # klines[-1] = 当前未完整bar
    # klines[-2] = 前一根完整bar
    # klines[-3] = 前二根完整bar
    # klines[-4] = 前三根完整bar
    vol_current = float(klines[-1][7] or 0.0)
    vol_prev1 = float(klines[-2][7] or 0.0)
    vol_prev2 = float(klines[-3][7] or 0.0)
    vol_prev3 = float(klines[-4][7] or 0.0)

    # 计算当前bar涨幅：bar_open → 现价
    bar_open_price = float(klines[-1][1] or 0.0)  # klines open price = field[1]
    price_change_15m_pct = (
        (price_now - bar_open_price) / bar_open_price * 100.0
        if bar_open_price > 0 else 0.0
    )

    # 条件1：连续三根倍量
    # klines[-2] >= klines[-3] * 2 且 klines[-1] >= klines[-2] * 2
    # 即当前bar >= 前三根的4倍
    continuous_double = (
        vol_prev1 >= vol_prev2 * 2.0
        and vol_current >= vol_prev1 * 2.0
        and vol_prev2 > 0
    )

    # 条件2：单根爆量
    # klines[-1] >= klines[-2] * 3
    single_burst = vol_current >= vol_prev1 * 3.0 and vol_prev1 > 0

    if not continuous_double and not single_burst:
        return None

    # 附加条件：24h涨幅 >= 10% 且 当前bar涨幅 >= 2%（双重过滤，避免横盘/下杀爆量）
    if price_change_24h_pct < 10.0:
        return None
    if price_change_15m_pct < 2.0:
        return None

    trigger_type = "连续倍量" if continuous_double else "单根爆量"

    return VolumeSignal(
        symbol=symbol,
        price_now=price_now,
        vol_current=vol_current,
        vol_prev1=vol_prev1,
        vol_prev2=vol_prev2,
        vol_prev3=vol_prev3,
        quote_volume_24h=quote_volume_24h,
        price_change_24h_pct=price_change_24h_pct,
        price_change_15m_pct=price_change_15m_pct,
        bar_open_time_ms=int(klines[-1][0] or 0),
        trigger_type=trigger_type,
    )


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {'alerts': {}, 'bars': {}}
    try:
        data = json.loads(STATE_PATH.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            data.setdefault('alerts', {})
            data.setdefault('bars', {})
            return data
    except Exception:
        pass
    return {'alerts': {}, 'bars': {}}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(STATE_PATH)


def in_cooldown(symbol: str, state: dict[str, Any]) -> bool:
    rec = state.get('alerts', {}).get(symbol)
    if not isinstance(rec, dict):
        return False
    ts = rec.get('last_alert_ts')
    return isinstance(ts, (int, float)) and (time.time() - float(ts) < COOLDOWN_SECONDS)


def is_new_bar(symbol: str, bar_open_time_ms: int, state: dict[str, Any]) -> bool:
    rec = state.get('bars', {}).get(symbol)
    if not isinstance(rec, dict):
        return True
    last_ts = rec.get('bar_open_time_ms')
    return not isinstance(last_ts, int) or bar_open_time_ms > last_ts


def mark_alerted(signal: VolumeSignal, state: dict[str, Any]) -> None:
    now_ts = time.time()
    state.setdefault('alerts', {})[signal.symbol] = {
        'last_alert_ts': now_ts,
        'trigger_type': signal.trigger_type,
        'bar_open_time_ms': signal.bar_open_time_ms,
    }
    state.setdefault('bars', {})[signal.symbol] = {
        'bar_open_time_ms': signal.bar_open_time_ms,
        'seen_at': now_ts,
    }


def fmt_money(value: float) -> str:
    mag = abs(value)
    if mag >= 1_000_000_000:
        return f'${mag/1_000_000_000:.2f}B'
    if mag >= 1_000_000:
        return f'${mag/1_000_000:.2f}M'
    if mag >= 1_000:
        return f'${mag/1_000:.2f}K'
    return f'${mag:.2f}'


def fmt_price(value: float) -> str:
    if value >= 1000:
        return f'${value:,.2f}'
    if value >= 1:
        return f'${value:,.4f}'
    return f'${value:,.6f}'


def fmt_time(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC') if ms else 'n/a'


def render_message(signal: VolumeSignal, trade_result: dict | None = None) -> str:
    emoji = "🔥" if signal.trigger_type == "单根爆量" else "📈"
    
    if signal.trigger_type == "连续倍量":
        detail = (
            f"**前三根**: {fmt_money(signal.vol_prev3)}\n"
            f"**前二根**: {fmt_money(signal.vol_prev2)} ({signal.ratio_prev1_vs_prev2:.2f}x)\n"
            f"**前一根**: {fmt_money(signal.vol_prev1)}\n"
            f"**当前bar**: {fmt_money(signal.vol_current)} ({signal.ratio_current_vs_prev1:.2f}x) ⚠️未完整"
        )
    else:
        detail = (
            f"**前一根**: {fmt_money(signal.vol_prev1)}\n"
            f"**当前bar**: {fmt_money(signal.vol_current)} ({signal.ratio_current_vs_prev1:.2f}x) ⚠️未完整"
        )

    base = [
        f"## {emoji} 量能异动｜{signal.trigger_type}",
        f"**交易对**: `{signal.symbol}`",
        f"**现价**: {fmt_price(signal.price_now)}",
        f"**bar涨幅**: {signal.price_change_15m_pct:+.2f}%（当前15m）",
        f"**24h涨跌**: {signal.price_change_24h_pct:+.2f}%",
        "",
        "**15m成交额变化**:",
        detail,
        "",
        f"💹 **24h成交额**: {fmt_money(signal.quote_volume_24h)}",
        f"🕐 {fmt_time(signal.bar_open_time_ms)}",
    ]

    # ── 附加：开单结果 ──
    if trade_result is not None:
        base.append("")
        base.append("━━━━━━━━━━━━━━━━━━━━━━")
        status = trade_result.get('status')
        if status == 'opened':
            tp_mark = '✅' if trade_result.get('tp_ok') else '❌'
            sl_mark = '✅' if trade_result.get('sl_ok') else '❌'
            base.extend([
                f"## 🤖 已自动开多",
                f"**入场价**: {fmt_price(float(trade_result.get('entry_price') or 0))}",
                f"**数量**: {trade_result.get('qty')}",
                f"**保证金**: {float(trade_result.get('margin_usdt') or 0):.2f} USDT",
                f"**名义价值**: {float(trade_result.get('notional') or 0):.2f} USDT",
                f"**杠杆**: {trade_result.get('leverage')}x",
                f"**止盈** {tp_mark}: {fmt_price(float(trade_result.get('tp_price') or 0))}  (+10%)",
                f"**止损** {sl_mark}: {fmt_price(float(trade_result.get('sl_price') or 0))}  (-5%)",
                f"**订单号**: `{trade_result.get('order_id')}`",
            ])
            if not trade_result.get('tp_ok') and trade_result.get('tp_err'):
                base.append(f"⚠️ 止盈挂单失败: `{str(trade_result['tp_err'])[:120]}`")
            if not trade_result.get('sl_ok') and trade_result.get('sl_err'):
                base.append(f"⚠️ 止损挂单失败: `{str(trade_result['sl_err'])[:120]}`")
        elif status == 'cooldown':
            base.append(f"🤖 *交易冷却中，未开单*")
        elif status == 'no_balance':
            base.append(f"🤖 *余额不足 ({trade_result.get('avail', 0):.2f}U)，未开单*")
        elif status == 'below_min_notional':
            base.append(
                f"🤖 *名义价值 {float(trade_result.get('notional') or 0):.2f}U "
                f"< 最小 {trade_result.get('min_notional')}U，未开单*"
            )
        elif status == 'error':
            base.append(f"🤖 *开单异常*: `{str(trade_result.get('error'))[:200]}`")

    base.append("")
    base.append("*📋 全市场USDT永续扫描 | 15m K线 | 同币15分钟内只推一次*")
    return "\n".join(base)


def send_telegram(message: str, env: dict[str, str]) -> None:
    token = env.get('TELEGRAM_BOT_TOKEN')
    allowed_users = env.get('TELEGRAM_ALLOWED_USERS', '').split(',')
    chat_id = next((x.strip() for x in allowed_users if x.strip()), '')
    if not token:
        raise RuntimeError('Missing TELEGRAM_BOT_TOKEN')
    if not chat_id:
        raise RuntimeError('Missing TELEGRAM_ALLOWED_USERS/chat id')
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown',
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode('utf-8', errors='replace')
    if '"ok":true' not in body:
        raise RuntimeError(f'Telegram send failed: {body[:500]}')


def scan_universe(symbols: list[str], ticker_map: dict[str, Any]) -> list[VolumeSignal]:
    out: list[VolumeSignal] = []
    with ThreadPoolExecutor(max_workers=KLINES_WORKERS) as ex:
        futures = [ex.submit(check_volume_spike, symbol, ticker_map) for symbol in symbols]
        for fut in as_completed(futures):
            try:
                signal = fut.result()
                if signal is not None:
                    out.append(signal)
            except Exception as e:
                log(f'scan error: {e}')
    return out


def loop() -> int:
    env = load_env()
    PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(os.getpid()), encoding='utf-8')
    log('volume spike monitor started')
    universe = build_universe()
    log(f'universe ready: {len(universe)} symbols')

    # 加载交易凭据（仅在 trader 可用时）
    trader_key, trader_secret = '', ''
    trader_active = False
    if TRADER_ENABLED:
        try:
            trader_key, trader_secret = load_credentials()
            trader_active = True
            log('trader credentials loaded; auto-trading on 连续倍量 ENABLED (5%/10x, TP+10%/SL-5%)')
        except Exception as e:
            log(f'trader credentials failed: {e}')
    else:
        log(f'trader import failed: {_trader_err}')

    # 启动提示，方便用户确认监控已重新上线
    try:
        trade_status = (
            "🤖 自动交易: ✅ 开启 (连续倍量, 5%保证金 10x杠杆 TP+10% SL-5%)"
            if trader_active
            else "🤖 自动交易: ❌ 关闭"
        )
        send_telegram(
            f"✅ *Binance 爆量监控已上线*\n"
            f"universe={len(universe)} 对\n"
            f"poll={POLL_SECONDS}s\n"
            f"条件: 爆量 + 24h涨幅≥10% + bar内涨幅≥2%\n"
            f"{trade_status}",
            env,
        )
    except Exception as e:  # noqa: BLE001
        log(f'startup ping failed: {e}')

    while True:
        try:
            state = load_state()
            now = time.time()
            tickers = fetch_json('/fapi/v1/ticker/24hr')
            ticker_map = {row.get('symbol'): row for row in tickers if isinstance(row, dict)}

            signals = scan_universe(universe, ticker_map)
            signals.sort(key=lambda s: -s.vol_current)

            sent = 0
            for signal in signals:
                if not is_new_bar(signal.symbol, signal.bar_open_time_ms, state):
                    continue
                if in_cooldown(signal.symbol, state):
                    continue

                # ── 连续倍量 → 自动开多 ──
                trade_result = None
                if trader_active and signal.trigger_type == "连续倍量":
                    try:
                        trade_result = execute_long_for_spike(
                            signal.symbol, signal.price_now, trader_key, trader_secret
                        )
                    except Exception as e:
                        log(f'trader call exception {signal.symbol}: {e}')
                        trade_result = {'status': 'error', 'symbol': signal.symbol, 'error': str(e)}

                msg = render_message(signal, trade_result)
                send_telegram(msg, env)
                mark_alerted(signal, state)
                save_state(state)  # 立即保存，防止同轮重复推送
                sent += 1
                trade_tag = ''
                if trade_result is not None:
                    trade_tag = f" trade={trade_result.get('status')}"
                log(
                    f"alert sent: {signal.symbol} type={signal.trigger_type} "
                    f"current={fmt_money(signal.vol_current)} prev1={fmt_money(signal.vol_prev1)}{trade_tag}"
                )

            state['last_scan_ts'] = now
            state['last_scan_signals'] = len(signals)
            save_state(state)

            if sent == 0 and signals:
                log(f'scan: {len(signals)} signals, no fresh alerts')
            elif sent == 0:
                log('scan complete: no volume spikes detected')

        except Exception as e:
            log(f'loop error: {e}')
        time.sleep(POLL_SECONDS)


if __name__ == '__main__':
    raise SystemExit(loop())
