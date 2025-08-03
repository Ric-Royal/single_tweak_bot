# 📊 Data Storage Guide

## Overview

The enhanced trading bot now includes optional data storage capabilities to track historical market data, indicators, GPT-4 decisions, and trade executions for analysis and backtesting.

## 🔧 Configuration

Data storage is controlled by environment variables in your `.env` file:

```bash
# Enable/disable all data storage (default: true)
ENABLE_DATA_STORAGE=true

# Save raw market data (can be large, default: false)
SAVE_MARKET_DATA=false
```

## 📁 Data Structure

When enabled, data is stored in the following structure:

```
data/
├── market_data/     # Raw OHLC data (if SAVE_MARKET_DATA=true)
├── indicators/      # Technical indicator values
├── decisions/       # GPT-4 decisions and reasoning
├── trades/          # Executed trades
└── performance/     # Performance metrics (future)
```

## 📊 Data Types Stored

### 1. **Indicators** (`data/indicators/`)
- File format: `{SYMBOL}_indicators_{YYYYMMDD}.jsonl`
- Contains: RSI, MACD, Bollinger Bands, SMA, Stochastic, ATR values
- Updated: Every trading cycle (every 5 minutes)

### 2. **GPT-4 Decisions** (`data/decisions/`)
- File format: `{SYMBOL}_decisions_{YYYYMMDD}.jsonl`
- Contains: GPT-4 prompts, responses, parsed decisions, reasoning
- Updated: Every trading cycle

### 3. **Trade Executions** (`data/trades/`)
- File format: `{SYMBOL}_trades_{YYYYMMDD}.jsonl`
- Contains: Trade details, execution results
- Updated: Only when trades are executed

### 4. **Market Data** (`data/market_data/`) - Optional
- File format: `{SYMBOL}_{TIMEFRAME}_{TIMESTAMP}.csv`
- Contains: OHLC data (300 bars)
- Updated: Every cycle (can be large)

## 🔍 Viewing Your Data

Use the built-in data viewer:

```bash
python data_viewer.py
```

This will show:
- 📊 Storage statistics
- 🤖 Recent GPT-4 decisions
- 📈 Recent indicator values
- 💰 Executed trades

## 📚 Sample Data Formats

### Indicators JSON Line
```json
{
  "timestamp": "2025-01-03T19:25:51.656000",
  "symbol": "EURUSD",
  "indicators": {
    "rsi": 65.2,
    "macd": 0.001234,
    "macd_signal": 0.001156,
    "bb_upper": 1.08567,
    "bb_lower": 1.08345,
    "sma_fast": 1.08456,
    "sma_slow": 1.08234,
    "stoch_k": 72.5,
    "stoch_d": 68.3,
    "atr": 0.0012
  }
}
```

### Decision JSON Line
```json
{
  "timestamp": "2025-01-03T19:25:56.492000",
  "symbol": "EURUSD",
  "prompt": "Asset: EURUSD, Timeframe: M5...",
  "response": "{\"action\": \"hold\", \"volume\": 0.01...}",
  "decision": {
    "action": "hold",
    "volume": 0.01,
    "stop_loss_pips": 20.0,
    "take_profit_pips": 50.0,
    "reasoning": "Mixed signals - waiting for confirmation"
  }
}
```

## 🔄 Data Management

### File Rotation
- New files created daily
- Files named with date: `{SYMBOL}_{TYPE}_{YYYYMMDD}.jsonl`
- Easy to archive/backup by date

### Storage Size
- **Indicators**: ~1KB per cycle × 288 cycles/day = ~300KB/day per symbol
- **Decisions**: ~2KB per cycle × 288 cycles/day = ~600KB/day per symbol  
- **Market Data**: ~50KB per cycle × 288 cycles/day = ~14MB/day per symbol
- **Trades**: Variable, only when trades execute

### Cleanup
- Data is stored indefinitely
- You can manually delete old files
- Consider archiving data older than 30 days

## 📈 Analysis Possibilities

With stored data, you can:

1. **Backtest Strategies**: Test indicator changes against historical data
2. **Analyze GPT-4 Performance**: Review decision quality over time
3. **Optimize Parameters**: Find best RSI/MACD/ATR settings
4. **Risk Analysis**: Track stop-loss effectiveness
5. **Market Research**: Study indicator behavior across market conditions

## 🛠️ Custom Analysis Scripts

Create your own analysis scripts using the data:

```python
from utils.data_manager import DataManager

# Load historical indicators
dm = DataManager()
df = dm.load_historical_indicators('EURUSD', days=7)

# Analyze RSI patterns
rsi_overbought = df[df['indicators'].apply(lambda x: x['rsi'] > 70)]
print(f"RSI overbought periods: {len(rsi_overbought)}")
```

## ⚠️ Important Notes

1. **Performance Impact**: Data storage adds minimal overhead (~1-2ms per cycle)
2. **Error Handling**: Storage failures don't affect trading operations
3. **Privacy**: All data is stored locally, never transmitted
4. **Disk Space**: Monitor disk usage, especially with SAVE_MARKET_DATA=true
5. **Backup**: Consider backing up the `data/` folder regularly

## 🚀 Future Enhancements

Planned features:
- 📊 Performance analytics dashboard
- 📈 Automated backtesting tools
- 📉 Risk metrics calculation
- 🔄 Data export to other formats
- 📱 Web-based data viewer

---

*Data storage is designed to be completely optional and non-intrusive to trading operations.*