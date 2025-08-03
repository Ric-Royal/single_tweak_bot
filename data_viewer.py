#!/usr/bin/env python3
"""
Data Viewer Utility

Simple script to view and analyze stored trading bot data
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from utils.data_manager import DataManager

def show_storage_stats():
    """Display storage statistics"""
    data_manager = DataManager(enabled=True)
    stats = data_manager.get_storage_stats()
    
    print("📊 Data Storage Statistics")
    print("=" * 40)
    
    if not stats.get("enabled", False):
        print("❌ Data storage is disabled")
        return
    
    total_files = 0
    total_size = 0
    
    for dir_name, info in stats.get("directories", {}).items():
        files = info.get("files", 0)
        size_mb = info.get("size_mb", 0)
        total_files += files
        total_size += size_mb
        
        print(f"📁 {dir_name.replace('_', ' ').title()}: {files} files ({size_mb} MB)")
    
    print("-" * 40)
    print(f"📈 Total: {total_files} files ({total_size:.2f} MB)")

def show_recent_decisions(symbol: str = "EURUSD", days: int = 1):
    """Show recent GPT-4 decisions"""
    print(f"\n🤖 Recent GPT-4 Decisions for {symbol}")
    print("=" * 50)
    
    try:
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")
            filename = f"data/decisions/{symbol}_decisions_{date_str}.jsonl"
            
            if os.path.exists(filename):
                print(f"\n📅 {date.strftime('%Y-%m-%d')}")
                print("-" * 30)
                
                with open(filename, 'r', encoding='utf-8') as f:
                    decisions = []
                    for line in f:
                        entry = json.loads(line.strip())
                        decisions.append(entry)
                
                for decision in decisions[-5:]:  # Show last 5 decisions
                    time = datetime.fromisoformat(decision['timestamp']).strftime('%H:%M:%S')
                    action = decision['decision']['action'].upper()
                    reasoning = decision['decision']['reasoning'][:100] + "..."
                    
                    print(f"⏰ {time} | {action:4} | {reasoning}")
            else:
                print(f"❌ No decisions found for {date.strftime('%Y-%m-%d')}")
                
    except Exception as e:
        print(f"❌ Error reading decisions: {e}")

def show_recent_indicators(symbol: str = "EURUSD", days: int = 1):
    """Show recent indicator values"""
    print(f"\n📈 Recent Indicators for {symbol}")
    print("=" * 50)
    
    try:
        data_manager = DataManager(enabled=True)
        df = data_manager.load_historical_indicators(symbol, days)
        
        if df is not None and not df.empty:
            # Show latest 5 entries
            latest = df.tail(5)
            
            for idx, row in latest.iterrows():
                indicators = row['indicators']
                time_str = idx.strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"\n⏰ {time_str}")
                print(f"   RSI: {indicators.get('rsi', 'N/A'):.1f}")
                print(f"   MACD: {indicators.get('macd', 'N/A'):.6f}")
                print(f"   Stochastic K: {indicators.get('stoch_k', 'N/A'):.1f}")
                print(f"   ATR: {indicators.get('atr', 'N/A'):.5f}")
        else:
            print("❌ No indicator data found")
            
    except Exception as e:
        print(f"❌ Error reading indicators: {e}")

def show_trades(symbol: str = "EURUSD", days: int = 7):
    """Show executed trades"""
    print(f"\n💰 Recent Trades for {symbol}")
    print("=" * 40)
    
    try:
        trades_found = False
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")
            filename = f"data/trades/{symbol}_trades_{date_str}.jsonl"
            
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    for line in f:
                        entry = json.loads(line.strip())
                        trades_found = True
                        
                        time = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                        action = entry['decision']['action'].upper()
                        volume = entry['decision']['volume']
                        sl_pips = entry['decision']['stop_loss_pips']
                        tp_pips = entry['decision']['take_profit_pips']
                        
                        print(f"📅 {time}")
                        print(f"   Action: {action} | Volume: {volume} | SL: {sl_pips} pips | TP: {tp_pips} pips")
        
        if not trades_found:
            print("📝 No trades executed yet")
            
    except Exception as e:
        print(f"❌ Error reading trades: {e}")

def main():
    """Main function"""
    print("🤖 Trading Bot Data Viewer")
    print("=" * 60)
    
    if not os.path.exists("data"):
        print("❌ No data directory found")
        print("💡 Data storage might be disabled or no data has been generated yet")
        return
    
    # Show overview
    show_storage_stats()
    
    # Show specific data
    show_recent_decisions()
    show_recent_indicators() 
    show_trades()
    
    print("\n✅ Data review complete!")

if __name__ == "__main__":
    main()