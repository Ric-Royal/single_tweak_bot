#!/usr/bin/env python3
"""
Entry Quality Gates System

Implements multiple quality filters to prevent bad entries:
- Closed-bar confirmation
- EMA separation threshold  
- Multi-timeframe alignment
- Mean-reversion conflict detection
- Session and spread filtering
"""

import logging
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from utils.indicators import calculate_ema, calculate_atr

logger = logging.getLogger(__name__)

class EntryQualityGates:
    """Quality gates to filter out poor entry opportunities."""
    
    def __init__(self,
                 ema_separation_factor: float = 0.15,  # Require EMA sep >= 0.15 * ATR
                 bb_conflict_threshold: float = 0.25,  # Top/bottom 25% of BB channel
                 max_spread_multiplier: float = 1.5,   # Max spread = 1.5x 30min median
                 max_spread_pips: float = 0.8):        # Absolute max spread in pips
        
        self.ema_separation_factor = ema_separation_factor
        self.bb_conflict_threshold = bb_conflict_threshold
        self.max_spread_multiplier = max_spread_multiplier
        self.max_spread_pips = max_spread_pips
        
        logger.info(f"Entry gates initialized: EMA sep >= {ema_separation_factor}x ATR, "
                   f"BB conflict at {bb_conflict_threshold*100:.0f}% extremes")
    
    def check_closed_bar_confirmation(self, symbol: str) -> Tuple[bool, str]:
        """
        Check if we're evaluating on a closed bar, not intrabar.
        For simplicity, we'll assume the bot runs on schedule and data is fresh.
        """
        try:
            # Get latest bar
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 2)
            if rates is None or len(rates) < 2:
                return False, "Cannot get recent bars for closed-bar check"
            
            # Check if latest bar is reasonably fresh (within last 6 minutes)
            latest_time = pd.to_datetime(rates[-1]['time'], unit='s')
            current_time = pd.Timestamp.now(tz=timezone.utc).tz_localize(None)
            time_diff = (current_time - latest_time).total_seconds() / 60  # minutes
            
            if time_diff > 6:  # More than 6 minutes old
                return False, f"Latest bar too old: {time_diff:.1f} min ago"
            
            return True, f"Closed bar OK: {time_diff:.1f} min ago"
            
        except Exception as e:
            logger.error(f"Error checking closed bar: {e}")
            return False, f"Closed bar check error: {e}"
    
    def check_ema_separation(self, df: pd.DataFrame, atr_value: float) -> Tuple[bool, str]:
        """
        Check if EMA(9) and EMA(21) have sufficient separation to avoid flat crossovers.
        Require: abs(EMA9 - EMA21) >= k * ATR (e.g., k = 0.15)
        """
        try:
            ema_fast = calculate_ema(df['close'], 9)
            ema_slow = calculate_ema(df['close'], 21)
            
            if ema_fast.empty or ema_slow.empty:
                return False, "Cannot calculate EMAs for separation check"
            
            ema9 = float(ema_fast.iloc[-1])
            ema21 = float(ema_slow.iloc[-1])
            
            separation = abs(ema9 - ema21)
            required_separation = self.ema_separation_factor * atr_value
            
            if separation < required_separation:
                return False, (f"EMA separation too small: {separation:.5f} < "
                             f"{required_separation:.5f} ({self.ema_separation_factor}x ATR)")
            
            trend = "bullish" if ema9 > ema21 else "bearish"
            return True, (f"EMA separation OK: {separation:.5f} >= {required_separation:.5f} "
                         f"({trend} trend)")
            
        except Exception as e:
            logger.error(f"Error checking EMA separation: {e}")
            return False, f"EMA separation check error: {e}"
    
    def check_mtf_alignment(self, symbol: str, m5_ema_trend: str) -> Tuple[bool, str]:
        """
        Check multi-timeframe alignment between M5 and M15 EMA trends.
        Only trade if both timeframes show same EMA trend direction.
        """
        try:
            # Get M15 data
            rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 50)
            if rates_m15 is None:
                return False, "Cannot get M15 data for MTF alignment"
            
            df_m15 = pd.DataFrame(rates_m15)
            ema_fast_m15 = calculate_ema(df_m15['close'], 9)
            ema_slow_m15 = calculate_ema(df_m15['close'], 21)
            
            if ema_fast_m15.empty or ema_slow_m15.empty:
                return False, "Cannot calculate M15 EMAs"
            
            m15_trend = "bullish" if ema_fast_m15.iloc[-1] > ema_slow_m15.iloc[-1] else "bearish"
            
            if m5_ema_trend != m15_trend:
                return False, f"MTF conflict: M5 {m5_ema_trend} vs M15 {m15_trend}"
            
            return True, f"MTF alignment OK: both M5 and M15 are {m5_ema_trend}"
            
        except Exception as e:
            logger.error(f"Error checking MTF alignment: {e}")
            return False, f"MTF alignment check error: {e}"
    
    def check_bb_mean_reversion_conflict(self, 
                                       price: float, 
                                       bb_upper: float, 
                                       bb_lower: float,
                                       gpt_action: str) -> Tuple[bool, str]:
        """
        Check for mean-reversion conflicts with GPT recommendations.
        
        Avoid:
        - Buying near Upper BB (expect rejection)
        - Selling near Lower BB (expect bounce)
        """
        try:
            bb_range = bb_upper - bb_lower
            bb_position = (price - bb_lower) / bb_range  # 0 = lower band, 1 = upper band
            
            # Define "near" as top/bottom 25% of channel
            upper_threshold = 1.0 - self.bb_conflict_threshold  # 0.75
            lower_threshold = self.bb_conflict_threshold        # 0.25
            
            conflict_detected = False
            conflict_reason = ""
            
            if bb_position >= upper_threshold and gpt_action == "buy":
                conflict_detected = True
                conflict_reason = f"Conflict: GPT says BUY but price at upper {bb_position*100:.1f}% of BB (expect rejection)"
                
            elif bb_position <= lower_threshold and gpt_action == "sell":
                conflict_detected = True
                conflict_reason = f"Conflict: GPT says SELL but price at lower {bb_position*100:.1f}% of BB (expect bounce)"
            
            if conflict_detected:
                return False, conflict_reason
            
            return True, f"BB conflict OK: {gpt_action} at {bb_position*100:.1f}% of BB range"
            
        except Exception as e:
            logger.error(f"Error checking BB conflict: {e}")
            return False, f"BB conflict check error: {e}"
    
    def check_trading_session(self) -> Tuple[bool, str]:
        """
        Check if we're in preferred trading session.
        Trade only during London/NY overlap (10:00-17:00 UTC).
        """
        try:
            current_utc = datetime.now(timezone.utc)
            hour_utc = current_utc.hour
            
            # London/NY overlap: 10:00-17:00 UTC (approximately)
            session_start = 10
            session_end = 17
            
            if session_start <= hour_utc < session_end:
                return True, f"Session OK: {hour_utc:02d}:XX UTC (London/NY overlap)"
            else:
                return False, f"Outside trading hours: {hour_utc:02d}:XX UTC (trade {session_start:02d}-{session_end:02d} UTC)"
                
        except Exception as e:
            logger.error(f"Error checking trading session: {e}")
            return False, f"Session check error: {e}"
    
    def check_spread_conditions(self, symbol: str) -> Tuple[bool, str]:
        """
        Check spread conditions to avoid trading during high spread periods.
        """
        try:
            # Get current spread
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return False, "Cannot get current tick for spread check"
            
            spread = tick.ask - tick.bid
            spread_pips = spread * 10000  # Convert to pips for major pairs
            
            # Check absolute spread limit
            if spread_pips > self.max_spread_pips:
                return False, f"Spread too wide: {spread_pips:.1f} pips > {self.max_spread_pips:.1f} pip limit"
            
            # TODO: For more sophisticated check, we could calculate 30-min median spread
            # and compare against that. For now, use absolute threshold.
            
            return True, f"Spread OK: {spread_pips:.1f} pips <= {self.max_spread_pips:.1f} pip limit"
            
        except Exception as e:
            logger.error(f"Error checking spread: {e}")
            return False, f"Spread check error: {e}"
    
    def evaluate_entry_quality(self, 
                              symbol: str,
                              df: pd.DataFrame,
                              indicators: Dict,
                              gpt_action: str,
                              current_price: float) -> Tuple[bool, List[str]]:
        """
        Master entry quality evaluation.
        
        Args:
            symbol: Trading symbol
            df: Market data DataFrame
            indicators: Technical indicators dict
            gpt_action: GPT recommended action ('buy', 'sell', 'hold')
            current_price: Current market price
            
        Returns:
            Tuple[bool, List[str]]: (entry_allowed, [reasons])
        """
        
        if gpt_action == "hold":
            return True, ["GPT recommends HOLD - no entry quality check needed"]
        
        # Determine M5 EMA trend
        try:
            ema_fast = calculate_ema(df['close'], 9)
            ema_slow = calculate_ema(df['close'], 21)
            m5_trend = "bullish" if ema_fast.iloc[-1] > ema_slow.iloc[-1] else "bearish"
        except:
            return False, ["Cannot determine M5 EMA trend"]
        
        # Run all quality gates
        checks = [
            self.check_closed_bar_confirmation(symbol),
            self.check_ema_separation(df, indicators.get('atr', 0.0001)),
            self.check_mtf_alignment(symbol, m5_trend),
            self.check_bb_mean_reversion_conflict(
                current_price, 
                indicators.get('bb_upper', current_price + 0.001),
                indicators.get('bb_lower', current_price - 0.001),
                gpt_action
            ),
            self.check_trading_session(),
            self.check_spread_conditions(symbol)
        ]
        
        passed_checks = []
        failed_checks = []
        
        for passed, reason in checks:
            if passed:
                passed_checks.append(reason)
            else:
                failed_checks.append(reason)
        
        # Entry allowed only if ALL checks pass
        entry_allowed = len(failed_checks) == 0
        
        if entry_allowed:
            logger.info(f"Entry quality APPROVED for {gpt_action} {symbol}")
            for reason in passed_checks:
                logger.info(f"   PASS: {reason}")
        else:
            logger.warning(f"Entry quality REJECTED for {gpt_action} {symbol}")
            for reason in failed_checks:
                logger.warning(f"   FAIL: {reason}")
        
        all_reasons = passed_checks + failed_checks
        return entry_allowed, all_reasons


# Convenience functions
def create_entry_gates() -> EntryQualityGates:
    """Create entry gates with default settings."""
    return EntryQualityGates()

def evaluate_entry(symbol: str, df: pd.DataFrame, indicators: Dict, 
                  gpt_action: str, current_price: float) -> Tuple[bool, List[str]]:
    """Convenience function for entry evaluation."""
    gates = create_entry_gates()
    return gates.evaluate_entry_quality(symbol, df, indicators, gpt_action, current_price)


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Entry Quality Gates Test")
    print("=" * 40)
    
    gates = EntryQualityGates()
    
    # Test individual checks
    print("\nTesting individual checks:")
    
    # Session check
    session_ok, session_reason = gates.check_trading_session()
    print(f"Session: {session_ok} - {session_reason}")
    
    # Spread check (requires MT5 connection)
    try:
        if mt5.initialize():
            spread_ok, spread_reason = gates.check_spread_conditions("EURUSD")
            print(f"Spread: {spread_ok} - {spread_reason}")
            mt5.shutdown()
    except:
        print("Spread: Cannot test (MT5 not available)")
