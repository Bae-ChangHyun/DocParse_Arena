# DocParse Arena

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

[English](README.md) | **한국어**

문서 파싱(OCR/VLM) 모델을 블라인드 테스트로 평가하는 셀프 호스팅 플랫폼입니다. ELO 랭킹 시스템을 통해 모델 성능을 객관적으로 비교할 수 있습니다.

> **AI로 개발** — 이 프로젝트의 90% 이상이 [Claude Code](https://docs.anthropic.com/en/docs/claude-code)(Anthropic의 에이전틱 코딩 도구)를 사용하여 개발되었습니다. 아키텍처 설계부터 구현, 테스트, Docker 배포까지 전 과정에서 Claude Code가 주요 개발 파트너로 활용되었습니다.

두 개의 익명 모델이 동일한 문서를 파싱하고, 사용자가 더 나은 결과에 투표하면 ELO 점수가 업데이트됩니다. 상용 API(Claude, GPT, Gemini, Mistral)와 자체 호스팅 모델(Ollama, vLLM 등 OpenAI 호환 엔드포인트)을 모두 지원합니다.

## 배경

[OCR Arena](https://www.ocrarena.ai)를 사용하여 상용 OCR 서비스를 비교하던 중, 자체 호스팅 VLM(DeepSeek-OCR, dots.ocr, PaddleOCR-VL 등)을 상용 모델과 비교하고 싶었습니다. 기존 플랫폼은 커스텀 모델 연결을 지원하지 않아서, 어떤 모델이든 연결하고 자체 데이터로 공정한 블라인드 평가를 수행할 수 있는 셀프 호스팅 대안으로 DocParse Arena를 만들었습니다.

이 프로젝트는 [LMSYS Chatbot Arena](https://lmsys.org/blog/2023-05-03-arena/)의 아레나 방식 평가를 문서 파싱 영역에 적용한 것에서 영감을 받았습니다.

## 스크린샷

| 배틀 - 블라인드 비교 | 리더보드 |
|:---:|:---:|
| ![Battle](docs/screenshots/battle.png) | ![Leaderboard](docs/screenshots/leaderboard.png) |
| 두 익명 모델이 동일 문서를 파싱하며 실시간 토큰 스트리밍으로 결과 표시. 투표 시 모델 이름 공개 및 ELO 업데이트. | ELO 레이팅, 승률, 모델 간 상대 전적 통계. |

| 플레이그라운드 | 설정 |
|:---:|:---:|
| ![Playground](docs/screenshots/playground.png) | ![Settings](docs/screenshots/settings-providers.png) |
| 개별 모델을 커스텀 프롬프트와 온도 조절로 테스트. | 프로바이더, 모델, 프롬프트, VLM 레지스트리 추천 관리. |

## 주요 기능

- **블라인드 배틀** — 두 익명 모델이 동일 문서를 파싱. 투표로 정체를 공개하고 랭킹 업데이트.
- **실시간 토큰 스트리밍** — SSE를 통해 OCR 결과가 토큰 단위로 표시되며, Markdown/LaTeX 실시간 렌더링.
- **ELO 랭킹** — K-factor 20 레이팅 시스템과 모델 간 상대 전적 통계.
- **공정한 매치메이킹** — 가중 랜덤 선택(`weight = max_battles - model_battles + 1`)으로 배틀 수가 적은 모델에 더 많은 기회 부여.
- **VLM 레지스트리** — 자체 호스팅 모델(DeepSeek-OCR, dots.ocr, PaddleOCR-VL, Nanonets 등)의 빌트인 프로필. 등록 시 추천 프롬프트와 후처리기 자동 적용.
- **멀티 프로바이더 지원** — Anthropic, OpenAI, Google Gemini, Mistral, Ollama 및 모든 OpenAI 호환 엔드포인트(vLLM, LiteLLM, LocalAI).
- **PDF 지원** — 자동 페이지 분할, 병렬 OCR 처리 및 결과 병합.
- **프롬프트 관리** — 글로벌 기본값 및 모델별 프롬프트 오버라이드.
- **플레이그라운드** — 개별 모델을 온도 조절과 커스텀 프롬프트로 테스트.
- **Docker 지원** — `docker compose up` 한 줄로 배포.
- **관리자 기능** — 프로바이더 연결 테스트, 모델 활성화/비활성화, 배틀 초기화, 팩토리 리셋.

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 프론트엔드 | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| 백엔드 | Python 3.13, FastAPI, SQLAlchemy (async), SQLite |
| 스트리밍 | SSE (Server-Sent Events), markstream-react |
| 렌더링 | react-markdown, remark-gfm, remark-math, rehype-katex, rehype-sanitize |
| 프로바이더 | Anthropic, OpenAI, Google Gemini, Mistral, Ollama, Custom (OpenAI 호환) |
| 배포 | Docker Compose, uv (Python), pnpm (Node.js) |

## 빠른 시작

### Docker Compose (권장)

가장 쉬운 방법은 Docker Compose를 사용하는 것입니다.

1. 레포지토리 클론:
   ```bash
   git clone https://github.com/Bae-ChangHyun/DocParse_Arena.git
   cd DocParse_Arena
   ```
2. 환경 변수 설정:
   ```bash
   cp .env.example .env
   # .env 파일을 열어 API 키와 ADMIN_PASSWORD 설정
   ```
3. 서비스 시작:
   ```bash
   docker compose up -d
   ```
4. 플랫폼 접속:
   - 프론트엔드: http://localhost:3000
   - 백엔드 API (수동 설치 시): http://localhost:8000/docs

### 수동 설치

#### 사전 요구사항
- Python 3.13+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python 패키지 매니저)
- [pnpm](https://pnpm.io/) (Node.js 패키지 매니저)

#### 1. 설치
```bash
git clone https://github.com/Bae-ChangHyun/DocParse_Arena.git
cd DocParse_Arena

# 백엔드 설정
cd backend
uv sync
cp .env.example .env
uv run python seed_db.py
cd ..

# 프론트엔드 설정
cd frontend
pnpm install
cd ..
```

#### 2. API 키 설정
`backend/.env`를 편집하거나, 애플리케이션 시작 후 Settings UI에서 설정할 수 있습니다.

#### 3. 실행
```bash
# 런처 스크립트 사용
./run.sh

# 또는 개별 서비스 실행
# 백엔드 (포트 8000)
cd backend && uv run uvicorn app.main:app --reload
# 프론트엔드 (포트 3000)
cd frontend && pnpm dev
```

## 설정

### 환경 변수
`.env.example`을 `.env`로 복사하고 API 키를 입력합니다. 사용할 프로바이더의 키만 설정하면 됩니다.

### VLM 레지스트리
자체 호스팅 모델 추가 시 모델 ID가 알려진 패턴(예: `deepseek-ocr`, `dots.ocr`, `paddleocr-vl`)과 일치하면 추천 프롬프트와 후처리 파이프라인이 자동 제안됩니다. 수락하거나 커스터마이즈할 수 있습니다.

현재 등록된 모델: DeepSeek-OCR, DeepSeek-OCR-2, dots.ocr, PaddleOCR-VL, LightOnOCR, Nanonets-OCR, GLM-OCR.

### Extra Kwargs
**Settings > Models > Edit**에서 추가 API 파라미터를 JSON으로 전달:

```json
{ "max_completion_tokens": 4096, "temperature": 0.7 }
```

### 프롬프트 커스터마이즈
**Settings > Prompts**에서 글로벌 기본값과 모델별 오버라이드를 설정할 수 있습니다.

## API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|----------|------|
| POST | `/api/battle/start` | 배틀 시작 (파일 업로드) |
| GET | `/api/battle/{id}/stream` | SSE로 OCR 결과 스트리밍 |
| POST | `/api/battle/{id}/vote` | 투표 및 ELO 업데이트 |
| GET | `/api/leaderboard` | 전체 랭킹 |
| GET | `/api/leaderboard/head-to-head` | 모델 간 상대 전적 |
| POST | `/api/playground/ocr` | 단일 모델 OCR 테스트 |
| GET/POST | `/api/admin/providers` | 프로바이더 관리 |
| GET/POST | `/api/admin/models` | 모델 관리 |
| GET/POST | `/api/admin/prompts` | 프롬프트 관리 |
| POST | `/api/admin/providers/{id}/test` | 연결 테스트 |

## 프로젝트 구조

```
DocParse_Arena/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 엔트리
│   │   ├── config.py            # 설정
│   │   ├── vlm_registry.py      # VLM 모델 레지스트리
│   │   ├── models/              # SQLAlchemy + Pydantic 스키마
│   │   ├── routers/             # API 엔드포인트
│   │   ├── services/            # 비즈니스 로직 (OCR, ELO, PDF, 스트리밍)
│   │   └── ocr_providers/       # 프로바이더 구현
│   ├── sample_docs/             # 샘플 문서
│   └── seed_db.py               # DB 시딩
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js 페이지 (battle, leaderboard, playground, settings)
│   │   ├── components/          # React 컴포넌트
│   │   └── lib/                 # API 클라이언트, 유틸리티
│   └── package.json
├── docker-compose.yml           # 원커맨드 배포
├── run.sh                       # 개발 런처 스크립트
└── .env.example                 # 환경 변수 템플릿
```

## 기여하기

기여를 환영합니다! 참여 방법:

- **VLM 레지스트리에 모델 추가** — 문서 파싱에 적합한 모델을 아시나요? `backend/app/vlm_registry.py`에 추가해주세요.
- **새 프로바이더 추가** — `backend/app/ocr_providers/`에서 `OCRProviderBase` 인터페이스를 구현합니다.
- **UI 개선** — 프론트엔드는 `frontend/src/`에 shadcn/ui 컴포넌트로 구성되어 있습니다.
- **버그 리포트** — [이슈](https://github.com/Bae-ChangHyun/DocParse_Arena/issues)를 열어주세요.

자세한 내용은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

## 보안

- `.env`에 강력한 `ADMIN_PASSWORD`를 설정하여 관리자 UI를 보호하세요.
- 공개 호스팅 시 `CORS_ORIGINS`를 설정하여 API 접근을 제한하세요.
- API 키는 데이터베이스에 저장됩니다 — `data/docparse_arena.db`를 안전하게 보호하고 절대 커밋하지 마세요.
- 업로드 파일은 경로 순회 방지, 크기 제한, PDF 페이지 상한으로 검증됩니다.

## 라이선스

[MIT License](LICENSE) — 자유롭게 사용, 수정, 배포할 수 있습니다.
