"""
backend/data/fetcher.py
yfinance를 통한 주가 데이터 수집 및 CSV 캐싱
"""
import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta, date
import pandas_market_calendars as mcal  # 설치 필요
# 지원 종목 정의
TICKERS = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "NAVER": "035420.KS",
    "KAKAO": "035720.KS",
    "현대차": "005380.KS",
    "Apple": "AAPL",
    "Tesla": "TSLA",
    "S&P 500": "^GSPC",
    "KOSPI 200": "^KS11",
    "Gold": "GC=F",
}

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def get_cache_path(ticker: str, period: str = "6mo") -> str:
    safe = ticker.replace("^", "").replace("=", "").replace(".", "_")
    return os.path.join(CACHE_DIR, f"{safe}_{period}.csv")



def get_last_market_close(ticker: str) -> datetime:
    """
    가장 최근 장마감 시간 반환
    주말/공휴일 고려
    """
    now = datetime.now()

    # 종목별 장마감 시간 설정
    if ".KS" in ticker or ticker in ["^KS11"]:
        close_hour, close_minute = 15, 30   # 한국 3:30 PM
    else:
        close_hour, close_minute = 6, 0     # 해외 미국장 기준 KST 06:00

    # 오늘부터 역순으로 탐색
    check_date = now.date()

    while True:
        weekday = check_date.weekday()  # 0=월 1=화 2=수 3=목 4=금 5=토 6=일

        # 주말이면 건너뜀
        if weekday >= 5:
            check_date -= timedelta(days=1)
            continue

        # 해당 날짜의 장마감 시간
        close_dt = datetime(
            check_date.year, check_date.month, check_date.day,
            close_hour, close_minute, 0
        )

        # 오늘인데 아직 장마감 전이면 하루 전으로
        if check_date == now.date() and now < close_dt:
            check_date -= timedelta(days=1)
            continue

        # 장마감 시간이 현재보다 이전 → 마지막 장마감
        return close_dt


def get_next_trading_day(from_dt: datetime) -> datetime:
    """
    다음 거래일 날짜 반환
    주말 건너뜀
    """
    next_date = from_dt.date() + timedelta(days=1)

    while next_date.weekday() >= 5:  # 토(5), 일(6) 건너뜀
        next_date += timedelta(days=1)

    return datetime(next_date.year, next_date.month, next_date.day)


def is_cache_valid(cache_path: str, ticker: str = "", max_age_hours: int = 24) -> bool:
    """
    캐시 유효성 확인
    - 캐시가 마지막 장마감 이후에 만들어졌으면 유효
    - 기존 24시간 조건도 유지
    """
    if not os.path.exists(cache_path):
        return False

    mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
    now = datetime.now()

    # ticker 있으면 장마감 기준으로 확인
    if ticker:
        last_close = get_last_market_close(ticker)

        # 캐시가 마지막 장마감 이후에 만들어졌으면 유효
        if mtime >= last_close:
            return True
        else:
            return False

    # ticker 없으면 기존 24시간 조건
    return (now - mtime) < timedelta(hours=max_age_hours)

# 일별 분석 기준
def _period_to_days(period: str) -> int:
    mapping = {
#        "1d": 1,
#        "1w": 5,
        "1mo": 21,
        "3mo": 63,
        "6mo": 126,
        "1y": 252,
        "2y": 504,
        "5y": 1260,
        "10y": 2520,
    }
    return mapping.get(period, 252)


def _generate_fallback_price_data(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """네트워크 실패 시 사용할 결정적 샘플 데이터 생성"""
    days = _period_to_days(period)
    index = pd.date_range(end=datetime.now(), periods=days, freq="B")

    seed = abs(hash(ticker)) % (2**32)
    rng = np.random.default_rng(seed)

    base_price = 100000 if ".KS" in ticker else 100
    daily_returns = rng.normal(loc=0.0004, scale=0.018, size=days)
    close = base_price * np.exp(np.cumsum(daily_returns))

    open_price = close * (1 + rng.normal(0, 0.002, size=days))
    high = np.maximum(open_price, close) * (1 + np.abs(rng.normal(0, 0.006, size=days)))
    low = np.minimum(open_price, close) * (1 - np.abs(rng.normal(0, 0.006, size=days)))
    volume = rng.integers(500_000, 8_000_000, size=days)

    df = pd.DataFrame(
        {
            "Open": open_price,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=index,
    )
    df["log_return"] = np.log(df["Close"] / df["Close"].shift(1))
    return df.dropna()


def fetch_price_data(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """
    주가 데이터 수집. 캐시가 유효하면 캐시에서 로드.
    
    Args:
        ticker: 종목 티커 (예: "005930.KS")
        period: 데이터 기간 ("1y", "2y", "5y", "10y" 등)
    
    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume, log_return
    """
    cache_path = get_cache_path(ticker, period)

    # ticker 추가로 넘겨주기
    if is_cache_valid(cache_path, ticker):
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        return df
    
    try:
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if df.empty:
            raise ValueError(f"No data for {ticker}")
        
        # 컬럼이 MultiIndex인 경우 처리
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 로그 수익률 계산
        df["log_return"] = np.log(df["Close"] / df["Close"].shift(1))
        df = df.dropna()
        
        df.to_csv(cache_path)
        return df
    
    except Exception as e:
        # 캐시가 만료됐더라도 파일이 있으면 마지막 데이터 사용
        if os.path.exists(cache_path):
            print(f"[WARNING] {ticker} 데이터 업데이트 실패, 캐시 사용: {e}")
            return pd.read_csv(cache_path, index_col=0, parse_dates=True)

        print(f"[WARNING] {ticker} 데이터 수집 실패, 샘플 데이터 사용: {e}")
        df = _generate_fallback_price_data(ticker, period)
        df.to_csv(cache_path)
        return df


def fetch_all_tickers(period: str = "6mo") -> dict[str, pd.DataFrame]:
    """모든 지원 종목 데이터 수집"""
    results = {}
    for name, ticker in TICKERS.items():
        try:
            results[name] = fetch_price_data(ticker, period)
            print(f"[OK] {name} ({ticker})")
        except Exception as e:
            print(f"[FAIL] {name} ({ticker}): {e}")
    return results


def get_ticker_name_map() -> dict[str, str]:
    """티커 → 종목명 역방향 맵"""
    return {v: k for k, v in TICKERS.items()}


if __name__ == "__main__":
    print("=== 데이터 수집 테스트 ===")
    df = fetch_price_data("005930.KS", period="1y")
    print(df.tail())
    print(f"Shape: {df.shape}")
