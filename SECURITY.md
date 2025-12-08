# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it privately.

**Do not open a public issue.**

Instead, please report security issues via:

- The **Security** tab in the GitHub repository (if enabled).
- Email to the maintainer (if provided in profile).

We will make every effort to acknowledge your report and provide a fix or workaround as soon as possible.

## Security Posture & Assurances

### Authentication

- **Google OAuth Only**: We do not store user passwords. Authentication is handled entirely via Google Identity Services.
- **Session Management**: Sessions are managed via secure, HTTP-only cookies (in production).

### Data Protection

- **Database Access**: Direct database access is restricted. The application uses an ORM (SQLAlchemy) with parameterized queries to prevent SQL injection.
- **Secrets**: No API keys or secrets are committed to the repository. All sensitive configuration is loaded from environment variables.

### Development Guidelines

- All code changes are reviewed for security implications.
- We follow OWASP best practices. See `.github/instructions/security-and-owasp.instructions.md` for our internal security guidelines.
