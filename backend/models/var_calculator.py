"""
backend/models/var_calculator.py
VaR(Value-at-Risk), ES(Expected Shortfall) 계산
- GARCH 기반 조건부 VaR (t-분포 사용)
"""
import numpy as np
import pandas as pd
from scipy import stats
from dataclasses import dataclass
from .garch_model import GARCHResult


@dataclass
class VaRResult:
    """VaR/ES 계산 결과"""
    var_series: pd.Series       # 일별 VaR (수익률 기준, 음수)
    es_series: pd.Series        # 일별 ES (수익률 기준, 음수)
    var_today: float            # 오늘 VaR (수익률)
    es_today: float             # 오늘 ES (수익률)
    var_amount: float           # 투자금 기준 VaR (원화 등)
    es_amount: float            # 투자금 기준 ES
    alpha: float                # 유의수준 (0.01 or 0.05)
    confidence: float           # 신뢰수준 (0.99 or 0.95)
    current_price: float        # 현재 주가
    
    @property
    def confidence_pct(self) -> str:
        return f"{self.confidence*100:.0f}%"


def calculate_var_es(
    garch_result: GARCHResult,
    close_prices: pd.Series,
    alpha: float = 0.01,
    investment: float = 10_000_000,
) -> VaRResult:
    """
    GARCH 조건부 변동성 기반 VaR/ES 계산
    
    수식: VaR_t = z_alpha * σ_t (t-분포 분위수 사용)
    
    Args:
        garch_result: GARCH 피팅 결과
        close_prices: 종가 시계열
        alpha: 유의수준 (0.01=99% 신뢰, 0.05=95% 신뢰)
        investment: 투자금 (기본값 1000만원)
    
    Returns:
        VaRResult
    """
    sigma = garch_result.conditional_volatility
    
    # 자유도 추출 (t-분포 파라미터)
    nu = garch_result.params.get("nu", 6.0)  # Student-t 자유도
    
    # t-분포 분위수 (음수: 손실 방향)
    z_var = stats.t.ppf(alpha, df=nu)        # 예: alpha=0.01 → 약 -2.63
    z_es = _es_t_quantile(alpha, nu)          # ES: 꼬리 평균
    
    # VaR, ES 시계열 (수익률 기준, 음수 = 손실)
    var_series = z_var * sigma
    es_series = z_es * sigma
    
    # 현재(마지막) 값
    var_today = float(var_series.iloc[-1])
    es_today = float(es_series.iloc[-1])
    current_price = float(close_prices.iloc[-1])
    
    # 투자금 기준 금액
    var_amount = var_today * investment
    es_amount = es_today * investment
    
    return VaRResult(
        var_series=var_series,
        es_series=es_series,
        var_today=var_today,
        es_today=es_today,
        var_amount=var_amount,
        es_amount=es_amount,
        alpha=alpha,
        confidence=1 - alpha,
        current_price=current_price,
    )


def _es_t_quantile(alpha: float, nu: float) -> float:
    """
    t-분포 기반 Expected Shortfall 계산
    ES = -σ * [ t_pdf(z_alpha) / alpha ] * (nu + z_alpha²) / (nu - 1)
    """
    z = stats.t.ppf(alpha, df=nu)
    pdf_z = stats.t.pdf(z, df=nu)
    es = -(pdf_z / alpha) * (nu + z**2) / (nu - 1)
    return es


def summarize_var(var_result: VaRResult, investment: float = 10_000_000) -> str:
    """VaR 결과를 자연어 요약으로 변환"""
    conf = var_result.confidence_pct
    var_pct = abs(var_result.var_today) * 100
    es_pct = abs(var_result.es_today) * 100
    var_won = abs(var_result.var_amount)
    es_won = abs(var_result.es_amount)
    
    summary = (
        f"신뢰수준 {conf} 기준 일별 VaR은 {var_pct:.2f}%로, "
        f"투자금 {investment/10000:.0f}만원 기준 최대 손실 예상액은 약 {var_won/10000:.1f}만원입니다. "
        f"최악의 {var_result.alpha*100:.0f}% 상황에서 평균 손실(ES)은 {es_pct:.2f}% "
        f"(약 {es_won/10000:.1f}만원)으로 추정됩니다."
    )
    return summary


if __name__ == "__main__":
    import sys
    sys.path.append("../..")
    from backend.data.fetcher import fetch_price_data
    from backend.models.garch_model import fit_gjr_garch
    
    df = fetch_price_data("005930.KS", period="2y")
    garch_res = fit_gjr_garch(df["log_return"])
    var_res = calculate_var_es(garch_res, df["Close"], alpha=0.01)
    
    print(summarize_var(var_res))
    print(f"\nVaR today: {var_res.var_today:.4f} ({var_res.var_today*100:.2f}%)")
    print(f"ES  today: {var_res.es_today:.4f} ({var_res.es_today*100:.2f}%)")
