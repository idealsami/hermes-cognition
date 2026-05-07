#!/usr/bin/env python3
"""
EVM钱包碰撞扫描器 v2 - 优化版
使用多线程和批量查询提高效率
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from eth_account import Account
from mnemonic import Mnemonic
from web3 import Web3

# ============================================================
# 配置
# ============================================================

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

SCAN_MODE = os.environ.get("SCAN_MODE", "mnemonic")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "20"))  # 增加批次大小
SCAN_INTERVAL = float(os.environ.get("SCAN_INTERVAL", "0.1"))  # 减少间隔
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "5"))  # 并发线程数

# 链配置 - 使用更快的RPC
CHAINS = {
    "ETH": "https://ethereum-rpc.publicnode.com",
    "BSC": "https://bsc-dataseed.binance.org",
    "Polygon": "https://polygon-bor-rpc.publicnode.com",
    "Arbitrum": "https://arb1.arbitrum.io/rpc",
    "Optimism": "https://mainnet.optimism.io",
    "Base": "https://mainnet.base.org",
    "Avalanche": "https://avalanche-c-chain-rpc.publicnode.com",
}

# ============================================================
# 工具函数
# ============================================================

mnemo = Mnemonic("english")

# 预创建Web3连接池
w3_pool = {}
for chain_name, rpc_url in CHAINS.items():
    w3_pool[chain_name] = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 3}))

def generate_mnemonic():
    return mnemo.generate(strength=128)

def mnemonic_to_keypair(mnemonic_str, index=0):
    Account.enable_unaudited_hdwallet_features()
    acct = Account.from_mnemonic(mnemonic_str, account_path=f"m/44'/60'/0'/0/{index}")
    return acct.address, acct.key.hex()

def generate_random_keypair():
    private_key = "0x" + "".join(random.choices("0123456789abcdef", k=64))
    acct = Account.from_key(private_key)
    return acct.address, private_key

def get_balance_single_chain(chain_name, address):
    """查询单条链余额"""
    try:
        w3 = w3_pool[chain_name]
        balance_wei = w3.eth.get_balance(address)
        balance_eth = float(w3.from_wei(balance_wei, "ether"))
        if balance_eth > 0:
            return chain_name, balance_eth
    except:
        pass
    return None, 0

def get_balances_parallel(address):
    """并行查询所有链余额"""
    balances = {}
    with ThreadPoolExecutor(max_workers=len(CHAINS)) as executor:
        futures = {executor.submit(get_balance_single_chain, chain, address): chain 
                  for chain in CHAINS.keys()}
        for future in as_completed(futures):
            chain_name, balance = future.result()
            if balance > 0:
                balances[chain_name] = balance
    return balances

def send_telegram(message):
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
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {message}"
    print(full_msg)
    send_telegram(full_msg)

# ============================================================
# 扫描逻辑
# ============================================================

def scan_one():
    """扫描一个随机钱包"""
    mnemonic_str = None
    private_key = None
    
    if SCAN_MODE == "mnemonic":
        mnemonic_str = generate_mnemonic()
        address, private_key = mnemonic_to_keypair(mnemonic_str)
    else:
        address, private_key = generate_random_keypair()
    
    balances = get_balances_parallel(address)
    return address, private_key, mnemonic_str, balances

def scan_batch(batch_size):
    """扫描一批钱包"""
    results = []
    for _ in range(batch_size):
        result = scan_one()
        results.append(result)
        time.sleep(SCAN_INTERVAL)
    return results

def main():
    notify(f"🔍 EVM碰撞扫描器 v2 启动 (优化版)")
    notify(f"   模式: {SCAN_MODE} | 每轮: {BATCH_SIZE} | 间隔: {SCAN_INTERVAL}s | 并发: {MAX_WORKERS}")
    notify(f"   链: {', '.join(CHAINS.keys())}")
    notify("-" * 50)
    
    total_scanned = 0
    found_count = 0
    start_time = time.time()
    
    try:
        while True:
            batch_start = time.time()
            
            # 扫描一批
            results = scan_batch(BATCH_SIZE)
            
            for address, private_key, mnemonic_str, balances in results:
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
            
            # 计算速度
            batch_time = time.time() - batch_start
            speed = BATCH_SIZE / batch_time if batch_time > 0 else 0
            elapsed = time.time() - start_time
            avg_speed = total_scanned / elapsed if elapsed > 0 else 0
            
            print(f"[批次完成] 本轮 {BATCH_SIZE} 个 | 累计 {total_scanned} 个 | 发现 {found_count} 个 | 速度 {speed:.1f}/s | 平均 {avg_speed:.1f}/s", flush=True)
            
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        avg_speed = total_scanned / elapsed if elapsed > 0 else 0
        notify(f"扫描停止。共扫描 {total_scanned} 个地址，发现 {found_count} 个有余额")
        notify(f"运行时间: {elapsed:.0f}s，平均速度: {avg_speed:.1f}/s")

if __name__ == "__main__":
    main()