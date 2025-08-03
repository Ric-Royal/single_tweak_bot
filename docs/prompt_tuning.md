# GPT Prompt Tuning Guide

This guide explains how to optimize GPT-4 prompts for better trading decisions in the MetaTrader5 trading bots.

## Understanding Prompt Engineering

### What is Prompt Engineering?
Prompt engineering is the process of designing and refining prompts to get the best possible responses from GPT models. For trading bots, this means crafting prompts that consistently produce accurate, actionable trading decisions.

### Key Principles
1. **Clarity**: Be explicit about what you want
2. **Context**: Provide relevant market information
3. **Structure**: Use consistent formatting
4. **Constraints**: Set clear boundaries and requirements
5. **Examples**: Show the desired output format

## Current Prompt Structure

### System Message
The system message sets the AI's role and behavior:

```python
{
    "role": "system",
    "content": "You are an expert forex trading analyst. Analyze technical indicators and provide precise trading recommendations in JSON format. Be conservative and prioritize risk management."
}
```

### User Message Template
```python
prompt = f"""Asset: {symbol}, Timeframe: 5m
Latest Price: {latest_price:.5f}

Technical Indicators:
- RSI({RSI_PERIOD}): {indicators['rsi']} {'(Overbought)' if indicators['rsi'] > 70 else '(Oversold)' if indicators['rsi'] < 30 else '(Neutral)'}
- MACD({FAST_MA},{SLOW_MA}): line={indicators['macd']:.6f}, signal={indicators['macd_signal']:.6f}
- Bollinger Bands({BB_PERIOD},{BB_STDDEV}): upper={indicators['bb_upper']:.5f}, lower={indicators['bb_lower']:.5f}
- SMA({SMA_FAST}): {indicators['sma_fast']:.5f}
- SMA({SMA_SLOW}): {indicators['sma_slow']:.5f}

Based on this technical analysis, what is your trading recommendation?

Respond ONLY in JSON format:
{{"action": "buy/sell/hold", "volume": 0.01, "stop_loss_pips": 20, "take_profit_pips": 50, "reasoning": "brief explanation"}}

Requirements:
- action: must be "buy", "sell", or "hold"
- volume: between 0.01 and {MAX_VOLUME}
- stop_loss_pips: reasonable stop loss in pips (10-100)
- take_profit_pips: reasonable take profit in pips (20-200)
- reasoning: brief explanation of your decision"""
```

## Optimization Strategies

### 1. Improving System Messages

#### Conservative Trading
```python
system_message = """You are a conservative forex trading analyst with 20 years of experience. 
Your primary goal is capital preservation. You prefer high-probability trades with favorable risk-reward ratios.
When in doubt, recommend 'hold'. Provide trading recommendations in strict JSON format."""
```

#### Aggressive Trading
```python
system_message = """You are an active forex trader focused on capturing short-term market movements.
You're comfortable with moderate risk for higher returns. Look for clear technical signals and momentum.
Provide trading recommendations in strict JSON format."""
```

#### Trend Following
```python
system_message = """You are a trend-following trading analyst. You believe 'the trend is your friend'.
Focus on moving average relationships, momentum indicators, and trend continuation patterns.
Avoid counter-trend trades. Provide recommendations in strict JSON format."""
```

### 2. Enhancing Indicator Context

#### Add Interpretation Context
```python
# Instead of just values, provide interpretation
rsi_context = f"RSI: {rsi_value} - {'Strong overbought (>80)' if rsi_value > 80 else 'Overbought (70-80)' if rsi_value > 70 else 'Oversold (20-30)' if rsi_value < 30 else 'Strong oversold (<20)' if rsi_value < 20 else 'Neutral (30-70)'}"
```

#### Include Historical Context
```python
# Add trend information
trend_context = f"Price vs SMA200: {'Uptrend (+{((current_price/sma200-1)*100):.1f}%)' if current_price > sma200 else 'Downtrend ({((current_price/sma200-1)*100):.1f}%)'}"
```

#### Add Volatility Context
```python
# Include ATR or Bollinger Band width
bb_width = (bb_upper - bb_lower) / bb_middle * 100
volatility_context = f"Market Volatility: {'High' if bb_width > 2.0 else 'Low' if bb_width < 1.0 else 'Normal'} (BB Width: {bb_width:.2f}%)"
```

### 3. Improving Output Format

#### Structured JSON with Confidence
```python
output_format = """{
    "analysis": {
        "trend": "uptrend/downtrend/sideways",
        "momentum": "bullish/bearish/neutral",
        "volatility": "high/medium/low"
    },
    "decision": {
        "action": "buy/sell/hold",
        "confidence": 0.85,
        "volume": 0.01,
        "stop_loss_pips": 20,
        "take_profit_pips": 50
    },
    "reasoning": "Brief explanation focusing on key factors"
}"""
```

#### Risk-Adjusted Recommendations
```python
output_format = """{
    "action": "buy/sell/hold",
    "volume": 0.01,
    "risk_level": "low/medium/high",
    "stop_loss_pips": 20,
    "take_profit_pips": 50,
    "risk_reward_ratio": 2.5,
    "reasoning": "Key technical factors supporting this decision"
}"""
```

### 4. Advanced Prompt Techniques

#### Chain of Thought Reasoning
```python
prompt_with_reasoning = f"""
First, analyze each indicator:
1. RSI Analysis: {rsi_value} indicates...
2. MACD Analysis: {macd_value} vs {signal_value} suggests...
3. Bollinger Bands: Price at {price} relative to bands...
4. Moving Averages: Trend direction based on MA relationship...

Then, synthesize these signals into a trading decision:
- Primary signals supporting buy/sell/hold
- Risk factors to consider
- Position sizing based on signal strength

Finally, provide your recommendation in JSON format:
{json_format}
"""
```

#### Multi-Timeframe Context
```python
# If you have multiple timeframe data
prompt_with_context = f"""
Higher Timeframe Context (H1):
- Trend: {h1_trend}
- Key levels: Support {h1_support}, Resistance {h1_resistance}

Current Timeframe (M5):
- Price: {current_price}
- Technical indicators: [detailed M5 analysis]

Consider both timeframes in your analysis. Higher timeframe trend should guide direction,
M5 signals should guide timing.
"""
```

## Testing and Validation

### 1. A/B Testing Different Prompts
```python
# Test different prompt versions
prompts_to_test = {
    "conservative": conservative_prompt,
    "aggressive": aggressive_prompt,
    "trend_following": trend_following_prompt
}

# Track performance metrics for each
for prompt_name, prompt_template in prompts_to_test.items():
    # Run backtest with this prompt
    # Track win rate, profit factor, drawdown
    pass
```

### 2. Response Quality Metrics
- **Consistency**: Same market conditions → similar decisions
- **Format Compliance**: Percentage of valid JSON responses
- **Decision Quality**: Alignment with profitable outcomes
- **Risk Management**: Appropriate SL/TP suggestions

### 3. Prompt Iteration Process
1. **Baseline**: Test current prompt performance
2. **Hypothesis**: Identify potential improvements
3. **Experiment**: Test modified prompt
4. **Measure**: Compare key metrics
5. **Iterate**: Refine based on results

## Common Issues and Solutions

### Issue 1: Inconsistent JSON Format
**Problem**: GPT sometimes returns invalid JSON

**Solution**: Strengthen format requirements
```python
json_instruction = """CRITICAL: Respond ONLY with valid JSON. No additional text before or after.
Use this exact format:
{"action": "buy", "volume": 0.01, "stop_loss_pips": 20, "take_profit_pips": 50, "reasoning": "explanation"}

Valid actions: buy, sell, hold
Valid volume: 0.01 to 1.0
Valid pips: positive numbers only"""
```

### Issue 2: Overly Conservative Decisions
**Problem**: GPT recommends "hold" too frequently

**Solution**: Adjust system message bias
```python
system_message = """You are an active trader who takes calculated risks when technical signals align.
A 'hold' decision should only be used when signals are genuinely conflicting or unclear.
When indicators show clear direction, take action with appropriate risk management."""
```

### Issue 3: Ignoring Market Context
**Problem**: GPT doesn't consider broader market conditions

**Solution**: Add market context to prompts
```python
market_context = f"""
Market Context:
- Market session: {get_market_session()}
- Major news events today: {get_news_events()}
- Market volatility: {calculate_market_volatility()}
- Correlation with major pairs: {get_correlation_info()}
"""
```

## Advanced Techniques

### 1. Dynamic Prompt Adjustment
```python
def adjust_prompt_for_market_conditions(base_prompt, market_conditions):
    if market_conditions['volatility'] == 'high':
        return base_prompt + "\nNote: High volatility detected. Consider wider stop losses and smaller position sizes."
    elif market_conditions['news_impact'] == 'high':
        return base_prompt + "\nNote: Major news expected. Consider reducing position size or avoiding trades."
    return base_prompt
```

### 2. Learning from Mistakes
```python
def analyze_failed_trades(failed_trades):
    """Analyze failed trades to improve prompts"""
    common_patterns = identify_failure_patterns(failed_trades)
    
    # Generate prompt improvements based on patterns
    if "false_breakout" in common_patterns:
        add_breakout_confirmation_rules()
    if "news_reversal" in common_patterns:
        add_news_awareness_instructions()
```

### 3. Ensemble Prompting
```python
def get_ensemble_decision(market_data):
    """Get decisions from multiple prompt styles and combine"""
    prompts = {
        'technical': create_technical_prompt(market_data),
        'trend': create_trend_prompt(market_data),
        'momentum': create_momentum_prompt(market_data)
    }
    
    decisions = []
    for style, prompt in prompts.items():
        decision = get_gpt_decision(prompt)
        decisions.append(decision)
    
    # Combine decisions using voting or weighting
    return combine_decisions(decisions)
```

## Monitoring Prompt Performance

### Key Metrics to Track
1. **Response Rate**: Percentage of valid responses
2. **Format Compliance**: Percentage of properly formatted JSON
3. **Decision Distribution**: Buy/Sell/Hold percentages
4. **Performance Metrics**: Win rate, profit factor, Sharpe ratio
5. **Risk Metrics**: Maximum drawdown, average SL distance

### Logging for Analysis
```python
def log_prompt_performance(prompt_version, decision, outcome):
    log_entry = {
        'timestamp': datetime.now(),
        'prompt_version': prompt_version,
        'decision': decision,
        'market_conditions': get_market_state(),
        'outcome': outcome,  # profit/loss after trade close
        'execution_success': True/False
    }
    # Store for later analysis
```

## Best Practices Summary

1. **Start Simple**: Begin with basic prompts and iterate
2. **Be Specific**: Clear requirements produce better results
3. **Test Thoroughly**: Use backtesting to validate prompt changes
4. **Monitor Continuously**: Track prompt performance over time
5. **Adapt to Markets**: Adjust prompts for different market regimes
6. **Document Changes**: Keep track of what works and what doesn't
7. **Balance Constraints**: Too rigid prompts limit adaptability
8. **Consider Costs**: Longer prompts increase API costs

Remember: Prompt engineering is an iterative process. What works in one market condition may not work in another, so continuous monitoring and adjustment are essential.