"""
Technical Indicators Module

This module provides functions to calculate various technical indicators
used by the GPT-4 MetaTrader5 trading bots.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate RSI (Relative Strength Index).
    
    Args:
        prices: Series of closing prices
        period: RSI period (default 14)
        
    Returns:
        Series of RSI values
    """
    delta = prices.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    
    # Use exponential moving average
    roll_up = up.ewm(span=period, adjust=False).mean()
    roll_down = down.ewm(span=period, adjust=False).mean()
    
    # Avoid division by zero
    rs = roll_up / (roll_down.replace(0, 1e-10))
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        prices: Series of closing prices
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line EMA period (default 9)
        
    Returns:
        Dictionary with 'macd', 'signal', and 'histogram' series
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
    """
    Calculate Bollinger Bands.
    
    Args:
        prices: Series of closing prices
        period: Moving average period (default 20)
        std_dev: Standard deviation multiplier (default 2)
        
    Returns:
        Dictionary with 'upper', 'middle', and 'lower' band series
    """
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    
    return {
        'upper': upper,
        'middle': middle,
        'lower': lower
    }


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """
    Calculate Simple Moving Average.
    
    Args:
        prices: Series of closing prices
        period: SMA period
        
    Returns:
        Series of SMA values
    """
    return prices.rolling(window=period).mean()


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average.
    
    Args:
        prices: Series of closing prices
        period: EMA period
        
    Returns:
        Series of EMA values
    """
    return prices.ewm(span=period, adjust=False).mean()


def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                        k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
    """
    Calculate Stochastic Oscillator.
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        k_period: %K period (default 14)
        d_period: %D period (default 3)
        
    Returns:
        Dictionary with '%K' and '%D' series
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=d_period).mean()
    
    return {
        '%K': k_percent,
        '%D': d_percent
    }


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range.
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        period: ATR period (default 14)
        
    Returns:
        Series of ATR values
    """
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr


def calculate_all_indicators(df: pd.DataFrame, config: Optional[Dict] = None) -> Dict:
    """
    Calculate all technical indicators for a price DataFrame.
    
    Args:
        df: DataFrame with OHLC data (columns: open, high, low, close)
        config: Configuration dictionary with indicator parameters
        
    Returns:
        Dictionary with all calculated indicators
    """
    if config is None:
        config = {
            'rsi_period': 14,
            'macd_fast': 6,
            'macd_slow': 13,
            'macd_signal': 5,
            'bb_period': 20,
            'bb_std_dev': 2,
            'sma_fast': 20,
            'sma_slow': 200,
            'stoch_k': 14,
            'stoch_d': 3,
            'atr_period': 14
        }
    
    # Ensure we have enough data
    required_bars = max(
        config.get('rsi_period', 14),
        config.get('macd_slow', 13),
        config.get('bb_period', 20),
        config.get('sma_slow', 200),
        config.get('stoch_k', 14),
        config.get('atr_period', 14)
    )
    
    if len(df) < required_bars:
        return None
    
    indicators = {}
    
    # RSI
    rsi = calculate_rsi(df['close'], config.get('rsi_period', 14))
    indicators['rsi'] = float(rsi.iloc[-1]) if not rsi.empty else None
    
    # MACD
    macd_data = calculate_macd(
        df['close'], 
        config.get('macd_fast', 6),
        config.get('macd_slow', 13),
        config.get('macd_signal', 5)
    )
    indicators['macd'] = float(macd_data['macd'].iloc[-1]) if not macd_data['macd'].empty else None
    indicators['macd_signal'] = float(macd_data['signal'].iloc[-1]) if not macd_data['signal'].empty else None
    indicators['macd_histogram'] = float(macd_data['histogram'].iloc[-1]) if not macd_data['histogram'].empty else None
    
    # Bollinger Bands
    bb_data = calculate_bollinger_bands(
        df['close'],
        config.get('bb_period', 20),
        config.get('bb_std_dev', 2)
    )
    indicators['bb_upper'] = float(bb_data['upper'].iloc[-1]) if not bb_data['upper'].empty else None
    indicators['bb_middle'] = float(bb_data['middle'].iloc[-1]) if not bb_data['middle'].empty else None
    indicators['bb_lower'] = float(bb_data['lower'].iloc[-1]) if not bb_data['lower'].empty else None
    
    # Moving Averages
    sma_fast = calculate_sma(df['close'], config.get('sma_fast', 20))
    sma_slow = calculate_sma(df['close'], config.get('sma_slow', 200))
    indicators['sma_fast'] = float(sma_fast.iloc[-1]) if not sma_fast.empty else None
    indicators['sma_slow'] = float(sma_slow.iloc[-1]) if not sma_slow.empty else None
    
    # Stochastic
    if 'high' in df.columns and 'low' in df.columns:
        stoch_data = calculate_stochastic(
            df['high'], df['low'], df['close'],
            config.get('stoch_k', 14),
            config.get('stoch_d', 3)
        )
        indicators['stoch_k'] = float(stoch_data['%K'].iloc[-1]) if not stoch_data['%K'].empty else None
        indicators['stoch_d'] = float(stoch_data['%D'].iloc[-1]) if not stoch_data['%D'].empty else None
    
    # ATR
    if 'high' in df.columns and 'low' in df.columns:
        atr = calculate_atr(df['high'], df['low'], df['close'], config.get('atr_period', 14))
        indicators['atr'] = float(atr.iloc[-1]) if not atr.empty else None
    
    # Round all values to appropriate decimal places
    for key, value in indicators.items():
        if value is not None:
            if key in ['rsi', 'stoch_k', 'stoch_d']:
                indicators[key] = round(value, 2)
            elif key in ['macd', 'macd_signal', 'macd_histogram']:
                indicators[key] = round(value, 6)
            else:
                indicators[key] = round(value, 5)
    
    return indicators


def get_indicator_interpretation(indicators: Dict) -> Dict[str, str]:
    """
    Get human-readable interpretations of indicator values.
    
    Args:
        indicators: Dictionary of indicator values
        
    Returns:
        Dictionary of indicator interpretations
    """
    interpretations = {}
    
    # RSI interpretation
    rsi = indicators.get('rsi')
    if rsi is not None:
        if rsi > 70:
            interpretations['rsi'] = 'Overbought'
        elif rsi < 30:
            interpretations['rsi'] = 'Oversold'
        else:
            interpretations['rsi'] = 'Neutral'
    
    # MACD interpretation
    macd = indicators.get('macd')
    macd_signal = indicators.get('macd_signal')
    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            interpretations['macd'] = 'Bullish (above signal)'
        else:
            interpretations['macd'] = 'Bearish (below signal)'
    
    # Bollinger Bands interpretation
    close_price = indicators.get('current_price')  # This would need to be passed separately
    bb_upper = indicators.get('bb_upper')
    bb_lower = indicators.get('bb_lower')
    
    if close_price and bb_upper and bb_lower:
        if close_price > bb_upper:
            interpretations['bollinger'] = 'Above upper band (overbought)'
        elif close_price < bb_lower:
            interpretations['bollinger'] = 'Below lower band (oversold)'
        else:
            interpretations['bollinger'] = 'Within bands (normal)'
    
    # Moving Average interpretation
    sma_fast = indicators.get('sma_fast')
    sma_slow = indicators.get('sma_slow')
    if sma_fast is not None and sma_slow is not None:
        if sma_fast > sma_slow:
            interpretations['trend'] = 'Uptrend (fast MA > slow MA)'
        else:
            interpretations['trend'] = 'Downtrend (fast MA < slow MA)'
    
    # Stochastic interpretation
    stoch_k = indicators.get('stoch_k')
    if stoch_k is not None:
        if stoch_k > 80:
            interpretations['stochastic'] = 'Overbought'
        elif stoch_k < 20:
            interpretations['stochastic'] = 'Oversold'
        else:
            interpretations['stochastic'] = 'Neutral'
    
    return interpretations