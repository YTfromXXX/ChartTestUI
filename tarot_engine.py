"""Tarot market mappings and minor arcana signal classification."""

from math import ceil
from typing import Any, Dict, List, TypedDict

import pandas as pd


class MajorArcanaSymbol(TypedDict):
    card: str
    symbol: str
    element: str


MAJOR_ARCANA_SYMBOLS: Dict[int, MajorArcanaSymbol] = {
    0: {"card": "0_THE_FOOL", "symbol": "DOGEUSD", "element": "AIR"},
    1: {"card": "1_THE_MAGICIAN", "symbol": "BTCUSD", "element": "FIRE"},
    2: {"card": "2_THE_HIGH_PRIESTESS", "symbol": "EURUSD", "element": "WATER"},
    3: {"card": "3_THE_EMPRESS", "symbol": "XAUUSD", "element": "EARTH"},
    4: {"card": "4_THE_EMPEROR", "symbol": "US500", "element": "FIRE"},
    5: {"card": "5_THE_HIEROPHANT", "symbol": "GBPUSD", "element": "EARTH"},
    6: {"card": "6_THE_LOVERS", "symbol": "ETHUSD", "element": "AIR"},
    7: {"card": "7_THE_CHARIOT", "symbol": "NAS100", "element": "WATER"},
    8: {"card": "8_STRENGTH", "symbol": "US30", "element": "FIRE"},
    9: {"card": "9_THE_HERMIT", "symbol": "USDJPY", "element": "EARTH"},
    10: {"card": "10_WHEEL_OF_FORTUNE", "symbol": "SOLUSD", "element": "AIR"},
    11: {"card": "11_JUSTICE", "symbol": "AUDUSD", "element": "AIR"},
    12: {"card": "12_THE_HANGED_MAN", "symbol": "XAGUSD", "element": "WATER"},
    13: {"card": "13_DEATH", "symbol": "LTCUSD", "element": "WATER"},
    14: {"card": "14_TEMPERANCE", "symbol": "USDCHF", "element": "WATER"},
    15: {"card": "15_THE_DEVIL", "symbol": "XRPUSD", "element": "FIRE"},
    16: {"card": "16_THE_TOWER", "symbol": "BTCXAU", "element": "FIRE"},
    17: {"card": "17_THE_STAR", "symbol": "NZDUSD", "element": "AIR"},
    18: {"card": "18_THE_MOON", "symbol": "USDCAD", "element": "WATER"},
    19: {"card": "19_THE_SUN", "symbol": "DAX40", "element": "FIRE"},
    20: {"card": "20_JUDGEMENT", "symbol": "ADAUSD", "element": "AIR"},
    21: {"card": "21_THE_WORLD", "symbol": "GER40", "element": "EARTH"},
}

WATCHLIST_SYMBOLS: List[str] = [entry["symbol"] for entry in MAJOR_ARCANA_SYMBOLS.values()]

ELEMENT_FIELD_COEFFICIENTS: dict[str, float] = {
    "FIRE": 1.5,
    "AIR": 1.2,
    "WATER": 0.8,
    "EARTH": 0.5,
}

if len(MAJOR_ARCANA_SYMBOLS) != 22 or len(set(WATCHLIST_SYMBOLS)) != 22:
    raise ValueError("Major Arcana watchlist must contain 22 unique symbols.")


def calculate_iching_weight(df_m7: pd.DataFrame, element: str) -> dict[str, Any]:
    """Translate six recent M7 bodies into an I Ching volatility field.

    The lower trigram begins with the oldest candle: yang is the visible force of a
    close at or above its open, while yin is the receptive force below it. A missing
    six-candle window returns a neutral, inspectable result rather than inventing a
    hexagram.
    """
    if not {"open", "close"}.issubset(df_m7.columns):
        return {"hexagram_binary": "", "hexagram_decimal": None, "volatility_weight": None}

    recent = df_m7[["open", "close"]].tail(6).apply(pd.to_numeric, errors="coerce").dropna()
    if len(recent) < 6:
        return {"hexagram_binary": "", "hexagram_decimal": None, "volatility_weight": None}

    # The six bodies become six lines; reading old to new preserves the lower-to-upper
    # movement of the hexagram instead of letting the latest candle overwrite history.
    lines = ["1" if close >= open_price else "0" for open_price, close in recent.itertuples(index=False)]
    binary = "".join(lines)
    decimal = int(binary, 2)

    # Sustained polarity stores energy; each yin/yang change releases or redirects it.
    yang_ratio = lines.count("1") / 6
    transitions = sum(left != right for left, right in zip(lines, lines[1:]))
    polarity_energy = 0.72 + abs(yang_ratio - 0.5) * 0.36
    transition_energy = transitions * 0.09
    hexagram_energy = 0.85 + (decimal / 63) * 0.3
    base_weight = polarity_energy + transition_energy + (hexagram_energy - 0.85)

    field_coefficient = ELEMENT_FIELD_COEFFICIENTS.get(element.upper(), 1.0)
    volatility_weight = round(base_weight * field_coefficient, 4)
    return {
        "hexagram_binary": binary,
        "hexagram_decimal": decimal,
        "volatility_weight": volatility_weight,
    }


def get_archetype_parameters(element: str, card_name: str) -> dict[str, float]:
    """Return volatility-sensitive thresholds for a Major Arcana archetype."""
    parameters: dict[str, float] = {
        "rsi_overbought": 80.0,
        "rsi_oversold": 20.0,
        "bbw_squeeze_threshold": 0.02,
        "delta_tolerance": 0.0005,
        "breakout_sensitivity": 1.0,
    }
    normalized_element = element.upper()
    normalized_card = card_name.upper()

    if normalized_element in {"FIRE", "AIR"}:
        parameters.update(rsi_overbought=85.0, rsi_oversold=15.0, delta_tolerance=0.001)
    elif normalized_element in {"EARTH", "WATER"}:
        parameters["bbw_squeeze_threshold"] = 0.015

    if normalized_card in {"0_THE_FOOL", "THE_FOOL"}:
        parameters["rsi_overbought"] = 90.0
    elif normalized_card in {"16_THE_TOWER", "THE_TOWER"}:
        parameters["breakout_sensitivity"] = 0.8

    return parameters


def _card_context(card_name: str | None = None, symbol: str | None = None) -> tuple[str, str]:
    """Resolve an element/card pair from an explicit card or mapped symbol."""
    if card_name:
        normalized_card = card_name.upper()
        for entry in MAJOR_ARCANA_SYMBOLS.values():
            if entry["card"].upper() == normalized_card or entry["card"].upper().endswith(f"_{normalized_card}"):
                return entry["element"], entry["card"]
        return "EARTH", card_name
    if symbol:
        for entry in MAJOR_ARCANA_SYMBOLS.values():
            if entry["symbol"] == symbol:
                return entry["element"], entry["card"]
    return "EARTH", ""


def _strength_1_to_10(value: float) -> int:
    """Clamp a normalized score to the ten minor-card strengths."""
    return max(1, min(10, ceil(value * 10)))


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Wilder-style RSI without requiring a third-party indicator package."""
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    average_gain = gains.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    average_loss = losses.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    relative_strength = average_gain / average_loss.replace(0, float("nan"))
    result = 100 - (100 / (1 + relative_strength))
    result = result.mask((average_loss == 0) & (average_gain > 0), 100)
    result = result.mask((average_loss == 0) & (average_gain == 0), 50)
    return result


def calculate_minor_arcana(df_m7: pd.DataFrame, card_name: str | None = None, symbol: str | None = None) -> str | None:
    """Classify the latest M7 candle as a numbered Minor Arcana card.

    Wands represent an overheated breakout above the upper two-sigma band. Cups
    represent an inner-band squeeze. The remaining states are assigned to Pentacles
    for balanced or recovering conditions and Swords for bearish pressure.
    """
    if "close" not in df_m7.columns or len(df_m7) < 50:
        return None

    context_card = card_name or df_m7.attrs.get("card_name")
    context_symbol = symbol or df_m7.attrs.get("symbol")
    element, resolved_card = _card_context(context_card, context_symbol)
    parameters = get_archetype_parameters(element, resolved_card)

    close = pd.to_numeric(df_m7["close"], errors="coerce")
    if close.isna().any():
        close = close.dropna()
    if len(close) < 50:
        return None

    sma20 = close.rolling(window=20, min_periods=20).mean()
    std20 = close.rolling(window=20, min_periods=20).std()
    bbw = ((sma20 + (2 * std20)) - (sma20 - (2 * std20))) / sma20.abs().replace(0, float("nan"))
    rsi = _rsi(close)
    metrics = pd.DataFrame(
        {
            "close": close,
            "sma20": sma20,
            "std20": std20,
            "bbw": bbw,
            "rsi": rsi,
        }
    ).dropna()
    if len(metrics) < 50:
        return None

    latest = metrics.iloc[-1]
    recent_bbw = metrics["bbw"].tail(50)
    current_close = float(latest["close"])
    sma_value = float(latest["sma20"])
    std_value = float(latest["std20"])
    current_bbw = float(latest["bbw"])
    average_bbw = float(recent_bbw.mean())
    minimum_bbw = float(recent_bbw.min())
    current_rsi = float(latest["rsi"])
    upper1 = sma_value + std_value
    lower1 = sma_value - std_value
    upper2 = sma_value + (2 * std_value)
    lower2 = sma_value - (2 * std_value)

    # Fire strength combines RSI heat and the distance beyond +2 sigma.
    breakout_distance = (current_close - upper2) / max(std_value, 1e-12)
    if current_close > upper2 and current_rsi >= parameters["rsi_overbought"]:
        rsi_range = max(100.0 - parameters["rsi_overbought"], 1.0)
        rsi_score = max(0.0, min(1.0, (current_rsi - parameters["rsi_overbought"]) / rsi_range))
        breakout_score = max(0.0, min(1.0, breakout_distance / parameters["breakout_sensitivity"]))
        return f"WANDS_{_strength_1_to_10((rsi_score + breakout_score) / 2)}"

    # Water requires both inner-band containment and a narrowing band.
    if lower1 <= current_close <= upper1 and current_bbw <= parameters["bbw_squeeze_threshold"] and current_bbw <= average_bbw:
        if current_bbw == 0 and average_bbw == 0:
            contraction_score = 1.0
        else:
            contraction_score = max(0.0, min(1.0, (average_bbw - current_bbw) / max(average_bbw - minimum_bbw, 1e-12)))
        return f"CUPS_{_strength_1_to_10(contraction_score)}"

    # Swords captures a confirmed downside expansion or clearly bearish momentum.
    if current_close < lower2 or (current_close < sma_value and current_rsi < parameters["rsi_oversold"] + 25):
        pressure_score = max(0.0, min(1.0, (lower2 - current_close) / max(std_value, 1e-12)))
        rsi_score = max(0.0, min(1.0, (45 - current_rsi) / 30))
        return f"SWORDS_{_strength_1_to_10(max(pressure_score, rsi_score))}"

    # Pentacles is the neutral/reversion fallback for all non-breakout conditions.
    return "PENTACLES_1" if sma_value == 0 else f"PENTACLES_{_strength_1_to_10(max(0.0, 1 - abs(current_close - sma_value) / max(std_value * 2, 1e-12)))}"


def detect_knots(
    df_m7: pd.DataFrame,
    price_tolerance: float | None = None,
    card_name: str | None = None,
    symbol: str | None = None,
) -> list[dict[str, Any]]:
    """Detect separated, volume-depleted double tops using archetype tolerance."""
    if "high" not in df_m7.columns or len(df_m7) < 3:
        return []
    element, resolved_card = _card_context(card_name, symbol or df_m7.attrs.get("symbol"))
    parameters = get_archetype_parameters(element, resolved_card)
    tolerance = price_tolerance if price_tolerance is not None else parameters["delta_tolerance"]
    volume_column = "tick_volume" if "tick_volume" in df_m7.columns else "volume"
    if volume_column not in df_m7.columns:
        return []

    peaks = [
        index for index in range(1, len(df_m7) - 1)
        if df_m7["high"].iloc[index] > df_m7["high"].iloc[index - 1]
        and df_m7["high"].iloc[index] >= df_m7["high"].iloc[index + 1]
    ]
    knots: list[dict[str, Any]] = []
    for first_position, first_peak in enumerate(peaks):
        for second_peak in peaks[first_position + 1:]:
            if second_peak - first_peak < 4:
                continue
            first_price = float(df_m7["high"].iloc[first_peak])
            second_price = float(df_m7["high"].iloc[second_peak])
            if abs(second_price - first_price) / max(abs(first_price), 1e-12) > tolerance:
                continue
            if float(df_m7[volume_column].iloc[second_peak]) >= float(df_m7[volume_column].iloc[first_peak]):
                continue
            knots.append({
                "knot_time": df_m7.index[second_peak],
                "top1_time": df_m7.index[first_peak],
                "top1_price": first_price,
                "top2_price": second_price,
            })
            break
    return knots


def evaluate_court_card(
    minor_card: str | None,
    micro_status: str | None,
    macro_status: str | None,
) -> str | None:
    """Promote a high-strength Wands card to a Knight or King court card.

    ``FILLING`` represents the S15 pressure trigger. A confirmed macro direction
    promotes the same synchronized setup from Knight to King. Other minor cards are
    returned unchanged so the function can be used directly in a signal pipeline.
    """
    if minor_card is None:
        return None

    normalized_minor = minor_card.upper()
    normalized_micro = (micro_status or "").upper()
    normalized_macro = (macro_status or "").upper()
    is_high_wands = normalized_minor in {f"WANDS_{strength}" for strength in range(8, 11)}
    if not is_high_wands or normalized_micro != "FILLING":
        return minor_card

    confirmed_macro = normalized_macro in {
        "DOWN",
        "DOWN_CONFIRMED",
        "UP",
        "UP_CONFIRMED",
    }
    if confirmed_macro:
        return "KING_OF_WANDS"
    return "KNIGHT_OF_WANDS"
