#!/usr/bin/env python3
"""
Daily Trading Guardrails System

Implements daily risk controls:
- Stop after -1.5% equity drawdown
- Stop after 3 consecutive losses  
- Max 6 trades per day
- Cooldown periods after losses
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

class DailyGuardrails:
    """Daily risk management and trading controls."""
    
    def __init__(self, 
                 max_daily_drawdown_pct: float = 1.5,
                 max_consecutive_losses: int = 3,
                 max_daily_trades: int = 6,
                 loss_cooldown_minutes: int = 60,
                 data_file: str = "data/daily_guardrails.json"):
        
        self.max_daily_drawdown_pct = max_daily_drawdown_pct / 100.0
        self.max_consecutive_losses = max_consecutive_losses
        self.max_daily_trades = max_daily_trades
        self.loss_cooldown_minutes = loss_cooldown_minutes
        self.data_file = data_file
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        
        # Load or initialize daily state
        self.daily_state = self._load_daily_state()
        
        logger.info(f"Daily guardrails initialized: {max_daily_drawdown_pct}% drawdown limit, "
                   f"{max_consecutive_losses} consecutive losses, {max_daily_trades} trades/day")
    
    def _load_daily_state(self) -> Dict:
        """Load daily trading state from file."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    state = json.load(f)
                
                # Reset if it's a new day
                today = datetime.now().date().isoformat()
                if state.get('date') != today:
                    logger.info(f"New trading day {today}, resetting daily state")
                    state = self._create_new_day_state()
                
                return state
            else:
                return self._create_new_day_state()
                
        except Exception as e:
            logger.error(f"Error loading daily state: {e}, creating new state")
            return self._create_new_day_state()
    
    def _create_new_day_state(self) -> Dict:
        """Create fresh daily state for new trading day."""
        return {
            'date': datetime.now().date().isoformat(),
            'trades_today': 0,
            'consecutive_losses': 0,
            'last_loss_time': None,
            'daily_trades': [],
            'starting_equity': None,
            'daily_stopped': False,
            'stop_reason': None
        }
    
    def _save_daily_state(self) -> None:
        """Save daily state to file."""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.daily_state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving daily state: {e}")
    
    def _get_starting_equity(self) -> Optional[float]:
        """Get or set starting equity for the day."""
        if self.daily_state['starting_equity'] is None:
            try:
                account_info = mt5.account_info()
                if account_info:
                    starting_equity = account_info.equity
                    self.daily_state['starting_equity'] = starting_equity
                    self._save_daily_state()
                    logger.info(f"Set starting equity for today: ${starting_equity:.2f}")
                    return starting_equity
                else:
                    logger.error("Could not get account info for starting equity")
                    return None
            except Exception as e:
                logger.error(f"Error getting starting equity: {e}")
                return None
        else:
            return self.daily_state['starting_equity']
    
    def check_daily_drawdown(self) -> Tuple[bool, str]:
        """Check if daily drawdown limit has been exceeded."""
        try:
            starting_equity = self._get_starting_equity()
            if starting_equity is None:
                return False, "Cannot check drawdown - starting equity unknown"
            
            account_info = mt5.account_info()
            if account_info is None:
                return False, "Cannot check drawdown - account info unavailable"
            
            current_equity = account_info.equity
            drawdown = (starting_equity - current_equity) / starting_equity
            drawdown_pct = drawdown * 100
            
            if drawdown >= self.max_daily_drawdown_pct:
                reason = f"Daily drawdown limit exceeded: {drawdown_pct:.2f}% >= {self.max_daily_drawdown_pct*100:.1f}%"
                self._stop_trading_for_day(reason)
                return False, reason
            
            return True, f"Drawdown OK: {drawdown_pct:.2f}% / {self.max_daily_drawdown_pct*100:.1f}%"
            
        except Exception as e:
            logger.error(f"Error checking daily drawdown: {e}")
            return False, f"Drawdown check error: {e}"
    
    def check_consecutive_losses(self) -> Tuple[bool, str]:
        """Check consecutive losses limit."""
        consecutive = self.daily_state['consecutive_losses']
        
        if consecutive >= self.max_consecutive_losses:
            reason = f"Consecutive losses limit reached: {consecutive} >= {self.max_consecutive_losses}"
            self._stop_trading_for_day(reason)
            return False, reason
        
        return True, f"Consecutive losses OK: {consecutive}/{self.max_consecutive_losses}"
    
    def check_daily_trade_limit(self) -> Tuple[bool, str]:
        """Check daily trade count limit."""
        trades_today = self.daily_state['trades_today']
        
        if trades_today >= self.max_daily_trades:
            reason = f"Daily trade limit reached: {trades_today} >= {self.max_daily_trades}"
            self._stop_trading_for_day(reason)
            return False, reason
        
        return True, f"Daily trades OK: {trades_today}/{self.max_daily_trades}"
    
    def check_loss_cooldown(self) -> Tuple[bool, str]:
        """Check if in cooldown period after recent losses."""
        last_loss_time = self.daily_state.get('last_loss_time')
        consecutive = self.daily_state['consecutive_losses']
        
        # Only apply cooldown after 2+ losses
        if consecutive >= 2 and last_loss_time:
            try:
                last_loss = datetime.fromisoformat(last_loss_time)
                time_since_loss = datetime.now() - last_loss
                cooldown_period = timedelta(minutes=self.loss_cooldown_minutes)
                
                if time_since_loss < cooldown_period:
                    remaining = cooldown_period - time_since_loss
                    remaining_minutes = remaining.total_seconds() / 60
                    return False, f"In cooldown: {remaining_minutes:.1f} min remaining after {consecutive} losses"
                
            except Exception as e:
                logger.error(f"Error checking cooldown: {e}")
        
        return True, "No cooldown active"
    
    def can_trade(self) -> Tuple[bool, str]:
        """
        Master check: can we trade right now?
        
        Returns:
            Tuple[bool, str]: (can_trade, reason)
        """
        
        # Check if already stopped for the day
        if self.daily_state['daily_stopped']:
            return False, f"Trading stopped for day: {self.daily_state['stop_reason']}"
        
        # Check all guardrails
        checks = [
            self.check_daily_drawdown(),
            self.check_consecutive_losses(), 
            self.check_daily_trade_limit(),
            self.check_loss_cooldown()
        ]
        
        for can_continue, reason in checks:
            if not can_continue:
                return False, reason
        
        return True, "All guardrails passed - can trade"
    
    def record_trade_entry(self, action: str, volume: float, price: float) -> None:
        """Record a new trade entry."""
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'volume': volume,
            'entry_price': price,
            'result': 'open'
        }
        
        self.daily_state['trades_today'] += 1
        self.daily_state['daily_trades'].append(trade_record)
        self._save_daily_state()
        
        logger.info(f"Recorded trade entry: {action} {volume} lots at {price} "
                   f"(trade {self.daily_state['trades_today']}/{self.max_daily_trades})")
    
    def record_trade_result(self, profit_loss: float, was_winner: bool) -> None:
        """Record trade result and update consecutive loss counter."""
        
        if was_winner:
            # Reset consecutive losses on win
            self.daily_state['consecutive_losses'] = 0
            logger.info(f"Trade won: +${profit_loss:.2f}, consecutive losses reset to 0")
        else:
            # Increment consecutive losses on loss
            self.daily_state['consecutive_losses'] += 1
            self.daily_state['last_loss_time'] = datetime.now().isoformat()
            logger.warning(f"Trade lost: -${abs(profit_loss):.2f}, "
                          f"consecutive losses: {self.daily_state['consecutive_losses']}")
        
        # Update the last trade record if available
        if self.daily_state['daily_trades']:
            self.daily_state['daily_trades'][-1]['result'] = 'win' if was_winner else 'loss'
            self.daily_state['daily_trades'][-1]['pnl'] = profit_loss
        
        self._save_daily_state()
    
    def _stop_trading_for_day(self, reason: str) -> None:
        """Stop trading for the remainder of the day."""
        self.daily_state['daily_stopped'] = True
        self.daily_state['stop_reason'] = reason
        self._save_daily_state()
        
        logger.critical(f"TRADING STOPPED FOR DAY: {reason}")
    
    def get_daily_stats(self) -> Dict:
        """Get current daily trading statistics."""
        try:
            starting_equity = self._get_starting_equity()
            account_info = mt5.account_info()
            current_equity = account_info.equity if account_info else 0
            
            drawdown_pct = 0
            if starting_equity and current_equity:
                drawdown_pct = ((starting_equity - current_equity) / starting_equity) * 100
            
            wins = sum(1 for trade in self.daily_state['daily_trades'] if trade.get('result') == 'win')
            losses = sum(1 for trade in self.daily_state['daily_trades'] if trade.get('result') == 'loss')
            
            return {
                'date': self.daily_state['date'],
                'trades_today': self.daily_state['trades_today'],
                'max_trades': self.max_daily_trades,
                'consecutive_losses': self.daily_state['consecutive_losses'],
                'max_consecutive': self.max_consecutive_losses,
                'starting_equity': starting_equity,
                'current_equity': current_equity,
                'daily_drawdown_pct': drawdown_pct,
                'max_drawdown_pct': self.max_daily_drawdown_pct * 100,
                'wins': wins,
                'losses': losses,
                'daily_stopped': self.daily_state['daily_stopped'],
                'stop_reason': self.daily_state.get('stop_reason')
            }
            
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            return {}
    
    def force_reset_day(self) -> None:
        """Force reset daily state (for testing/manual override)."""
        logger.warning("Forcing daily state reset")
        self.daily_state = self._create_new_day_state()
        self._save_daily_state()


# Convenience functions
def create_guardrails() -> DailyGuardrails:
    """Create guardrails instance with default settings."""
    return DailyGuardrails()

def can_trade_now() -> Tuple[bool, str]:
    """Quick check if trading is allowed right now."""
    guardrails = create_guardrails()
    return guardrails.can_trade()


# Testing and example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Daily Guardrails Test")
    print("=" * 40)
    
    guardrails = DailyGuardrails()
    
    # Test current state
    can_trade, reason = guardrails.can_trade()
    print(f"Can trade: {can_trade}")
    print(f"Reason: {reason}")
    
    # Show daily stats
    stats = guardrails.get_daily_stats()
    print(f"\nDaily Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
