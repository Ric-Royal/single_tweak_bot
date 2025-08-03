# GPT-4 Powered MetaTrader5 Trading Bots

## Overview

This solution provides two Python trading bot scripts (single-asset and multi-asset) that integrate MetaTrader 5 (MT5) with OpenAI's GPT-4 API to automate trading decisions. The bots fetch real-time **5-minute (M5) price data** from MT5, compute key technical indicators (RSI, MACD, Bollinger Bands, moving averages), and feed this information into GPT-4 to receive trade recommendations. The AI's response includes a **trade action** (buy, sell, or hold), a **volume** (lot size), and suggested **stop-loss (SL)** and **take-profit (TP)** levels. The script then validates the signal and executes the trade via the MT5 Python API, logging all prompts and decisions for transparency and analysis. This approach leverages GPT-4's natural language processing to interpret market data and generate precise trading signals with entry and exit levels.

**Key Features:**

* **Real-Time Data & Indicators:** Continuously retrieves M5 OHLC data for one or multiple assets from MT5 and calculates RSI, MACD (6,13,5), Bollinger Bands (20-period, 2σ), and moving averages (e.g. 50 and 200 period) in Python.
* **AI-Based Decisions:** Sends a prompt containing recent price history and indicator values to OpenAI's API (GPT-4 model) and receives an **actionable signal** (BUY/SELL or HOLD) with recommended lot size, SL, and TP.
* **Trade Execution:** Parses the AI response and, if a trade signal is given, submits an order via `MetaTrader5.order_send()` with the specified parameters (market order with SL/TP). It uses a small price **deviation** (slippage tolerance) and includes a unique trade comment and magic number for tracking.
* **Logging & Monitoring:** All prompts, AI responses, and trade results are logged to a file (or console) with timestamps for auditability. This includes whether trades were executed successfully or if any errors occurred.
* **Secure API Access:** The OpenAI API key is loaded from an environment variable (e.g. `OPENAI_API_KEY`) for security – **no hard-coded keys** in the script. This prevents accidental exposure of the secret key and follows best practices by treating it like a password.
* **Fault Tolerance & Safety:** The bot is designed with error handling to ensure stability. It checks for valid data and API responses, handles exceptions (like network issues or API errors) by safely retrying or skipping a cycle, and will not execute trades on unrecognized or unsafe instructions. The volume and SL/TP values are validated to be reasonable (e.g., non-zero, within instrument ranges) before sending orders. If the AI suggests "hold" or provides an incomplete response, the bot will log it and not trade.

## 📁 Project Structure

```
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .env.template               # Environment variables template
├── mt5_gpt_single.py           # Single-asset trading bot
├── mt5_gpt_portfolio.py        # Multi-asset portfolio bot
├── config/                     # Configuration files
│   ├── config.yaml             # Bot configuration
│   └── symbols.yaml            # Trading symbols configuration
├── utils/                      # Utility modules
│   ├── __init__.py
│   ├── indicators.py           # Technical indicators calculations
│   ├── parser.py               # GPT response parsing
│   └── logger.py               # Logging utilities
├── logs/                       # Log files directory
└── docs/                       # Documentation
    ├── setup.md                # Detailed setup guide
    ├── prompt_tuning.md        # GPT prompt optimization guide
    └── risk_management.md      # Risk management guidelines
```

## 🛠️ Setup and Dependencies

### Prerequisites

* **MetaTrader 5 Terminal:** Install MetaTrader 5 on Windows 10+ and **log in to a broker account** (demo or live). Ensure the MT5 terminal is running and **Algo Trading is enabled** (if required for API trading).
* **Python Environment:** Install Python 3.7+ on Windows. It's recommended to create a virtual environment.
* **MT5 Python Package:** Install the official MetaTrader5 Python module (`pip install MetaTrader5`). This allows Python to connect to the running MT5 terminal and perform trade operations.
* **OpenAI API Package:** Install OpenAI's Python SDK (`pip install openai`). This is used to call GPT-4.
* **Data and Indicator Libraries:** Install Pandas for data handling (`pip install pandas`). Optionally, install a TA library like **pandas_ta** for technical indicators (`pip install pandas_ta`), or we will compute indicators manually using Pandas/Numpy.

### Installation

1. **Clone or download this repository:**
```bash
git clone <repository-url>
cd gpt4-mt5-trading-bot
```

2. **Create a virtual environment (recommended):**
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
```bash
# Copy the template
copy .env.template .env

# Edit .env and add your OpenAI API key
OPENAI_API_KEY=your_openai_api_key_here
```

5. **Configure trading settings:**
```bash
# Edit config/config.yaml with your preferred settings
# Edit config/symbols.yaml to set trading symbols
```

### Environment Variable Setup

Ensure your OpenAI API key is stored in the environment. The script will retrieve it as shown below:

```python
import os
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")
```

This line fetches the key from the environment and configures the OpenAI client. If the environment variable is not set, the script will be unable to authenticate – you should handle this by exiting with an error message prompting the user to set the variable. Never commit your API key to code or logs.

### Dependencies

All required dependencies are listed in `requirements.txt`:

* **MetaTrader5:** Official MetaQuotes API for MT5
* **openai:** OpenAI Python client for GPT-3/4
* **pandas:** DataFrame library for managing OHLC data
* **pandas_ta:** Technical analysis indicators library (for RSI, MACD, etc.)
* **python-dotenv:** To load environment variables from a .env file
* **pyyaml:** For configuration file parsing

## 🚀 Usage

### Single-Asset Trading Bot

Run the single-asset bot for focused trading on one symbol:

```bash
python mt5_gpt_single.py
```

This bot focuses on one symbol (configurable in the script). It fetches the latest data for that symbol, gets a GPT-4 decision, and executes it.

### Portfolio Trading Bot

Run the portfolio bot for multi-asset trading:

```bash
python mt5_gpt_portfolio.py
```

This script extends the logic to multiple assets. It iterates through a list of symbols, querying each in turn.

### Configuration

Edit the configuration files in the `config/` directory:

- `config.yaml`: Main bot settings (timeframes, risk parameters, etc.)
- `symbols.yaml`: Trading symbols and their specific settings

## 🔒 Security & Safety Precautions

When deploying these bots, consider the following precautions:

* **API Key Security:** Never hard-code your OpenAI API key in the script. Use environment variables or secure storage.
* **Cost Management:** Calling GPT-4 for every cycle incurs API costs. Monitor the frequency of calls and consider using `gpt-3.5-turbo` for more frequent strategies.
* **Testing in Demo:** Always test the bots on a **demo account** before deploying on a live account.
* **Risk Management:** Implement limits to ensure the AI's suggestions stay within your risk tolerance.
* **Error Handling:** The scripts include try/except blocks around API calls and trade execution.
* **Logging & Monitoring:** Review the logs regularly to monitor bot performance.

## 📊 How the Bots Work

Both scripts follow a similar flow, with the portfolio version simply looping over multiple symbols:

1. **Initialize MT5 Connection:** Connect Python to the running MetaTrader 5 terminal
2. **Data Retrieval:** Fetch recent M5 price data for the asset(s)
3. **Indicator Calculation:** Compute RSI, MACD, Bollinger Bands, and moving averages
4. **Prompt Creation:** Format market data for GPT-4 analysis
5. **OpenAI API Call:** Send prompt to GPT-4 and receive trading recommendation
6. **Response Parsing:** Extract action, volume, stop-loss, and take-profit from AI response
7. **Trade Execution:** Validate and execute trades via MT5 API
8. **Logging:** Record all decisions and outcomes for analysis

## 🎯 Prompt Tuning Tips

Getting optimal results from GPT-4 for trading decisions may require some experimentation:

* **Clarity:** Be very clear in the prompt about what you want
* **Format Enforcement:** Request JSON or structured format for easier parsing
* **Include Context:** Incorporate brief strategy hints in the system message
* **Indicator Interpretation:** Ensure the model understands indicator meanings
* **Temperature and Max Tokens:** Use low temperature (0-0.3) for deterministic responses
* **Test Prompts Offline:** Test your prompt structure before deployment

## 📈 Technical Indicators

The bots calculate the following technical indicators:

* **RSI (14-period):** Measures momentum of price changes
* **MACD (12-26-9):** Moving Average Convergence Divergence
* **Bollinger Bands (20, 2σ):** Volatility and price extreme indicators
* **Moving Averages:** 50-period and 200-period SMAs for trend analysis

## 📝 Logging

All bot activities are logged with timestamps:

- **Single bot:** `logs/trading_bot.log`
- **Portfolio bot:** `logs/trading_bot_portfolio.log`

Logs include:
- GPT-4 prompts and responses
- Trade execution results
- Error messages and warnings
- Performance metrics

## ⚠️ Disclaimer

**IMPORTANT:** Trading involves substantial risk and is not suitable for all investors. Past performance is not indicative of future results. Use this software at your own risk. Always test on demo accounts before live trading.

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please read the contributing guidelines and submit pull requests for any improvements.

## 📞 Support

For support and questions, please open an issue in the repository or refer to the documentation in the `docs/` folder.