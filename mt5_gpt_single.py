#!/usr/bin/env python3
"""
GPT-4 Powered MetaTrader5 Single-Asset Trading Bot

This bot focuses on one symbol, fetches M5 data, computes technical indicators,
and uses GPT-4 to make trading decisions with stop-loss and take-profit levels.

Author: GPT-4 MetaTrader5 Trading Bot
Version: 1.0.0
"""

import os
import time
import logging
import json
import re
from datetime import datetime
from typing import Dict, Optional, Union

import MetaTrader5 as mt5
import pandas as pd
import openai
from dotenv import load_dotenv
from utils.indicators import calculate_all_indicators, get_indicator_interpretation

# Load environment variables
load_dotenv()

# === Configuration ===
SYMBOL = "EURUSD"            # trading symbol
TIMEFRAME = mt5.TIMEFRAME_M5 # 5-minute timeframe
BARS_COUNT = 300             # number of bars to retrieve for analysis
CYCLE_INTERVAL = 300         # seconds between cycles (5 minutes)

# Technical Indicator Parameters
RSI_PERIOD = 14
FAST_MA = 6
SLOW_MA = 13
MACD_SIGNAL = 5
BB_PERIOD = 20
BB_STDDEV = 2
SMA_FAST = 20
SMA_SLOW = 200

# Trading Parameters
MAX_VOLUME = 1.0             # maximum lot size
DEFAULT_VOLUME = 0.01        # default lot size
DEFAULT_SL_PIPS = 20         # default stop-loss in pips
DEFAULT_TP_PIPS = 50         # default take-profit in pips
MAX_SLIPPAGE = 10            # maximum slippage in points
MAGIC_NUMBER = 123456        # unique identifier for bot trades

# OpenAI Parameters
OPENAI_MODEL = "gpt-4"
OPENAI_TEMPERATURE = 0.0
OPENAI_MAX_TOKENS = 150

# Logging setup
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/trading_bot_single.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MT5GPTSingleBot:
    """Single-asset trading bot powered by GPT-4."""
    
    def __init__(self):
        self.symbol = SYMBOL
        self.running = False
        self.openai_client = None
        
    def initialize(self) -> bool:
        """Initialize MT5 connection and OpenAI client."""
        try:
            # Initialize MT5
            if not mt5.initialize():
                logger.error("MT5 initialize() failed, error code=%s", mt5.last_error())
                return False
            
            logger.info("MT5 initialized successfully")
            
            # Check symbol availability
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None:
                logger.error("Symbol %s not found", self.symbol)
                return False
            
            # Make symbol visible if needed
            if not symbol_info.visible:
                if not mt5.symbol_select(self.symbol, True):
                    logger.error("Failed to select symbol %s", self.symbol)
                    return False
            
            logger.info("Symbol %s is available and selected", self.symbol)
            
            # Initialize OpenAI client
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("OPENAI_API_KEY not found in environment variables")
                return False
            
            self.openai_client = openai.OpenAI(api_key=api_key)
            
            # Test OpenAI connection
            try:
                response = self.openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                )
                logger.info("OpenAI API connection successful")
            except Exception as e:
                logger.error("OpenAI API test failed: %s", e)
                return False
            
            return True
            
        except Exception as e:
            logger.error("Initialization failed: %s", e)
            return False
    
    def compute_indicators(self, df: pd.DataFrame) -> Optional[Dict]:
        """Compute technical indicators from price data using utils module."""
        try:
            # Create config with our specific parameters
            config = {
                'rsi_period': RSI_PERIOD,
                'macd_fast': FAST_MA,
                'macd_slow': SLOW_MA,
                'macd_signal': MACD_SIGNAL,
                'bb_period': BB_PERIOD,
                'bb_std_dev': BB_STDDEV,
                'sma_fast': SMA_FAST,
                'sma_slow': SMA_SLOW,
                'stoch_k': 14,  # %K period for Stochastic
                'stoch_d': 3,   # %D period for Stochastic  
                'atr_period': 14  # ATR period
            }
            
            # Use the centralized indicator calculation
            indicators = calculate_all_indicators(df, config)
            
            if indicators is None:
                logger.warning("Failed to compute indicators - insufficient data")
                return None
            
            return indicators
            
        except Exception as e:
            logger.error("Error computing indicators: %s", e)
            return None
    
    def create_prompt(self, latest_price: float, indicators: Dict) -> str:
        """Create GPT-4 prompt with market data and indicators."""
        # Calculate additional context
        macd_direction = "Bullish" if indicators['macd'] > indicators['macd_signal'] else "Bearish"
        bb_position = "Upper" if latest_price > indicators['bb_upper'] else "Lower" if latest_price < indicators['bb_lower'] else "Middle"
        trend_alignment = "Bullish" if indicators['sma_fast'] > indicators['sma_slow'] else "Bearish"
        price_vs_sma200 = f"{((latest_price/indicators['sma_slow']-1)*100):+.2f}%" if indicators['sma_slow'] else "N/A"
        
        # Stochastic interpretation
        stoch_status = "Overbought" if indicators.get('stoch_k', 50) > 80 else "Oversold" if indicators.get('stoch_k', 50) < 20 else "Neutral"
        
        # ATR for volatility context
        atr_pips = indicators.get('atr', 0) * 10000  # Convert to pips for major pairs
        
        prompt = f"""Asset: {self.symbol}, Timeframe: M5
Current Price: {latest_price:.5f}

Technical Analysis:
- RSI({RSI_PERIOD}): {indicators['rsi']:.1f} {'(Overbought Zone)' if indicators['rsi'] > 70 else '(Oversold Zone)' if indicators['rsi'] < 30 else '(Neutral Zone)'}
- MACD({FAST_MA},{SLOW_MA},{MACD_SIGNAL}): Line={indicators['macd']:.6f}, Signal={indicators['macd_signal']:.6f} → {macd_direction}
- Bollinger Bands({BB_PERIOD},{BB_STDDEV}): Upper={indicators['bb_upper']:.5f}, Middle={indicators['bb_middle']:.5f}, Lower={indicators['bb_lower']:.5f} → Price at {bb_position} band
- SMA({SMA_FAST}): {indicators['sma_fast']:.5f}
- SMA({SMA_SLOW}): {indicators['sma_slow']:.5f} → Price {price_vs_sma200} from SMA200
- Stochastic(14,3): %K={indicators.get('stoch_k', 0):.1f}, %D={indicators.get('stoch_d', 0):.1f} → {stoch_status}
- ATR(14): {indicators.get('atr', 0):.5f} ({atr_pips:.1f} pips) → Volatility measure

Market Context:
- Overall Trend: {trend_alignment} (SMA20 vs SMA200)
- MACD Momentum: {macd_direction}
- Volatility Zone: {bb_position} Bollinger Band  
- Stochastic Position: {stoch_status}
- Average Volatility: {atr_pips:.1f} pips (use for stop-loss sizing)
- Price vs Long-term Trend: {price_vs_sma200}

Based on this comprehensive technical analysis with momentum and volatility confirmation, what is your trading recommendation?

Respond ONLY in JSON format:
{{"action": "buy/sell/hold", "volume": 0.01, "stop_loss_pips": 20, "take_profit_pips": 50, "reasoning": "brief explanation"}}

Requirements:
- action: must be "buy", "sell", or "hold"
- volume: between 0.01 and {MAX_VOLUME}
- stop_loss_pips: reasonable stop loss in pips (10-100)
- take_profit_pips: reasonable take profit in pips (20-200)
- reasoning: brief explanation of your decision"""
        
        return prompt
    
    def call_gpt4(self, prompt: str) -> Optional[str]:
        """Call GPT-4 API with the trading prompt."""
        try:
            response = self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert forex trading analyst specializing in M5 (5-minute) timeframe analysis. 

Your technical analysis toolkit includes:
• RSI(14) - Momentum oscillator for overbought/oversold conditions (>70 overbought, <30 oversold)
• MACD(6,13,5) - Fast trend/momentum indicator with 6-period fast EMA, 13-period slow EMA, 5-period signal line
• Bollinger Bands(20,2) - Volatility indicator with 20-period SMA and 2 standard deviations
• SMA(20) - Short-term trend filter 
• SMA(200) - Long-term trend filter and major support/resistance
• Stochastic(14,3) - Momentum oscillator for confirming overbought/oversold (>80 overbought, <20 oversold)
• ATR(14) - Average True Range for measuring market volatility and sizing stops

Trading Guidelines:
- MACD crossovers provide entry signals, but confirm with trend direction (price vs SMA200)
- RSI extremes indicate potential reversal points, especially near Bollinger Band edges
- Stochastic provides momentum confirmation - align with RSI for stronger signals
- Price above SMA200 = uptrend bias, below = downtrend bias
- SMA20 vs SMA200 relationship shows overall trend strength
- Bollinger Band squeezes indicate low volatility before potential breakouts
- ATR guides stop-loss sizing: use 1.5-2x ATR for normal volatility, 1x ATR for high volatility
- Consider confluence of multiple indicators for higher probability trades

Signal Confluence Requirements:
- Strong Buy: RSI<70, MACD bullish, Price>SMA200, Stochastic not overbought
- Strong Sell: RSI>30, MACD bearish, Price<SMA200, Stochastic not oversold
- Avoid trades when RSI and Stochastic both show extreme readings (potential reversal)

Risk Management:
- Default position size: 0.01 lots, maximum 1.0 lots
- Stop losses: Use ATR-based sizing (1-2x ATR), minimum 10 pips, maximum 100 pips
- Take profits: 20-200 pips, preferably 1.5-3x the stop loss distance
- Risk-reward ratio should be at least 1:1.5, preferably 1:2 or better
- Be conservative during high-impact news events or low liquidity periods

Respond ONLY in JSON format with clear reasoning for your decision."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=OPENAI_TEMPERATURE,
                max_tokens=OPENAI_MAX_TOKENS
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error("OpenAI API call failed: %s", e)
            return None
    
    def parse_gpt_response(self, response: str) -> Optional[Dict]:
        """Parse GPT-4 response and extract trading decision."""
        try:
            # Try to parse as JSON first
            try:
                decision = json.loads(response)
                return {
                    "action": decision.get("action", "").lower(),
                    "volume": float(decision.get("volume", DEFAULT_VOLUME)),
                    "stop_loss_pips": float(decision.get("stop_loss_pips", DEFAULT_SL_PIPS)),
                    "take_profit_pips": float(decision.get("take_profit_pips", DEFAULT_TP_PIPS)),
                    "reasoning": decision.get("reasoning", "No reasoning provided")
                }
            except json.JSONDecodeError:
                # Fallback to regex parsing
                logger.warning("Failed to parse JSON, attempting regex parsing")
                
                text = response.lower()
                
                # Extract action
                action = None
                if "buy" in text and "sell" not in text:
                    action = "buy"
                elif "sell" in text and "buy" not in text:
                    action = "sell"
                elif "hold" in text:
                    action = "hold"
                
                # Extract numbers
                volume_match = re.search(r"volume[\":\s]+([0-9]*\.?[0-9]+)", text)
                sl_match = re.search(r"stop_?loss_?pips[\":\s]+([0-9]*\.?[0-9]+)", text)
                tp_match = re.search(r"take_?profit_?pips[\":\s]+([0-9]*\.?[0-9]+)", text)
                
                volume = float(volume_match.group(1)) if volume_match else DEFAULT_VOLUME
                sl_pips = float(sl_match.group(1)) if sl_match else DEFAULT_SL_PIPS
                tp_pips = float(tp_match.group(1)) if tp_match else DEFAULT_TP_PIPS
                
                return {
                    "action": action,
                    "volume": volume,
                    "stop_loss_pips": sl_pips,
                    "take_profit_pips": tp_pips,
                    "reasoning": "Parsed from text response"
                }
                
        except Exception as e:
            logger.error("Error parsing GPT response: %s", e)
            return None
    
    def validate_trade_decision(self, decision: Dict) -> bool:
        """Validate the trading decision parameters."""
        if not decision:
            return False
        
        action = decision.get("action")
        if action not in ["buy", "sell", "hold"]:
            logger.warning("Invalid action: %s", action)
            return False
        
        if action == "hold":
            return True  # No further validation needed for hold
        
        volume = decision.get("volume", 0)
        if volume <= 0 or volume > MAX_VOLUME:
            logger.warning("Invalid volume: %s (must be between 0 and %s)", volume, MAX_VOLUME)
            return False
        
        sl_pips = decision.get("stop_loss_pips", 0)
        tp_pips = decision.get("take_profit_pips", 0)
        
        if sl_pips <= 0 or sl_pips > 100:
            logger.warning("Invalid stop loss pips: %s (must be between 0 and 100)", sl_pips)
            return False
        
        if tp_pips <= 0 or tp_pips > 200:
            logger.warning("Invalid take profit pips: %s (must be between 0 and 200)", tp_pips)
            return False
        
        return True
    
    def calculate_prices(self, action: str, entry_price: float, sl_pips: float, tp_pips: float) -> Dict:
        """Calculate stop loss and take profit prices from pips."""
        symbol_info = mt5.symbol_info(self.symbol)
        if not symbol_info:
            raise ValueError(f"Cannot get symbol info for {self.symbol}")
        
        # Calculate pip value based on symbol digits
        if symbol_info.digits in (3, 5):
            pip_value = 0.0001 if symbol_info.digits == 5 else 0.01
        else:
            pip_value = 0.01 if symbol_info.digits == 3 else 0.0001
        
        if action == "buy":
            sl_price = entry_price - (sl_pips * pip_value)
            tp_price = entry_price + (tp_pips * pip_value)
        else:  # sell
            sl_price = entry_price + (sl_pips * pip_value)
            tp_price = entry_price - (tp_pips * pip_value)
        
        return {
            "sl_price": round(sl_price, symbol_info.digits),
            "tp_price": round(tp_price, symbol_info.digits)
        }
    
    def execute_trade(self, decision: Dict) -> bool:
        """Execute the trading decision via MT5."""
        try:
            action = decision["action"]
            volume = decision["volume"]
            sl_pips = decision["stop_loss_pips"]
            tp_pips = decision["take_profit_pips"]
            
            # Get current market prices
            tick = mt5.symbol_info_tick(self.symbol)
            if not tick:
                logger.error("Failed to get tick data for %s", self.symbol)
                return False
            
            # Determine entry price and order type
            if action == "buy":
                entry_price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY
            else:  # sell
                entry_price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
            
            # Calculate SL and TP prices
            prices = self.calculate_prices(action, entry_price, sl_pips, tp_pips)
            sl_price = prices["sl_price"]
            tp_price = prices["tp_price"]
            
            # Final validation of SL/TP prices
            if action == "buy":
                if sl_price >= entry_price or tp_price <= entry_price:
                    logger.error("Invalid SL/TP for buy: SL=%.5f, Entry=%.5f, TP=%.5f", 
                               sl_price, entry_price, tp_price)
                    return False
            else:  # sell
                if sl_price <= entry_price or tp_price >= entry_price:
                    logger.error("Invalid SL/TP for sell: SL=%.5f, Entry=%.5f, TP=%.5f", 
                               sl_price, entry_price, tp_price)
                    return False
            
            # Prepare order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": volume,
                "type": order_type,
                "price": entry_price,
                "sl": sl_price,
                "tp": tp_price,
                "deviation": MAX_SLIPPAGE,
                "magic": MAGIC_NUMBER,
                "comment": f"GPT4_bot_{action}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_RETURN,
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error("Trade execution failed: retcode=%s, description=%s", 
                           result.retcode, result.comment)
                return False
            else:
                logger.info("Trade executed successfully: %s %.2f lots at %.5f (SL=%.5f, TP=%.5f)", 
                          action.upper(), volume, entry_price, sl_price, tp_price)
                logger.info("Order ticket: %s, Deal: %s", result.order, result.deal)
                return True
                
        except Exception as e:
            logger.error("Error executing trade: %s", e)
            return False
    
    def run_cycle(self) -> bool:
        """Run one complete trading cycle."""
        try:
            logger.info("Starting trading cycle for %s", self.symbol)
            
            # Get market data
            rates = mt5.copy_rates_from_pos(self.symbol, TIMEFRAME, 0, BARS_COUNT)
            if rates is None:
                logger.error("Failed to retrieve data for %s: %s", self.symbol, mt5.last_error())
                return False
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Compute indicators
            indicators = self.compute_indicators(df)
            if not indicators:
                logger.warning("Failed to compute indicators, skipping cycle")
                return False
            
            # Get latest price
            latest_price = float(df['close'].iloc[-1])
            
            # Create prompt for GPT-4
            prompt = self.create_prompt(latest_price, indicators)
            logger.info("Created prompt for GPT-4")
            
            # Call GPT-4
            gpt_response = self.call_gpt4(prompt)
            if not gpt_response:
                logger.error("Failed to get GPT-4 response")
                return False
            
            logger.info("GPT-4 response: %s", gpt_response)
            
            # Parse response
            decision = self.parse_gpt_response(gpt_response)
            if not decision:
                logger.error("Failed to parse GPT-4 response")
                return False
            
            logger.info("Parsed decision: %s", decision)
            
            # Validate decision
            if not self.validate_trade_decision(decision):
                logger.warning("Invalid trade decision, skipping execution")
                return False
            
            # Execute trade if not hold
            if decision["action"] == "hold":
                logger.info("GPT-4 recommends HOLD - no trade executed")
                return True
            else:
                success = self.execute_trade(decision)
                return success
                
        except Exception as e:
            logger.error("Error in trading cycle: %s", e)
            return False
    
    def run(self):
        """Main bot loop."""
        logger.info("Starting GPT-4 MetaTrader5 Single-Asset Trading Bot")
        logger.info("Symbol: %s, Timeframe: %s, Cycle Interval: %ds", 
                   self.symbol, "M5", CYCLE_INTERVAL)
        
        if not self.initialize():
            logger.error("Bot initialization failed")
            return
        
        self.running = True
        
        try:
            while self.running:
                success = self.run_cycle()
                
                if success:
                    logger.info("Cycle completed successfully")
                else:
                    logger.warning("Cycle completed with errors")
                
                # Wait for next cycle
                logger.info("Waiting %d seconds for next cycle...", CYCLE_INTERVAL)
                time.sleep(CYCLE_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error("Unexpected error in main loop: %s", e)
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown the bot."""
        logger.info("Shutting down bot...")
        self.running = False
        mt5.shutdown()
        logger.info("Bot shutdown complete")


def main():
    """Main entry point."""
    bot = MT5GPTSingleBot()
    try:
        bot.run()
    except Exception as e:
        logger.error("Fatal error: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    exit(main())