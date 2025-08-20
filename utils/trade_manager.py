#!/usr/bin/env python3
"""
Trade Management System

Implements mechanical exit rules:
- ATR-based SL/TP calculation
- Move to breakeven at +1R
- Partial take profit at +1R
- ATR trailing stop (Chandelier-style)
- Time-based exit after 12-16 bars
"""

import logging
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from utils.indicators import calculate_atr

logger = logging.getLogger(__name__)

class TradeManager:
    """Mechanical trade management with ATR-based exits."""
    
    def __init__(self,
                 atr_sl_multiplier: float = 3.5,      # Base SL = 3.5x ATR
                 atr_tp_ratio: float = 2.0,           # TP = 2x SL
                 extreme_rsi_sl_multiplier: float = 4.5,  # Wider SL at RSI extremes
                 extreme_rsi_tp_ratio: float = 1.5,   # Tighter TP at RSI extremes
                 trailing_atr_multiplier: float = 2.0, # Trail at 2x ATR
                 time_exit_bars: int = 15,            # Exit after 15 bars (75 min on M5)
                 partial_tp_percent: float = 50.0):   # Close 50% at +1R
        
        self.atr_sl_multiplier = atr_sl_multiplier
        self.atr_tp_ratio = atr_tp_ratio
        self.extreme_rsi_sl_multiplier = extreme_rsi_sl_multiplier
        self.extreme_rsi_tp_ratio = extreme_rsi_tp_ratio
        self.trailing_atr_multiplier = trailing_atr_multiplier
        self.time_exit_bars = time_exit_bars
        self.partial_tp_percent = partial_tp_percent / 100.0
        
        logger.info(f"Trade manager initialized: SL={atr_sl_multiplier}x ATR, "
                   f"TP={atr_tp_ratio}x SL, time exit={time_exit_bars} bars")
    
    def calculate_atr_based_levels(self, 
                                  symbol: str,
                                  action: str,
                                  entry_price: float,
                                  atr_value: float,
                                  rsi_value: float = 50.0) -> Dict:
        """
        Calculate ATR-based SL and TP levels with RSI adjustments.
        
        Args:
            symbol: Trading symbol
            action: 'buy' or 'sell'
            entry_price: Entry price
            atr_value: Current ATR value
            rsi_value: Current RSI value for extreme adjustments
            
        Returns:
            Dict with SL/TP prices and pips
        """
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                raise ValueError(f"Cannot get symbol info for {symbol}")
            
            # Calculate pip value
            if symbol_info.digits == 5:
                pip_value = 0.0001
            elif symbol_info.digits == 3:
                pip_value = 0.01
            else:
                pip_value = 0.0001  # Default
            
            # Check for RSI extremes and adjust multipliers
            if (action == "buy" and rsi_value > 70) or (action == "sell" and rsi_value < 30):
                # Trading against momentum at extremes - use wider stops
                sl_multiplier = self.extreme_rsi_sl_multiplier
                tp_ratio = self.extreme_rsi_tp_ratio
                risk_note = f"RSI extreme ({rsi_value:.1f}) - wider SL, tighter TP"
            else:
                # Normal conditions
                sl_multiplier = self.atr_sl_multiplier
                tp_ratio = self.atr_tp_ratio
                risk_note = f"Normal RSI ({rsi_value:.1f}) - standard SL/TP"
            
            # Calculate SL distance in price units
            sl_distance = atr_value * sl_multiplier
            tp_distance = sl_distance * tp_ratio
            
            # Calculate SL and TP prices
            if action == "buy":
                sl_price = entry_price - sl_distance
                tp_price = entry_price + tp_distance
            else:  # sell
                sl_price = entry_price + sl_distance
                tp_price = entry_price - tp_distance
            
            # Convert to pips for logging
            sl_pips = sl_distance / pip_value
            tp_pips = tp_distance / pip_value
            
            # Round prices to symbol digits
            sl_price = round(sl_price, symbol_info.digits)
            tp_price = round(tp_price, symbol_info.digits)
            
            return {
                'sl_price': sl_price,
                'tp_price': tp_price,
                'sl_pips': sl_pips,
                'tp_pips': tp_pips,
                'atr_multiplier': sl_multiplier,
                'tp_ratio': tp_ratio,
                'risk_note': risk_note,
                'r_distance': sl_distance  # 1R distance for later calculations
            }
            
        except Exception as e:
            logger.error(f"Error calculating ATR levels: {e}")
            return {}
    
    def get_position_info(self, symbol: str, magic_number: int) -> List[Dict]:
        """Get current positions for the symbol with specific magic number."""
        try:
            positions = mt5.positions_get(symbol=symbol)
            if not positions:
                return []
            
            position_list = []
            for pos in positions:
                if pos.magic == magic_number:
                    # Calculate current P&L in R multiples
                    current_price = self._get_current_price(symbol, pos.type)
                    if current_price:
                        if pos.type == mt5.POSITION_TYPE_BUY:
                            price_move = current_price - pos.price_open
                        else:
                            price_move = pos.price_open - current_price
                        
                        # Estimate R based on SL distance
                        sl_distance = abs(pos.sl - pos.price_open) if pos.sl > 0 else 0.002  # Fallback
                        r_multiple = price_move / sl_distance if sl_distance > 0 else 0
                        
                        position_info = {
                            'ticket': pos.ticket,
                            'symbol': pos.symbol,
                            'type': pos.type,
                            'volume': pos.volume,
                            'open_price': pos.price_open,
                            'current_price': current_price,
                            'sl': pos.sl,
                            'tp': pos.tp,
                            'profit': pos.profit,
                            'open_time': datetime.fromtimestamp(pos.time),
                            'r_multiple': r_multiple,
                            'comment': pos.comment
                        }
                        position_list.append(position_info)
            
            return position_list
            
        except Exception as e:
            logger.error(f"Error getting position info: {e}")
            return []
    
    def _get_current_price(self, symbol: str, position_type: int) -> Optional[float]:
        """Get current price for position evaluation."""
        try:
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return None
            
            # Use bid for long positions, ask for short positions
            if position_type == mt5.POSITION_TYPE_BUY:
                return tick.bid
            else:
                return tick.ask
                
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return None
    
    def move_to_breakeven(self, position: Dict) -> bool:
        """Move stop loss to breakeven when position is at +1R."""
        try:
            if position['r_multiple'] >= 1.0 and position['sl'] != position['open_price']:
                
                # Modify position to move SL to entry
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": position['ticket'],
                    "sl": position['open_price'],
                    "tp": position['tp']  # Keep existing TP
                }
                
                result = mt5.order_send(request)
                
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"Moved to breakeven: {position['symbol']} ticket {position['ticket']} "
                               f"at +{position['r_multiple']:.2f}R")
                    return True
                else:
                    logger.error(f"Failed to move to breakeven: {result.retcode} - {result.comment}")
                    return False
            
            return False  # No action needed
            
        except Exception as e:
            logger.error(f"Error moving to breakeven: {e}")
            return False
    
    def partial_take_profit(self, position: Dict) -> bool:
        """Close partial position at +1R profit."""
        try:
            if position['r_multiple'] >= 1.0:
                
                # Calculate partial volume
                partial_volume = round(position['volume'] * self.partial_tp_percent, 2)
                
                # Make sure we have minimum volume
                if partial_volume < 0.01:
                    return False
                
                # Close partial position
                close_type = mt5.ORDER_TYPE_SELL if position['type'] == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": position['ticket'],
                    "symbol": position['symbol'],
                    "volume": partial_volume,
                    "type": close_type,
                    "price": position['current_price'],
                    "comment": f"Partial_TP_{self.partial_tp_percent*100:.0f}%"
                }
                
                result = mt5.order_send(request)
                
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"Partial TP: Closed {partial_volume} lots of {position['symbol']} "
                               f"at +{position['r_multiple']:.2f}R")
                    return True
                else:
                    logger.error(f"Failed partial TP: {result.retcode} - {result.comment}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error in partial take profit: {e}")
            return False
    
    def apply_trailing_stop(self, position: Dict, atr_value: float) -> bool:
        """Apply ATR-based trailing stop."""
        try:
            # Calculate trailing distance
            trail_distance = atr_value * self.trailing_atr_multiplier
            
            if position['type'] == mt5.POSITION_TYPE_BUY:
                # For long positions, trail up
                new_sl = position['current_price'] - trail_distance
                # Only move SL up, never down
                if new_sl > position['sl']:
                    update_sl = True
                else:
                    update_sl = False
            else:
                # For short positions, trail down
                new_sl = position['current_price'] + trail_distance
                # Only move SL down, never up
                if new_sl < position['sl']:
                    update_sl = True
                else:
                    update_sl = False
            
            if update_sl:
                # Round to symbol digits
                symbol_info = mt5.symbol_info(position['symbol'])
                if symbol_info:
                    new_sl = round(new_sl, symbol_info.digits)
                
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": position['ticket'],
                    "sl": new_sl,
                    "tp": position['tp']
                }
                
                result = mt5.order_send(request)
                
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"Trail stop: {position['symbol']} SL moved to {new_sl:.5f} "
                               f"({self.trailing_atr_multiplier}x ATR trail)")
                    return True
                else:
                    logger.error(f"Failed trailing stop: {result.retcode} - {result.comment}")
                    return False
            
            return False  # No update needed
            
        except Exception as e:
            logger.error(f"Error applying trailing stop: {e}")
            return False
    
    def check_time_exit(self, position: Dict) -> bool:
        """Check if position should be closed due to time limit."""
        try:
            time_in_trade = datetime.now() - position['open_time']
            bars_in_trade = time_in_trade.total_seconds() / (5 * 60)  # 5-minute bars
            
            if bars_in_trade >= self.time_exit_bars:
                # Close position due to time limit
                close_type = mt5.ORDER_TYPE_SELL if position['type'] == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": position['ticket'],
                    "symbol": position['symbol'],
                    "volume": position['volume'],
                    "type": close_type,
                    "price": position['current_price'],
                    "comment": f"Time_exit_{self.time_exit_bars}bars"
                }
                
                result = mt5.order_send(request)
                
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"Time exit: Closed {position['symbol']} after {bars_in_trade:.1f} bars "
                               f"at {position['r_multiple']:+.2f}R")
                    return True
                else:
                    logger.error(f"Failed time exit: {result.retcode} - {result.comment}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking time exit: {e}")
            return False
    
    def manage_positions(self, symbol: str, magic_number: int) -> Dict:
        """
        Main position management function - call this each cycle.
        
        Returns:
            Dict with management actions taken
        """
        actions_taken = {
            'breakeven_moves': 0,
            'partial_tps': 0,
            'trailing_stops': 0,
            'time_exits': 0,
            'positions_managed': 0
        }
        
        try:
            positions = self.get_position_info(symbol, magic_number)
            if not positions:
                return actions_taken
            
            # Get current ATR for trailing calculations
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 50)
            if rates is not None:
                df = pd.DataFrame(rates)
                atr_series = calculate_atr(df['high'], df['low'], df['close'], 14)
                current_atr = float(atr_series.iloc[-1]) if not atr_series.empty else 0.0001
            else:
                current_atr = 0.0001  # Fallback
            
            for position in positions:
                actions_taken['positions_managed'] += 1
                
                # Check time exit first (highest priority)
                if self.check_time_exit(position):
                    actions_taken['time_exits'] += 1
                    continue  # Position closed, skip other checks
                
                # Check for partial TP opportunity
                if self.partial_take_profit(position):
                    actions_taken['partial_tps'] += 1
                
                # Move to breakeven if profitable
                if self.move_to_breakeven(position):
                    actions_taken['breakeven_moves'] += 1
                
                # Apply trailing stop
                if self.apply_trailing_stop(position, current_atr):
                    actions_taken['trailing_stops'] += 1
            
            if actions_taken['positions_managed'] > 0:
                logger.info(f"Position management complete: {actions_taken}")
            
            return actions_taken
            
        except Exception as e:
            logger.error(f"Error in position management: {e}")
            return actions_taken


# Convenience functions
def create_trade_manager() -> TradeManager:
    """Create trade manager with default settings."""
    return TradeManager()

def calculate_trade_levels(symbol: str, action: str, entry_price: float, 
                         atr_value: float, rsi_value: float = 50.0) -> Dict:
    """Convenience function for calculating trade levels."""
    manager = TradeManager()
    return manager.calculate_atr_based_levels(symbol, action, entry_price, atr_value, rsi_value)


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Trade Manager Test")
    print("=" * 40)
    
    manager = TradeManager()
    
    # Test level calculations
    test_levels = manager.calculate_atr_based_levels(
        symbol="EURUSD",
        action="buy",
        entry_price=1.08500,
        atr_value=0.0012,
        rsi_value=45.0
    )
    
    print(f"\nATR-based levels test:")
    for key, value in test_levels.items():
        print(f"  {key}: {value}")
        
    # Test position management (requires MT5 connection)
    try:
        if mt5.initialize():
            actions = manager.manage_positions("EURUSD", 123457)
            print(f"\nPosition management test: {actions}")
            mt5.shutdown()
    except:
        print("\nPosition management: Cannot test (MT5 not available)")
