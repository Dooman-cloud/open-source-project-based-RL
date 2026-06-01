"""
backend/utils/risk_ranking.py
전체 종목 리스크 랭킹 시스템
- 변동성 증가율, VaR 크기 기준 TOP 3 종목 제공
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from backend.data.fetcher import TICKERS, fetch_price_data
from backend.models.garch_model import fit_gjr_garch
from backend.models.var_calculator import calculate_var_es


@dataclass
class StockRiskSummary:
    name: str
    ticker: str
    current_price: float
    var_today: float          # 수익률 기준 VaR (음수)
    volatility_today: float   # 현재 변동성
    volatility_5d_avg: float  # 최근 5일 평균 변동성
    vol_change_pct: float     # 전일 대비 변동성 변화율 (%)
    vol_change_5d_pct: float  # 5일 평균 대비 변동성 변화율 (%)


def compute_risk_ranking(alpha: float = 0.01) -> list[StockRiskSummary]:
    """
    모든 종목 리스크 계산 후 변동성 기준 랭킹 반환
    
    Returns:
        변동성 높은 순으로 정렬된 StockRiskSummary 리스트
    """
    summaries = []
    
    for name, ticker in TICKERS.items():
        try:
            df = fetch_price_data(ticker, period="1y")
            garch_res = fit_gjr_garch(df["log_return"])
            var_res = calculate_var_es(garch_res, df["Close"], alpha=alpha)
            
            vol = garch_res.conditional_volatility
            vol_today = float(vol.iloc[-1])
            vol_prev = float(vol.iloc[-2]) if len(vol) > 1 else vol_today
            vol_5d_avg = float(vol.iloc[-5:].mean())
            
            summaries.append(StockRiskSummary(
                name=name,
                ticker=ticker,
                current_price=var_res.current_price,
                var_today=var_res.var_today,
                volatility_today=vol_today,
                volatility_5d_avg=vol_5d_avg,
                vol_change_pct=(vol_today - vol_prev) / vol_prev * 100,
                vol_change_5d_pct=(vol_today - vol_5d_avg) / vol_5d_avg * 100,
            ))
        except Exception as e:
            print(f"[RANKING] {name} 건너뜀: {e}")
    
    # 변동성 크기 기준 내림차순 정렬
    summaries.sort(key=lambda x: x.volatility_today, reverse=True)
    return summaries


def format_ranking_for_display(summaries: list[StockRiskSummary], top_n: int = 3) -> list[dict]:
    """
    Streamlit 표시용 딕셔너리 리스트 변환
    """
    result = []
    for i, s in enumerate(summaries[:top_n], 1):
        change_sign = "+" if s.vol_change_pct >= 0 else ""
        result.append({
            "rank": i,
            "name": s.name,
            "ticker": s.ticker,
            "vol_display": f"{change_sign}{s.vol_change_pct:.1f}% Volatility",
            "var_display": f"VaR {s.var_today*100:.2f}%",
            "volatility": s.volatility_today,
            "is_high_risk": s.vol_change_pct > 10 or abs(s.var_today) > 0.03,
        })
    return result


if __name__ == "__main__":
    print("=== 리스크 랭킹 계산 중... ===")
    ranking = compute_risk_ranking(alpha=0.01)
    
    print("\n📊 TODAY'S RISK RANKING (TOP 3)")
    for i, s in enumerate(ranking[:3], 1):
        print(f"{i}. {s.name} ({s.ticker})")
        print(f"   변동성: {s.volatility_today*100:.2f}% | VaR: {s.var_today*100:.2f}%")
        print(f"   전일 대비: {s.vol_change_pct:+.1f}%")
