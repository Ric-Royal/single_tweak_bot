#!/usr/bin/env python3
"""
Single Trade Test Script
Tests the complete trading bot workflow including GPT-4 decision making
"""

import os
import sys
from mt5_gpt_single import MT5GPTSingleBot
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def test_single_trade():
    """Test a single trading cycle with the bot"""
    print("🤖 Testing GPT-4 MetaTrader5 Single Bot")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("📝 Please create a .env file with your OpenAI API key:")
        print("   OPENAI_API_KEY=your_api_key_here")
        return False
    
    # Create bot instance
    print("\n1. Creating bot instance...")
    bot = MT5GPTSingleBot()
    print("✅ Bot created successfully")
    
    # Initialize connections
    print("\n2. Initializing connections...")
    if not bot.initialize():
        print("❌ Bot initialization failed!")
        return False
    print("✅ Both MT5 and OpenAI connections successful")
    
    # Run one trading cycle
    print("\n3. Running single trading cycle...")
    print("   📊 Fetching market data...")
    print("   🧮 Calculating indicators...")
    print("   🤖 Consulting GPT-4...")
    print("   📈 Making trading decision...")
    
    try:
        success = bot.run_cycle()
        if success:
            print("✅ Trading cycle completed successfully!")
            return True
        else:
            print("⚠️  Trading cycle completed but with warnings")
            return False
    except Exception as e:
        print(f"❌ Trading cycle failed: {e}")
        return False
    finally:
        # Always shutdown properly
        bot.shutdown()

def check_openai_key():
    """Check if OpenAI API key is properly set"""
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False
    
    if api_key == "your_openai_api_key_here":
        print("❌ Please replace the placeholder with your actual API key")
        return False
    
    if not api_key.startswith("sk-"):
        print("❌ OpenAI API key should start with 'sk-'")
        return False
    
    print(f"✅ OpenAI API key found: {api_key[:8]}...{api_key[-4:]}")
    return True

if __name__ == "__main__":
    print("🔑 Checking OpenAI API key...")
    if not check_openai_key():
        print("\n💡 To fix this:")
        print("1. Create a .env file in the project root")
        print("2. Add this line: OPENAI_API_KEY=your_actual_key_here")
        print("3. Replace 'your_actual_key_here' with your OpenAI API key")
        sys.exit(1)
    
    print("\n🧪 Starting trading test...")
    success = test_single_trade()
    
    if success:
        print("\n🎉 SUCCESS! The bot is working correctly!")
        print("💡 You can now run the full bot with: python mt5_gpt_single.py")
    else:
        print("\n❌ Test failed. Check the logs above for details.")
        print("💡 Common issues:")
        print("   - Make sure MetaTrader5 is running and logged in")
        print("   - Verify your OpenAI API key has credit")
        print("   - Check network connectivity")