"""
backend/utils/indicators.py
보조 기술 지표 계산: RSI, SMA, EMA, Bollinger Bands, Golden Cross
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class IndicatorResult:
    rsi: pd.Series
    sma_20: pd.Series
    sma_60: pd.Series
    ema_20: pd.Series
    bb_upper: pd.Series
    bb_middle: pd.Series
    bb_lower: pd.Series
    golden_cross: pd.Series     # 1=골든크로스, -1=데드크로스, 0=없음
    volume: pd.Series


def calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(com=window - 1, min_periods=window).mean()
    avg_loss = loss.ewm(com=window - 1, min_periods=window).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_bollinger_bands(
    close: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """볼린저 밴드 (상단, 중간, 하단) 반환"""
    sma = close.rolling(window=window).mean()
    std = close.rolling(window=window).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    return upper, sma, lower


def calculate_golden_cross(
    sma_short: pd.Series, sma_long: pd.Series
) -> pd.Series:
    """
    골든/데드크로스 감지
    1 = 골든크로스 (단기선이 장기선 상향 돌파)
    -1 = 데드크로스 (단기선이 장기선 하향 돌파)
    0 = 없음
    """
    signal = pd.Series(0, index=sma_short.index)
    above = (sma_short > sma_long).to_numpy(dtype=bool)
    prev_above = np.roll(above, 1)
    prev_above[0] = False
    cross_up = above & ~prev_above
    cross_down = ~above & prev_above
    signal[cross_up] = 1
    signal[cross_down] = -1
    return signal


def calculate_all_indicators(df: pd.DataFrame) -> IndicatorResult:
    """
    모든 기술 지표를 한번에 계산
    
    Args:
        df: OHLCV DataFrame (Close, Volume 필수)
    """
    close = df["Close"]
    volume = df["Volume"] if "Volume" in df.columns else pd.Series(dtype=float)
    
    # RSI
    rsi = calculate_rsi(close, window=14)
    
    # 이동평균
    sma_20 = close.rolling(20).mean()
    sma_60 = close.rolling(60).mean()
    ema_20 = close.ewm(span=20, adjust=False).mean()
    
    # 볼린저 밴드
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(close)
    
    # 골든크로스
    golden_cross = calculate_golden_cross(sma_20, sma_60)
    
    return IndicatorResult(
        rsi=rsi,
        sma_20=sma_20,
        sma_60=sma_60,
        ema_20=ema_20,
        bb_upper=bb_upper,
        bb_middle=bb_middle,
        bb_lower=bb_lower,
        golden_cross=golden_cross,
        volume=volume,
    )


def get_rsi_signal(rsi_value: float) -> str:
    """RSI 값 → 시장 상태 해석"""
    if rsi_value >= 70:
        return "과매수 (하락 경계)"
    elif rsi_value <= 30:
        return "과매도 (상승 기대)"
    else:
        return "중립"


def get_bb_signal(close: float, upper: float, lower: float) -> str:
    """볼린저 밴드 위치 해석"""
    if close >= upper:
        return "상단 밴드 돌파 (과매수)"
    elif close <= lower:
        return "하단 밴드 돌파 (과매도)"
    else:
        bandwidth = (upper - lower) / ((upper + lower) / 2) * 100
        return f"밴드 내 (폭 {bandwidth:.1f}%)"
