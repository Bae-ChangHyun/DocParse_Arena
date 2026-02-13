# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT open a public GitHub issue.**
2. Use [GitHub Security Advisories](https://github.com/Bae-ChangHyun/docparse-arena/security/advisories/new) to report privately.
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact

We will acknowledge receipt within 48 hours and provide a fix timeline.

## Scope

- Backend API (FastAPI)
- Frontend (Next.js)
- Docker deployment
- Authentication system

## Known Limitations

- This is a self-hosted tool intended for internal/evaluation use.
- API keys stored in the database are not encrypted at rest. Use environment-level security to protect the SQLite database file.
- Admin authentication uses JWT tokens with configurable expiry. Set `ADMIN_PASSWORD` in production.

## Best Practices for Deployment

- Always set `ADMIN_PASSWORD` and `JWT_SECRET` environment variables in production.
- Restrict CORS origins via `CORS_ORIGINS` to your domain.
- Run behind a reverse proxy (nginx, Caddy) with HTTPS.
- Do not expose the SQLite database file publicly.
