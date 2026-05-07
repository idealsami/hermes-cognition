#!/usr/bin/env python3
"""
Momentum 策略回测 — 对比做多 vs 做空
扫描全 USDT-perp 市场近 30 天 5m K 线
信号: 5m 涨≥2% + 量≥近12h 5m中位 ×2 + 24h vol ≥5M USDT + 阳线
"""
import json, time, urllib.request, urllib.parse
from datetime import datetime, timezone
from statistics import median
from collections import defaultdict

BASE = "https://fapi.binance.com"

PRICE_THR = 2.0   # %
VOL_MULT  = 2.0
MIN_24H_QV = 5_000_000
TP_PCT = 3.0
SL_PCT = 1.5
MAX_HOLD_BARS = 12  # 60min / 5m
COIN_COOLDOWN_BARS = 6  # 30min

DAYS = 30
BARS_PER_DAY = 288
TOTAL_BARS = DAYS * BARS_PER_DAY  # 8640

def http_get(path, params=None, retries=3):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == retries-1: raise
            time.sleep(2)

# 1. 拿 24h ticker, 选 vol ≥ 5M USDT 的 USDT 永续, 取活跃前 N
print("[1/4] 拉取 24h ticker...")
ticker = http_get("/fapi/v1/ticker/24hr")
candidates = []
for t in ticker:
    sym = t["symbol"]
    if not sym.endswith("USDT"): continue
    qv = float(t.get("quoteVolume",0))
    if qv < MIN_24H_QV: continue
    candidates.append((sym, qv))
candidates.sort(key=lambda x:-x[1])
# 活跃前 80 个 (避免请求量太大)
TOP_N = 80
symbols = [s for s,_ in candidates[:TOP_N]]
print(f"  共 {len(candidates)} 个合格币, 取前 {TOP_N} 活跃币回测")
print(f"  样本前5: {symbols[:5]}")

# 2. 拉每个币近 30 天 5m K 线 (8640 根, 需 9 次分页)
print(f"\n[2/4] 拉取 5m K 线 ({TOP_N} 币 × {TOTAL_BARS} 根)...")
end_ms = int(time.time()*1000)
start_ms = end_ms - DAYS*86400*1000

all_kl = {}
for idx, sym in enumerate(symbols, 1):
    bars = []
    cursor = start_ms
    try:
        while cursor < end_ms:
            data = http_get("/fapi/v1/klines", {
                "symbol": sym, "interval":"5m",
                "startTime": cursor, "limit": 1500
            })
            if not data: break
            bars.extend(data)
            cursor = data[-1][0] + 1
            if len(data) < 1500: break
            time.sleep(0.05)
        all_kl[sym] = bars
        if idx % 10 == 0:
            print(f"  [{idx}/{TOP_N}] {sym}: {len(bars)} bars")
    except Exception as e:
        print(f"  [{idx}/{TOP_N}] {sym} FAIL: {e}")

print(f"  拿到 {len(all_kl)} 个币的数据")

# 3. 扫描信号 + 同步回测做多/做空
# K 线格式: [open_time, open, high, low, close, volume, close_time, qv, ...]
print(f"\n[3/4] 扫描信号 + 回测...")

trades_long = []
trades_short = []

for sym, bars in all_kl.items():
    if len(bars) < 144 + 13: continue  # 12h baseline + 至少 13 根观察
    # 把 bars 转成数值
    bars = [(int(b[0]), float(b[1]), float(b[2]), float(b[3]), float(b[4]), float(b[7])) for b in bars]
    # bar = (ts, o, h, l, c, qv)

    last_signal_idx = -999  # 单币冷却

    # 从第 144 根开始扫描 (前面留作 baseline)
    for i in range(144, len(bars)-13):
        ts, o, h, l, c, qv = bars[i]
        # 信号 1: 涨≥2%
        if o <= 0: continue
        chg = (c - o) / o * 100
        if chg < PRICE_THR: continue
        # 信号 2: 量≥12h 5m 中位 ×2
        baseline_qvs = [b[5] for b in bars[i-144:i]]
        med_qv = median(baseline_qvs) if baseline_qvs else 0
        if med_qv <= 0: continue
        vol_x = qv / med_qv
        if vol_x < VOL_MULT: continue
        # 信号 3: 阳线 (c > o) 已隐含
        if c <= o: continue
        # 单币冷却
        if i - last_signal_idx < COIN_COOLDOWN_BARS: continue
        last_signal_idx = i

        # 入场: 下一根开盘价
        if i+1 >= len(bars): continue
        entry_bar = bars[i+1]
        entry_price = entry_bar[1]  # next bar open
        if entry_price <= 0: continue

        # ─── 做多回测 ───
        tp_long = entry_price * (1 + TP_PCT/100)
        sl_long = entry_price * (1 - SL_PCT/100)
        result_long = None
        for k in range(i+1, min(i+1+MAX_HOLD_BARS, len(bars))):
            _, _, hi, lo, cl, _ = bars[k]
            # 假设同 bar 内先碰到的:保守估计先 SL
            hit_sl = lo <= sl_long
            hit_tp = hi >= tp_long
            if hit_sl and hit_tp:
                result_long = ("SL", -SL_PCT, k-i)  # 保守
                break
            if hit_sl:
                result_long = ("SL", -SL_PCT, k-i); break
            if hit_tp:
                result_long = ("TP", +TP_PCT, k-i); break
        if result_long is None:
            # 60min 后市价平
            exit_price = bars[min(i+MAX_HOLD_BARS, len(bars)-1)][4]
            pnl = (exit_price - entry_price)/entry_price * 100
            result_long = ("TIMEOUT", pnl, MAX_HOLD_BARS)
        trades_long.append((sym, ts, chg, vol_x, entry_price, *result_long))

        # ─── 做空回测 (镜像 TP/SL) ───
        tp_short = entry_price * (1 - TP_PCT/100)  # 跌 3% 止盈
        sl_short = entry_price * (1 + SL_PCT/100)  # 涨 1.5% 止损
        result_short = None
        for k in range(i+1, min(i+1+MAX_HOLD_BARS, len(bars))):
            _, _, hi, lo, cl, _ = bars[k]
            hit_sl_s = hi >= sl_short
            hit_tp_s = lo <= tp_short
            if hit_sl_s and hit_tp_s:
                result_short = ("SL", -SL_PCT, k-i); break
            if hit_sl_s:
                result_short = ("SL", -SL_PCT, k-i); break
            if hit_tp_s:
                result_short = ("TP", +TP_PCT, k-i); break
        if result_short is None:
            exit_price = bars[min(i+MAX_HOLD_BARS, len(bars)-1)][4]
            pnl = (entry_price - exit_price)/entry_price * 100
            result_short = ("TIMEOUT", pnl, MAX_HOLD_BARS)
        trades_short.append((sym, ts, chg, vol_x, entry_price, *result_short))

print(f"  扫到 {len(trades_long)} 个信号 (= {len(trades_long)/DAYS:.1f} 个/天)")

# 4. 统计
print(f"\n[4/4] 结果对比 (基于币本身价格,不算杠杆)\n")

def stats(trades, name):
    if not trades:
        print(f"{name}: 无信号"); return
    n = len(trades)
    pnls = [t[6] for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p <= 0)
    avg = sum(pnls)/n
    total = sum(pnls)
    tps = sum(1 for t in trades if t[5]=="TP")
    sls = sum(1 for t in trades if t[5]=="SL")
    tos = sum(1 for t in trades if t[5]=="TIMEOUT")
    print(f"━━━━━━━━━━━ {name} ━━━━━━━━━━━")
    print(f"  样本数:     {n}")
    print(f"  胜率:       {wins/n*100:.1f}%  ({wins}胜 / {losses}负)")
    print(f"  TP 触发:    {tps} ({tps/n*100:.1f}%)")
    print(f"  SL 触发:    {sls} ({sls/n*100:.1f}%)")
    print(f"  TIMEOUT:    {tos} ({tos/n*100:.1f}%)")
    print(f"  单笔均值:   {avg:+.3f}% (币价)")
    print(f"  总收益:     {total:+.2f}% (币价 累计)")
    # 折算账户 ROI: 5% 仓位 ×10x => 币价 1% = 账户 0.5%
    print(f"  折算账户均值: {avg*0.5:+.3f}% / 单 (5%仓×10x)")
    print(f"  折算账户总:   {total*0.5:+.2f}% (账户 累计)")
    # 含手续费: 进+出 各 0.05% taker = 0.1% 币价 / 单
    avg_fee = avg - 0.1
    print(f"  扣 0.1% 手续费后均值: {avg_fee:+.3f}% (币价)")
    print(f"  扣手续费后账户均值:   {avg_fee*0.5:+.3f}% / 单")

stats(trades_long, "做多 (TP+3%/SL-1.5%)")
print()
stats(trades_short, "做空 (TP-3%/SL+1.5%)")

# 保存原始 trades
import csv
with open("/tmp/momentum_backtest_long.csv","w") as f:
    w = csv.writer(f); w.writerow(["sym","ts","chg%","vol_x","entry","exit_type","pnl%","bars_held"])
    w.writerows(trades_long)
with open("/tmp/momentum_backtest_short.csv","w") as f:
    w = csv.writer(f); w.writerow(["sym","ts","chg%","vol_x","entry","exit_type","pnl%","bars_held"])
    w.writerows(trades_short)
print(f"\n[原始 trades 已保存到 /tmp/momentum_backtest_{{long,short}}.csv]")
