#!/usr/bin/env python3
"""
Enhanced Trading Bot Launcher

Quick launcher for the enhanced professional trading bot with
comprehensive risk management and quality controls.
"""

import sys
import os
import logging
from datetime import datetime

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mt5_gpt_single_tweak_enhanced import EnhancedMT5TradingBot

def main():
    """Launch the enhanced trading bot."""
    print("Enhanced Professional Trading Bot Launcher")
    print("=" * 60)
    print(f"Launch Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Show configuration
    print("CONFIGURATION:")
    print("• Symbol: EURUSD")
    print("• Risk per trade: 0.15%") 
    print("• Max volume: 0.05 lots")
    print("• Daily limits: 6 trades, -1.5% drawdown, 3 consecutive losses")
    print("• Time exits: 15 bars (75 minutes)")
    print("• Sessions: London/NY overlap (10:00-17:00 UTC)")
    print()
    
    # Check requirements
    print("PRE-FLIGHT CHECKS:")
    
    try:
        import MetaTrader5 as mt5
        print("[OK] MetaTrader5 package available")
    except ImportError:
        print("[FAIL] MetaTrader5 package not found - install with: pip install MetaTrader5")
        return 1
    
    try:
        import openai
        print("[OK] OpenAI package available")
    except ImportError:
        print("[FAIL] OpenAI package not found - install with: pip install openai")
        return 1
    
    # Check environment variables
    if os.getenv("OPENAI_API_KEY"):
        print("[OK] OPENAI_API_KEY found")
    else:
        print("[FAIL] OPENAI_API_KEY not found - set your OpenAI API key")
        return 1
    
    print()
    
    # Final confirmation
    try:
        response = input("Ready to launch enhanced bot? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Launch cancelled")
            return 0
    except KeyboardInterrupt:
        print("\nLaunch cancelled")
        return 0
    
    print()
    print("LAUNCHING ENHANCED TRADING BOT...")
    print("   Press Ctrl+C to stop")
    print("=" * 60)
    
    # Launch the bot
    try:
        bot = EnhancedMT5TradingBot()
        bot.run()
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
