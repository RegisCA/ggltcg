# Troubleshooting Guide

## Common Issues

### Backend/API Issues

- **Health Check**: Verify the backend is running by visiting `http://localhost:8000/health`.
- **API Documentation**: Check the interactive API docs at `http://localhost:8000/docs`.
- **Frontend Connection**: If the frontend cannot connect, inspect the browser console and verify `VITE_API_URL` points to the correct backend URL.

### Authentication

- **Google OAuth**: Confirm your Google OAuth credentials and environment variables are set correctly.
- **References**:
  - `docs/development/GOOGLE_OAUTH_SETUP.md`
  - `docs/development/AUTH_IMPLEMENTATION.md`

### AI & LLM Integration

#### Rate Limit Exceeded

- **Check Usage**: Monitor your usage at <https://aistudio.google.com/usage>.
- **Free Tier Limits**: The free tier allows 15 requests per minute (RPM) for most models.
- **Solution**: Wait 1 minute and try again, or slow down gameplay. The code automatically retries with exponential backoff (1s, 2s, 4s).

#### AI Not Making Decisions

- **Logs**: Check the backend terminal for detailed logs showing Gemini API calls.
- **Errors**: Look for `ERROR` or `WARNING` messages in the output. Logs include prompts, responses, and error details.

#### Using Alternative LLM Providers

- **Support**: This project supports multiple LLM providers (Gemini, Claude, etc.).
- **Setup**: See `backend/AI_SETUP.md` for detailed setup instructions for each provider.
- **Recommendation**: Gemini is recommended for development due to its generous free tier.
