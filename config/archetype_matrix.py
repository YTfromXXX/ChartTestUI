"""Master data for the 22 Major Arcana knot archetypes."""

from typing import Dict, List, TypedDict


class ArchetypeDefinition(TypedDict):
    card_name: str
    knot_type: str
    market_behavior: str
    symbol_pool: List[str]


ARCHETYPE_MATRIX: Dict[int, ArchetypeDefinition] = {
    0: {"card_name": "愚者", "knot_type": "投げ縄結び", "market_behavior": "予測不能な急騰（Meme/IPO）", "symbol_pool": ["DOGEUSD", "AMC", "US2000"]},
    1: {"card_name": "魔術師", "knot_type": "らせん結び", "market_behavior": "トレンド発生（Tech株/GC）", "symbol_pool": ["BTCUSD", "NVDA", "NAS100"]},
    2: {"card_name": "女教皇", "knot_type": "網代結び", "market_behavior": "分厚い抵抗帯（債券/静かなレンジ）", "symbol_pool": ["APTUSD", "EURUSD", "TLT"]},
    3: {"card_name": "女帝", "knot_type": "鎖結び", "market_behavior": "長期安定上昇（S&P500/Gold）", "symbol_pool": ["ETHUSD", "XAUUSD", "US500"]},
    4: {"card_name": "皇帝", "knot_type": "タークス・ヘッド", "market_behavior": "絶対的サポート（優良株/外貨準備）", "symbol_pool": ["SOLUSD", "AAPL", "BRK.B"]},
    5: {"card_name": "教皇", "knot_type": "本結び", "market_behavior": "チャネル推移（ペッグ通貨）", "symbol_pool": ["USDTUSD", "GBPUSD", "USDC"]},
    6: {"card_name": "恋人", "knot_type": "キャリック・ベンド", "market_behavior": "美しい相関（EUR/USDペア等）", "symbol_pool": ["MATICUSD", "EURJPY", "EURGBP"]},
    7: {"card_name": "戦車", "knot_type": "自在結び", "market_behavior": "押し目からの再加速", "symbol_pool": ["LINKUSD", "AMD", "USTEC"]},
    8: {"card_name": "力", "knot_type": "ブラッドノット", "market_behavior": "シンメトリカル・トライアングル", "symbol_pool": ["AVAXUSD", "US30", "DAX40"]},
    9: {"card_name": "隠者", "knot_type": "もやい結び", "market_behavior": "底値のダイバージェンス", "symbol_pool": ["LTCUSD", "XAGUSD", "USDJPY"]},
    10: {"card_name": "運命の輪", "knot_type": "猿の手結び", "market_behavior": "ボラティリティ圧縮（VIX低下）", "symbol_pool": ["XRPUSD", "TSLA", "VIX"]},
    11: {"card_name": "正義", "knot_type": "ふた結び", "market_behavior": "アセンディング・トライアングル", "symbol_pool": ["ADAUSD", "AUDUSD", "MSFT"]},
    12: {"card_name": "吊るされた男", "knot_type": "引き解け結び", "market_behavior": "トラップ（騙し）", "symbol_pool": ["PEPEUSD", "XRPJPY", "NFLX"]},
    13: {"card_name": "死神", "knot_type": "ひと結び", "market_behavior": "トレンド終焉（三尊天井）", "symbol_pool": ["SHIBUSD", "LTCBTC", "META"]},
    14: {"card_name": "節制", "knot_type": "中間者結び", "market_behavior": "フィボナッチ半値戻し", "symbol_pool": ["USDCUSD", "USDCHF", "KO"]},
    15: {"card_name": "悪魔", "knot_type": "8の字結び", "market_behavior": "異常出来高（インサイダー/仕手）", "symbol_pool": ["DOTUSD", "INTC", "XLE"]},
    16: {"card_name": "塔", "knot_type": "巻き結び（崩壊）", "market_behavior": "パニック売り（暴落）", "symbol_pool": ["BTCXAU", "LUNAUSD", "UVXY"]},
    17: {"card_name": "星", "knot_type": "テント結び", "market_behavior": "明けの明星（希望の光）", "symbol_pool": ["UNIUSD", "NZDUSD", "ORCL"]},
    18: {"card_name": "月", "knot_type": "蝶々結び", "market_behavior": "不確実性（フェイクニュース）", "symbol_pool": ["ATOMUSD", "USDCAD", "GDX"]},
    19: {"card_name": "太陽", "knot_type": "三つ編み（PO）", "market_behavior": "全面高（リスクオン）", "symbol_pool": ["NEARUSD", "AMZN", "DAX30"]},
    20: {"card_name": "審判", "knot_type": "命綱結び", "market_behavior": "V字回復（歴史的転換）", "symbol_pool": ["TRXUSD", "XAUJPY", "SPY"]},
    21: {"card_name": "世界", "knot_type": "エンドレス・ノット", "market_behavior": "サイクル完成（エリオット第5波）", "symbol_pool": ["FILUSD", "GER40", "IWM"]},
}

if set(ARCHETYPE_MATRIX) != set(range(22)):
    raise ValueError("ARCHETYPE_MATRIX must define exactly Major Arcana 0 through 21.")

_CRYPTO_FALLBACK_SYMBOLS = {
    "ADAUSD", "AVAXUSD", "BTCUSD", "BTCXAU", "DOGEUSD", "ETHUSD", "LINKUSD",
    "LTCUSD", "LUNAUSD", "MATICUSD", "NEARUSD", "PEPEUSD", "SHIBUSD", "SOLUSD",
    "TRXUSD", "UNIUSD", "USDC", "USDCUSD", "USDTUSD", "XRPUSD", "ATOMUSD", "DOTUSD", "FILUSD", "APTUSD",
}
if any(len(entry["symbol_pool"]) != 3 for entry in ARCHETYPE_MATRIX.values()):
    raise ValueError("Every archetype must define exactly three symbol-pool candidates.")
if any(not set(entry["symbol_pool"]) & _CRYPTO_FALLBACK_SYMBOLS for entry in ARCHETYPE_MATRIX.values()):
    raise ValueError("Every archetype must include at least one 24/7 crypto fallback.")
