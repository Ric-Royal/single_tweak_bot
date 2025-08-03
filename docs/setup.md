# Detailed Setup Guide

This guide provides step-by-step instructions for setting up the GPT-4 powered MetaTrader5 trading bots.

## Prerequisites

### 1. Windows Environment
- Windows 10 or Windows 11 (64-bit)
- Minimum 4GB RAM (8GB recommended)
- Stable internet connection

### 2. MetaTrader 5 Terminal
1. Download MetaTrader 5 from your broker's website or from [MetaQuotes](https://www.metatrader5.com/)
2. Install MT5 and create/login to your trading account (demo recommended for testing)
3. Ensure **Algo Trading** is enabled:
   - Open MT5
   - Go to Tools → Options → Expert Advisors
   - Check "Allow automated trading"
   - Check "Allow DLL imports"

### 3. Python Environment
1. Download Python 3.8+ from [python.org](https://www.python.org/)
2. During installation, check "Add Python to PATH"
3. Verify installation:
   ```cmd
   python --version
   pip --version
   ```

### 4. OpenAI API Account
1. Create an account at [OpenAI](https://platform.openai.com/)
2. Generate an API key in the API section
3. Ensure you have sufficient credits for GPT-4 usage

## Installation Steps

### Step 1: Download the Project
```bash
# Clone or download the repository
git clone <repository-url>
cd gpt4-mt5-trading-bot
```

### Step 2: Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
1. Copy the environment template:
   ```bash
   copy .env.template .env
   ```

2. Edit `.env` file and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_actual_api_key_here
   ```

### Step 5: Configure Trading Settings
1. Edit `config/config.yaml` to customize bot settings:
   - Trading parameters (volume limits, risk settings)
   - Technical indicator parameters
   - OpenAI model settings
   - Logging preferences

2. Edit `config/symbols.yaml` to set trading symbols:
   - For single-asset bot: modify `single_asset.symbol`
   - For portfolio bot: modify `portfolio.symbols` list

## Configuration Details

### Trading Configuration
```yaml
trading:
  max_volume: 1.0              # Maximum lot size per trade
  default_volume: 0.01         # Default lot size
  max_daily_trades: 10         # Maximum trades per day
  max_open_positions: 5        # Maximum concurrent positions
  default_sl_pips: 20          # Default stop loss in pips
  default_tp_pips: 50          # Default take profit in pips
```

### Risk Management Settings
- **max_volume**: Caps the maximum position size
- **max_daily_trades**: Prevents over-trading
- **max_open_positions**: Limits portfolio exposure
- **sl_pips/tp_pips**: Default risk/reward ratios

### OpenAI Configuration
```yaml
openai:
  model: "gpt-4"               # Use gpt-3.5-turbo for lower costs
  temperature: 0.0             # Deterministic responses
  max_tokens: 150              # Response length limit
```

## Testing the Setup

### 1. Test MT5 Connection
```python
import MetaTrader5 as mt5

# Test connection
if mt5.initialize():
    print("MT5 connection successful")
    print(f"Terminal info: {mt5.terminal_info()}")
    print(f"Account info: {mt5.account_info()}")
    mt5.shutdown()
else:
    print("MT5 connection failed")
```

### 2. Test OpenAI API
```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello, are you working?"}],
        max_tokens=10
    )
    print("OpenAI API connection successful")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"OpenAI API connection failed: {e}")
```

### 3. Run Demo Mode
Start with the single-asset bot in demo mode:
```bash
python mt5_gpt_single.py
```

## Troubleshooting

### Common Issues

#### 1. MT5 Connection Failed
- **Error**: `MT5 initialize() failed`
- **Solutions**:
  - Ensure MT5 terminal is running
  - Check if auto-trading is enabled
  - Verify account login
  - Run Python script as administrator

#### 2. Symbol Not Found
- **Error**: `Symbol EURUSD not found`
- **Solutions**:
  - Add symbol to Market Watch in MT5
  - Check symbol spelling in config
  - Verify broker supports the symbol

#### 3. OpenAI API Errors
- **Error**: `API key not found` or `Insufficient credits`
- **Solutions**:
  - Verify API key in `.env` file
  - Check OpenAI account billing
  - Ensure sufficient API credits

#### 4. Import Errors
- **Error**: `ModuleNotFoundError`
- **Solutions**:
  - Activate virtual environment
  - Reinstall requirements: `pip install -r requirements.txt`
  - Check Python version compatibility

### Performance Optimization

#### 1. Reduce API Costs
- Use `gpt-3.5-turbo` instead of `gpt-4`
- Increase `cycle_interval` to reduce API calls
- Optimize prompt length

#### 2. Improve Execution Speed
- Use SSD for faster file I/O
- Close unnecessary MT5 charts
- Optimize indicator calculation periods

#### 3. Network Stability
- Use stable internet connection
- Consider using a VPS for 24/7 operation
- Implement retry logic for network failures

## Security Best Practices

### 1. API Key Security
- Never hardcode API keys in scripts
- Use environment variables or secure vaults
- Rotate API keys regularly
- Monitor API usage

### 2. Trading Account Security
- Start with demo accounts
- Use separate accounts for bot trading
- Monitor account activity regularly
- Set up account alerts

### 3. Risk Management
- Start with small position sizes
- Test thoroughly before live trading
- Monitor bot performance continuously
- Have kill switches for emergency stops

## Next Steps

1. **Start Testing**: Begin with demo account and small volumes
2. **Monitor Performance**: Track bot decisions and outcomes
3. **Optimize Prompts**: Tune GPT prompts based on results
4. **Scale Gradually**: Increase volumes and add symbols slowly
5. **Implement Monitoring**: Set up alerts and performance tracking

## Support and Resources

- **Documentation**: Check the `docs/` folder for additional guides
- **Logs**: Monitor log files in `logs/` directory for troubleshooting
- **Configuration**: Refer to config files for parameter explanations
- **Testing**: Use demo accounts extensively before live trading

Remember: Always test thoroughly and start small when transitioning to live trading!