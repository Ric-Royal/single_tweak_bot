"""
GPT Response Parser Module

This module provides functions to parse GPT-4 responses for trading decisions.
"""

import json
import re
import logging
from typing import Dict, Optional, Union, Any


logger = logging.getLogger(__name__)


def parse_json_response(response: str) -> Optional[Dict]:
    """
    Parse GPT response as JSON.
    
    Args:
        response: Raw GPT response string
        
    Returns:
        Parsed dictionary or None if parsing fails
    """
    try:
        # Try direct JSON parsing
        return json.loads(response.strip())
    except json.JSONDecodeError:
        # Try to extract JSON from response
        return extract_json_from_text(response)


def extract_json_from_text(text: str) -> Optional[Dict]:
    """
    Extract JSON object from text that may contain additional content.
    
    Args:
        text: Text containing JSON object
        
    Returns:
        Extracted JSON dictionary or None
    """
    try:
        # Look for JSON blocks between curly braces
        start_idx = text.find('{')
        end_idx = text.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx:end_idx]
            return json.loads(json_str)
        
        # Try to find JSON-like patterns with regex
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting JSON from text: {e}")
        return None


def parse_text_response(response: str) -> Optional[Dict]:
    """
    Parse GPT response using text pattern matching.
    
    Args:
        response: Raw GPT response string
        
    Returns:
        Parsed dictionary or None if parsing fails
    """
    try:
        text = response.lower().strip()
        result = {}
        
        # Extract action
        action = extract_action(text)
        if action:
            result['action'] = action
        
        # Extract volume
        volume = extract_number_after_keyword(text, ['volume', 'lot', 'lots', 'size'])
        if volume:
            result['volume'] = volume
        
        # Extract stop loss
        sl = extract_number_after_keyword(text, ['stop_loss', 'stop-loss', 'sl', 'stoploss'])
        if sl:
            result['stop_loss_pips'] = sl
        
        # Extract take profit
        tp = extract_number_after_keyword(text, ['take_profit', 'take-profit', 'tp', 'takeprofit'])
        if tp:
            result['take_profit_pips'] = tp
        
        # Extract reasoning
        reasoning = extract_reasoning(response)
        if reasoning:
            result['reasoning'] = reasoning
        
        return result if result else None
        
    except Exception as e:
        logger.error(f"Error parsing text response: {e}")
        return None


def extract_action(text: str) -> Optional[str]:
    """
    Extract trading action from text.
    
    Args:
        text: Text to search for action
        
    Returns:
        Trading action ('buy', 'sell', 'hold') or None
    """
    text = text.lower()
    
    # Count occurrences to handle conflicts
    buy_count = len(re.findall(r'\bbuy\b', text))
    sell_count = len(re.findall(r'\bsell\b', text))
    hold_count = len(re.findall(r'\bhold\b', text))
    
    # Check for explicit negations
    if re.search(r'\b(do not|don\'t|avoid|no)\s+(buy|sell)', text):
        return 'hold'
    
    if re.search(r'\b(not\s+recommend|against)\s+(buy|sell)', text):
        return 'hold'
    
    # Determine action based on counts and context
    if hold_count > 0 or re.search(r'\b(hold|wait|stay|neutral|no trade)\b', text):
        return 'hold'
    elif buy_count > sell_count and buy_count > 0:
        return 'buy'
    elif sell_count > buy_count and sell_count > 0:
        return 'sell'
    elif buy_count == sell_count and buy_count > 0:
        # If equal, look for stronger indicators
        if re.search(r'\b(strong buy|buy signal|bullish)\b', text):
            return 'buy'
        elif re.search(r'\b(strong sell|sell signal|bearish)\b', text):
            return 'sell'
        else:
            return 'hold'
    
    return None


def extract_number_after_keyword(text: str, keywords: list) -> Optional[float]:
    """
    Extract number that appears after specific keywords.
    
    Args:
        text: Text to search
        keywords: List of keywords to look for
        
    Returns:
        Extracted number or None
    """
    for keyword in keywords:
        # Pattern to match keyword followed by number
        patterns = [
            rf'\b{keyword}[:\s=]+([0-9]*\.?[0-9]+)',
            rf'\b{keyword}\s*[:\s=]*\s*([0-9]*\.?[0-9]+)',
            rf'{keyword}[^0-9]*([0-9]*\.?[0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
    
    return None


def extract_reasoning(text: str) -> Optional[str]:
    """
    Extract reasoning or explanation from response.
    
    Args:
        text: Text to extract reasoning from
        
    Returns:
        Reasoning text or None
    """
    # Look for common reasoning keywords
    reasoning_patterns = [
        r'reasoning[:\s]+(.*?)(?:\n|$)',
        r'explanation[:\s]+(.*?)(?:\n|$)',
        r'because[:\s]+(.*?)(?:\n|$)',
        r'rationale[:\s]+(.*?)(?:\n|$)',
        r'analysis[:\s]+(.*?)(?:\n|$)'
    ]
    
    for pattern in reasoning_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            reasoning = match.group(1).strip()
            # Clean up the reasoning
            reasoning = re.sub(r'\s+', ' ', reasoning)  # Normalize whitespace
            reasoning = reasoning.strip('",}')  # Remove trailing punctuation
            if len(reasoning) > 10:  # Ensure it's substantial
                return reasoning
    
    return None


def validate_parsed_decision(decision: Dict, defaults: Optional[Dict] = None) -> Dict:
    """
    Validate and normalize parsed trading decision.
    
    Args:
        decision: Parsed decision dictionary
        defaults: Default values for missing fields
        
    Returns:
        Validated and normalized decision dictionary
    """
    if defaults is None:
        defaults = {
            'volume': 0.01,
            'stop_loss_pips': 20,
            'take_profit_pips': 50,
            'reasoning': 'No reasoning provided'
        }
    
    # Ensure action is valid
    action = decision.get('action', '').lower()
    if action not in ['buy', 'sell', 'hold']:
        logger.warning(f"Invalid action '{action}', defaulting to 'hold'")
        decision['action'] = 'hold'
    else:
        decision['action'] = action
    
    # Validate and set volume
    volume = decision.get('volume')
    try:
        volume = float(volume) if volume is not None else defaults['volume']
        if volume <= 0:
            volume = defaults['volume']
        decision['volume'] = volume
    except (TypeError, ValueError):
        decision['volume'] = defaults['volume']
    
    # Validate and set stop loss
    sl = decision.get('stop_loss_pips')
    try:
        sl = float(sl) if sl is not None else defaults['stop_loss_pips']
        if sl <= 0:
            sl = defaults['stop_loss_pips']
        decision['stop_loss_pips'] = sl
    except (TypeError, ValueError):
        decision['stop_loss_pips'] = defaults['stop_loss_pips']
    
    # Validate and set take profit
    tp = decision.get('take_profit_pips')
    try:
        tp = float(tp) if tp is not None else defaults['take_profit_pips']
        if tp <= 0:
            tp = defaults['take_profit_pips']
        decision['take_profit_pips'] = tp
    except (TypeError, ValueError):
        decision['take_profit_pips'] = defaults['take_profit_pips']
    
    # Set reasoning
    if 'reasoning' not in decision or not decision['reasoning']:
        decision['reasoning'] = defaults['reasoning']
    
    return decision


def parse_gpt_response(response: str, require_json: bool = True, 
                      fallback_to_text: bool = True, 
                      defaults: Optional[Dict] = None) -> Optional[Dict]:
    """
    Main function to parse GPT-4 response for trading decisions.
    
    Args:
        response: Raw GPT response string
        require_json: Whether to require JSON format
        fallback_to_text: Whether to fallback to text parsing if JSON fails
        defaults: Default values for missing fields
        
    Returns:
        Parsed and validated trading decision dictionary
    """
    if not response or not response.strip():
        logger.error("Empty GPT response")
        return None
    
    # Try JSON parsing first
    decision = parse_json_response(response)
    
    if decision is None and fallback_to_text:
        logger.info("JSON parsing failed, attempting text parsing")
        decision = parse_text_response(response)
    
    if decision is None:
        logger.error("Failed to parse GPT response")
        return None
    
    # Validate and normalize the decision
    decision = validate_parsed_decision(decision, defaults)
    
    logger.info(f"Successfully parsed decision: {decision}")
    return decision


def extract_price_levels(text: str, current_price: float) -> Dict[str, Optional[float]]:
    """
    Extract price levels (absolute prices) from text.
    
    Args:
        text: Text containing price levels
        current_price: Current market price for validation
        
    Returns:
        Dictionary with extracted price levels
    """
    levels = {'stop_loss_price': None, 'take_profit_price': None}
    
    # Pattern for price levels (e.g., "1.23456", "123.45")
    price_pattern = r'([0-9]+\.[0-9]{2,5})'
    
    # Look for stop loss prices
    sl_patterns = [
        rf'stop.?loss[:\s=]+{price_pattern}',
        rf'sl[:\s=]+{price_pattern}',
        rf'stop[:\s=]+{price_pattern}'
    ]
    
    for pattern in sl_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                price = float(match.group(1))
                # Basic validation - SL should be different from current price
                if abs(price - current_price) > 0.0001:
                    levels['stop_loss_price'] = price
                    break
            except ValueError:
                continue
    
    # Look for take profit prices
    tp_patterns = [
        rf'take.?profit[:\s=]+{price_pattern}',
        rf'tp[:\s=]+{price_pattern}',
        rf'target[:\s=]+{price_pattern}'
    ]
    
    for pattern in tp_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                price = float(match.group(1))
                # Basic validation - TP should be different from current price
                if abs(price - current_price) > 0.0001:
                    levels['take_profit_price'] = price
                    break
            except ValueError:
                continue
    
    return levels