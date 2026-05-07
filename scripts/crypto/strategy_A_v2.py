#!/usr/bin/env python3
"""
策略 A 加严版 v2 回测
对照: A原版 vs A加严
加严内容:
  1. 仅 24h vol ≥ 1 亿 USDT 的币
  2. 持仓缩到 4h (48 根 5m)
  3. 全局 1 单冷却 (同一时刻只允许 1 个仓位, 跨币也算)
  4. 单币冷却 6h (72 根)
"""
import json, time, urllib.request, urllib.parse, pickle, os
from statistics import median
from datetime import datetime, timezone

CACHE = "/tmp/momentum_kline_cache.pkl"
DAYS = 30

print("[1/3] 加载缓存...")
with open(CACHE,"rb") as f: c = pickle.load(f)
all_kl = c["kl"]; ticker_qv = c["qv"]
print(f"  {len(all_kl)} 个币, vol≥1亿: {sum(1 for v in ticker_qv.values() if v>=1e8)} 个")

print("[2/3] 数值化...")
KL = {}
for sym, bars in all_kl.items():
    KL[sym] = [(int(b[0]), float(b[1]), float(b[2]), float(b[3]), float(b[4]),
                float(b[5]), float(b[7])) for b in bars]

# ── 通用模拟 ────────────────────────────────────────────
def simulate(entry_idx, bars, side, entry_price, tp_pct, sl_pct, max_hold_bars):
    """返回 (exit_type, pnl%, bars_held, exit_ts_idx)"""
    if side == "L":
        tp = entry_price * (1 + tp_pct/100); sl = entry_price * (1 - sl_pct/100)
    for k in range(entry_idx+1, min(entry_idx+1+max_hold_bars, len(bars))):
        _, _, hi, lo, cl, _, _ = bars[k]
        hit_sl = lo <= sl; hit_tp = hi >= tp
        if hit_sl and hit_tp: return ("SL", -sl_pct, k-entry_idx, k)
        if hit_sl: return ("SL", -sl_pct, k-entry_idx, k)
        if hit_tp: return ("TP", +tp_pct, k-entry_idx, k)
    last_k = min(entry_idx+max_hold_bars, len(bars)-1)
    exit_p = bars[last_k][4]
    pnl = (exit_p - entry_price)/entry_price * 100
    return ("TIMEOUT", pnl, max_hold_bars, last_k)

# ── A 加严扫描 ──────────────────────────────────────────
# 不同于原版: 每个币内部扫触发, 但所有信号汇总后按时间排序, 全局 1 单冷却
def scan_signals_A(min_vol_usdt, coin_cooldown_bars):
    """扫所有币的触发点, 返回 [(ts, sym, bar_idx, entry_price)]"""
    sigs = []
    eligible = {s for s,v in ticker_qv.items() if v >= min_vol_usdt}
    for sym, bars in KL.items():
        if sym not in eligible: continue
        if len(bars) < 290: continue
        last_sig = -999
        for i in range(288, len(bars)-1):
            ts, o, h, l, c, v, qv = bars[i]
            high_24h = max(b[2] for b in bars[i-288:i])
            if c < high_24h * 0.998: continue
            qv_1h = sum(b[6] for b in bars[i-11:i+1])
            qv_5m_baseline = [b[6] for b in bars[i-288:i]]
            med_5m = median(qv_5m_baseline)
            if med_5m <= 0: continue
            if qv_1h < med_5m * 12 * 1.5: continue
            if i - last_sig < coin_cooldown_bars: continue
            last_sig = i
            entry_p = bars[i+1][1]
            if entry_p <= 0: continue
            sigs.append((ts, sym, i, entry_p))
    sigs.sort()
    return sigs

# 执行: 全局 1 单, 持仓中其他信号丢弃
def execute(sigs, max_hold_bars, tp, sl):
    trades = []
    busy_until_ts = 0
    for ts, sym, i, entry_p in sigs:
        if ts < busy_until_ts: continue
        bars = KL[sym]
        res = simulate(i, bars, "L", entry_p, tp, sl, max_hold_bars)
        exit_type, pnl, held, exit_k = res
        # 转 ts: bar_idx 的 5m K = 5min 后才平
        exit_ts = bars[exit_k][0]
        busy_until_ts = exit_ts
        trades.append((sym, ts, entry_p, exit_type, pnl, held))
    return trades

def stats(name, trades):
    if not trades: print(f"{name}: 无信号"); return None
    n = len(trades)
    pnls = [t[4] for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    tps = sum(1 for t in trades if t[3]=="TP")
    sls = sum(1 for t in trades if t[3]=="SL")
    tos = sum(1 for t in trades if t[3]=="TIMEOUT")
    avg = sum(pnls)/n
    avg_fee = avg - 0.1
    avg_pos = sum(p for p in pnls if p>0)/max(1,wins)
    avg_neg = sum(p for p in pnls if p<=0)/max(1,n-wins)
    # 最大连亏
    cur_loss = max_loss = 0; cur_dd = 0; max_dd = 0; equity = 0; peak = 0
    for p in pnls:
        net = p - 0.1
        equity += net * 0.5  # 账户 ROI 累加
        if equity > peak: peak = equity
        dd = peak - equity
        if dd > max_dd: max_dd = dd
        if net <= 0: cur_loss += 1; max_loss = max(max_loss, cur_loss)
        else: cur_loss = 0
    print(f"━━━ {name} ━━━")
    print(f"  样本数:       {n}  ({n/DAYS:.2f}/天)")
    print(f"  胜率:         {wins/n*100:.1f}%")
    print(f"  TP/SL/TO:     {tps}/{sls}/{tos}")
    print(f"  平均盈/亏:    {avg_pos:+.3f}% / {avg_neg:+.3f}%")
    print(f"  扣费均值:     {avg_fee:+.3f}% / 单")
    print(f"  扣费账户ROI:  {avg_fee*0.5:+.4f}% / 单")
    print(f"  30天账户总:   {avg_fee*0.5*n:+.2f}%")
    print(f"  最大回撤:     {max_dd:.2f}% (账户)")
    print(f"  最大连亏:     {max_loss} 笔")
    return {"n":n,"wr":wins/n*100,"avg_fee":avg_fee,"total":avg_fee*0.5*n,"dd":max_dd}

# ── 跑 ───────────────────────────────────────────────
print("\n[3/3] 三个版本对比\n")

# 原版: 24h vol≥500万, 持仓 8h, 单币冷却 2h, 无全局冷却 (回顾)
print(">>> 原版 A (24h vol≥500万 / 持仓8h / 无全局冷却 / 单币冷却2h)")
sigs_orig = scan_signals_A(min_vol_usdt=5_000_000, coin_cooldown_bars=24)
# 模拟无全局冷却 = busy_until=0 永远
trades_orig = []
for ts, sym, i, entry_p in sigs_orig:
    bars = KL[sym]
    res = simulate(i, bars, "L", entry_p, 4.0, 2.0, 96)
    trades_orig.append((sym, ts, entry_p, res[0], res[1], res[2]))
r1 = stats("A 原版", trades_orig); print()

# 加严 v1: 仅 vol ≥ 1 亿
print(">>> A 加严 v1 (vol≥1亿 / 持仓8h / 无全局冷却 / 单币冷却2h)")
sigs_v1 = scan_signals_A(min_vol_usdt=100_000_000, coin_cooldown_bars=24)
trades_v1 = []
for ts, sym, i, entry_p in sigs_v1:
    bars = KL[sym]
    res = simulate(i, bars, "L", entry_p, 4.0, 2.0, 96)
    trades_v1.append((sym, ts, entry_p, res[0], res[1], res[2]))
r2 = stats("A v1", trades_v1); print()

# 加严 v2: vol≥1亿 + 持仓4h + 单币冷却6h + 全局1单
print(">>> A 加严 v2 (vol≥1亿 / 持仓4h / 单币冷却6h / 全局1单)")
sigs_v2 = scan_signals_A(min_vol_usdt=100_000_000, coin_cooldown_bars=72)
trades_v2 = execute(sigs_v2, max_hold_bars=48, tp=4.0, sl=2.0)
r3 = stats("A v2", trades_v2); print()

# 加严 v3: vol≥5000万 + 持仓4h + 单币冷却6h + 全局1单 (折中)
print(">>> A 加严 v3 (vol≥5000万 / 持仓4h / 单币冷却6h / 全局1单)")
sigs_v3 = scan_signals_A(min_vol_usdt=50_000_000, coin_cooldown_bars=72)
trades_v3 = execute(sigs_v3, max_hold_bars=48, tp=4.0, sl=2.0)
r4 = stats("A v3", trades_v3); print()

print("\n━━━━━━━━━ 推荐排序 ━━━━━━━━━")
results = [("原版 A",r1),("A v1 (vol≥1亿)",r2),("A v2 (vol≥1亿+全局1单)",r3),("A v3 (vol≥5千万+全局1单)",r4)]
results.sort(key=lambda x: -x[1]["total"] if x[1] else 1)
for name, r in results:
    if r:
        sharp = r["total"]/max(0.01,r["dd"])
        print(f"  {name:30s}: {r['n']:4d}单  WR{r['wr']:.1f}%  扣费{r['avg_fee']:+.3f}%/单  总{r['total']:+.1f}%  DD{r['dd']:.1f}%  收益/回撤={sharp:.2f}")
