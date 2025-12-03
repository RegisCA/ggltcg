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

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. Ensure the test suite passes.
4. Make sure your code lints.
5. Issue that pull request!

## Coding Standards

### Backend (Python)

- Follow PEP 8 style guidelines.
- Use type hints for function arguments and return values.
- Write unit tests for new logic in `backend/tests/`.

### Frontend (React/TypeScript)

- Use functional components and hooks.
- Ensure strict type safety (no `any` unless absolutely necessary).
- Follow the existing project structure.

## License

By contributing, you agree that your contributions will be licensed under its AGPL-3.0 License.
