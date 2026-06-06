"""
frontend/app.py
RiskGuard AI — 메인 Streamlit 앱
"""
from datetime import date
import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.data.fetcher import TICKERS, fetch_price_data
from backend.models.garch_model import fit_gjr_garch
from backend.models.var_calculator import calculate_var_es, summarize_var
from backend.utils.indicators import calculate_all_indicators, get_rsi_signal, get_bb_signal
from backend.utils.risk_ranking import compute_risk_ranking, format_ranking_for_display
from frontend.components.charts import (
    plot_price_with_var,
    plot_volatility,
    plot_technical_indicators,
)

# ── 페이지 설정 ──────────────────────────────────────
st.set_page_config(
    page_title="리스크 관리 AIP",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded", #사이드 바 펼쳐진 상태 
)

#  CSS 
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;600&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .stApp { 
        background: radial-gradient(circle at 50% 0%, #1E293B 0%, #0F172A 50%, #020617 100%) !important; 
    }    
    .metric-card {
        background: linear-gradient(135deg, #1E293B, #0F172A);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
    }
    .metric-label { color: #CBD5E1; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { color: #E2E8F0; font-size: 24px; font-weight: 600; font-family: 'JetBrains Mono'; margin-top: 4px; }
    .metric-value.negative { color: #F87171; }
    
    .risk-card {
        background: #1E293B;
        border-left: 3px solid #EF4444;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
    }
    .risk-card.medium { border-left-color: #F59E0B; }
    .risk-card.low { border-left-color: #22C55E; }
    
    .rank-number { color: #CBD5E1; font-size: 12px; }
    .rank-name { color: #E2E8F0; font-weight: 600; font-size: 15px; }
    .rank-stat { color: #E2E8F0; font-size: 13px; font-family: 'JetBrains Mono'; }

    .page-title {
        color: #F8FAFC;
        font-size: 28px;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 6px;
    }
    .section-title {
        color: #F8FAFC;
        font-size: 21px;
        font-weight: 800;
        letter-spacing: -0.015em;
        margin: 0 0 12px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .section-title .accent {
        color: #38BDF8;
    }
    
    .disclaimer {
        color: #CBD5E1;
        font-size: 11px;
        text-align: center;
        padding: 12px;
        border-top: 1px solid rgba(255,255,255,0.05);
        margin-top: 24px;
    }
    
    [data-testid="stSidebar"] { 
        background: transparent !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #162032 0%, #050B14 100%) !important;
        border-right: 1px solid rgba(56, 189, 248, 0.2) !important;
        box-shadow: 2px 0 15px rgba(0, 0, 0, 0.5) !important;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #1D4ED8, #1E40AF);
        color: white; border: none; border-radius: 8px;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


# ── 사이드바 
with st.sidebar:
    st.markdown("## 🛡️ 금융 리스크관리 AI 플랫폼")
    st.markdown("---")
    
    st.markdown("### 종목")
    ticker_name = st.selectbox(
        "종목",
        list(TICKERS.keys()),
        label_visibility="collapsed",
    )
    ticker = TICKERS[ticker_name]
    
    st.markdown("### 신뢰수준 (%)")
    confidence_pct = st.slider(
        "신뢰수준 (%)",
        min_value=90.0,
        max_value=99.9,
        value=99.0,
        step=0.1,
        format="%0.1f%%",
        label_visibility="collapsed",
    )

    st.caption("예: 99% 신뢰수준은 투자 손실액이 예측치를 초과할 확률이 1%임을 의미합니다.")
    alpha = 1 - (confidence_pct / 100.0)
    confidence_label = f"{confidence_pct:.1f}".rstrip("0").rstrip(".") + "%"
    
    st.markdown("### 분석 기간")
    period_map = {"1주": "1mo", "3개월": "3mo", "6개월": "6mo", "1년": "1y", "2년": "2y", "5년": "5y"}
    period_label = st.select_slider("분석 기간", list(period_map.keys()), value="6개월", label_visibility="collapsed")
    period = period_map[period_label]
    
    st.markdown("### 투자금")
    investment = st.number_input(
        "투자금 (원)",
        value=10_000_000,
        step=1_000_000,
        label_visibility="collapsed",
    )
    st.caption(f"현재 투자금: {investment:,.0f}원")
    
    st.markdown("---")
    st.markdown("<div class='disclaimer'>⚠️ 본 서비스는 의사결정 보조 도구이며<br>투자 손실에 대한 책임은 본인에게 있습니다.</div>", unsafe_allow_html=True)


# ── 메인 콘텐츠 ───────────────────────────────────────
st.markdown(f"<div class='page-title' style='font-size: 44px;'>{ticker_name.upper()}</div>", unsafe_allow_html=True)

# 데이터 로딩
@st.cache_data(ttl=3600)
def load_analysis(ticker: str, period: str, alpha: float, investment: float):
    df = fetch_price_data(ticker, period=period)
    garch_res = fit_gjr_garch(df["log_return"])
    var_res = calculate_var_es(garch_res, df["Close"], alpha=alpha, investment=investment)
    latest_df = fetch_price_data(ticker, period="1mo")
    var_res.current_price = float(latest_df["Close"].iloc[-1])
    indicators = calculate_all_indicators(df)
    return df, garch_res, var_res, indicators

with st.spinner("분석 중..."):
    try:
        df, garch_res, var_res, indicators = load_analysis(ticker, period, alpha, investment)
    except Exception as e:
        st.error(f"데이터 로딩 실패: {e}")
        st.stop()

# ── 상단 메트릭 카드 
col1, col2, col3, col4 = st.columns(4)

with col1:
    price_str = f"{var_res.current_price:,.0f}"
    currency = "KRW" if ".KS" in ticker or ticker.startswith("^KS") else "USD"
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Closing Price</div>
        <div class='metric-value'>{price_str} {currency}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    var_pct = var_res.var_today * 100
    var_str = f"{var_pct:.2f}%"
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>{confidence_label} Daily VaR</div>
        <div class='metric-value negative'>{var_str}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    es_pct = var_res.es_today * 100
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Expected Shortfall</div>
        <div class='metric-value negative'>{es_pct:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    vol_today = garch_res.forecast_volatility * 100
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Forecasted Volatility (σ)</div>
        <div class='metric-value'>{vol_today:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

# ── AI 리포트 (전체 너비) ──────────────────────────────
rsi_val = float(indicators.rsi.iloc[-1])
rsi_signal = get_rsi_signal(rsi_val)
bb_signal = get_bb_signal(
    float(df["Close"].iloc[-1]),
    float(indicators.bb_upper.iloc[-1]),
    float(indicators.bb_lower.iloc[-1]),
)
vol_5d = float(garch_res.conditional_volatility.iloc[-5:].mean())
vol_change = (float(garch_res.conditional_volatility.iloc[-1]) - vol_5d) / vol_5d * 100
# 골든크로스 신호 해석(챗봇에만 적용)
golden_cross = int(indicators.golden_cross.iloc[-1])
if golden_cross == 1:
    cross_signal = "골든크로스 발생 (매수 신호)"
elif golden_cross == -1:
    cross_signal = "데드크로스 발생 (매도 신호)"
else:
    cross_signal = "신호 없음"
summary = summarize_var(var_res, investment)

st.markdown("---")
st.markdown("<div class='section-title' style='font-size: 30px;'><span class='accent'>✨</span> AI 리포트 요약</div>", unsafe_allow_html=True)

st.markdown(f"""
<div style="
    background: linear-gradient(145deg, #1E293B, #0F172A);
    border: 1px solid rgba(56, 189, 248, 0.2);
    border-left: 5px solid #38BDF8;
    border-radius: 10px;
    padding: 24px;
    color: #F8FAFC;
    font-size: 17px;
    font-weight: 500;
    line-height: 1.7;
    letter-spacing: 0.3px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    margin-bottom: 24px;
">
    {summary}
</div>
""", unsafe_allow_html=True)

st.markdown("<h5 style='color: #E2E8F0; margin-bottom: 12px;'>📊 세부 기술적 지표 분석</h5>", unsafe_allow_html=True)
st.markdown(f"""
<div style="background-color: #111827; padding: 18px 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); color: #CBD5E1; font-size: 14.5px; line-height: 1.6;">
    <ul style="margin: 0; padding-left: 10px; list-style-type: none;">
        <li style="margin-bottom: 12px;">
            <strong style="color: #F8FAFC;">RSI (상대강도지수):</strong> <span style="color: #38BDF8; font-weight: 600;">{rsi_val:.1f} ({rsi_signal})</span>
            <br> <span style="color: #64748B;">↳</span> <small style="color: #94A3B8;">현재 주가의 상승/하락 압력 크기를 나타냅니다. (일반적으로 70 이상은 과매수/고평가, 30 이하 구간은 과매도/저평가 상태로 봅니다.)</small>
        </li>
        <li style="margin-bottom: 12px;">
            <strong style="color: #F8FAFC;">볼린저 밴드 (Bollinger Bands):</strong> <span style="color: #38BDF8; font-weight: 600;">{bb_signal}</span>
            <br> <span style="color: #64748B;">↳</span> <small style="color: #94A3B8;">주가의 정상적인 변동 범위를 의미합니다. 밴드 상단을 돌파하면 단기 고점, 하단을 이탈하면 단기 저점일 확률이 높아 주의가 필요합니다.</small>
        </li>
        <li>
            <strong style="color: #F8FAFC;">단기 변동성 추이 (GARCH):</strong> 최근 5일 평균 대비 <span style="color: #38BDF8; font-weight: 600;">{vol_change:+.1f}%</span>
            <br> <span style="color: #64748B;">↳</span> <small style="color: #94A3B8;">최근 5거래일 동안의 평균적인 위험도에 비해 오늘 예측된 위험(조건부 변동성)이 얼마나 증가/감소했는지 보여주는 직관적인 지표입니다.</small>
        </li>
    </ul>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── 차트 (왼쪽) + 랭킹+챗봇 (오른쪽) ────────────────────
chart_col, right_col = st.columns([2, 1])

with chart_col:
    fig1 = plot_price_with_var(
        df["Close"], var_res.var_series, ticker_name, confidence_label
    )
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = plot_volatility(garch_res.conditional_volatility, ticker_name)
    st.plotly_chart(fig2, use_container_width=True)

    fig3 = plot_technical_indicators(
        df["Close"],
        indicators.rsi,
        indicators.sma_20,
        indicators.sma_60,
        indicators.bb_upper,
        indicators.bb_lower,
        indicators.volume,
    )
    st.plotly_chart(fig3, use_container_width=True)

with right_col:
    # ── 랭킹 ──────────────────────────────────────────
    today = date.today()
    st.markdown(f"<div class='section-title'><span class='accent'></span> 손실 고위험 종목 TOP 3 </div>", unsafe_allow_html=True)
    st.markdown(f"<div class='section-subtitle'><span style='color: #E1E1E1;'>({today.year}/{today.month}/{today.day}기준)</div>", unsafe_allow_html=True)

    @st.cache_data(ttl=3600)
    def get_ranking(alpha, period, investment):
        return compute_risk_ranking(alpha, period, investment)

    with st.spinner("랭킹 계산 중..."):
        try:
            ranking = get_ranking(alpha, period, investment)
            items = format_ranking_for_display(ranking, top_n=3)
            for item in items:
                color_class = "risk-card" if item["is_high_risk"] else "risk-card medium"
                st.markdown(f"""
                <div class='{color_class}'>
                    <div class='rank-number'>#{item['rank']}</div>
                    <div class='rank-name'>{item['name']}</div>
                    <div class='rank-stat'>{item['vol_display']}</div>
                    <div class='rank-stat'>{item['var_display']}</div>
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"랭킹 로딩 실패: {e}")

    st.markdown("---")

# ── 챗봇 ──────────────────────────────────────────
    st.markdown("#### 금융 리스크 분석 전문 AI 어시스턴트")

    chat_container = st.container(height=600)

    if (
        "current_ticker" not in st.session_state
        or st.session_state.current_ticker != ticker_name
        or st.session_state.current_period != period
        or st.session_state.current_alpha != alpha
        ):
        st.session_state.current_ticker = ticker_name
        st.session_state.current_period = period      # ← 추가
        st.session_state.current_alpha = alpha         # ← 추가

    welcome_msg = (
        f"안녕하세요! 👋 **{ticker_name}**의 실시간 리스크 분석이 완료되었습니다.\n\n"
        f"현재 **{confidence_label} 기준 예측 최대 손실(VaR)은 {var_res.var_today*100:.2f}%** 이며, "
        f"기술적 지표인 RSI는 **{rsi_val:.1f} ({rsi_signal})** 상태를 가리키고 있습니다.\n\n"
        f"이 수치가 의미하는 바가 무엇인지, 혹은 앞으로의 투자 리스크에 대해 궁금한 점이 있으시다면 편하게 질문해 주세요!"
        )
    st.session_state.messages = [{"role": "assistant", "content": welcome_msg}]

    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])  # st.write 대신 markdown을 쓰면 글씨체가 더 예쁘게 먹힘!

    if prompt := st.chat_input("리스크 지표에 대해 질문하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})


        with chat_container:
            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("분석 중..."):
                    try:
                        from google import genai
                        from google.genai import types
                        from dotenv import load_dotenv
                        load_dotenv()

                        api_key = os.getenv("GEMINI_API_KEY")
                        if not api_key:
                            raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다.")

                        client = genai.Client(api_key=api_key)

                        context = f"""
당신은 금융 리스크 분석 전문 AI 어시스턴트입니다.
단기 매매 추천이 아니라, 제공된 수치 기반의 리스크 해석과 투자 판단 보조에 주요 초점을 둡니다.

[현재 분석 종목]
- 종목: {ticker_name} ({ticker})
- 현재 주가: {var_res.current_price:,.0f}
- 신뢰수준: {confidence_label} (α={alpha:.3f})

[현재 리스크 지표]
- {confidence_label} VaR: {var_res.var_today*100:.2f}%
- Expected Shortfall: {var_res.es_today*100:.2f}%
- GARCH 예측 변동성: {vol_today:.2f}%
- RSI: {rsi_val:.1f} ({rsi_signal})
- 볼린저 밴드: {bb_signal}
- 골든크로스: {cross_signal}

[답변 방식 - 단계적 분석]
아래 분석 절차를 내부적으로 따른 뒤, 최종 답변에는 핵심 근거와 결론만 간결하게 제시하세요.

1단계 - 질문 파악:
사용자가 묻는 핵심이 무엇인지 파악하세요.

2단계 - 데이터 선택 및 해석:
위 리스크 지표 중 질문과 관련된 지표를 이용해 해석하세요.
질문과 관련 없는 지표는 억지로 모두 설명하지 마세요.

3단계 - 종합 판단:
선택한 지표들을 종합하여 현재 리스크 수준을 객관적으로 판단하세요.

4단계 - 쉬운 설명:
전문 용어를 최소화하고 일반 투자자도 이해할 수 있는 쉬운 한국어로 설명하세요.

[제약 조건]
"에 투자하세요", "를 매수/매도하세요" 처럼 결정론적인 투자 판단은 하지 마세요.
특정 행동을 지시하지 말고, 사용자가 점검할 수 있는 리스크 요인을 제시하세요.
제공된 수치는 과거 데이터와 모형 기반 추정치이며, 미래 손실을 확정적으로 예측하지 않습니다.

[답변 마지막 고정 문구]
⚠️ 본 해석은 의사결정 보조 도구이며 투자 손실에 대한 책임은 본인에게 있습니다.
                        """

                        history = []
                        for message in st.session_state.messages[:-1]:
                            history.append({
                                "role": "user" if message["role"] == "user" else "model",
                                "parts": [{"text": message["content"]}],
                            })

                        contents = history + [{"role": "user", "parts": [{"text": prompt}]}]

                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=contents,
                            config=types.GenerateContentConfig(
                                system_instruction=context,
                                temperature=0.4,
                            ),
                        )
                        reply = response.text

                    except Exception as e:
                        reply = f"챗봇 연결 오류: {e}\n.env 파일에 GEMINI_API_KEY를 확인해주세요."

                    st.write(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})