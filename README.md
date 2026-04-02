
# 하이브리드 통계-AI 모델 기반 실시간 금융 리스크 관리 플랫폼

## 1. 프로젝트 배경 및 필요성

기존 시계열의 통계적 모델은 주식 가격 자체를 예측하려는 경향이 강함. 하지만, 
주식가격의 변동은 이러한 예측의 정확성과 실시간성을 반영하는 데 한계가 존재.
따라서, 본 프로젝트는 주식의 변동성에 대한 위험성 예측으로 리스크 관리를 보조함.
웹 서비스는 투자자 및 리스크 관리자에게 실시간 차트와 통계적 지표를 보기 쉽게 제시하고, 현재 시장의 리스크를 분석하여 직관적인 의사결정을 보조함.


## 2. 서비스 주요 기능

## 1) 실시간 리스크 대시보드

- **Dynamic Risk Detection Chart**: 주가 차트 위에 실시간으로 변하는 VaR 라인, ES, SMA, EMA, 볼린저 밴드를 오버레이하여 시각화.
- **Statistical Chart**: RSI와 거래량을 배치한 종합 기술적 지표 차트.

## 2) 사용자 맞춤형 AI/Statistical 리포트

- **Indicator Alert**: 골든크로스 발생, RSI 과매도 진입 등 주요 기술적 이벤트 발생 시 실시간 대시보드 업데이트.
- **Risk Regime Indicator**: 현재 시장 상태를 신호등 형태(Red/Green)로 표시하여 직관적 모니터링 지원.
- **Statistical Prediction**: 모델이 예측한 내일의 수익률 방향과 변동성 수치를 테이블 및 그래프로 요약 출력.

## 개발자 가이드

## 사용자 가이드

## 프로젝트 파일 구조
```
RiskGuard-RL/
├── data/                 # 데이터 관리
│   
├── main/                 # 핵심 엔진 및 실험
│   ├── notebooks/        # GJR-GARCH 및 DDQN 학습 실험 (Jupyter Notebooks)
│   └── src/              # 재사용 가능한 핵심 로직 (Python Scripts)
│           # VaR/ES 산출 및 통계 검정 로직 [cite: 12, 1151]
├── UI/                   # 프론트엔드 (Streamlit)
│  
├── README.md             # 프로젝트 제안서 및 사용 설명서
└── require_library.txt   # 의존성 라이브러리 목록 (requirements.txt 대용)
```
