#!/usr/bin/env python3
"""
Data Manager Module

Handles optional data storage for historical market data, indicators,
and trading performance without interfering with bot operations.
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class DataManager:
    """Manages optional data storage for trading bots"""
    
    def __init__(self, enabled: bool = True, base_path: str = "data"):
        self.enabled = enabled
        self.base_path = base_path
        
        if self.enabled:
            self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.base_path,
            f"{self.base_path}/market_data",
            f"{self.base_path}/indicators", 
            f"{self.base_path}/decisions",
            f"{self.base_path}/trades",
            f"{self.base_path}/performance"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def save_market_data(self, symbol: str, timeframe: str, df: pd.DataFrame) -> bool:
        """
        Save market data to CSV file
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            timeframe: Timeframe (e.g., 'M5')
            df: DataFrame with market data
            
        Returns:
            True if saved successfully, False if disabled or error
        """
        if not self.enabled:
            return False
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.base_path}/market_data/{symbol}_{timeframe}_{timestamp}.csv"
            
            # Save with timestamp as index
            df_copy = df.copy()
            if 'time' in df_copy.columns:
                df_copy.set_index('time', inplace=True)
            
            df_copy.to_csv(filename)
            logger.debug(f"Market data saved: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save market data: {e}")
            return False
    
    def save_indicators(self, symbol: str, timestamp: datetime, indicators: Dict) -> bool:
        """
        Save calculated indicators to JSON file
        
        Args:
            symbol: Trading symbol
            timestamp: Current timestamp
            indicators: Dictionary of indicator values
            
        Returns:
            True if saved successfully
        """
        if not self.enabled:
            return False
            
        try:
            date_str = timestamp.strftime("%Y%m%d")
            filename = f"{self.base_path}/indicators/{symbol}_indicators_{date_str}.jsonl"
            
            # Prepare data entry
            entry = {
                "timestamp": timestamp.isoformat(),
                "symbol": symbol,
                "indicators": indicators
            }
            
            # Append to daily file (JSONL format)
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save indicators: {e}")
            return False
    
    def save_gpt_decision(self, symbol: str, timestamp: datetime, 
                         prompt: str, response: str, decision: Dict) -> bool:
        """
        Save GPT-4 decision data
        
        Args:
            symbol: Trading symbol
            timestamp: Decision timestamp
            prompt: GPT-4 prompt sent
            response: GPT-4 raw response
            decision: Parsed decision dictionary
            
        Returns:
            True if saved successfully
        """
        if not self.enabled:
            return False
            
        try:
            date_str = timestamp.strftime("%Y%m%d")
            filename = f"{self.base_path}/decisions/{symbol}_decisions_{date_str}.jsonl"
            
            entry = {
                "timestamp": timestamp.isoformat(),
                "symbol": symbol,
                "prompt": prompt,
                "response": response,
                "decision": decision
            }
            
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save GPT decision: {e}")
            return False
    
    def save_trade_execution(self, symbol: str, timestamp: datetime,
                           decision: Dict, execution_result: Dict) -> bool:
        """
        Save trade execution details
        
        Args:
            symbol: Trading symbol
            timestamp: Execution timestamp
            decision: Original trading decision
            execution_result: MT5 execution result
            
        Returns:
            True if saved successfully
        """
        if not self.enabled:
            return False
            
        try:
            date_str = timestamp.strftime("%Y%m%d")
            filename = f"{self.base_path}/trades/{symbol}_trades_{date_str}.jsonl"
            
            entry = {
                "timestamp": timestamp.isoformat(),
                "symbol": symbol,
                "decision": decision,
                "execution": execution_result
            }
            
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save trade execution: {e}")
            return False
    
    def load_historical_indicators(self, symbol: str, days: int = 7) -> Optional[pd.DataFrame]:
        """
        Load historical indicator data
        
        Args:
            symbol: Trading symbol
            days: Number of days to load
            
        Returns:
            DataFrame with historical indicators or None
        """
        if not self.enabled:
            return None
            
        try:
            all_data = []
            
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                date_str = date.strftime("%Y%m%d")
                filename = f"{self.base_path}/indicators/{symbol}_indicators_{date_str}.jsonl"
                
                if os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8') as f:
                        for line in f:
                            entry = json.loads(line.strip())
                            all_data.append(entry)
            
            if all_data:
                df = pd.DataFrame(all_data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                return df
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load historical indicators: {e}")
            return None
    
    def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        if not self.enabled:
            return {"enabled": False}
            
        try:
            stats = {"enabled": True, "directories": {}}
            
            for subdir in ["market_data", "indicators", "decisions", "trades"]:
                path = f"{self.base_path}/{subdir}"
                if os.path.exists(path):
                    files = os.listdir(path)
                    total_size = sum(os.path.getsize(os.path.join(path, f)) 
                                   for f in files if os.path.isfile(os.path.join(path, f)))
                    
                    stats["directories"][subdir] = {
                        "files": len(files),
                        "size_mb": round(total_size / (1024 * 1024), 2)
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {"enabled": True, "error": str(e)}


# Convenience functions for easy integration
def create_data_manager(enabled: bool = True) -> DataManager:
    """Create a data manager instance"""
    return DataManager(enabled=enabled)

def save_cycle_data(data_manager: DataManager, symbol: str, df: pd.DataFrame, 
                   indicators: Dict, prompt: str, response: str, decision: Dict):
    """Save all data from a trading cycle"""
    if not data_manager.enabled:
        return
        
    timestamp = datetime.now()
    
    # Save market data (optional - can be large)
    data_manager.save_market_data(symbol, "M5", df)
    
    # Save indicators (recommended)
    data_manager.save_indicators(symbol, timestamp, indicators)
    
    # Save GPT decision (recommended for analysis)
    data_manager.save_gpt_decision(symbol, timestamp, prompt, response, decision)