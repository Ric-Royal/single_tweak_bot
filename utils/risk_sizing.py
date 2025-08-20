#!/usr/bin/env python3
"""
Risk-Based Position Sizing Module

Implements professional risk management with percentage-based position sizing
rather than arbitrary GPT-suggested volumes.
"""

import logging
import MetaTrader5 as mt5
from typing import Dict, Optional, Tuple
import math

logger = logging.getLogger(__name__)

class RiskBasedSizing:
    """Professional risk-based position sizing calculator."""
    
    def __init__(self, 
                 default_risk_pct: float = 0.15,  # 0.15% per trade
                 min_volume: float = 0.01,
                 max_volume: float = 0.05,  # Conservative until live stats justify more
                 max_daily_risk_pct: float = 1.5):  # 1.5% daily drawdown limit
        
        self.default_risk_pct = default_risk_pct / 100.0  # Convert to decimal (0.30 -> 0.003)
        self.min_volume = min_volume
        self.max_volume = max_volume
        self.max_daily_risk_pct = max_daily_risk_pct / 100.0
        
        logger.info(f"Risk sizing initialized: {default_risk_pct}% per trade, "
                   f"volume range [{min_volume}, {max_volume}]")
    
    def get_account_info(self) -> Optional[Dict]:
        """Get current account information."""
        try:
            account_info = mt5.account_info()
            if account_info is None:
                logger.error("Failed to get account info")
                return None
            
            return {
                'balance': account_info.balance,
                'equity': account_info.equity,
                'free_margin': account_info.margin_free,
                'currency': account_info.currency
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    def calculate_pip_value(self, symbol: str) -> Optional[float]:
        """Calculate pip value in account currency per lot per pip."""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"Cannot get symbol info for {symbol}")
                return None
            
            # Get contract size (usually 100,000 for major pairs)
            contract_size = symbol_info.trade_contract_size
            
            # Calculate price increment per pip
            if symbol_info.digits == 5:
                pip_increment = 10 * symbol_info.point  # 1 pip = 10 points (0.0001)
            elif symbol_info.digits == 3:
                pip_increment = symbol_info.point  # 1 pip = 1 point (0.01 for JPY)
            elif symbol_info.digits == 4:
                pip_increment = symbol_info.point  # 1 pip = 1 point (0.0001)
            elif symbol_info.digits == 2:
                pip_increment = symbol_info.point  # 1 pip = 1 point (0.01)
            else:
                pip_increment = 10 * symbol_info.point  # Default
                logger.warning(f"Unusual digits ({symbol_info.digits}) for {symbol}")
            
            # For major pairs vs USD account currency
            if symbol.startswith('USD'):
                # USDXXX pairs: pip value = contract_size * pip_increment
                pip_value = contract_size * pip_increment
            elif symbol.endswith('USD'):
                # XXXUSD pairs: pip value = contract_size * pip_increment
                pip_value = contract_size * pip_increment  
            else:
                # Cross pairs: simplified calculation (not perfect but functional)
                pip_value = contract_size * pip_increment
            
            logger.debug(f"{symbol}: contract_size={contract_size}, pip_increment={pip_increment:.6f}, "
                        f"pip_value=${pip_value:.2f}")
            
            return pip_value
            
        except Exception as e:
            logger.error(f"Error calculating pip value for {symbol}: {e}")
            return None
    
    def calc_position_size(self, 
                          symbol: str,
                          sl_pips: float,
                          risk_pct: Optional[float] = None,
                          account_balance: Optional[float] = None) -> Dict:
        """
        Calculate position size based on risk percentage.
        
        Args:
            symbol: Trading symbol
            sl_pips: Stop loss in pips
            risk_pct: Risk percentage (optional, uses default if None)
            account_balance: Account balance (optional, fetches if None)
            
        Returns:
            Dict with volume, risk_amount, reasoning, and validation info
        """
        
        if risk_pct is None:
            risk_pct = self.default_risk_pct
        else:
            risk_pct = risk_pct / 100.0  # Convert percentage to decimal (0.30 -> 0.003)
        
        try:
            # Get account info
            if account_balance is None:
                account_info = self.get_account_info()
                if account_info is None:
                    return self._fallback_sizing("Failed to get account info")
                balance = account_info['balance']
                equity = account_info['equity']
            else:
                balance = account_balance
                equity = account_balance
            
            # Calculate pip value
            pip_value = self.calculate_pip_value(symbol)
            if pip_value is None:
                return self._fallback_sizing("Failed to calculate pip value")
            
            # Risk amount calculation
            risk_amount = balance * risk_pct
            
            # Position size calculation
            # volume = risk_amount / (sl_pips * pip_value)
            if sl_pips <= 0:
                return self._fallback_sizing("Invalid stop loss pips")
            
            raw_volume = risk_amount / (sl_pips * pip_value)
            
            # Clamp to allowed range
            volume = max(self.min_volume, min(self.max_volume, raw_volume))
            
            # Round to valid lot size (0.01 increments)
            volume = round(volume, 2)
            
            # Calculate actual risk with clamped volume
            actual_risk_amount = volume * sl_pips * pip_value
            actual_risk_pct = (actual_risk_amount / balance) * 100
            
            reasoning = (f"Risk calc: {risk_pct*100:.3f}% of ${balance:.2f} = ${risk_amount:.2f}, "
                        f"SL {sl_pips} pips * pip_value {pip_value:.6f} = "
                        f"raw_vol {raw_volume:.4f} → clamped to {volume:.2f} "
                        f"(actual risk: ${actual_risk_amount:.2f} = {actual_risk_pct:.3f}%)")
            
            return {
                'volume': volume,
                'risk_amount': actual_risk_amount,
                'risk_pct': actual_risk_pct,
                'pip_value': pip_value,
                'raw_volume': raw_volume,
                'clamped': raw_volume != volume,
                'reasoning': reasoning,
                'valid': True
            }
            
        except Exception as e:
            logger.error(f"Error in position size calculation: {e}")
            return self._fallback_sizing(f"Calculation error: {e}")
    
    def _fallback_sizing(self, reason: str) -> Dict:
        """Fallback to minimum position size with explanation."""
        logger.warning(f"Using fallback sizing: {reason}")
        
        return {
            'volume': self.min_volume,
            'risk_amount': 0.0,
            'risk_pct': 0.0,
            'pip_value': 0.0001,  # Default for EURUSD
            'raw_volume': self.min_volume,
            'clamped': True,
            'reasoning': f"FALLBACK: {reason}, using minimum volume {self.min_volume}",
            'valid': False
        }
    
    def validate_daily_risk(self, new_trade_risk: float) -> Tuple[bool, str]:
        """
        Check if new trade would exceed daily risk limits.
        
        Args:
            new_trade_risk: Risk amount for the new trade
            
        Returns:
            Tuple[bool, str]: (can_trade, reason)
        """
        try:
            account_info = self.get_account_info()
            if account_info is None:
                return False, "Cannot validate daily risk - account info unavailable"
            
            balance = account_info['balance']
            equity = account_info['equity']
            
            # Calculate current drawdown
            current_drawdown_pct = ((balance - equity) / balance) * 100
            
            # Estimate risk if new trade goes to full stop loss
            potential_new_equity = equity - new_trade_risk
            potential_drawdown_pct = ((balance - potential_new_equity) / balance) * 100
            
            max_daily_drawdown_amount = balance * self.max_daily_risk_pct
            
            if current_drawdown_pct >= self.max_daily_risk_pct * 100:
                return False, f"Daily drawdown limit reached: {current_drawdown_pct:.2f}% >= {self.max_daily_risk_pct*100:.1f}%"
            
            if potential_drawdown_pct >= self.max_daily_risk_pct * 100:
                return False, f"New trade would exceed daily limit: {potential_drawdown_pct:.2f}% >= {self.max_daily_risk_pct*100:.1f}%"
            
            return True, f"Daily risk OK: current {current_drawdown_pct:.2f}%, potential {potential_drawdown_pct:.2f}%"
            
        except Exception as e:
            logger.error(f"Error validating daily risk: {e}")
            return False, f"Risk validation error: {e}"


def calc_position_size(symbol: str, 
                      sl_pips: float, 
                      risk_pct: float = 0.15,
                      account_balance: Optional[float] = None) -> Dict:
    """
    Convenience function for position size calculation.
    
    Args:
        symbol: Trading symbol
        sl_pips: Stop loss in pips
        risk_pct: Risk percentage (default 0.15%)
        account_balance: Account balance (fetches if None)
        
    Returns:
        Dict with volume and risk information
    """
    sizer = RiskBasedSizing()
    return sizer.calc_position_size(symbol, sl_pips, risk_pct, account_balance)


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test the sizing calculator
    sizer = RiskBasedSizing()
    
    # Test with different scenarios
    test_cases = [
        ("EURUSD", 20.0, 0.15),  # Normal case
        ("EURUSD", 50.0, 0.25),  # Wider stop
        ("EURUSD", 10.0, 0.10),  # Tight stop, lower risk
    ]
    
    print("Risk-Based Position Sizing Test Results:")
    print("=" * 60)
    
    for symbol, sl_pips, risk_pct in test_cases:
        result = sizer.calc_position_size(symbol, sl_pips, risk_pct)
        print(f"\nSymbol: {symbol}, SL: {sl_pips} pips, Risk: {risk_pct}%")
        print(f"Volume: {result['volume']:.2f}")
        print(f"Risk Amount: ${result['risk_amount']:.2f}")
        print(f"Reasoning: {result['reasoning']}")
