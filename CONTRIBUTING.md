# Contributing to GGLTCG

First off, thanks for taking the time to contribute! 🎉

The following is a set of guidelines for contributing to GGLTCG. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## Getting Started

### Prerequisites

- **Python 3.13+**
- **Node.js 18+**
- **Google Gemini API Key** (Get one for free at [Google AI Studio](https://aistudio.google.com/api-keys))

### Setting Up the Development Environment

1. **Clone the repository**

    ```bash
    git clone https://github.com/RegisCA/ggltcg.git
    cd ggltcg
    ```

2. **Backend Setup**

    ```bash
    cd backend
    python3.13 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    
    # Configure Environment
    cp .env.example .env
    # Edit .env and add:
    # GOOGLE_API_KEY=your_key_here
    # DATABASE_URL=postgresql://user:password@localhost/ggltcg_db
    # GOOGLE_CLIENT_ID=your_google_oauth_client_id
    ```

3. **Frontend Setup**

    ```bash
    cd frontend
    npm install
    # Create .env.local for Google OAuth
    echo "VITE_GOOGLE_CLIENT_ID=your_google_oauth_client_id" > .env.local
    ```

4. **Running the Application**

    *Terminal 1 (Backend):*

    ```bash
    cd backend
    source venv/bin/activate
    python run_server.py
    ```

    *Terminal 2 (Frontend):*

    ```bash
    cd frontend
    npm run dev
    ```

    Open <http://localhost:5173> to play.

## How to Contribute

### Reporting Bugs

This section guides you through submitting a bug report for GGLTCG. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

- **Use a clear and descriptive title** for the issue to identify the problem.
- **Describe the exact steps which reproduce the problem** in as many details as possible.
- **Provide specific examples** to demonstrate the steps.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for GGLTCG, including completely new features and minor improvements to existing functionality.

- **Use a clear and descriptive title** for the issue to identify the suggestion.
- **Provide a step-by-step description of the suggested enhancement** in as many details as possible.
- **Explain why this enhancement would be useful** to most GGLTCG users.

### Pull Requests

1. **Fork & Branch**: Fork the repo and create your branch from `main`.
2. **Tests**: If you've added code that should be tested, add tests. Ensure the test suite passes.
3. **Linting**: Make sure your code lints.
4. **Submit PR**: Issue that pull request to the `main` branch.
   - **Note**: Direct pushes to `main` are blocked. All changes must go through a Pull Request.
   - **Approval**: PRs require at least one approval from a maintainer before merging.

## Coding Standards & Guidelines

We have detailed internal instructions that serve as the authoritative source for coding standards, security practices, and documentation. Please review these before contributing:

- **[Coding Instructions](.github/instructions/coding.instructions.md)**: Comprehensive coding standards, architecture principles, and best practices.
- **[Security & OWASP](.github/instructions/security-and-owasp.instructions.md)**: Secure coding guidelines and security requirements.
- **[Markdown & Docs](.github/instructions/markdown.instructions.md)**: Standards for documentation and content creation.

### Quick Summary

- **Backend (Python)**: Follow PEP 8, use type hints, and write tests in `backend/tests/`.
- **Frontend (React)**: Use functional components, TypeScript interfaces, and Tailwind CSS.
- **Security**: Never commit secrets. Use environment variables.


### Frontend (React/TypeScript)

- Use functional components and hooks.
- Ensure strict type safety (no `any` unless absolutely necessary).
- Follow the existing project structure.

## License

By contributing, you agree that your contributions will be licensed under its AGPL-3.0 License.
