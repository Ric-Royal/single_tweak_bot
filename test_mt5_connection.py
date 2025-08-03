#!/usr/bin/env python3
"""
MetaTrader5 Connection Test Script
Tests basic MT5 connectivity before running the trading bot
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

def test_mt5_connection():
    """Test basic MetaTrader5 connection and functionality"""
    print("=== MetaTrader5 Connection Test ===")
    
    # Test 1: Initialize MT5
    print("\n1. Testing MT5 initialization...")
    if not mt5.initialize():
        print(f"❌ MT5 initialize() failed, error code: {mt5.last_error()}")
        return False
    print("✅ MT5 initialized successfully")
    
    # Test 2: Get account info
    print("\n2. Testing account information...")
    account_info = mt5.account_info()
    if account_info is None:
        print("❌ Failed to get account info")
        return False
    
    print(f"✅ Account info retrieved:")
    print(f"   - Login: {account_info.login}")
    print(f"   - Server: {account_info.server}")
    print(f"   - Balance: {account_info.balance}")
    print(f"   - Equity: {account_info.equity}")
    print(f"   - Margin: {account_info.margin}")
    print(f"   - Trade allowed: {account_info.trade_allowed}")
    
    # Test 3: Check symbol availability
    print("\n3. Testing symbol availability (EURUSD)...")
    symbol = "EURUSD"
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"❌ Symbol {symbol} not found")
        return False
    
    print(f"✅ Symbol {symbol} available:")
    print(f"   - Bid: {symbol_info.bid}")
    print(f"   - Ask: {symbol_info.ask}")
    print(f"   - Spread: {symbol_info.spread}")
    print(f"   - Trade allowed: {symbol_info.trade_mode}")
    
    # Test 4: Get market data
    print("\n4. Testing market data retrieval...")
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 10)
    if rates is None:
        print(f"❌ Failed to get rates for {symbol}")
        return False
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(f"✅ Retrieved {len(df)} bars of data:")
    print(f"   - Latest close: {df['close'].iloc[-1]}")
    print(f"   - Latest time: {df['time'].iloc[-1]}")
    
    # Test 5: Check trading permissions
    print("\n5. Testing trading permissions...")
    if not account_info.trade_allowed:
        print("⚠️  WARNING: Trading is not allowed on this account!")
        print("   - This might be a demo account with restrictions")
        print("   - Or trading permissions are disabled")
    else:
        print("✅ Trading is allowed on this account")
    
    # Test 6: Get current positions
    print("\n6. Checking current positions...")
    positions = mt5.positions_get()
    if positions is None:
        print("❌ Failed to get positions")
    else:
        print(f"✅ Current positions: {len(positions)}")
        for pos in positions:
            print(f"   - {pos.symbol}: {pos.type_str} {pos.volume} lots")
    
    print("\n=== Connection Test Complete ===")
    mt5.shutdown()
    return True

if __name__ == "__main__":
    try:
        success = test_mt5_connection()
        if success:
            print("\n🎉 All tests passed! MT5 connection is working.")
            print("📝 Next step: Create .env file with your OpenAI API key")
            print("🚀 Then you can run the trading bot")
        else:
            print("\n❌ Connection test failed!")
            print("💡 Make sure MetaTrader5 terminal is running and logged in")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        print("💡 Make sure MetaTrader5 terminal is running and logged in")