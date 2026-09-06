"""Tarot market mappings and minor arcana signal classification."""

from datetime import datetime
from math import atan, ceil, exp, isfinite, log10, pi, sqrt
from typing import Any, Dict, List, Mapping, Sequence, TypedDict

import pandas as pd

from config.archetype_matrix import ARCHETYPE_MATRIX


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


def calculate_knot_topology(price_history: Sequence[float] | pd.Series | pd.DataFrame) -> dict[str, float]:
    """Calculate Frenet-Serret curvature and torsion for a price trajectory."""
    if isinstance(price_history, pd.DataFrame):
        values = price_history.get("close", pd.Series(dtype=float))
    else:
        values = price_history
    prices = pd.to_numeric(pd.Series(values), errors="coerce").dropna().to_numpy(dtype=float)
    if len(prices) < 4:
        return {"kappa": 0.0, "tau": 0.0}

    velocity = prices[1:] - prices[:-1]
    acceleration = velocity[1:] - velocity[:-1]
    jerk = acceleration[1:] - acceleration[:-1]
    snap = jerk[1:] - jerk[:-1] if len(jerk) > 1 else [0.0]
    first = [1.0, velocity[-1], acceleration[-1]]
    second = [0.0, acceleration[-1], jerk[-1]]
    third = [0.0, jerk[-1], snap[-1]]
    cross = [
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    ]
    first_norm = sqrt(sum(component * component for component in first))
    cross_norm_squared = sum(component * component for component in cross)
    curvature = sqrt(cross_norm_squared) / max(first_norm ** 3, 1e-12)
    determinant = sum(
        first[index] * (second[(index + 1) % 3] * third[(index + 2) % 3] - second[(index + 2) % 3] * third[(index + 1) % 3])
        for index in range(3)
    )
    torsion = determinant / max(cross_norm_squared, 1e-12)
    return {
        "kappa": float(round(curvature if isfinite(curvature) else 0.0, 6)),
        "tau": float(round(torsion if isfinite(torsion) else 0.0, 6)),
    }


def calculate_gravity_gradient(order_book: Mapping[str, Any] | None) -> float:
    """Estimate signed liquidity gravity from bid and ask depth."""
    if not order_book:
        return 0.0

    def weighted_depth(levels: Any) -> float:
        if isinstance(levels, (int, float)):
            return max(float(levels), 0.0)
        total = 0.0
        for level in levels if isinstance(levels, (list, tuple)) else []:
            if isinstance(level, Mapping):
                volume = level.get("volume", level.get("quantity", 0.0))
                distance = level.get("distance", 1.0)
            elif isinstance(level, (list, tuple)) and len(level) >= 2:
                _, volume = level[:2]
                distance = 1.0
            else:
                continue
            try:
                total += max(float(volume), 0.0) / max(abs(float(distance)), 1e-6)
            except (TypeError, ValueError):
                continue
        return total

    bid_depth = weighted_depth(order_book.get("bids", order_book.get("bid_volume", 0.0)))
    ask_depth = weighted_depth(order_book.get("asks", order_book.get("ask_volume", 0.0)))
    total_depth = bid_depth + ask_depth
    return round((bid_depth - ask_depth) / total_depth, 6) if total_depth else 0.0


def calculate_branch_probabilities(
    kappa: float, tau: float, gravity_tensor: float
) -> list[dict[str, str | float]]:
    """Convert topology and liquidity gravity into four normalized attractors."""
    curvature = max(float(kappa), 0.0)
    torsion = float(tau)
    gravity = max(-1.0, min(1.0, float(gravity_tensor)))
    scores = [
        exp(max(-20.0, min(20.0, 1.8 * curvature + gravity + 0.5 * torsion))),
        exp(max(-20.0, min(20.0, 0.5 + 1.5 * abs(torsion) + 0.4 * curvature))),
        exp(max(-20.0, min(20.0, 1.0 - 2.0 * curvature - abs(torsion) - abs(gravity)))),
        exp(max(-20.0, min(20.0, 0.4 - gravity + 0.7 * abs(torsion)))),
    ]
    probabilities = [score / sum(scores) * 100.0 for score in scores]
    rounded = [round(probability, 1) for probability in probabilities]
    rounded[-1] = round(100.0 - sum(rounded[:-1]), 1)
    branches = (("wands", "#FFD700"), ("swords", "#00FFFF"), ("cups", "#FFFFFF"), ("pentacles", "#800080"))
    return [
        {"id": branch_id, "prob": probability, "color_hex": color}
        for (branch_id, color), probability in zip(branches, rounded)
    ]


def evaluate_micro_distortion(
    df_s15: pd.DataFrame,
    current_minor_card: str | None,
    macro_trend: str | None,
) -> str:
    """Promote an extreme Minor Arcana card when the S15 pressure agrees.

    The latest four S15 bars form the micro impulse. A volume spike is measured
    against the preceding four-bar average when available; without that baseline,
    the function conservatively declines to promote the card.
    """
    if not current_minor_card or len(df_s15) < 4 or not {"open", "close", "volume"}.issubset(df_s15.columns):
        return current_minor_card or ""

    card_parts = current_minor_card.upper().split("_")
    if len(card_parts) != 2 or card_parts[0] not in {"WANDS", "CUPS", "SWORDS", "PENTACLES"} or card_parts[1] not in {"8", "9", "10"}:
        return current_minor_card

    recent = df_s15[["open", "close", "volume"]].tail(4).apply(pd.to_numeric, errors="coerce")
    if recent.isna().any().any():
        return current_minor_card

    net_delta = float(recent["close"].iloc[-1] - recent["open"].iloc[0])
    reference_price = max(abs(float(recent["open"].iloc[0])), 1e-12)
    delta_ratio = abs(net_delta) / reference_price
    prior = df_s15["volume"].iloc[:-4].tail(4).apply(pd.to_numeric, errors="coerce").dropna()
    if prior.empty:
        return current_minor_card
    volume_ratio = float(recent["volume"].sum()) / max(float(prior.mean()) * 4, 1e-12)
    if delta_ratio < 0.0005 or volume_ratio < 1.5:
        return current_minor_card

    normalized_macro = (macro_trend or "").upper()
    moving_down = net_delta < 0
    direction_matches = (moving_down and normalized_macro in {"DOWN", "DOWN_CONFIRMED"}) or (
        not moving_down and normalized_macro in {"UP", "UP_CONFIRMED"}
    )
    if not direction_matches:
        return current_minor_card

    suit = card_parts[0]
    volatility_weight = df_s15.attrs.get("volatility_weight")
    if volatility_weight is None and "volatility_weight" in df_s15.columns:
        volatility_weight = df_s15["volatility_weight"].iloc[-1]
    try:
        field_is_synchronized = float(volatility_weight) >= 1.0
    except (TypeError, ValueError):
        field_is_synchronized = False
    return f"KING_OF_{suit}" if field_is_synchronized else f"KNIGHT_OF_{suit}"


def evaluate_court_promotion(
    df_s15: pd.DataFrame,
    current_minor_card: str,
    macro_trend: str,
    volatility_weight: float,
) -> str:
    """Promote a mature numbered card when four S15 bars break out.

    Volume is compared with the preceding four-bar average. Delta is the sum of each
    S15 candle body, normalized by the opening price so the thresholds work across
    instruments with different price scales.
    """
    if not current_minor_card or len(df_s15) < 4:
        return current_minor_card
    if not {"open", "close"}.issubset(df_s15.columns):
        return current_minor_card

    card_parts = current_minor_card.upper().split("_")
    suits = {"WANDS", "CUPS", "SWORDS", "PENTACLES"}
    suit = next((part for part in card_parts if part in suits), None)
    strength = next((part for part in card_parts if part in {"8", "9", "10"}), None)
    if suit is None or strength is None:
        return current_minor_card

    volume_column = "tick_volume" if "tick_volume" in df_s15.columns else "volume"
    if volume_column not in df_s15.columns or len(df_s15) <= 4:
        return current_minor_card

    recent = df_s15[["open", "close", volume_column]].tail(4).apply(pd.to_numeric, errors="coerce")
    reference = df_s15[volume_column].iloc[:-4].tail(4).apply(pd.to_numeric, errors="coerce").dropna()
    if recent.isna().any().any() or reference.empty:
        return current_minor_card

    volume_sum = float(recent[volume_column].sum())
    reference_sum = float(reference.mean()) * 4
    volume_ratio = volume_sum / max(reference_sum, 1e-12)
    cumulative_delta = float((recent["close"] - recent["open"]).sum())
    opening_price = max(abs(float(recent["open"].iloc[0])), 1e-12)
    delta_ratio = abs(cumulative_delta) / opening_price

    try:
        tolerance = max(abs(float(volatility_weight)), 1e-6) * 0.0005
    except (TypeError, ValueError):
        tolerance = 0.0005
    normalized_macro = (macro_trend or "").upper()
    direction_matches = (
        cumulative_delta > 0 and normalized_macro in {"UP", "UP_CONFIRMED"}
    ) or (
        cumulative_delta < 0 and normalized_macro in {"DOWN", "DOWN_CONFIRMED"}
    )

    if volume_ratio >= 1.5 and direction_matches and delta_ratio >= tolerance * 2.5:
        return f"KING_OF_{suit}"
    if volume_ratio >= 1.5 and direction_matches and delta_ratio >= tolerance:
        return f"KNIGHT_OF_{suit}"
    if volume_ratio >= 1.2 and direction_matches and delta_ratio <= tolerance:
        return f"QUEEN_OF_{suit}"
    if volume_ratio >= 1.5 and not direction_matches:
        return f"PAGE_OF_{suit}"
    return current_minor_card


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


ICHING_SYMBOLS = [
    "䷀", "䷁", "䷂", "䷃", "䷄", "䷅", "䷆", "䷇", "䷈", "䷉", "䷊", "䷋", "䷌", "䷍", "䷎", "䷏",
    "䷐", "䷑", "䷒", "䷓", "䷔", "䷕", "䷖", "䷗", "䷘", "䷙", "䷚", "䷛", "䷜", "䷝", "䷞", "䷟",
    "䷠", "䷡", "䷢", "䷣", "䷤", "䷥", "䷦", "䷧", "䷨", "䷩", "䷪", "䷫", "䷬", "䷭", "䷮", "䷯",
    "䷰", "䷱", "䷲", "䷳", "䷴", "䷵", "䷶", "䷷", "䷸", "䷹", "䷺", "䷻", "䷼", "䷽", "䷾", "䷿",
]

_ICHING_COLORS = ("#0B1F33", "#123C4A", "#2B5D4F", "#667A3E", "#A77B35", "#9C4A3C", "#5C315D", "#E0B44C")


def _market_value(data: Mapping[str, Any], *names: str, default: float = 0.0) -> float:
    """Read the first finite numeric market field, treating bad feeds as missing."""
    for name in names:
        try:
            value = float(data.get(name, default))
            if pd.notna(value):
                return value
        except (TypeError, ValueError):
            continue
    return default


def _sigmoid(value: float) -> float:
    value = max(-60.0, min(60.0, value))
    return 1.0 / (1.0 + exp(-value))


def calculate_physics_parameters(market_data: Mapping[str, Any]) -> dict[str, float | bool]:
    """Convert normalized market fields into the 3D chart physics contract.

    ``market_data`` may contain scalar indicators and/or ``history`` (a DataFrame).
    Missing optional indicators use neutral values so a provider outage cannot emit NaN.
    """
    history = market_data.get("history")
    frame = history if isinstance(history, pd.DataFrame) else pd.DataFrame()
    close = pd.to_numeric(frame.get("close", pd.Series(dtype=float)), errors="coerce").dropna()
    volume = pd.to_numeric(frame.get("volume", frame.get("tick_volume", pd.Series(dtype=float))), errors="coerce").dropna()
    current_price = _market_value(market_data, "price", "close", default=float(close.iloc[-1]) if not close.empty else 1.0)
    previous_price = _market_value(market_data, "previous_close", default=float(close.iloc[-2]) if len(close) > 1 else current_price)
    short_return = _market_value(market_data, "short_return", "price_change_rate", default=(current_price - previous_price) / max(abs(previous_price), 1e-12))
    rsi = _market_value(market_data, "rsi", default=float(_rsi(close).iloc[-1]) if len(close) >= 15 and pd.notna(_rsi(close).iloc[-1]) else 50.0)

    market_cap = max(_market_value(market_data, "market_cap", "market_capitalization", default=current_price), 1e-12)
    volume_24h = max(_market_value(market_data, "volume_24h", "quote_volume", default=float(volume.tail(24).sum()) if not volume.empty else 1.0), 1e-12)
    thickness_r = log10(1.0 + market_cap) / max(log10(1.0 + volume_24h), 1e-12)

    tension_t = abs(short_return) * 100.0 + abs(rsi - 50.0) / 50.0
    if len(close) >= 20:
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        bandwidth = float((4 * std20.iloc[-1]) / max(abs(sma20.iloc[-1]), 1e-12))
        baseline = float(((4 * std20) / sma20.abs().replace(0, float("nan"))).dropna().tail(20).mean())
        complexity_c = _sigmoid((bandwidth / max(baseline, 1e-12) - 1.0) * 3.0)
        short_ma = float(close.rolling(5).mean().iloc[-1])
        long_ma = float(close.rolling(20).mean().iloc[-1])
    else:
        bandwidth = _market_value(market_data, "bollinger_bandwidth", "bbw")
        baseline = max(_market_value(market_data, "bollinger_baseline", default=bandwidth), 1e-12)
        complexity_c = _sigmoid((bandwidth / baseline - 1.0) * 3.0)
        short_ma = _market_value(market_data, "short_ma", "ma_short", default=current_price)
        long_ma = _market_value(market_data, "long_ma", "ma_long", default=current_price)

    ma_divergence = (short_ma - long_ma) / max(abs(long_ma), 1e-12)
    macd_histogram = _market_value(market_data, "macd_histogram", "macd_hist", default=ma_divergence * current_price)
    macd_scale = max(abs(current_price), 1e-12)
    tornado_tilt_deg = (180.0 / pi) * atan((ma_divergence * 10.0) + (macd_histogram / macd_scale * 10.0))
    bid_volume = _market_value(market_data, "bid_volume", "buy_volume")
    ask_volume = _market_value(market_data, "ask_volume", "sell_volume")
    imbalance = (bid_volume - ask_volume) / max(bid_volume + ask_volume, 1e-12) if bid_volume + ask_volume else 0.0
    return {
        "thickness_r": round(max(0.0, thickness_r), 6),
        "tension_t": round(max(0.0, tension_t), 6),
        "complexity_c": round(max(0.0, min(1.0, complexity_c)), 6),
        "tornado_tilt_deg": round(tornado_tilt_deg, 6),
        "gravity_g": round(max(-1.0, min(1.0, imbalance)), 6),
        "trigger_firework": abs(tornado_tilt_deg) > 45.0,
    }


def map_market_archetype(symbol: str, physics: Mapping[str, Any]) -> dict[str, str | int]:
    """Map the configured Major Arcana matrix and knot model to current conditions."""
    normalized = symbol.upper()
    arcana = next((number for number, entry in ARCHETYPE_MATRIX.items() if normalized in entry["symbol_pool"]), None)
    if arcana is None:
        volatility = float(physics.get("complexity_c", 0.5))
        tilt = abs(float(physics.get("tornado_tilt_deg", 0.0)))
        arcana = 16 if tilt > 45 else 10 if volatility < 0.35 else 1
    entry = ARCHETYPE_MATRIX[arcana]
    knot_model = {"本結び": "honda_knot", "らせん結び": "spiral_knot"}.get(entry["knot_type"], entry["knot_type"])
    return {"major_arcana": arcana, "knot_model": knot_model}


def calculate_iching_visuals(volatility: float, timestamp: datetime | None = None) -> dict[str, str]:
    """Select a deterministic 64-hexagram symbol and seasonal background color."""
    moment = timestamp or datetime.utcnow()
    seasonal = (moment.month - 1) // 3
    normalized = max(0.0, min(1.0, float(volatility)))
    decimal = (int(round(normalized * 63.0)) + seasonal * 7) % 64
    color_index = (decimal // 8 + seasonal) % len(_ICHING_COLORS)
    return {"i_ching_hexagram_symbol": ICHING_SYMBOLS[decimal], "background_hex": _ICHING_COLORS[color_index]}
