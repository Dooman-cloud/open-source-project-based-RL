"""
frontend/components/charts.py
Plotly 기반 인터랙티브 차트 컴포넌트
"""
import plotly.graph_objects as go #차트 요소 객체 만들기 
from plotly.subplots import make_subplots #차트 여러개 한 화면에 배치
import pandas as pd
import numpy as np


COLORS = {
    "price": "#00D4FF", #주가 선색 
    "var_upper": "rgba(255, 80, 80, 0.3)",
    "var_lower": "rgba(255, 80, 80, 0.8)",
    "volatility": "#FF6B35", #변동성 선색 
    "rsi": "#A855F7",
    "sma_20": "#22C55E",
    "sma_60": "#F59E0B",
    "bb_upper": "rgba(100, 200, 255, 0.4)",
    "bb_lower": "rgba(100, 200, 255, 0.4)",
    "volume": "rgba(100, 150, 200, 0.5)",
    "background": "#0F172A", #배경 색
    "grid": "rgba(255,255,255,0.06)",
    "text": "#94A3B8",
}

LAYOUT_BASE = dict(
    paper_bgcolor=COLORS["background"], #차트 밖 배경
    plot_bgcolor=COLORS["background"], # 차트 안 배경 
    font=dict(color=COLORS["text"], family="monospace"), 
    xaxis=dict(
        showgrid=True, 
        gridcolor=COLORS["grid"], #격자선 보이기
        showline=False,  #x축 선 숨기기
        zeroline=False, #x축 0기준 안보이게 
        rangeslider=dict(visible=False), #하단슬라이더 숨기기
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor=COLORS["grid"],
        showline=False, 
        zeroline=False,
    ),
    margin=dict(l=10, r=10, t=40, b=10),
    hovermode="x unified", #마우스 올렸을 때 x축 기준으로 모든 데이터 보여주기
    legend=dict(
        bgcolor="rgba(0,0,0,0.3)",
        bordercolor="rgba(255,255,255,0.1)",
        borderwidth=1,
    ),
)


#가격과 VaR을 함께 보여주는 차트 함수
def plot_price_with_var(
    close: pd.Series, #종가 데이터 받기 
    var_series: pd.Series, #VaR 수익률 시리즈 받기
    ticker_name: str, #종목명 받기 
    confidence: str = "99%", #신뢰수준 기본값 
) -> go.Figure:
    """
    주가 + GARCH VaR 오버레이 차트
    """
    # VaR 가격 기준 변환 (수익률 → 가격 변화)
    var_price = close * var_series   # 음수값
    
    fig = go.Figure()
    
    # 주가 캔들 or 라인
    fig.add_trace(go.Scatter(
        x=close.index, y=close,
        name="종가",
        line=dict(color=COLORS["price"], width=1.5),
        fill="tozeroy",
        fillcolor="rgba(0, 212, 255, 0.03)",
    ))
    
    # VaR 라인 (주가 기준)
    var_line = close + var_price  # close + (음수) = VaR 손실 수준
    fig.add_trace(go.Scatter(
        x=var_line.index, y=var_line,
        name=f"GARCH VaR ({confidence})",
        line=dict(color=COLORS["var_lower"], width=1, dash="dash"),
    )) #점선으로 만듬 
    
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(
            text=f"📈 {ticker_name} — 주가 & VaR ({confidence} 신뢰수준)",
            font=dict(size=14, color="#E2E8F0"),
        ),
        height=350,
    )
    return fig

# GARCH 모델로 계산된 조건부 변동성 차트 함수
def plot_volatility(
    volatility: pd.Series, #변동성 
    ticker_name: str,
) -> go.Figure:
    """GARCH 조건부 변동성 차트"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=volatility.index,
        y=volatility * 100,   # % 단위
        name="일별 변동성 (σ)",
        line=dict(color=COLORS["volatility"], width=1.5),
        fill="tozeroy",
        fillcolor="rgba(255, 107, 53, 0.1)",
    ))
    
    # 평균선
    avg_vol = volatility.mean() * 100
    fig.add_hline(
        y=avg_vol,
        line_dash="dot",
        line_color="rgba(255,255,255,0.3)",
        annotation_text=f"평균 {avg_vol:.2f}%",
        annotation_font_color="#94A3B8",
    )
    
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(
            text=f"📊 {ticker_name} — 변동성(%)",
            font=dict(size=14, color="#E2E8F0"),
        ),
        yaxis_title="변동성 (%)",
        height=280,
    )
    return fig


def plot_technical_indicators(
    close: pd.Series, #종가
    rsi: pd.Series, # RSI 
    sma_20: pd.Series, 
    sma_60: pd.Series,
    bb_upper: pd.Series, 
    bb_lower: pd.Series,
    volume: pd.Series,
) -> go.Figure:
    """기술 지표 차트 (RSI + 이동평균 + 볼린저 밴드 + 거래량)"""
    
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True, #x축 공유 날짜 맞추기 위해
        row_heights=[0.5, 0.3, 0.2],
        vertical_spacing=0.1, #행사이 간격 
        subplot_titles=("주가 + MA + BB", "RSI", "거래량"),
    )
    
    # ── Row 1: 주가 + 이동평균 + 볼린저 밴드 ──
    # 볼린저 밴드 영역
    fig.add_trace(go.Scatter(
        x=bb_upper.index, y=bb_upper,
        line=dict(color="rgba(100,200,255,0.1)"),
        showlegend=False, name="BB Upper",
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=bb_lower.index, y=bb_lower,
        fill="tonexty",
        fillcolor="rgba(100, 200, 255, 0.07)",
        line=dict(color="rgba(100,200,255,0.3)"),
        name="볼린저 밴드",
    ), row=1, col=1)
    
    #종가
    fig.add_trace(go.Scatter(
        x=close.index, y=close,
        line=dict(color=COLORS["price"], width=1.2),
        name="종가",
    ), row=1, col=1)
    
    #SMA 20 추가
    fig.add_trace(go.Scatter(
        x=sma_20.index, y=sma_20,
        line=dict(color=COLORS["sma_20"], width=1, dash="dot"),
        name="SMA 20",
    ), row=1, col=1)
    
    #SMA 60 추가
    fig.add_trace(go.Scatter(
        x=sma_60.index, y=sma_60,
        line=dict(color=COLORS["sma_60"], width=1, dash="dot"),
        name="SMA 60",
    ), row=1, col=1)
    
    # ── Row 2: RSI 
    fig.add_trace(go.Scatter(
        x=rsi.index, y=rsi,
        line=dict(color=COLORS["rsi"], width=1.5),
        name="RSI(14)",
    ), row=2, col=1)
    
    #RSI 70선과 30선 과매수 과매도 경계 만들기 
    for level, color in [(70, "rgba(255,80,80,0.4)"), (30, "rgba(80,200,80,0.4)")]:
        fig.add_hline(y=level, line_dash="dot", line_color=color, row=2, col=1)
    
    # ── Row 3: 거래량 
    if not volume.empty:
        fig.add_trace(go.Bar( #막대 그래프
            x=volume.index, y=volume,
            marker_color=COLORS["volume"],
            name="거래량",
        ), row=3, col=1)
    
    fig.update_layout(
        **LAYOUT_BASE,
        height=500,
        title=dict(
            text="📉 기술 지표",
            font=dict(size=14, color="#E2E8F0"),
        ),
    )
    
    # 서브플롯별 y축 설정
    for i in range(1, 4):
        fig.update_yaxes(
            showgrid=True, gridcolor=COLORS["grid"],
            showline=False, zeroline=False,
            row=i, col=1,
        )
        fig.update_xaxes(
            showgrid=True, gridcolor=COLORS["grid"],
            row=i, col=1,
        )
    
    return fig
