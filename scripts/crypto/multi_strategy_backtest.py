#!/usr/bin/env python3
"""
三策略并行回测: A=1h突破趋势跟随 / C=超跌反弹 / D=亚盘开盘逆向
统一: 80 活跃币 × 30 天 5m K 线
统一手续费: 0.1% (taker 双边)
"""
import json, time, urllib.request, urllib.parse, pickle, os
from statistics import median
from datetime import datetime, timezone

BASE = "https://fapi.binance.com"
DAYS = 30
TOP_N = 80
MIN_24H_QV_C = 50_000_000   # C 用更严的 5000 万
MIN_24H_QV_OTHER = 5_000_000

CACHE = "/tmp/momentum_kline_cache.pkl"

def http_get(path, params=None, retries=3):
    url = BASE + path
    if params: url += "?" + urllib.parse.urlencode(params)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == retries-1: raise
            time.sleep(2)

# ── 1. 数据准备 ───────────────────────────────────────────
if os.path.exists(CACHE):
    print("[1/5] 加载缓存...")
    with open(CACHE,"rb") as f: cache = pickle.load(f)
    all_kl = cache["kl"]; ticker_qv = cache["qv"]
    print(f"  缓存: {len(all_kl)} 个币")
else:
    print("[1/5] 拉 24h ticker...")
    ticker = http_get("/fapi/v1/ticker/24hr")
    cands = []
    ticker_qv = {}
    for t in ticker:
        s = t["symbol"]
        if not s.endswith("USDT"): continue
        qv = float(t.get("quoteVolume",0))
        if qv < MIN_24H_QV_OTHER: continue
        cands.append((s, qv))
        ticker_qv[s] = qv
    cands.sort(key=lambda x:-x[1])
    symbols = [s for s,_ in cands[:TOP_N]]
    print(f"  取前 {TOP_N} 活跃币")

    print(f"[2/5] 拉 5m K 线 30 天...")
    end_ms = int(time.time()*1000); start_ms = end_ms - DAYS*86400*1000
    all_kl = {}
    for idx, sym in enumerate(symbols, 1):
        bars = []; cursor = start_ms
        try:
            while cursor < end_ms:
                d = http_get("/fapi/v1/klines", {"symbol":sym,"interval":"5m","startTime":cursor,"limit":1500})
                if not d: break
                bars.extend(d)
                cursor = d[-1][0]+1
                if len(d) < 1500: break
                time.sleep(0.05)
            all_kl[sym] = bars
            if idx % 10 == 0: print(f"  [{idx}/{TOP_N}] {sym}: {len(bars)}")
        except Exception as e:
            print(f"  [{idx}] {sym} FAIL: {e}")
    with open(CACHE,"wb") as f: pickle.dump({"kl":all_kl,"qv":ticker_qv}, f)
    print(f"  缓存写入 {CACHE}")

# 转数值: bar = (ts, o, h, l, c, vol, qv)
print("[3/5] 数值化 K 线...")
KL = {}
for sym, bars in all_kl.items():
    KL[sym] = [(int(b[0]), float(b[1]), float(b[2]), float(b[3]), float(b[4]),
                float(b[5]), float(b[7])) for b in bars]
print(f"  {len(KL)} 个币")

# ── 通用回测函数 ─────────────────────────────────────────
def simulate(entry_idx, bars, side, entry_price, tp_pct, sl_pct, max_hold_bars):
    """side: 'L'/'S'. tp_pct/sl_pct 都是正数 %"""
    if side == "L":
        tp = entry_price * (1 + tp_pct/100); sl = entry_price * (1 - sl_pct/100)
    else:
        tp = entry_price * (1 - tp_pct/100); sl = entry_price * (1 + sl_pct/100)
    for k in range(entry_idx+1, min(entry_idx+1+max_hold_bars, len(bars))):
        _, _, hi, lo, cl, _, _ = bars[k]
        if side == "L":
            hit_sl = lo <= sl; hit_tp = hi >= tp
        else:
            hit_sl = hi >= sl; hit_tp = lo <= tp
        if hit_sl and hit_tp: return ("SL", -sl_pct, k-entry_idx)  # 保守
        if hit_sl: return ("SL", -sl_pct, k-entry_idx)
        if hit_tp: return ("TP", +tp_pct, k-entry_idx)
    # 超时
    exit_p = bars[min(entry_idx+max_hold_bars, len(bars)-1)][4]
    if side == "L": pnl = (exit_p - entry_price)/entry_price * 100
    else:           pnl = (entry_price - exit_p)/entry_price * 100
    return ("TIMEOUT", pnl, max_hold_bars)

def stats(name, trades):
    if not trades: print(f"{name}: 无信号"); return
    n = len(trades)
    pnls = [t[6] for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    tps = sum(1 for t in trades if t[5]=="TP")
    sls = sum(1 for t in trades if t[5]=="SL")
    tos = sum(1 for t in trades if t[5]=="TIMEOUT")
    avg = sum(pnls)/n
    avg_fee = avg - 0.1
    print(f"━━━ {name} ━━━")
    print(f"  样本数:     {n}  ({n/DAYS:.1f}/天)")
    print(f"  胜率:       {wins/n*100:.1f}%  ({wins}胜 / {n-wins}负)")
    print(f"  TP/SL/TO:   {tps}/{sls}/{tos}")
    print(f"  币价均值:   {avg:+.3f}% / 单")
    print(f"  扣费均值:   {avg_fee:+.3f}% / 单  (扣 0.1% 双边)")
    print(f"  扣费账户ROI: {avg_fee*0.5:+.4f}% / 单 (5%×10x)")
    print(f"  30天总账户: {avg_fee*0.5*n:+.2f}%")
    return {"n":n,"wr":wins/n*100,"avg_fee":avg_fee,"acc_roi_total":avg_fee*0.5*n}

# ── 策略 A: 1h 突破趋势跟随 ─────────────────────────────
# 5m K 线聚合成 1h: 12 根一组 (用 5m 序列模拟 1h 触发, 但每根 5m 都判定能否触发)
# 简化: 在每根 5m 收盘看 [过去 12 根 5m 内最高价] vs [过去 288 根 5m 24h 最高价]
# 触发: 当前 5m 收盘 ≥ 24h 最高 × 0.998
#       当前 5m 量 + 过去 11 根 (= 1h 量) ≥ 过去 288 根 5m 中位 × 12 × 1.5
def backtest_A():
    trades = []
    TP, SL, HOLD = 4.0, 2.0, 96  # 8h
    COOLDOWN = 24  # 2h
    for sym, bars in KL.items():
        if len(bars) < 288 + HOLD + 1: continue
        last_sig = -999
        for i in range(288, len(bars)-HOLD-1):
            ts, o, h, l, c, v, qv = bars[i]
            # 24h 高
            high_24h = max(b[2] for b in bars[i-288:i])
            if c < high_24h * 0.998: continue
            # 1h 量 vs 24h/12 的中位
            qv_1h = sum(b[6] for b in bars[i-11:i+1])
            qv_5m_baseline = [b[6] for b in bars[i-288:i]]
            med_5m = median(qv_5m_baseline)
            if med_5m <= 0: continue
            if qv_1h < med_5m * 12 * 1.5: continue
            if i - last_sig < COOLDOWN: continue
            last_sig = i
            entry_p = bars[i+1][1]
            if entry_p <= 0: continue
            res = simulate(i, bars, "L", entry_p, TP, SL, HOLD)
            trades.append((sym, ts, c, qv_1h, entry_p, *res))
    return trades

# ── 策略 C: 超跌反弹 ────────────────────────────────────
# 触发: 1h 累计跌幅 ≥ -4% (current_close vs price_12bars_ago)
#       5m RSI(14) ≤ 25
#       24h vol ≥ 5000万 (用 ticker_qv 过滤币种)
# 做多, TP+1.5% / SL-1% / hold 12 根 (60min)
def rsi(closes, period=14):
    if len(closes) < period+1: return None
    gains = []; losses = []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d,0)); losses.append(max(-d,0))
    avg_g = sum(gains[-period:])/period
    avg_l = sum(losses[-period:])/period
    if avg_l == 0: return 100
    rs = avg_g/avg_l
    return 100 - 100/(1+rs)

def backtest_C():
    trades = []
    TP, SL, HOLD = 1.5, 1.0, 12
    COOLDOWN = 6
    big_syms = {s for s,qv in ticker_qv.items() if qv >= MIN_24H_QV_C}
    for sym in big_syms:
        bars = KL.get(sym)
        if not bars or len(bars) < 50: continue
        last_sig = -999
        for i in range(20, len(bars)-HOLD-1):
            ts, o, h, l, c, v, qv = bars[i]
            # 1h 跌幅
            ref = bars[i-12][4] if i >= 12 else None
            if not ref or ref <= 0: continue
            chg_1h = (c - ref)/ref * 100
            if chg_1h > -4.0: continue
            # RSI
            closes = [b[4] for b in bars[i-19:i+1]]
            r = rsi(closes, 14)
            if r is None or r > 25: continue
            if i - last_sig < COOLDOWN: continue
            last_sig = i
            entry_p = bars[i+1][1]
            if entry_p <= 0: continue
            res = simulate(i, bars, "L", entry_p, TP, SL, HOLD)
            trades.append((sym, ts, chg_1h, r, entry_p, *res))
    return trades

# ── 策略 D: 亚盘开盘逆向 (UTC 0:00 后第一根高量阴线反弹) ──
# 触发: 该 5m 的 UTC 时间 在 [0:00, 0:25] 范围内
#       该 K 线为阴线, 实体跌 ≤ -1.5%
#       量 ≥ 过去 288 根 5m 中位 × 3
# 做多, TP+1.5% / SL-1% / hold 12 根
def backtest_D():
    trades = []
    TP, SL, HOLD = 1.5, 1.0, 12
    for sym, bars in KL.items():
        if len(bars) < 300: continue
        last_sig = -999
        for i in range(288, len(bars)-HOLD-1):
            ts, o, h, l, c, v, qv = bars[i]
            dt = datetime.fromtimestamp(ts/1000, tz=timezone.utc)
            if dt.hour != 0: continue
            if dt.minute > 25: continue
            # 阴线实体 ≥ -1.5%
            if o <= 0: continue
            body = (c - o)/o * 100
            if body > -1.5: continue
            # 量倍
            med = median(b[6] for b in bars[i-288:i])
            if med <= 0: continue
            if qv < med * 3: continue
            if i - last_sig < 12: continue
            last_sig = i
            entry_p = bars[i+1][1]
            if entry_p <= 0: continue
            res = simulate(i, bars, "L", entry_p, TP, SL, HOLD)
            trades.append((sym, ts, body, qv/med, entry_p, *res))
    return trades

print("\n[4/5] 运行三策略...")
print(">>> A: 1h 突破趋势跟随 (TP+4%/SL-2%/8h)")
TA = backtest_A()
print(f"  {len(TA)} 笔")
print(">>> C: 超跌反弹 (1h≤-4% + RSI≤25, TP+1.5%/SL-1%/60min)")
TC = backtest_C()
print(f"  {len(TC)} 笔")
print(">>> D: 亚盘开盘逆向 (UTC 0:00 高量阴线, TP+1.5%/SL-1%/60min)")
TD = backtest_D()
print(f"  {len(TD)} 笔")

print("\n[5/5] 结果\n")
ra = stats("策略 A: 1h 突破趋势跟随", TA); print()
rc = stats("策略 C: 超跌反弹", TC); print()
rd = stats("策略 D: 亚盘开盘逆向", TD); print()

print("\n━━━━━━━━━ 推荐 ━━━━━━━━━")
results = [("A",ra),("C",rc),("D",rd)]
results = [(n,r) for n,r in results if r]
results.sort(key=lambda x: -x[1]["acc_roi_total"])
for name, r in results:
    print(f"  {name}: 30天账户 {r['acc_roi_total']:+.2f}%, WR {r['wr']:.1f}%, 单笔扣费 {r['avg_fee']:+.3f}%")
