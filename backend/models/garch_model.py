"""
backend/models/garch_model.py
GJR-GARCH 모델을 이용한 변동성 추정
- GJR-GARCH: 하락 충격에 더 민감하게 반응 (주식 시장 특성 반영)
"""
import numpy as np
import pandas as pd
from arch import arch_model
from dataclasses import dataclass


@dataclass
class GARCHResult:
    """GARCH 모델 결과 컨테이너"""
    conditional_volatility: pd.Series   # 조건부 변동성 (일별)
    params: dict                         # 모델 파라미터
    aic: float
    bic: float
    forecast_volatility: float          # 다음날 예측 변동성
    model_type: str = "GJR-GARCH(1,1)"


def fit_gjr_garch(log_returns: pd.Series, dist: str = "t") -> GARCHResult:
    """
    GJR-GARCH(1,1) 모델 피팅
    
    Args:
        log_returns: 로그 수익률 시계열
        dist: 오차 분포 ("t" = Student-t, "normal")
    
    Returns:
        GARCHResult
    """
    # 스케일링: arch 라이브러리는 수익률 * 100 권장
    returns_scaled = log_returns * 100
    
    model = arch_model(
        returns_scaled,
        vol="GARCH",
        p=1, o=1, q=1,     # GJR-GARCH: o=1이 비대칭 항
        dist=dist,
        mean="Constant"
    )
    
    result = model.fit(disp="off", show_warning=False)
    
    # 조건부 변동성을 원래 스케일로 되돌림
    cond_vol = result.conditional_volatility / 100
    
    # 1-step ahead 예측
    forecast = result.forecast(horizon=1, reindex=False)
    forecast_var = forecast.variance.values[-1, 0]
    forecast_vol = np.sqrt(forecast_var) / 100  # 분산 → 표준편차, 역스케일링
    
    return GARCHResult(
        conditional_volatility=cond_vol,
        params=dict(result.params),
        aic=result.aic,
        bic=result.bic,
        forecast_volatility=float(forecast_vol),
    )


def fit_garch(log_returns: pd.Series, dist: str = "t") -> GARCHResult:
    """
    표준 GARCH(1,1) 모델 피팅 (비교용)
    """
    returns_scaled = log_returns * 100
    
    model = arch_model(
        returns_scaled,
        vol="GARCH",
        p=1, q=1,
        dist=dist,
        mean="Constant"
    )
    
    result = model.fit(disp="off", show_warning=False)
    cond_vol = result.conditional_volatility / 100
    
    forecast = result.forecast(horizon=1, reindex=False)
    forecast_var = forecast.variance.values[-1, 0]
    forecast_vol = np.sqrt(forecast_var) / 100
    
    return GARCHResult(
        conditional_volatility=cond_vol,
        params=dict(result.params),
        aic=result.aic,
        bic=result.bic,
        forecast_volatility=float(forecast_vol),
        model_type="GARCH(1,1)"
    )


if __name__ == "__main__":
    # 간단 테스트
    import sys
    sys.path.append("../..")
    from backend.data.fetcher import fetch_price_data
    
    df = fetch_price_data("005930.KS", period="2y")
    garch_res = fit_gjr_garch(df["log_return"])
    
    print(f"모델: {garch_res.model_type}")
    print(f"내일 예측 변동성: {garch_res.forecast_volatility:.4f} ({garch_res.forecast_volatility*100:.2f}%)")
    print(f"AIC: {garch_res.aic:.2f}, BIC: {garch_res.bic:.2f}")
    print(f"최근 5일 변동성:\n{garch_res.conditional_volatility.tail()}")
