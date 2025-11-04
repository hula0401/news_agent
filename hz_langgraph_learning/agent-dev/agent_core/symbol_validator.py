"""
Symbol validation and correction utilities.

Handles common symbol naming issues and provides corrections.
"""
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# Common symbol mappings (company name/alias -> correct ticker)
SYMBOL_CORRECTIONS = {
    # Google/Alphabet
    "GOOGLE": ["GOOGL", "GOOG"],
    "ALPHABET": ["GOOGL", "GOOG"],

    # Meta/Facebook
    "FACEBOOK": ["META"],
    "FB": ["META"],

    # Berkshire Hathaway
    "BERKSHIRE": ["BRK.B", "BRK.A"],
    "BRKA": ["BRK.A"],
    "BRKB": ["BRK.B"],

    # Other common cases
    "TWITTER": ["X"],  # Historical reference
    "JPMORGAN": ["JPM"],
    "GOLDMAN": ["GS"],
    "MORGAN STANLEY": ["MS"],
    "BANK OF AMERICA": ["BAC"],
    "WELLS FARGO": ["WFC"],
    "CITIGROUP": ["C"],

    # Tech companies
    "APPLE": ["AAPL"],
    "MICROSOFT": ["MSFT"],
    "AMAZON": ["AMZN"],
    "NVIDIA": ["NVDA"],
    "TESLA": ["TSLA"],
    "NETFLIX": ["NFLX"],
    "AMD": ["AMD"],
    "INTEL": ["INTC"],

    # ETFs
    "SPY": ["SPY"],
    "QQQ": ["QQQ"],
    "DIA": ["DIA"],
    "IWM": ["IWM"],
    "VTI": ["VTI"],
    "VOO": ["VOO"],
}


def validate_and_correct_symbol(symbol: str) -> Tuple[List[str], bool]:
    """
    Validate a ticker symbol and return corrections if needed.

    Args:
        symbol: The ticker symbol to validate

    Returns:
        Tuple of (corrected_symbols, was_corrected)
        - If symbol is valid: ([symbol], False)
        - If symbol needs correction: ([corrected_symbol(s)], True)
        - If symbol is unknown but looks valid: ([symbol], False)

    Examples:
        >>> validate_and_correct_symbol("GOOGLE")
        (["GOOGL", "GOOG"], True)

        >>> validate_and_correct_symbol("TSLA")
        (["TSLA"], False)

        >>> validate_and_correct_symbol("AAPL")
        (["AAPL"], False)
    """
    symbol_upper = symbol.upper().strip()

    # Check if symbol needs correction
    if symbol_upper in SYMBOL_CORRECTIONS:
        corrected = SYMBOL_CORRECTIONS[symbol_upper]
        logger.info(f"✅ Symbol corrected: {symbol} → {corrected}")
        return corrected, True

    # Symbol appears valid (or unknown but we'll try it)
    return [symbol_upper], False


def validate_and_correct_symbols(symbols: List[str]) -> Tuple[List[str], dict]:
    """
    Validate and correct a list of symbols.

    Args:
        symbols: List of ticker symbols to validate

    Returns:
        Tuple of (corrected_symbols, correction_info)
        - corrected_symbols: List of corrected symbols (may be longer if one symbol maps to multiple)
        - correction_info: Dict mapping original symbol to correction info

    Example:
        >>> validate_and_correct_symbols(["GOOGLE", "TSLA", "AAPL"])
        (["GOOGL", "GOOG", "TSLA", "AAPL"],
         {"GOOGLE": {"corrected_to": ["GOOGL", "GOOG"], "was_corrected": True}})
    """
    if not symbols:
        return [], {}

    corrected_symbols = []
    correction_info = {}

    for symbol in symbols:
        corrected, was_corrected = validate_and_correct_symbol(symbol)
        corrected_symbols.extend(corrected)

        if was_corrected:
            correction_info[symbol] = {
                "corrected_to": corrected,
                "was_corrected": True
            }

    # Remove duplicates while preserving order
    seen = set()
    unique_corrected = []
    for sym in corrected_symbols:
        if sym not in seen:
            seen.add(sym)
            unique_corrected.append(sym)

    return unique_corrected, correction_info


def get_correction_message(correction_info: dict) -> Optional[str]:
    """
    Generate a user-friendly message about symbol corrections.

    Args:
        correction_info: Dict from validate_and_correct_symbols

    Returns:
        Human-readable correction message, or None if no corrections

    Example:
        >>> info = {"GOOGLE": {"corrected_to": ["GOOGL", "GOOG"], "was_corrected": True}}
        >>> get_correction_message(info)
        "Note: I corrected GOOGLE to GOOGL and GOOG (Google's actual ticker symbols)."
    """
    if not correction_info:
        return None

    messages = []
    for original, info in correction_info.items():
        if info["was_corrected"]:
            corrected = info["corrected_to"]
            if len(corrected) == 1:
                messages.append(f"{original} → {corrected[0]}")
            else:
                messages.append(f"{original} → {' and '.join(corrected)}")

    if not messages:
        return None

    return f"Note: I corrected {', '.join(messages)}."


# Example usage and tests
if __name__ == "__main__":
    # Test cases
    test_cases = [
        ["GOOGLE"],
        ["GOOGLE", "TSLA", "AAPL"],
        ["FACEBOOK", "META"],
        ["AAPL", "MSFT"],
        [],
        ["INVALID123"],
    ]

    for symbols in test_cases:
        print(f"\n📝 Testing: {symbols}")
        corrected, info = validate_and_correct_symbols(symbols)
        print(f"   Corrected: {corrected}")
        print(f"   Info: {info}")
        msg = get_correction_message(info)
        if msg:
            print(f"   Message: {msg}")
