#!/usr/bin/env python3
"""
GPT-4 Powered MetaTrader5 Portfolio Trading Bot

This bot manages multiple trading symbols, fetches M5 data for each,
computes technical indicators, and uses GPT-4 to make trading decisions.

Author: GPT-4 MetaTrader5 Trading Bot
Version: 1.0.0
"""

import os
import time
import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Union

import MetaTrader5 as mt5
import pandas as pd
import openai
from dotenv import load_dotenv
from utils.indicators import calculate_all_indicators, get_indicator_interpretation
from utils.data_manager import create_data_manager, save_cycle_data

# Load environment variables
load_dotenv()

# === Configuration ===
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD"]  # Trading symbols
TIMEFRAME = mt5.TIMEFRAME_M5  # 5-minute timeframe
BARS_COUNT = 300              # number of bars to retrieve for analysis
CYCLE_INTERVAL = 300          # seconds between cycles (5 minutes)
SYMBOL_DELAY = 30             # seconds delay between symbols in same cycle

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
MAX_VOLUME = 0.5              # maximum lot size per trade
DEFAULT_VOLUME = 0.01         # default lot size
DEFAULT_SL_PIPS = 20          # default stop-loss in pips
DEFAULT_TP_PIPS = 50          # default take-profit in pips
MAX_SLIPPAGE = 20             # maximum slippage in points
MAGIC_NUMBER = 789012         # unique identifier for bot trades

# Risk Management
MAX_DAILY_TRADES = 10         # maximum trades per day
MAX_OPEN_POSITIONS = 5        # maximum concurrent positions

# Data Storage Configuration
ENABLE_DATA_STORAGE = os.getenv("ENABLE_DATA_STORAGE", "true").lower() == "true"
SAVE_MARKET_DATA = os.getenv("SAVE_MARKET_DATA", "false").lower() == "true"

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
        logging.FileHandler("logs/trading_bot_portfolio.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MT5GPTPortfolioBot:
    """Multi-asset portfolio trading bot powered by GPT-4."""
    
    def __init__(self):
        self.symbols = SYMBOLS
        self.running = False
        self.openai_client = None
        self.daily_trades = 0
        self.last_trade_date = None
        
        # Initialize optional data storage
        self.data_manager = create_data_manager(enabled=ENABLE_DATA_STORAGE)
        if ENABLE_DATA_STORAGE:
            logger.info("Portfolio data storage enabled - historical data will be saved")
        
    def initialize(self) -> bool:
        """Initialize MT5 connection and OpenAI client."""
        try:
            # Initialize MT5
            if not mt5.initialize():
                logger.error("MT5 initialize() failed, error code=%s", mt5.last_error())
                return False
            
            logger.info("MT5 initialized successfully")
            
            # Check all symbols availability
            available_symbols = []
            for symbol in self.symbols:
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info is None:
                    logger.warning("Symbol %s not found, skipping", symbol)
                    continue
                
                # Make symbol visible if needed
                if not symbol_info.visible:
                    if not mt5.symbol_select(symbol, True):
                        logger.warning("Failed to select symbol %s, skipping", symbol)
                        continue
                
                available_symbols.append(symbol)
                logger.info("Symbol %s is available and selected", symbol)
            
            if not available_symbols:
                logger.error("No trading symbols available")
                return False
            
            self.symbols = available_symbols
            logger.info("Trading symbols: %s", self.symbols)
            
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
    
    def create_prompt(self, symbol: str, latest_price: float, indicators: Dict) -> str:
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
        
        # Currency analysis
        base_currency = symbol[:3]
        quote_currency = symbol[3:]
        currency_context = f"{base_currency} vs {quote_currency}"
        
        prompt = f"""Asset: {symbol} ({currency_context}), Timeframe: M5, Portfolio Context
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

Portfolio Considerations:
- Currency Pair: {currency_context}
- This trade affects portfolio exposure to {base_currency} strength and {quote_currency} weakness
- Consider correlation with other USD, EUR, GBP, JPY, CHF, AUD positions
- Maximum portfolio limits: 5 open positions, 10 daily trades across all pairs
- ATR-based position sizing: Lower volatility pairs can take larger positions

Based on this comprehensive technical analysis with momentum, volatility confirmation, and portfolio impact, what is your trading recommendation for {symbol}?

Respond ONLY in JSON format:
{{"action": "buy/sell/hold", "volume": 0.01, "stop_loss_pips": 20, "take_profit_pips": 50, "reasoning": "brief explanation"}}

Requirements:
- action: must be "buy", "sell", or "hold"
- volume: between 0.01 and {MAX_VOLUME}
- stop_loss_pips: reasonable stop loss in pips (10-50)
- take_profit_pips: reasonable take profit in pips (20-100)
- reasoning: brief explanation focusing on key indicators"""
        
        return prompt
    
    def call_gpt4(self, prompt: str) -> Optional[str]:
        """Call GPT-4 API with the trading prompt."""
        try:
            response = self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert forex portfolio manager specializing in M5 (5-minute) multi-asset analysis across major currency pairs: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD.

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

Portfolio-Specific Considerations:
- EUR pairs (EURUSD) often correlate positively with each other
- USD pairs (USDJPY, USDCHF) may show inverse correlation to EUR pairs
- Commodity currencies (AUDUSD) can behave differently during risk-on/risk-off sentiment
- Avoid overexposure to USD strength/weakness across multiple positions
- Maximum 5 open positions, 10 trades per day across all pairs
- Consider market sessions: Asian (low volatility), London (high volatility), NY (high volatility)
- Use ATR to adjust position sizes: lower volatility pairs can have slightly larger positions

Risk Management:
- Default position size: 0.01 lots, maximum 0.5 lots per trade (lower than single-asset bot)
- Stop losses: Use ATR-based sizing (1-2x ATR), minimum 10 pips, maximum 50 pips (tighter for portfolio)
- Take profits: 20-100 pips, preferably 1.5-3x the stop loss distance
- Diversify risk across currency groups rather than concentrating in correlated pairs
- Be extra conservative during major news events affecting multiple currencies

Respond ONLY in JSON format with clear reasoning considering both technical analysis and portfolio impact."""
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
                
                # Extract numbers using regex
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
    
    def check_risk_limits(self) -> bool:
        """Check portfolio risk limits before trading."""
        # Check daily trade limit
        current_date = datetime.now().date()
        if self.last_trade_date != current_date:
            self.daily_trades = 0
            self.last_trade_date = current_date
        
        if self.daily_trades >= MAX_DAILY_TRADES:
            logger.warning("Daily trade limit reached (%d trades)", MAX_DAILY_TRADES)
            return False
        
        # Check open positions limit
        positions = mt5.positions_get()
        if positions and len(positions) >= MAX_OPEN_POSITIONS:
            logger.warning("Maximum open positions limit reached (%d positions)", MAX_OPEN_POSITIONS)
            return False
        
        return True
    
    def calculate_prices(self, symbol: str, action: str, entry_price: float, sl_pips: float, tp_pips: float) -> Dict:
        """Calculate stop loss and take profit prices from pips."""
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            raise ValueError(f"Cannot get symbol info for {symbol}")
        
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
    
    def execute_trade(self, symbol: str, decision: Dict) -> bool:
        """Execute the trading decision via MT5."""
        try:
            action = decision["action"]
            volume = decision["volume"]
            sl_pips = decision["stop_loss_pips"]
            tp_pips = decision["take_profit_pips"]
            
            # Get current market prices
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                logger.error("Failed to get tick data for %s", symbol)
                return False
            
            # Determine entry price and order type
            if action == "buy":
                entry_price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY
            else:  # sell
                entry_price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
            
            # Calculate SL and TP prices
            prices = self.calculate_prices(symbol, action, entry_price, sl_pips, tp_pips)
            sl_price = prices["sl_price"]
            tp_price = prices["tp_price"]
            
            # Final validation of SL/TP prices
            if action == "buy":
                if sl_price >= entry_price or tp_price <= entry_price:
                    logger.error("Invalid SL/TP for %s buy: SL=%.5f, Entry=%.5f, TP=%.5f", 
                               symbol, sl_price, entry_price, tp_price)
                    return False
            else:  # sell
                if sl_price <= entry_price or tp_price >= entry_price:
                    logger.error("Invalid SL/TP for %s sell: SL=%.5f, Entry=%.5f, TP=%.5f", 
                               symbol, sl_price, entry_price, tp_price)
                    return False
            
            # Prepare order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": entry_price,
                "sl": sl_price,
                "tp": tp_price,
                "deviation": MAX_SLIPPAGE,
                "magic": MAGIC_NUMBER,
                "comment": f"GPT4_portfolio_{action}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_RETURN,
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error("Trade execution failed for %s: retcode=%s, description=%s", 
                           symbol, result.retcode, result.comment)
                return False
            else:
                logger.info("%s -> %s %.2f lots at %.5f (SL=%.5f, TP=%.5f)", 
                          symbol, action.upper(), volume, entry_price, sl_price, tp_price)
                logger.info("Order ticket: %s, Deal: %s", result.order, result.deal)
                self.daily_trades += 1
                return True
                
        except Exception as e:
            logger.error("Error executing trade for %s: %s", symbol, e)
            return False
    
    def process_symbol(self, symbol: str) -> bool:
        """Process one symbol through the complete trading cycle."""
        try:
            logger.info("Processing symbol: %s", symbol)
            
            # Get market data
            rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, BARS_COUNT)
            if rates is None:
                logger.error("Failed to retrieve data for %s: %s", symbol, mt5.last_error())
                return False
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Compute indicators
            indicators = self.compute_indicators(df)
            if not indicators:
                logger.warning("Failed to compute indicators for %s, skipping", symbol)
                return False
            
            # Get latest price
            latest_price = float(df['close'].iloc[-1])
            
            # Create prompt for GPT-4
            prompt = self.create_prompt(symbol, latest_price, indicators)
            
            # Call GPT-4
            gpt_response = self.call_gpt4(prompt)
            if not gpt_response:
                logger.error("Failed to get GPT-4 response for %s", symbol)
                return False
            
            logger.info("%s GPT-4 response: %s", symbol, gpt_response)
            
            # Parse response
            decision = self.parse_gpt_response(gpt_response)
            if not decision:
                logger.error("Failed to parse GPT-4 response for %s", symbol)
                return False
            
            logger.info("%s decision: %s", symbol, decision)
            
            # Validate decision
            if not self.validate_trade_decision(decision):
                logger.warning("Invalid trade decision for %s, skipping", symbol)
                return False
            
            # Save cycle data (optional, non-blocking)
            try:
                if SAVE_MARKET_DATA:
                    save_cycle_data(self.data_manager, symbol, df, indicators, prompt, gpt_response, decision)
                else:
                    # Save only indicators and decisions (lighter storage)
                    timestamp = datetime.now()
                    self.data_manager.save_indicators(symbol, timestamp, indicators)
                    self.data_manager.save_gpt_decision(symbol, timestamp, prompt, gpt_response, decision)
            except Exception as e:
                logger.warning(f"Failed to save cycle data for {symbol}: {e}")
                # Continue execution - don't let storage issues stop trading
            
            # Execute trade if not hold and risk limits allow
            if decision["action"] == "hold":
                logger.info("%s -> HOLD - no trade executed", symbol)
                return True
            else:
                if not self.check_risk_limits():
                    logger.warning("Risk limits exceeded, skipping trade for %s", symbol)
                    return False
                
                success = self.execute_trade(symbol, decision)
                
                # Save trade execution data if successful
                try:
                    if success and decision["action"] in ["buy", "sell"]:
                        execution_result = {"success": True, "action": decision["action"]}
                        self.data_manager.save_trade_execution(symbol, datetime.now(), decision, execution_result)
                except Exception as e:
                    logger.warning(f"Failed to save trade execution data for {symbol}: {e}")
                
                return success
                
        except Exception as e:
            logger.error("Error processing symbol %s: %s", symbol, e)
            return False
    
    def run_cycle(self) -> bool:
        """Run one complete portfolio trading cycle."""
        try:
            logger.info("Starting portfolio trading cycle")
            cycle_success = True
            
            for i, symbol in enumerate(self.symbols):
                success = self.process_symbol(symbol)
                if not success:
                    cycle_success = False
                
                # Add delay between symbols to avoid API rate limits
                if i < len(self.symbols) - 1:  # Don't delay after last symbol
                    logger.info("Waiting %d seconds before processing next symbol...", SYMBOL_DELAY)
                    time.sleep(SYMBOL_DELAY)
            
            return cycle_success
            
        except Exception as e:
            logger.error("Error in portfolio trading cycle: %s", e)
            return False
    
    def log_portfolio_status(self):
        """Log current portfolio status."""
        try:
            positions = mt5.positions_get()
            if positions:
                logger.info("Current positions: %d", len(positions))
                total_profit = sum(pos.profit for pos in positions)
                logger.info("Total unrealized P&L: %.2f", total_profit)
            else:
                logger.info("No open positions")
            
            logger.info("Daily trades executed: %d/%d", self.daily_trades, MAX_DAILY_TRADES)
            
        except Exception as e:
            logger.error("Error logging portfolio status: %s", e)
    
    def run(self):
        """Main bot loop."""
        logger.info("Starting GPT-4 MetaTrader5 Portfolio Trading Bot")
        logger.info("Symbols: %s", self.symbols)
        logger.info("Timeframe: M5, Cycle Interval: %ds", CYCLE_INTERVAL)
        logger.info("Risk Limits: Max daily trades=%d, Max positions=%d", 
                   MAX_DAILY_TRADES, MAX_OPEN_POSITIONS)
        
        if not self.initialize():
            logger.error("Bot initialization failed")
            return
        
        self.running = True
        
        try:
            while self.running:
                success = self.run_cycle()
                
                if success:
                    logger.info("Portfolio cycle completed successfully")
                else:
                    logger.warning("Portfolio cycle completed with errors")
                
                # Log portfolio status
                self.log_portfolio_status()
                
                # Wait for next cycle
                logger.info("Waiting %d seconds for next portfolio cycle...", CYCLE_INTERVAL)
                time.sleep(CYCLE_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error("Unexpected error in main loop: %s", e)
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown the bot."""
        logger.info("Shutting down portfolio bot...")
        self.running = False
        mt5.shutdown()
        logger.info("Portfolio bot shutdown complete")


def main():
    """Main entry point."""
    bot = MT5GPTPortfolioBot()
    try:
        bot.run()
    except Exception as e:
        logger.error("Fatal error: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    exit(main())