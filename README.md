# DocParse Arena

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)

A blind-test and ELO ranking platform for document parsing (OCR) models.

Compare various document parsing models (Claude, GPT, Gemini, Mistral, Ollama, Custom) on the same document through blind testing and generate ELO rankings based on user votes. Connect your own API keys and models to host your private leaderboard.

## Inspired by

This project is a self-hosted platform inspired by the arena-style evaluation method of [LMSYS Chatbot Arena](https://lmsys.org/blog/2023-05-03-arena/), applied to the document parsing (OCR) domain. Evaluate model performance using your own private datasets and custom model connections.

## Screenshots

### Battle - Blind OCR Comparison
Upload a document, and two anonymous models perform OCR simultaneously. Compare the results and vote to reveal the model names and update their ELO ratings.

![Battle Page](docs/screenshots/battle.png)

### Leaderboard - ELO Rankings
View ELO ratings, win rates, and average latency for each model.

![Leaderboard](docs/screenshots/leaderboard.png)

### Playground - Single Model Test
Select a specific model to test individual OCR results.

![Playground](docs/screenshots/playground.png)

### Settings - Provider Management
Configure API keys, Base URLs, and perform connection tests. Add multiple custom providers like vLLM or LiteLLM.

![Settings - Providers](docs/screenshots/settings-providers.png)

### Settings - Model Management
Add or delete models, toggle activation status, and reset ELO ratings.

![Settings - Models](docs/screenshots/settings-models.png)

### Settings - Prompt Management
Configure global default prompts and model-specific overrides.

![Settings - Prompts](docs/screenshots/settings-prompts.png)

## Features

- **Blind Battle**: Anonymously compare OCR results from two models and vote for the better one.
- **ELO Ranking**: Rating system based on K-factor 20 for accurate performance tracking.
- **Fair Matchmaking**: Weighted random selection system (`weight = max_battles - model_battles + 1`) ensures models with fewer evaluations get more opportunities.
- **Multi-Provider Support**: Integrated support for Anthropic (Claude), OpenAI (GPT), Google (Gemini), Mistral, Ollama, and custom OpenAI-compatible endpoints.
- **PDF Support**: Automatically splits PDFs into per-page images for parallel OCR processing and result merging.
- **Markdown Rendering**: Advanced rendering support for Markdown, HTML, and LaTeX (KaTeX).
- **Prompt Management**: Centralized management of default and model-specific prompt overrides.
- **Real-time Connection Testing**: Validates provider connectivity through actual API calls (e.g., `GET /v1/models`) rather than simple string validation.
- **Custom Providers**: Register multiple OpenAI-compatible endpoints such as vLLM, LiteLLM, or LocalAI.
- **Flexible API Parameters**: Configure model-specific `Extra Kwargs` via JSON (e.g., supporting `max_completion_tokens` for OpenAI o1/o3).

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), SQLite |
| OCR Providers | Anthropic, OpenAI, Google GenAI, Mistral, Ollama, Custom |
| Rendering | react-markdown, remark-gfm, remark-math, rehype-katex, rehype-sanitize |
| Package Managers | uv (Python), pnpm (Node.js) |

## Quick Start

### Docker Compose (Recommended)

The easiest way to get DocParse Arena running is using Docker Compose.

1. Clone the repository:
   ```bash
   git clone https://github.com/Bae-ChangHyun/docparse-arena.git
   cd docparse-arena
   ```
2. Set up your environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and ADMIN_PASSWORD
   ```
3. Start the services:
   ```bash
   docker compose up -d
   ```
4. Access the platform:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs

### Manual Setup

#### Prerequisites
- Python 3.13+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [pnpm](https://pnpm.io/) (Node.js package manager)

#### 1. Installation
```bash
git clone https://github.com/Bae-ChangHyun/docparse-arena.git
cd docparse-arena

# Backend setup
cd backend
uv sync
cp .env.example .env
uv run python seed_db.py
cd ..

# Frontend setup
cd frontend
pnpm install
cd ..
```

#### 2. Configure API Keys
Edit `backend/.env` or configure them through the Settings UI after starting the application.

#### 3. Run the Application
```bash
# Using the launcher script
./run.sh

# Or start services individually
# Backend (Port 8000)
cd backend && uv run uvicorn app.main:app --reload
# Frontend (Port 3000)
cd frontend && pnpm dev
```

## Configuration

### Model-Specific API Parameters (Extra Kwargs)
In **Settings > Models > Edit**, you can define `Extra Kwargs` in JSON format. These are passed directly to the provider's API.

```json
{
  "max_completion_tokens": 4096,
  "temperature": 0.7
}
```
*Note: For Claude models, `max_tokens` is forced to 4096 by default.*

### Prompt Customization
Manage prompts in **Settings > Prompts**:
- **Default Prompt**: Applied to all models.
- **Model-Specific Prompt**: Overrides the default prompt for a specific model.

### Fair Matchmaking (Weighted Random Selection)
To ensure all models receive equal evaluation opportunities, the system uses a weighted selection algorithm:
`weight = max_battles - model_battles + 1`

Models with fewer battles have a higher probability of being selected for the next match.

### Provider Connection Testing
The "Test Connection" feature performs a real API call (e.g., `GET /v1/models`) to ensure the provider is correctly configured. If a test fails, all associated models are automatically deactivated to prevent errors during battles.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/battle/start` | Start a battle (file upload) |
| GET | `/api/battle/{id}/stream` | Stream OCR results via SSE |
| POST | `/api/battle/{id}/vote` | Submit vote and update ELO |
| GET | `/api/leaderboard` | Get global rankings |
| GET | `/api/leaderboard/head-to-head` | Get win rates between models |
| POST | `/api/playground/ocr` | Single model OCR test |
| GET/POST | `/api/admin/providers` | Manage providers |
| GET/POST | `/api/admin/models` | Manage models |
| GET/POST | `/api/admin/prompts` | Manage prompts |
| POST | `/api/admin/providers/{id}/test` | Connection test |

## Project Structure

```
docparse-arena/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry
│   │   ├── config.py            # Settings
│   │   ├── models/
│   │   │   ├── database.py      # SQLAlchemy models
│   │   │   └── schemas.py       # Pydantic schemas
│   │   ├── routers/
│   │   │   ├── battle.py        # Battle API (start/stream/vote)
│   │   │   ├── leaderboard.py   # Ranking API
│   │   │   ├── playground.py    # Single model OCR
│   │   │   ├── documents.py     # Document management
│   │   │   └── admin.py         # Settings API
│   │   ├── services/
│   │   │   ├── ocr_service.py   # OCR orchestration
│   │   │   ├── elo_service.py   # ELO calculation
│   │   │   ├── pdf_service.py   # PDF to images
│   │   │   └── diff_service.py  # Text diff
│   │   └── ocr_providers/       # Provider implementations
│   ├── sample_docs/             # Sample documents
│   ├── seed_db.py               # DB seeding
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   ├── components/          # React components
│   │   └── lib/api.ts           # API client
│   └── package.json
├── run.sh                       # Launcher script
└── README.md
```

## Contributing

We welcome contributions! To contribute:
1. Fork the repository.
2. Create a new feature branch (`git checkout -b feature/your-feature`).
3. Commit your changes.
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a Pull Request.

## Security

- **ADMIN_PASSWORD**: Ensure you set a strong `ADMIN_PASSWORD` in your `.env` file to protect the settings and model management UI.
- **CORS Config**: Configure `CORS_ORIGINS` in your `.env` file to restrict API access if hosting publicly (defaults to `http://localhost:3000`).
- **API Keys**: API keys are stored in the database. Ensure your database file (`data/ocr_arena.db`) is properly secured and not publicly accessible.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
