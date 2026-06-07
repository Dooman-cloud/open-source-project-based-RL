FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 코드 전체를 도커 안으로 복사
COPY . .

# 스트림릿 기본 포트(8501) 열어두기
EXPOSE 8501

# 최종 명령어
CMD ["streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0"]