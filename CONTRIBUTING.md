# Contributing to DocParse Arena

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/<your-username>/docparse-arena.git
   cd docparse-arena
   ```
3. **Set up the development environment**:
   ```bash
   # Backend
   cd backend
   cp .env.example .env  # Edit with your API keys
   uv sync
   uv run python seed_db.py
   uv run uvicorn app.main:app --reload --port 8000

   # Frontend (in a separate terminal)
   cd frontend
   pnpm install
   pnpm dev
   ```

## Development Workflow

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature main
   ```
2. Make your changes
3. Test your changes locally
4. Commit with clear messages
5. Push and open a Pull Request against the `main` branch

## Code Style

### Backend (Python)
- Python 3.13+
- Follow existing code patterns (FastAPI routers, SQLAlchemy async)
- Use type hints

### Frontend (TypeScript)
- Next.js 15 App Router
- Tailwind CSS + shadcn/ui components
- TypeScript strict mode

## Adding a New OCR Provider

1. Create a new file in `backend/app/ocr_providers/`
2. Extend `OcrProvider` base class from `base.py`
3. Implement `process_image()` and `process_image_stream()`
4. Register the provider in `backend/app/ocr_providers/__init__.py`

## Reporting Issues

- Use GitHub Issues for bugs and feature requests
- Include steps to reproduce for bug reports
- For security issues, please report privately via GitHub Security Advisories

## Pull Request Guidelines

- Keep PRs focused on a single change
- Update documentation if needed
- Ensure the frontend builds without errors (`pnpm build`)
- Ensure the backend starts without errors

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
