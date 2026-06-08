# RISKDOC

**통계·AI 모델 기반 일별 금융 자산 리스크 관리 플랫폼**

GJR-GARCH와 Student-t VaR/ES로 일별 리스크를 산출하고, Streamlit 대시보드와 Gemini 챗봇으로 개인 투자자가 이해하기 쉽게 제공하는 오픈소스 웹 서비스입니다.

> ⚠️ 본 서비스는 **의사결정 보조 도구**이며 투자 손실에 대한 책임은 이용자 본인에게 있습니다.  
> VaR·ES 수치는 통계 모델이 산출하며, 챗봇(Gemini)은 해석 보조에만 사용됩니다.

---

## 시연 영상





Uploading RISKDOC_시연영상.mp4…


---
## 문서


| 문서                                                 | 설명      |
| -------------------------------------------------- | ------- |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md)           | 사용자 가이드 |
| [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | 개발자 가이드 |
| [docs/최종보고서.md](docs/최종보고서.md)                     | 최종 보고서  |

---
## 주요 기능


| 기능               | 설명                                       |
| ---------------- | ---------------------------------------- |
| **VaR 대시보드**     | 조정 종가, 예측 VaR·ES, 예측 변동성(σ) 메트릭 + AI 리포트 |
| **차트 3종**        | 주가+VaR 오버레이, GARCH 변동성, RSI·MA·BB·거래량    |
| **손실 고위험 TOP 3** | 10개 종목 중 예측 VaR 손실액(원) 상위 3개 랭킹          |
| **AI 챗봇**        | `gemini-2.5-flash` + CoT 프롬프트, 매매 지시 금지  |
| **투자 옵션**        | 신뢰수준 90.0~99.9%, 분석 기간, 투자금, 10종목 선택     |
| **장마감 인지**       | 한국/미국 장 상태·예측일 라벨, 장마감 기준 CSV 캐시         |


---

## 빠른 시작

### 요구사항

- Python **3.11+** (권장) · pip · (선택) Docker
- [Gemini API 키](https://aistudio.google.com/apikey) — 챗봇 사용 시

### 로컬 실행

```bash
git clone <repository-url>
cd risk_management_platform

python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
```

프로젝트 루트에 `.env` 파일 생성:

```env
GEMINI_API_KEY=발급받은_API_키
```

```bash
streamlit run frontend/app.py
```

브라우저에서 **[http://localhost:8501](http://localhost:8501)** 접속

### Docker 실행

```bash
docker compose up --build
docker compose down   # 종료
```

---

## 기술 스택


| 영역     | 기술                                                            |
| ------ | ------------------------------------------------------------- |
| UI     | Streamlit 1.45, Plotly 5.22, 다크 테마 (`.streamlit/config.toml`) |
| 데이터    | yfinance, pandas, CSV 파일 캐시                                   |
| 리스크 모델 | GJR-GARCH(1,1), Student-t VaR/ES (`arch`, `scipy`)            |
| 보조 지표  | RSI, SMA, Bollinger Bands, Golden Cross                       |
| AI 챗봇  | google-genai (Gemini 2.5 Flash)                               |
| 배포     | Docker Compose (`riskdoc-app`, 포트 8501)                       |
| CI     | GitHub Actions — import 검증 + Docker build (`dev`, `main`)     |


---

## 프로젝트 구조

```
risk_management_platform/
├── .github/workflows/ci.yml
├── .streamlit/config.toml
├── backend/
│   ├── data/fetcher.py          # TICKERS, yfinance, 장마감 캐시
│   ├── models/
│   │   ├── garch_model.py       # GJR-GARCH(1,1)
│   │   └── var_calculator.py    # VaR, ES
│   └── utils/
│       ├── indicators.py
│       └── risk_ranking.py      # precomputed 최적화
├── frontend/
│   ├── app.py                   # Streamlit 메인 (~590줄)
│   └── components/charts.py
├── docker/Dockerfile
├── docker-compose.yml
├── docs/                        # 가이드·최종보고서
├── requirements.txt
└── README.md
```

---

## 지원 종목 (10)


| 종목                              | 티커                       |
| ------------------------------- | ------------------------ |
| 삼성전자, SK하이닉스, NAVER, KAKAO, 현대차 | `*.KS`                   |
| Apple, Tesla                    | `AAPL`, `TSLA`           |
| S&P 500, KOSPI 200, Gold        | `^GSPC`, `^KS11`, `GC=F` |


---



## 데이터 흐름 (요약)

```
yfinance → fetcher.py (로그수익률, CSV 캐시)
              ├→ garch_model.py → var_calculator.py (VaR/ES)
              └→ indicators.py (RSI, MA, BB)
app.py → 차트 · AI 리포트 · risk_ranking (TOP 3) · Gemini 챗봇
```

- **분석**: 5년 OHLCV로 기술지표 계산 → 사용자 선택 기간만 슬라이스 후 GARCH/VaR
- **캐시**: `@st.cache_data(ttl=3600)` + 장마감 기준 CSV (`backend/data/cache/`)

---

## 브랜치 전략


| 브랜치           | 용도       |
| ------------- | -------- |
| `main`        | 최종 배포    |
| `valid`       | 백엔드 작업   |
| `valid_front` | 프론트엔드 작업 |
| `dev`         | CI 트리거   |


`valid` 또는 `valid_front`에서 작업 후 `main`으로 merge합니다.

---

## 개발 참고

**종목 추가** — `backend/data/fetcher.py`의 `TICKERS`에 yfinance 심볼 추가

