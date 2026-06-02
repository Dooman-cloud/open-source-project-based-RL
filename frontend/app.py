"""
frontend/app.py
RiskGuard AI — 메인 Streamlit 앱
"""
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
    
    .stApp { background-color: #0F172A; }
    
    .metric-card {
        background: linear-gradient(135deg, #1E293B, #0F172A);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
    }
    .metric-label { color: #64748B; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
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
    
    .rank-number { color: #64748B; font-size: 12px; }
    .rank-name { color: #E2E8F0; font-weight: 600; font-size: 15px; }
    .rank-stat { color: #94A3B8; font-size: 13px; font-family: 'JetBrains Mono'; }
    
    .disclaimer {
        color: #475569;
        font-size: 11px;
        text-align: center;
        padding: 12px;
        border-top: 1px solid rgba(255,255,255,0.05);
        margin-top: 24px;
    }
    
    div[data-testid="stSidebar"] { background-color: #0D1829; }
    
    .stButton>button {
        background: linear-gradient(135deg, #1D4ED8, #1E40AF);
        color: white; border: none; border-radius: 8px;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


# ── 사이드바 
with st.sidebar:
    st.markdown("## 🛡️ 리스크관리 AI 플랫폼")
    st.markdown("---")
    
    st.markdown("### 종목 선택")
    ticker_name = st.selectbox(
        "종목 선택",
        list(TICKERS.keys()),
        label_visibility="collapsed",
    )
    ticker = TICKERS[ticker_name]
    
    st.markdown("### 투자 성향")
    risk_mode = st.radio(
        "투자 성향",
        ["Conservative (α=0.01)", "Aggressive (α=0.05)"],
        label_visibility="collapsed",
    )
    alpha = 0.01 if "Conservative" in risk_mode else 0.05
    confidence_label = "99%" if alpha == 0.01 else "95%"
    
    st.markdown("### 분석 기간")
    period_map = {"1주": "1mo", "3개월": "3mo", "6개월": "6mo", "1년": "1y", "2년": "2y", "5년": "5y"}
    period_label = st.select_slider("분석 기간", list(period_map.keys()), value="1년", label_visibility="collapsed")
    period = period_map[period_label]
    
    st.markdown("### 투자금")
    investment = st.number_input("투자금 (원)", value=10_000_000, step=1_000_000, label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("<div class='disclaimer'>⚠️ 본 서비스는 의사결정 보조 도구이며<br>투자 손실에 대한 책임은 본인에게 있습니다.</div>", unsafe_allow_html=True)


# ── 메인 콘텐츠 ───────────────────────────────────────
st.markdown(f"## DAILY RISK MANAGEMENT  — {ticker_name.upper()}")

# 데이터 로딩
@st.cache_data(ttl=3600)
def load_analysis(ticker: str, period: str, alpha: float):
    df = fetch_price_data(ticker, period=period)
    garch_res = fit_gjr_garch(df["log_return"])
    var_res = calculate_var_es(garch_res, df["Close"], alpha=alpha, investment=10_000_000)
    indicators = calculate_all_indicators(df)
    return df, garch_res, var_res, indicators

with st.spinner("분석 중..."):
    try:
        df, garch_res, var_res, indicators = load_analysis(ticker, period, alpha)
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
    vol_today = float(garch_res.conditional_volatility.iloc[-1]) * 100
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Volatility (GARCH σ)</div>
        <div class='metric-value'>{vol_today:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 차트 레이아웃 ──────────────────────────────────────
chart_col, info_col = st.columns([3, 1])

with chart_col:
    tab1, tab2, tab3 = st.tabs(["📈 주가 + VaR", "📊 변동성", "📉 기술 지표"])
    
    with tab1:
        fig1 = plot_price_with_var(
            df["Close"], var_res.var_series, ticker_name, confidence_label
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with tab2:
        fig2 = plot_volatility(garch_res.conditional_volatility, ticker_name)
        st.plotly_chart(fig2, use_container_width=True)
    
    with tab3:
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

with info_col:
    # AI 리스크 리포트
    st.markdown("#### 🤖 AI 위험 Report")
    summary = summarize_var(var_res, investment)
    
    rsi_val = float(indicators.rsi.iloc[-1])
    rsi_signal = get_rsi_signal(rsi_val)
    bb_signal = get_bb_signal(
        float(df["Close"].iloc[-1]),
        float(indicators.bb_upper.iloc[-1]),
        float(indicators.bb_lower.iloc[-1]),
    )
    
    vol_5d = float(garch_res.conditional_volatility.iloc[-5:].mean())
    vol_change = (float(garch_res.conditional_volatility.iloc[-1]) - vol_5d) / vol_5d * 100
    
    st.info(f"{summary}\n\nRSI: {rsi_val:.1f} ({rsi_signal})\nBB: {bb_signal}\n변동성 5일 평균 대비: {vol_change:+.1f}%")
    
    # 리스크 랭킹
    st.markdown("#### 📋 Today's Risk Ranking")
    
    @st.cache_data(ttl=3600)
    def get_ranking(alpha):
        return compute_risk_ranking(alpha)
    
    with st.spinner("랭킹 계산 중..."):
        try:
            ranking = get_ranking(alpha)
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

# ── 챗봇 ─────────────────────────────────────────────
# ── 챗봇 ─────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 💬 리스크 분석 챗봇")

if "messages" not in st.session_state:
    st.session_state.messages = []

# 이전 대화 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("리스크 지표에 대해 질문하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("분석 중..."):
            try:
                import google.generativeai as genai
                from dotenv import load_dotenv
                load_dotenv()
                # .env에서 GEMINI_API_KEY 읽기

                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                # Gemini API 설정

                context = f"""
당신은 금융 리스크 분석 전문 AI 어시스턴트입니다.
현재 분석 중인 종목: {ticker_name} ({ticker})
현재 분석 데이터:
- 현재 주가: {var_res.current_price:,.0f}
- {confidence_label} VaR: {var_res.var_today*100:.2f}%
- Expected Shortfall: {var_res.es_today*100:.2f}%
- GARCH 변동성: {vol_today:.2f}%
- RSI: {rsi_val:.1f} ({rsi_signal})
- 볼린저 밴드: {bb_signal}
- 투자 성향: {"안정형" if alpha==0.01 else "공격형"} (α={alpha})
사용자의 질문에 위 데이터를 바탕으로 쉽고 직관적인 한국어로 답변하세요.
투자 손실에 대한 책임은 본인에게 있음을 적절히 안내하세요.
                """

                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    # 무료 모델
                    system_instruction=context,
                    # 현재 분석 데이터 전달
                )

                # 이전 대화 기록을 Gemini 형식으로 변환
                history = []
                for m in st.session_state.messages[:-1]:
                # 마지막 메시지 제외 (방금 입력한 것)
                    history.append({
                        "role": "user" if m["role"] == "user" else "model",
                        # Gemini는 "assistant" 대신 "model" 사용
                        "parts": [m["content"]]
                    })

                chat = model.start_chat(history=history)
                # 대화 기록 포함해서 채팅 시작

                response = chat.send_message(prompt)
                # 메시지 전송

                reply = response.text
                # 응답 텍스트 추출

            except Exception as e:
                reply = f"챗봇 연결 오류: {e}\n.env 파일에 GEMINI_API_KEY를 설정해주세요."

            st.write(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})