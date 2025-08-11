#!/usr/bin/env python3
"""
Enhanced GPT-4 Powered MetaTrader5 Trading Bot - Professional Edition

Complete transformation with:
- Risk-based position sizing (0.15% per trade)
- Daily guardrails and risk controls  
- Entry quality gates and filters
- Mechanical trade management
- Comprehensive performance tracking

Author: GPT-4 MetaTrader5 Trading Bot
Version: 3.0.0 - Professional Enhancement
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, Optional

import MetaTrader5 as mt5
import pandas as pd
import openai
from dotenv import load_dotenv

# Import our enhanced utility modules
from utils.indicators import calculate_all_indicators, calculate_ema, calculate_atr
from utils.risk_sizing import RiskBasedSizing
from utils.daily_guardrails import DailyGuardrails
from utils.entry_gates import EntryQualityGates
from utils.trade_manager import TradeManager
from utils.trade_telemetry import TradeTelemetry
from utils.data_manager import create_data_manager

# Load environment variables
load_dotenv()

# === ENHANCED CONFIGURATION ===
SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
CONFIRMATION_TIMEFRAME = mt5.TIMEFRAME_M15
BARS_COUNT = 300
CONFIRMATION_BARS = 50
CYCLE_INTERVAL = 300  # 5 minutes

# Technical Indicators
RSI_PERIOD = 14
FAST_MA = 6
SLOW_MA = 13
MACD_SIGNAL = 5
BB_PERIOD = 20
BB_STDDEV = 2
SMA_SLOW = 200
EMA_FAST = 9
EMA_SLOW = 21

# Professional Trading Parameters
RISK_PER_TRADE_PCT = 0.15     # 0.15% risk per trade
MAX_VOLUME = 0.05             # Conservative max until live stats justify more
MAGIC_NUMBER = 123457
MAX_SLIPPAGE = 10

# OpenAI Parameters
OPENAI_MODEL = "gpt-4"
OPENAI_TEMPERATURE = 0.0
OPENAI_MAX_TOKENS = 200

# Logging setup
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/trading_bot_enhanced.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EnhancedMT5TradingBot:
    """Professional trading bot with comprehensive risk management."""
    
    def __init__(self):
        self.symbol = SYMBOL
        self.running = False
        self.openai_client = None
        self.current_trade_id = None
        
        # Initialize all professional systems
        self.risk_sizer = RiskBasedSizing(
            default_risk_pct=RISK_PER_TRADE_PCT,
            max_volume=MAX_VOLUME
        )
        self.guardrails = DailyGuardrails()
        self.entry_gates = EntryQualityGates()
        self.trade_manager = TradeManager()
        self.telemetry = TradeTelemetry()
        
        # Optional data storage
        self.data_manager = create_data_manager(enabled=True)
        
        logger.info("Enhanced Professional Trading Bot initialized")
        logger.info(f"Risk per trade: {RISK_PER_TRADE_PCT}%, Max volume: {MAX_VOLUME}")
    
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
            
            if not symbol_info.visible:
                if not mt5.symbol_select(self.symbol, True):
                    logger.error("Failed to select symbol %s", self.symbol)
                    return False
            
            logger.info("Symbol %s is available", self.symbol)
            
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
    
    def get_multi_timeframe_data(self) -> Optional[Dict]:
        """Get M15 timeframe data for confirmation."""
        try:
            rates_m15 = mt5.copy_rates_from_pos(self.symbol, CONFIRMATION_TIMEFRAME, 0, CONFIRMATION_BARS)
            if rates_m15 is None:
                logger.warning("Failed to retrieve M15 data")
                return None
            
            df_m15 = pd.DataFrame(rates_m15)
            df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s')
            
            ema_fast_m15 = calculate_ema(df_m15['close'], EMA_FAST)
            ema_slow_m15 = calculate_ema(df_m15['close'], EMA_SLOW)
            
            if ema_fast_m15.empty or ema_slow_m15.empty:
                return None
            
            return {
                'ema_fast_m15': float(ema_fast_m15.iloc[-1]),
                'ema_slow_m15': float(ema_slow_m15.iloc[-1]),
                'trend_m15': 'bullish' if ema_fast_m15.iloc[-1] > ema_slow_m15.iloc[-1] else 'bearish'
            }
            
        except Exception as e:
            logger.error("Error getting M15 data: %s", e)
            return None
    
    def compute_indicators(self, df: pd.DataFrame) -> Optional[Dict]:
        """Compute technical indicators."""
        try:
            config = {
                'rsi_period': RSI_PERIOD,
                'macd_fast': FAST_MA,
                'macd_slow': SLOW_MA,
                'macd_signal': MACD_SIGNAL,
                'bb_period': BB_PERIOD,
                'bb_std_dev': BB_STDDEV,
                'sma_slow': SMA_SLOW,
                'stoch_k': 14,
                'stoch_d': 3,
                'atr_period': 14
            }
            
            indicators = calculate_all_indicators(df, config)
            if indicators is None:
                return None
            
            # Add EMA calculations
            ema_fast = calculate_ema(df['close'], EMA_FAST)
            ema_slow = calculate_ema(df['close'], EMA_SLOW)
            
            if not ema_fast.empty and not ema_slow.empty:
                indicators['ema_fast'] = float(ema_fast.iloc[-1])
                indicators['ema_slow'] = float(ema_slow.iloc[-1])
            else:
                return None
            
            return indicators
            
        except Exception as e:
            logger.error("Error computing indicators: %s", e)
            return None
    
    def create_enhanced_prompt(self, latest_price: float, indicators: Dict, m15_data: Optional[Dict] = None) -> str:
        """Create enhanced GPT-4 prompt WITHOUT volume requests."""
        
        # Calculate analysis context
        macd_direction = "Bullish" if indicators['macd'] > indicators['macd_signal'] else "Bearish"
        
        # Enhanced Bollinger Band position
        bb_range = indicators['bb_upper'] - indicators['bb_lower']
        bb_position_ratio = (latest_price - indicators['bb_lower']) / bb_range
        
        if latest_price > indicators['bb_upper']:
            bb_position = "Above Upper Band (Extreme Overbought)"
        elif latest_price < indicators['bb_lower']:
            bb_position = "Below Lower Band (Extreme Oversold)"
        elif bb_position_ratio < 0.25:
            bb_position = "Lower Quarter (Mean Reversion Zone)"
        elif bb_position_ratio < 0.4:
            bb_position = "Lower Third"
        elif bb_position_ratio < 0.6:
            bb_position = "Middle Band (Neutral Zone)"
        elif bb_position_ratio < 0.75:
            bb_position = "Upper Third"
        else:
            bb_position = "Upper Quarter (Mean Reversion Zone)"
        
        # EMA analysis
        ema_trend = "Bullish" if indicators['ema_fast'] > indicators['ema_slow'] else "Bearish"
        ema_separation = abs(indicators['ema_fast'] - indicators['ema_slow'])
        
        # Multi-timeframe alignment
        m15_status = "N/A"
        m15_alignment = "Unknown"
        if m15_data:
            m15_status = f"M15 EMA({EMA_FAST})={m15_data['ema_fast_m15']:.5f}, EMA({EMA_SLOW})={m15_data['ema_slow_m15']:.5f} → {m15_data['trend_m15'].title()}"
            m5_bullish = indicators['ema_fast'] > indicators['ema_slow']
            m15_bullish = m15_data['trend_m15'] == 'bullish'
            m15_alignment = "Aligned" if m5_bullish == m15_bullish else "Conflicted"
        
        # ATR context
        atr_pips = indicators.get('atr', 0) * 10000
        
        prompt = f"""Professional Trading Analysis: {self.symbol}

MARKET DATA:
Current Price: {latest_price:.5f}

TECHNICAL INDICATORS:
• RSI({RSI_PERIOD}): {indicators['rsi']:.1f} {'(Overbought)' if indicators['rsi'] > 70 else '(Oversold)' if indicators['rsi'] < 30 else '(Neutral)'}
• MACD({FAST_MA},{SLOW_MA},{MACD_SIGNAL}): Line={indicators['macd']:.6f}, Signal={indicators['macd_signal']:.6f} → {macd_direction}
• Bollinger Bands({BB_PERIOD},{BB_STDDEV}): {bb_position}
  - Upper: {indicators['bb_upper']:.5f}
  - Middle: {indicators['bb_middle']:.5f}  
  - Lower: {indicators['bb_lower']:.5f}
• EMA Crossover({EMA_FAST},{EMA_SLOW}): Fast={indicators['ema_fast']:.5f}, Slow={indicators['ema_slow']:.5f} → {ema_trend}
  - Separation: {ema_separation:.5f}
• SMA({SMA_SLOW}): {indicators['sma_slow']:.5f}
• Stochastic(14,3): %K={indicators.get('stoch_k', 0):.1f}, %D={indicators.get('stoch_d', 0):.1f}
• ATR(14): {indicators.get('atr', 0):.5f} ({atr_pips:.1f} pips)

MULTI-TIMEFRAME ANALYSIS:
• M5 EMA Trend: {ema_trend}
• M15 Status: {m15_status}
• Timeframe Alignment: {m15_alignment}

CRITICAL REQUIREMENTS:
1. EMA ALIGNMENT: State both M5 and M15 EMA trend direction
2. BB ZONE: Specify exact Bollinger Band position  
3. RSI STATE: Note if RSI is in extreme territory (>70 or <30)

Based on this analysis, provide your trading recommendation.

Respond ONLY in JSON format:
{{"action": "buy/sell/hold", "reasoning": "MUST include EMA alignment, BB zone, and RSI state"}}

IMPORTANT: 
- DO NOT include volume, stop_loss_pips, or take_profit_pips in your response
- Position sizing and exits are handled automatically by risk management systems
- Focus ONLY on trade direction (buy/sell/hold) and detailed reasoning"""
        
        return prompt
    
    def call_gpt4(self, prompt: str) -> Optional[str]:
        """Call GPT-4 API with enhanced system message."""
        try:
            response = self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional forex analyst providing trade direction advice for EURUSD.

ANALYSIS FRAMEWORK:
• EMA(9,21) Crossover: Primary trend identification
• Multi-timeframe Alignment: M5 and M15 must agree for high-probability trades
• Bollinger Bands: Mean reversion and volatility analysis
• RSI/Stochastic: Momentum confirmation and extreme detection

TRADE DECISION RULES:
• STRONG BUY: EMA(9) > EMA(21) on BOTH M5 and M15, price not at upper BB extreme, RSI < 70
• STRONG SELL: EMA(9) < EMA(21) on BOTH M5 and M15, price not at lower BB extreme, RSI > 30
• HOLD: Conflicting signals, extreme levels, or insufficient confluence

MEAN REVERSION PROTECTION:
• AVOID buying when price is above upper Bollinger Band
• AVOID selling when price is below lower Bollinger Band
• At BB extremes, wait for price to return toward middle band

REQUIRED OUTPUT:
• action: "buy", "sell", or "hold" ONLY
• reasoning: MUST explain EMA alignment, BB position, and RSI state

Focus purely on trade direction. Position sizing, stops, and exits are handled by automated risk management systems."""
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
        """Parse GPT-4 response - only extract action and reasoning."""
        try:
            response = response.strip()
            
            # Try JSON parsing
            import json
            try:
                decision = json.loads(response)
                action = decision.get("action", "").lower()
                reasoning = decision.get("reasoning", "No reasoning provided")
                
                # Validate action
                if action not in ["buy", "sell", "hold"]:
                    logger.warning("Invalid action in GPT response: %s", action)
                    return None
                
                # Check if reasoning contains required elements (more flexible)
                reasoning_lower = reasoning.lower()
                
                # Check for EMA mentions
                has_ema = any(term in reasoning_lower for term in ["ema", "moving average", "crossover"])
                
                # Check for Bollinger Band mentions  
                has_bb = any(term in reasoning_lower for term in ["bb", "bollinger", "band", "upper", "lower", "middle"])
                
                # Check for RSI mentions
                has_rsi = any(term in reasoning_lower for term in ["rsi", "overbought", "oversold", "momentum"])
                
                missing_elements = []
                if not has_ema:
                    missing_elements.append("EMA/moving average")
                if not has_bb:
                    missing_elements.append("Bollinger Band")
                if not has_rsi:
                    missing_elements.append("RSI/momentum")
                
                if missing_elements:
                    logger.warning("Reasoning missing required elements: %s", missing_elements)
                    return None
                
                return {
                    "action": action,
                    "reasoning": reasoning
                }
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON response, trying text parsing")
                
                # Fallback text parsing
                text = response.lower()
                action = None
                
                if "buy" in text and "sell" not in text:
                    action = "buy"
                elif "sell" in text and "buy" not in text:
                    action = "sell"
                elif "hold" in text:
                    action = "hold"
                
                if action:
                    return {
                        "action": action,
                        "reasoning": "Parsed from text response"
                    }
                
                return None
                
        except Exception as e:
            logger.error("Error parsing GPT response: %s", e)
            return None
    
    def execute_trade(self, decision: Dict, indicators: Dict, current_price: float) -> bool:
        """Execute trade with professional risk management."""
        try:
            action = decision["action"]
            
            # Calculate ATR-based SL/TP levels
            atr_value = indicators.get('atr', 0.0001)
            rsi_value = indicators.get('rsi', 50.0)
            
            trade_levels = self.trade_manager.calculate_atr_based_levels(
                symbol=self.symbol,
                action=action,
                entry_price=current_price,
                atr_value=atr_value,
                rsi_value=rsi_value
            )
            
            if not trade_levels:
                logger.error("Failed to calculate trade levels")
                return False
            
            sl_pips = trade_levels['sl_pips']
            
            # Calculate risk-based position size
            sizing_result = self.risk_sizer.calc_position_size(
                symbol=self.symbol,
                sl_pips=sl_pips,
                risk_pct=RISK_PER_TRADE_PCT
            )
            
            if not sizing_result['valid']:
                logger.error("Invalid position sizing: %s", sizing_result['reasoning'])
                return False
            
            volume = sizing_result['volume']
            sl_price = trade_levels['sl_price']
            tp_price = trade_levels['tp_price']
            
            # Get current market prices
            tick = mt5.symbol_info_tick(self.symbol)
            if not tick:
                logger.error("Failed to get tick data")
                return False
            
            # Determine entry price and order type
            if action == "buy":
                entry_price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY
            else:  # sell
                entry_price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
            
            # Validate SL/TP logic
            if action == "buy":
                if sl_price >= entry_price or tp_price <= entry_price:
                    logger.error("Invalid SL/TP for buy")
                    return False
            else:
                if sl_price <= entry_price or tp_price >= entry_price:
                    logger.error("Invalid SL/TP for sell")
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
                "comment": f"Enhanced_{action}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Execute order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error("Trade execution failed: %s - %s", result.retcode, result.comment)
                return False
            
            # Log successful execution
            logger.info("TRADE EXECUTED: %s %.2f lots at %.5f (SL=%.5f, TP=%.5f)", 
                       action.upper(), volume, entry_price, sl_price, tp_price)
            logger.info("Risk: %.3f%% (${:.2f}), R:R = 1:%.1f", 
                       sizing_result['risk_pct'], sizing_result['risk_amount'], trade_levels['tp_ratio'])
            
            # Record trade in telemetry
            self.current_trade_id = self.telemetry.log_trade_entry(
                symbol=self.symbol,
                action=action,
                volume=volume,
                entry_price=entry_price,
                sl_price=sl_price,
                tp_price=tp_price,
                indicators=indicators,
                risk_amount=sizing_result['risk_amount'],
                risk_pct=sizing_result['risk_pct'],
                magic_number=MAGIC_NUMBER
            )
            
            # Record in guardrails
            self.guardrails.record_trade_entry(action, volume, entry_price)
            
            return True
            
        except Exception as e:
            logger.error("Error executing trade: %s", e)
            return False
    
    def run_cycle(self) -> bool:
        """Run one complete enhanced trading cycle."""
        try:
            logger.info("Starting enhanced trading cycle")
            
            # 1. Check daily guardrails first
            can_trade, guardrail_reason = self.guardrails.can_trade()
            if not can_trade:
                logger.warning("Guardrails prevent trading: %s", guardrail_reason)
                return True  # Not an error, just can't trade
            
            logger.info("Guardrails passed: %s", guardrail_reason)
            
            # 2. Get market data
            rates = mt5.copy_rates_from_pos(self.symbol, TIMEFRAME, 0, BARS_COUNT)
            if rates is None:
                logger.error("Failed to retrieve market data")
                return False
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # 3. Get M15 confirmation
            m15_data = self.get_multi_timeframe_data()
            
            # 4. Compute indicators
            indicators = self.compute_indicators(df)
            if not indicators:
                logger.warning("Failed to compute indicators")
                return False
            
            # 5. Get current price
            current_price = float(df['close'].iloc[-1])
            
            # 6. Create enhanced prompt (no volume request)
            prompt = self.create_enhanced_prompt(current_price, indicators, m15_data)
            
            # 7. Get GPT-4 decision
            gpt_response = self.call_gpt4(prompt)
            if not gpt_response:
                logger.error("Failed to get GPT-4 response")
                return False
            
            logger.info("GPT-4 response: %s", gpt_response)
            
            # 8. Parse response (action + reasoning only)
            decision = self.parse_gpt_response(gpt_response)
            if not decision:
                logger.error("Failed to parse GPT-4 response")
                return False
            
            logger.info("Parsed decision: %s", decision)
            
            # 9. Apply entry quality gates (if not hold)
            if decision["action"] != "hold":
                entry_allowed, gate_reasons = self.entry_gates.evaluate_entry_quality(
                    symbol=self.symbol,
                    df=df,
                    indicators=indicators,
                    gpt_action=decision["action"],
                    current_price=current_price
                )
                
                if not entry_allowed:
                    logger.warning("Entry gates rejected trade")
                    for reason in gate_reasons:
                        logger.warning("   %s", reason)
                    return True  # Not an error, just filtered out
                
                logger.info("Entry gates approved trade")
            
            # 10. Execute trade if approved
            if decision["action"] == "hold":
                logger.info("GPT recommends HOLD - no trade executed")
            else:
                success = self.execute_trade(decision, indicators, current_price)
                if not success:
                    logger.error("Trade execution failed")
                    return False
            
            # 11. Manage existing positions
            management_actions = self.trade_manager.manage_positions(self.symbol, MAGIC_NUMBER)
            if management_actions['positions_managed'] > 0:
                logger.info("Position management: %s", management_actions)
            
            return True
            
        except Exception as e:
            logger.error("Error in trading cycle: %s", e)
            return False
    
    def run(self):
        """Main enhanced bot loop."""
        logger.info("Starting Enhanced Professional Trading Bot")
        logger.info("Symbol: %s | Risk: %s%% | Max Volume: %s", 
                   self.symbol, RISK_PER_TRADE_PCT, MAX_VOLUME)
        
        if not self.initialize():
            logger.error("Bot initialization failed")
            return
        
        # Show initial guardrails status
        stats = self.guardrails.get_daily_stats()
        logger.info("Daily Status: %d/%d trades, %d consecutive losses", 
                   stats.get('trades_today', 0), stats.get('max_trades', 6),
                   stats.get('consecutive_losses', 0))
        
        self.running = True
        
        try:
            while self.running:
                success = self.run_cycle()
                
                if success:
                    logger.info("Trading cycle completed successfully")
                else:
                    logger.warning("Trading cycle completed with errors")
                
                # Generate weekly report (once per day)
                if datetime.now().hour == 17 and datetime.now().minute < 10:  # 5 PM UTC
                    try:
                        report = self.telemetry.generate_weekly_report(MAGIC_NUMBER)
                        logger.info("Weekly Report Generated")
                        print(report[:500] + "..." if len(report) > 500 else report)
                    except Exception as e:
                        logger.error("Error generating weekly report: %s", e)
                
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
        logger.info("Shutting down enhanced trading bot...")
        self.running = False
        
        # Final position management
        try:
            management_actions = self.trade_manager.manage_positions(self.symbol, MAGIC_NUMBER)
            logger.info("Final position management: %s", management_actions)
        except:
            pass
        
        # Generate final report
        try:
            report = self.telemetry.generate_weekly_report(MAGIC_NUMBER)
            logger.info("Final Performance Report:\n%s", report)
        except:
            pass
        
        mt5.shutdown()
        logger.info("Enhanced trading bot shutdown complete")


def main():
    """Main entry point for the enhanced bot."""
    bot = EnhancedMT5TradingBot()
    try:
        bot.run()
    except Exception as e:
        logger.error("Fatal error: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
