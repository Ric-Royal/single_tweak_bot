"""
Logging Utilities Module

This module provides enhanced logging functionality for the GPT-4 MetaTrader5 trading bots.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional


def setup_logging(log_level: str = "INFO", 
                 log_dir: str = "logs",
                 log_file: Optional[str] = None,
                 console_logging: bool = True,
                 file_logging: bool = True,
                 max_log_size: int = 10485760,  # 10MB
                 backup_count: int = 5) -> logging.Logger:
    """
    Setup comprehensive logging for the trading bot.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        log_file: Specific log file name (if None, auto-generated)
        console_logging: Enable console output
        file_logging: Enable file logging
        max_log_size: Maximum log file size in bytes
        backup_count: Number of backup log files to keep
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if file_logging and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if file_logging:
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d")
            log_file = f"trading_bot_{timestamp}.log"
        
        log_path = os.path.join(log_dir, log_file)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_log_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def log_trade_execution(logger: logging.Logger, 
                       symbol: str,
                       action: str,
                       volume: float,
                       entry_price: float,
                       sl_price: float,
                       tp_price: float,
                       result: dict) -> None:
    """
    Log trade execution details.
    
    Args:
        logger: Logger instance
        symbol: Trading symbol
        action: Trade action (buy/sell)
        volume: Trade volume
        entry_price: Entry price
        sl_price: Stop loss price
        tp_price: Take profit price
        result: MT5 order result
    """
    if result.retcode == 10009:  # TRADE_RETCODE_DONE
        logger.info(
            f"✅ TRADE EXECUTED | {symbol} | {action.upper()} | "
            f"Vol: {volume} | Entry: {entry_price:.5f} | "
            f"SL: {sl_price:.5f} | TP: {tp_price:.5f} | "
            f"Ticket: {result.order} | Deal: {result.deal}"
        )
    else:
        logger.error(
            f"❌ TRADE FAILED | {symbol} | {action.upper()} | "
            f"Vol: {volume} | Entry: {entry_price:.5f} | "
            f"Error: {result.retcode} - {result.comment}"
        )


def log_gpt_interaction(logger: logging.Logger,
                       symbol: str,
                       prompt: str,
                       response: str,
                       decision: dict,
                       truncate_prompt: bool = True) -> None:
    """
    Log GPT-4 interaction details.
    
    Args:
        logger: Logger instance
        symbol: Trading symbol
        prompt: GPT prompt sent
        response: GPT response received
        decision: Parsed decision
        truncate_prompt: Whether to truncate long prompts
    """
    # Truncate prompt if too long
    if truncate_prompt and len(prompt) > 500:
        prompt_log = prompt[:500] + "... [truncated]"
    else:
        prompt_log = prompt
    
    logger.info(f"🤖 GPT INTERACTION | {symbol}")
    logger.debug(f"📤 PROMPT: {prompt_log}")
    logger.info(f"📥 RESPONSE: {response}")
    logger.info(f"🎯 DECISION: {decision}")


def log_market_analysis(logger: logging.Logger,
                       symbol: str,
                       price: float,
                       indicators: dict) -> None:
    """
    Log market analysis data.
    
    Args:
        logger: Logger instance
        symbol: Trading symbol
        price: Current price
        indicators: Technical indicators
    """
    logger.info(f"📊 MARKET ANALYSIS | {symbol} | Price: {price:.5f}")
    
    # Log key indicators
    if 'rsi' in indicators:
        rsi_status = "🔴 Overbought" if indicators['rsi'] > 70 else "🟢 Oversold" if indicators['rsi'] < 30 else "🟡 Neutral"
        logger.info(f"   RSI: {indicators['rsi']:.2f} {rsi_status}")
    
    if 'macd' in indicators and 'macd_signal' in indicators:
        macd_status = "🟢 Bullish" if indicators['macd'] > indicators['macd_signal'] else "🔴 Bearish"
        logger.info(f"   MACD: {indicators['macd']:.6f} vs Signal: {indicators['macd_signal']:.6f} {macd_status}")
    
    if 'bb_upper' in indicators and 'bb_lower' in indicators:
        if price > indicators['bb_upper']:
            bb_status = "🔴 Above Upper Band"
        elif price < indicators['bb_lower']:
            bb_status = "🟢 Below Lower Band"
        else:
            bb_status = "🟡 Within Bands"
        logger.info(f"   BB: Upper: {indicators['bb_upper']:.5f}, Lower: {indicators['bb_lower']:.5f} {bb_status}")


def log_performance_metrics(logger: logging.Logger,
                          total_trades: int,
                          winning_trades: int,
                          total_pnl: float,
                          max_drawdown: float = None) -> None:
    """
    Log performance metrics.
    
    Args:
        logger: Logger instance
        total_trades: Total number of trades
        winning_trades: Number of winning trades
        total_pnl: Total profit/loss
        max_drawdown: Maximum drawdown (optional)
    """
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    logger.info("📈 PERFORMANCE METRICS")
    logger.info(f"   Total Trades: {total_trades}")
    logger.info(f"   Winning Trades: {winning_trades}")
    logger.info(f"   Win Rate: {win_rate:.1f}%")
    logger.info(f"   Total P&L: {total_pnl:.2f}")
    
    if max_drawdown is not None:
        logger.info(f"   Max Drawdown: {max_drawdown:.2f}")


def log_error_with_context(logger: logging.Logger,
                          error: Exception,
                          context: str,
                          symbol: str = None) -> None:
    """
    Log error with context information.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Context where error occurred
        symbol: Trading symbol (if applicable)
    """
    symbol_info = f" | {symbol}" if symbol else ""
    logger.error(f"❌ ERROR in {context}{symbol_info}: {type(error).__name__}: {str(error)}")
    logger.debug(f"Error details:", exc_info=True)


def log_bot_startup(logger: logging.Logger,
                   bot_type: str,
                   symbols: list,
                   config: dict) -> None:
    """
    Log bot startup information.
    
    Args:
        logger: Logger instance
        bot_type: Type of bot (single/portfolio)
        symbols: List of trading symbols
        config: Bot configuration
    """
    logger.info("🚀 STARTING GPT-4 METATRADER5 TRADING BOT")
    logger.info(f"   Bot Type: {bot_type}")
    logger.info(f"   Symbols: {', '.join(symbols)}")
    logger.info(f"   Timeframe: {config.get('timeframe', 'M5')}")
    logger.info(f"   Cycle Interval: {config.get('cycle_interval', 300)}s")
    logger.info(f"   Max Volume: {config.get('max_volume', 1.0)}")
    logger.info(f"   Risk Limits: Max Trades/Day: {config.get('max_daily_trades', 10)}")


def log_bot_shutdown(logger: logging.Logger, reason: str = "Normal shutdown") -> None:
    """
    Log bot shutdown information.
    
    Args:
        logger: Logger instance
        reason: Reason for shutdown
    """
    logger.info(f"🛑 SHUTTING DOWN BOT: {reason}")


class TradingBotLogger:
    """Enhanced logger class specifically for trading bots."""
    
    def __init__(self, name: str, config: dict = None):
        """
        Initialize trading bot logger.
        
        Args:
            name: Logger name
            config: Logger configuration
        """
        self.name = name
        self.config = config or {}
        
        self.logger = setup_logging(
            log_level=self.config.get('log_level', 'INFO'),
            log_dir=self.config.get('log_dir', 'logs'),
            console_logging=self.config.get('console_logging', True),
            file_logging=self.config.get('file_logging', True),
            max_log_size=self.config.get('max_log_size', 10485760),
            backup_count=self.config.get('backup_count', 5)
        )
        
        # Performance tracking
        self.trade_count = 0
        self.successful_trades = 0
        self.failed_trades = 0
        self.total_pnl = 0.0
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
    
    def log_trade(self, symbol: str, action: str, volume: float, 
                  entry_price: float, sl_price: float, tp_price: float, 
                  result: dict) -> None:
        """Log trade execution."""
        log_trade_execution(self.logger, symbol, action, volume, 
                          entry_price, sl_price, tp_price, result)
        
        self.trade_count += 1
        if result.retcode == 10009:  # Success
            self.successful_trades += 1
        else:
            self.failed_trades += 1
    
    def log_gpt(self, symbol: str, prompt: str, response: str, decision: dict) -> None:
        """Log GPT interaction."""
        log_gpt_interaction(self.logger, symbol, prompt, response, decision)
    
    def log_analysis(self, symbol: str, price: float, indicators: dict) -> None:
        """Log market analysis."""
        log_market_analysis(self.logger, symbol, price, indicators)
    
    def log_startup(self, bot_type: str, symbols: list, config: dict) -> None:
        """Log bot startup."""
        log_bot_startup(self.logger, bot_type, symbols, config)
    
    def log_shutdown(self, reason: str = "Normal shutdown") -> None:
        """Log bot shutdown."""
        log_bot_shutdown(self.logger, reason)
    
    def log_performance(self) -> None:
        """Log current performance metrics."""
        log_performance_metrics(
            self.logger,
            self.trade_count,
            self.successful_trades,
            self.total_pnl
        )
    
    def log_error_context(self, error: Exception, context: str, symbol: str = None) -> None:
        """Log error with context."""
        log_error_with_context(self.logger, error, context, symbol)