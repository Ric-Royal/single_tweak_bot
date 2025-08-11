#!/usr/bin/env python3
"""
Trade Telemetry and Performance Tracking System

Implements comprehensive trade logging and performance analysis:
- Per-trade metrics (entry_time, MFE, MAE, bars_in_trade, etc.)
- Feature logging (EMA states, BB position, etc.)
- Weekly performance reports
- Expectancy calculations
"""

import logging
import json
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

@dataclass
class TradeMetrics:
    """Complete trade metrics for analysis."""
    # Basic trade info
    timestamp: str
    symbol: str
    action: str
    volume: float
    entry_price: float
    exit_price: Optional[float] = None
    sl_price: float = 0.0
    tp_price: float = 0.0
    
    # Trade outcome
    profit_loss: float = 0.0
    profit_pips: float = 0.0
    result_r: float = 0.0  # Result in R multiples
    bars_in_trade: int = 0
    
    # Market conditions at entry
    ema9: float = 0.0
    ema21: float = 0.0
    ema_separation: float = 0.0
    macd_line: float = 0.0
    macd_signal: float = 0.0
    rsi: float = 50.0
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    bb_position_pct: float = 50.0  # Position within BB channel (0-100%)
    atr: float = 0.0
    spread_pips: float = 0.0
    
    # Session and timing
    session: str = "unknown"
    hour_utc: int = 0
    
    # Risk metrics
    risk_amount: float = 0.0
    risk_pct: float = 0.0
    
    # Trade quality metrics (filled during trade lifecycle)
    mfe_pips: float = 0.0  # Maximum Favorable Excursion
    mae_pips: float = 0.0  # Maximum Adverse Excursion
    exit_reason: str = "open"
    
    # Magic number for filtering
    magic_number: int = 0

@dataclass
class PerformanceStats:
    """Performance statistics for reporting."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    avg_win_pips: float = 0.0
    avg_loss_pips: float = 0.0
    avg_win_r: float = 0.0
    avg_loss_r: float = 0.0
    
    total_profit_pips: float = 0.0
    total_profit_r: float = 0.0
    expectancy_pips: float = 0.0
    expectancy_r: float = 0.0
    
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    profit_factor: float = 0.0  # Gross profit / Gross loss
    sharpe_ratio: float = 0.0
    
    best_trade_r: float = 0.0
    worst_trade_r: float = 0.0


class TradeTelemetry:
    """Trade telemetry and performance tracking system."""
    
    def __init__(self, data_dir: str = "data/telemetry"):
        self.data_dir = data_dir
        
        # Ensure directories exist
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(f"{data_dir}/trades", exist_ok=True)
        os.makedirs(f"{data_dir}/reports", exist_ok=True)
        
        self.trades_file = f"{data_dir}/trades/trade_metrics.jsonl"
        
        logger.info(f"Trade telemetry initialized: {data_dir}")
    
    def capture_entry_features(self, 
                              symbol: str,
                              indicators: Dict,
                              current_price: float) -> Dict:
        """Capture market features at trade entry."""
        try:
            # Calculate BB position
            bb_upper = indicators.get('bb_upper', current_price + 0.001)
            bb_lower = indicators.get('bb_lower', current_price - 0.001)
            bb_range = bb_upper - bb_lower
            bb_position_pct = ((current_price - bb_lower) / bb_range * 100) if bb_range > 0 else 50.0
            
            # Calculate EMA separation
            ema9 = indicators.get('ema_fast', current_price)
            ema21 = indicators.get('ema_slow', current_price)
            ema_separation = abs(ema9 - ema21)
            
            # Get spread
            spread_pips = self._get_current_spread_pips(symbol)
            
            # Determine session
            session = self._get_current_session()
            
            features = {
                'ema9': ema9,
                'ema21': ema21,
                'ema_separation': ema_separation,
                'macd_line': indicators.get('macd', 0.0),
                'macd_signal': indicators.get('macd_signal', 0.0),
                'rsi': indicators.get('rsi', 50.0),
                'bb_upper': bb_upper,
                'bb_middle': indicators.get('bb_middle', current_price),
                'bb_lower': bb_lower,
                'bb_position_pct': bb_position_pct,
                'atr': indicators.get('atr', 0.0001),
                'spread_pips': spread_pips,
                'session': session,
                'hour_utc': datetime.now().hour
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Error capturing entry features: {e}")
            return {}
    
    def _get_current_spread_pips(self, symbol: str) -> float:
        """Get current spread in pips."""
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                spread = tick.ask - tick.bid
                return spread * 10000  # Convert to pips for major pairs
            return 0.0
        except:
            return 0.0
    
    def _get_current_session(self) -> str:
        """Determine current trading session."""
        hour_utc = datetime.now().hour
        
        if 0 <= hour_utc < 6:
            return "asian"
        elif 6 <= hour_utc < 10:
            return "london_pre"
        elif 10 <= hour_utc < 17:
            return "london_ny_overlap"
        elif 17 <= hour_utc < 22:
            return "ny_close"
        else:
            return "off_hours"
    
    def log_trade_entry(self,
                       symbol: str,
                       action: str,
                       volume: float,
                       entry_price: float,
                       sl_price: float,
                       tp_price: float,
                       indicators: Dict,
                       risk_amount: float,
                       risk_pct: float,
                       magic_number: int) -> str:
        """
        Log trade entry with full market context.
        
        Returns:
            Trade ID for later reference
        """
        try:
            # Generate unique trade ID
            trade_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Capture entry features
            features = self.capture_entry_features(symbol, indicators, entry_price)
            
            # Create trade metrics record
            trade = TradeMetrics(
                timestamp=datetime.now().isoformat(),
                symbol=symbol,
                action=action,
                volume=volume,
                entry_price=entry_price,
                sl_price=sl_price,
                tp_price=tp_price,
                risk_amount=risk_amount,
                risk_pct=risk_pct,
                magic_number=magic_number,
                **features  # Unpack all the features
            )
            
            # Save to file
            self._append_trade_record(trade_id, trade)
            
            logger.info(f"Trade entry logged: {trade_id} - {action} {volume} {symbol} at {entry_price}")
            
            return trade_id
            
        except Exception as e:
            logger.error(f"Error logging trade entry: {e}")
            return ""
    
    def log_trade_exit(self,
                      trade_id: str,
                      exit_price: float,
                      profit_loss: float,
                      exit_reason: str,
                      bars_in_trade: int = 0) -> None:
        """Log trade exit and calculate final metrics."""
        try:
            # Load existing trade record
            trade_record = self._load_trade_record(trade_id)
            if not trade_record:
                logger.error(f"Cannot find trade record for {trade_id}")
                return
            
            # Calculate metrics
            if trade_record['action'] == 'buy':
                profit_pips = (exit_price - trade_record['entry_price']) * 10000
            else:
                profit_pips = (trade_record['entry_price'] - exit_price) * 10000
            
            # Calculate R multiple
            sl_distance = abs(trade_record['sl_price'] - trade_record['entry_price'])
            result_r = (abs(profit_loss) / trade_record['risk_amount']) if trade_record['risk_amount'] > 0 else 0
            if profit_loss < 0:
                result_r = -result_r
            
            # Update trade record
            trade_record.update({
                'exit_price': exit_price,
                'profit_loss': profit_loss,
                'profit_pips': profit_pips,
                'result_r': result_r,
                'bars_in_trade': bars_in_trade,
                'exit_reason': exit_reason
            })
            
            # Save updated record
            self._update_trade_record(trade_id, trade_record)
            
            logger.info(f"Trade exit logged: {trade_id} - {exit_reason} "
                       f"{profit_pips:+.1f} pips ({result_r:+.2f}R)")
            
        except Exception as e:
            logger.error(f"Error logging trade exit: {e}")
    
    def _append_trade_record(self, trade_id: str, trade: TradeMetrics) -> None:
        """Append trade record to JSONL file."""
        try:
            record = {
                'trade_id': trade_id,
                'trade_data': asdict(trade)
            }
            
            with open(self.trades_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record) + '\n')
                
        except Exception as e:
            logger.error(f"Error appending trade record: {e}")
    
    def _load_trade_record(self, trade_id: str) -> Optional[Dict]:
        """Load specific trade record by ID."""
        try:
            if not os.path.exists(self.trades_file):
                return None
            
            with open(self.trades_file, 'r', encoding='utf-8') as f:
                for line in f:
                    record = json.loads(line.strip())
                    if record['trade_id'] == trade_id:
                        return record['trade_data']
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading trade record: {e}")
            return None
    
    def _update_trade_record(self, trade_id: str, updated_data: Dict) -> None:
        """Update existing trade record."""
        try:
            if not os.path.exists(self.trades_file):
                return
            
            # Read all records
            records = []
            with open(self.trades_file, 'r', encoding='utf-8') as f:
                for line in f:
                    record = json.loads(line.strip())
                    if record['trade_id'] == trade_id:
                        record['trade_data'] = updated_data
                    records.append(record)
            
            # Write back all records
            with open(self.trades_file, 'w', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record) + '\n')
                    
        except Exception as e:
            logger.error(f"Error updating trade record: {e}")
    
    def load_trades(self, days_back: int = 30, magic_number: Optional[int] = None) -> List[Dict]:
        """Load trades from the last N days."""
        try:
            if not os.path.exists(self.trades_file):
                return []
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            trades = []
            
            with open(self.trades_file, 'r', encoding='utf-8') as f:
                for line in f:
                    record = json.loads(line.strip())
                    trade_data = record['trade_data']
                    
                    # Filter by date
                    trade_time = datetime.fromisoformat(trade_data['timestamp'])
                    if trade_time < cutoff_date:
                        continue
                    
                    # Filter by magic number if specified
                    if magic_number and trade_data.get('magic_number') != magic_number:
                        continue
                    
                    # Only include completed trades
                    if trade_data.get('exit_price') is not None:
                        trades.append(trade_data)
            
            return trades
            
        except Exception as e:
            logger.error(f"Error loading trades: {e}")
            return []
    
    def calculate_performance_stats(self, trades: List[Dict]) -> PerformanceStats:
        """Calculate comprehensive performance statistics."""
        if not trades:
            return PerformanceStats()
        
        try:
            stats = PerformanceStats()
            stats.total_trades = len(trades)
            
            # Separate wins and losses
            wins = [t for t in trades if t['profit_loss'] > 0]
            losses = [t for t in trades if t['profit_loss'] <= 0]
            
            stats.winning_trades = len(wins)
            stats.losing_trades = len(losses)
            stats.win_rate = (stats.winning_trades / stats.total_trades * 100) if stats.total_trades > 0 else 0
            
            # Calculate averages
            if wins:
                stats.avg_win_pips = np.mean([t['profit_pips'] for t in wins])
                stats.avg_win_r = np.mean([t['result_r'] for t in wins])
            
            if losses:
                stats.avg_loss_pips = np.mean([abs(t['profit_pips']) for t in losses])
                stats.avg_loss_r = np.mean([abs(t['result_r']) for t in losses])
            
            # Total profits
            stats.total_profit_pips = sum(t['profit_pips'] for t in trades)
            stats.total_profit_r = sum(t['result_r'] for t in trades)
            
            # Expectancy
            stats.expectancy_pips = stats.total_profit_pips / stats.total_trades if stats.total_trades > 0 else 0
            stats.expectancy_r = stats.total_profit_r / stats.total_trades if stats.total_trades > 0 else 0
            
            # Profit factor
            gross_profit = sum(t['profit_loss'] for t in wins) if wins else 0
            gross_loss = abs(sum(t['profit_loss'] for t in losses)) if losses else 1
            stats.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            
            # Best/worst trades
            stats.best_trade_r = max((t['result_r'] for t in trades), default=0)
            stats.worst_trade_r = min((t['result_r'] for t in trades), default=0)
            
            # Consecutive wins/losses
            consecutive_wins = 0
            consecutive_losses = 0
            current_wins = 0
            current_losses = 0
            
            for trade in trades:
                if trade['profit_loss'] > 0:
                    current_wins += 1
                    current_losses = 0
                    consecutive_wins = max(consecutive_wins, current_wins)
                else:
                    current_losses += 1
                    current_wins = 0
                    consecutive_losses = max(consecutive_losses, current_losses)
            
            stats.max_consecutive_wins = consecutive_wins
            stats.max_consecutive_losses = consecutive_losses
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating performance stats: {e}")
            return PerformanceStats()
    
    def generate_weekly_report(self, magic_number: Optional[int] = None) -> str:
        """Generate comprehensive weekly performance report."""
        try:
            # Load last 7 days of trades
            trades = self.load_trades(days_back=7, magic_number=magic_number)
            stats = self.calculate_performance_stats(trades)
            
            # Generate report
            report_lines = [
                "WEEKLY TRADING PERFORMANCE REPORT",
                "=" * 50,
                f"Report Period: {datetime.now().strftime('%Y-%m-%d')} (Last 7 days)",
                f"Magic Number: {magic_number if magic_number else 'All'}",
                "",
                "OVERALL PERFORMANCE",
                f"Total Trades: {stats.total_trades}",
                f"Win Rate: {stats.win_rate:.1f}% ({stats.winning_trades}W / {stats.losing_trades}L)",
                f"Expectancy: {stats.expectancy_r:+.3f}R ({stats.expectancy_pips:+.1f} pips)",
                f"Profit Factor: {stats.profit_factor:.2f}",
                "",
                "TRADE QUALITY",
                f"Average Win: {stats.avg_win_r:.2f}R ({stats.avg_win_pips:.1f} pips)",
                f"Average Loss: -{stats.avg_loss_r:.2f}R ({stats.avg_loss_pips:.1f} pips)",
                f"Best Trade: {stats.best_trade_r:+.2f}R",
                f"Worst Trade: {stats.worst_trade_r:+.2f}R",
                "",
                "CONSISTENCY",
                f"Max Consecutive Wins: {stats.max_consecutive_wins}",
                f"Max Consecutive Losses: {stats.max_consecutive_losses}",
                "",
                "TOTALS",
                f"Total Profit: {stats.total_profit_r:+.2f}R ({stats.total_profit_pips:+.1f} pips)",
            ]
            
            # Add trade-by-trade details if not too many
            if len(trades) <= 20:
                report_lines.extend([
                    "",
                    "RECENT TRADES",
                    "-" * 30
                ])
                
                for trade in trades[-10:]:  # Last 10 trades
                    entry_time = datetime.fromisoformat(trade['timestamp']).strftime('%m-%d %H:%M')
                    report_lines.append(
                        f"{entry_time} | {trade['action'].upper():4} | "
                        f"{trade['result_r']:+.2f}R | {trade['exit_reason']}"
                    )
            
            report = "\n".join(report_lines)
            
            # Save report to file
            report_file = f"{self.data_dir}/reports/weekly_report_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(report_file, 'w') as f:
                f.write(report)
            
            logger.info(f"Weekly report generated: {report_file}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            return "Error generating report"


# Convenience functions
def create_telemetry() -> TradeTelemetry:
    """Create telemetry instance with default settings."""
    return TradeTelemetry()

def log_entry(symbol: str, action: str, volume: float, entry_price: float,
              sl_price: float, tp_price: float, indicators: Dict,
              risk_amount: float, risk_pct: float, magic_number: int) -> str:
    """Convenience function for logging trade entry."""
    telemetry = create_telemetry()
    return telemetry.log_trade_entry(symbol, action, volume, entry_price,
                                   sl_price, tp_price, indicators,
                                   risk_amount, risk_pct, magic_number)


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Trade Telemetry Test")
    print("=" * 40)
    
    telemetry = TradeTelemetry()
    
    # Test feature capture
    test_indicators = {
        'rsi': 65.2,
        'macd': 0.0012,
        'macd_signal': 0.0008,
        'bb_upper': 1.08567,
        'bb_middle': 1.08456,
        'bb_lower': 1.08345,
        'atr': 0.0012,
        'ema_fast': 1.08478,
        'ema_slow': 1.08432
    }
    
    features = telemetry.capture_entry_features("EURUSD", test_indicators, 1.08450)
    print(f"\nFeatures captured:")
    for key, value in features.items():
        print(f"  {key}: {value}")
    
    # Generate test report
    report = telemetry.generate_weekly_report()
    print(f"\nWeekly report preview (first 10 lines):")
    for line in report.split('\n')[:10]:
        print(line)
