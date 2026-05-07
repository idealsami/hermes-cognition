#!/usr/bin/env python3
"""
EVM钱包碰撞扫描器
随机生成助记词/私钥，检查多链余额，发现余额推送通知
"""

import os
import sys
import time
import json
import random
import string
import hashlib
import requests
from datetime import datetime
from eth_account import Account
from mnemonic import Mnemonic
from web3 import Web3

# ============================================================
# 配置
# ============================================================

# Telegram推送配置（可选，留空则只打印）
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

# 扫描模式: "mnemonic" (助记词) 或 "random" (随机私钥)
SCAN_MODE = os.environ.get("SCAN_MODE", "mnemonic")

# 每轮扫描数量
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))

# 扫描间隔（秒），防止被RPC限流
SCAN_INTERVAL = float(os.environ.get("SCAN_INTERVAL", "0.5"))

# 链配置：名称 -> RPC（选稳定的公共RPC）
CHAINS = {
    "ETH":       "https://ethereum-rpc.publicnode.com",
    "BSC":       "https://bsc-dataseed.binance.org",
    "Polygon":   "https://polygon-bor-rpc.publicnode.com",
    "Arbitrum":  "https://arb1.arbitrum.io/rpc",
    "Optimism":  "https://mainnet.optimism.io",
    "Base":      "https://mainnet.base.org",
    "Avalanche": "https://avalanche-c-chain-rpc.publicnode.com",
}

# ============================================================
# 工具函数
# ============================================================

mnemo = Mnemonic("english")

def generate_mnemonic():
    """生成12词助记词"""
    return mnemo.generate(strength=128)

def mnemonic_to_keypair(mnemonic_str, index=0):
    """助记词派生钱包（默认 m/44'/60'/0'/0/0）"""
    Account.enable_unaudited_hdwallet_features()
    acct = Account.from_mnemonic(mnemonic_str, account_path=f"m/44'/60'/0'/0/{index}")
    return acct.address, acct.key.hex()

def generate_random_keypair():
    """随机生成私钥和地址"""
    # 随机32字节私钥
    private_key = "0x" + "".join(random.choices("0123456789abcdef", k=64))
    acct = Account.from_key(private_key)
    return acct.address, private_key

def get_balances(address):
    """查询所有链的余额，返回 {链名: balance_eth} 字典"""
    balances = {}
    for chain_name, rpc_url in CHAINS.items():
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 5}))
            balance_wei = w3.eth.get_balance(address)
            balance_eth = float(w3.from_wei(balance_wei, "ether"))
            if balance_eth > 0:
                balances[chain_name] = balance_eth
        except Exception as e:
            pass  # 静默跳过RPC错误
    return balances

def send_telegram(message):
    """发送Telegram通知"""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TG_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
    except:
        pass

def notify(message):
    """统一通知入口"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {message}"
    print(full_msg)
    send_telegram(full_msg)

# ============================================================
# 主扫描逻辑
# ============================================================

def scan_one():
    """扫描一个随机钱包，返回 (地址, 私钥, 助记词, 余额字典)"""
    mnemonic_str = None
    private_key = None
    
    if SCAN_MODE == "mnemonic":
        mnemonic_str = generate_mnemonic()
        address, private_key = mnemonic_to_keypair(mnemonic_str)
    else:
        address, private_key = generate_random_keypair()
    
    balances = get_balances(address)
    return address, private_key, mnemonic_str, balances

def main():
    notify(f"🔍 EVM碰撞扫描器启动")
    notify(f"   模式: {SCAN_MODE} | 每轮: {BATCH_SIZE} | 间隔: {SCAN_INTERVAL}s")
    notify(f"   链: {', '.join(CHAINS.keys())}")
    notify("-" * 50)
    
    total_scanned = 0
    found_count = 0
    
    try:
        while True:
            for i in range(BATCH_SIZE):
                address, private_key, mnemonic_str, balances = scan_one()
                total_scanned += 1
                
                if balances:
                    found_count += 1
                    balance_str = " | ".join(f"{k}: {v:.6f} ETH" for k, v in balances.items())
                    notify(f"🎯 发现有余额地址！")
                    notify(f"   地址: {address}")
                    if mnemonic_str:
                        notify(f"   助记词: {mnemonic_str}")
                    notify(f"   私钥: {private_key}")
                    notify(f"   余额: {balance_str}")
                    notify("=" * 50)
                else:
                    # 无余额，打印进度
                    print(f"[进度] 已扫描 {total_scanned} 个 | {address[:10]}...{address[-6:]}", flush=True)
                
                time.sleep(SCAN_INTERVAL)
            
            # 每批次结束打印统计
            print(f"[批次完成] 本轮 {BATCH_SIZE} 个 | 累计 {total_scanned} 个 | 发现 {found_count} 个", flush=True)
            
    except KeyboardInterrupt:
        notify(f"扫描停止。共扫描 {total_scanned} 个地址，发现 {found_count} 个有余额")

if __name__ == "__main__":
    main()
