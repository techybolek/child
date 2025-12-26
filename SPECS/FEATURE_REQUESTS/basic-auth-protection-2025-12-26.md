# Feature Request: Basic Auth Protection for GCP Deployment

**Date:** 2025-12-26
**Status:** Refined

## Overview
Add HTTP Basic Authentication to the backend API when deployed to GCP to prevent unauthorized access and protect against API abuse that could incur LLM costs.

## Problem Statement
The backend API is currently deployed with `--allow-unauthenticated` on Cloud Run, meaning anyone who discovers the endpoint can directly call `/api/chat` and trigger LLM API calls (OpenAI/Groq), potentially racking up significant costs.

## Users & Stakeholders
- **Primary Users:** Select users who receive shared credentials
- **Admin:** Developer who shares credentials with trusted users

## Functional Requirements

1. **Backend API requires HTTP Basic Auth when `REQUIRE_AUTH=true`**
   - All `/api/*` endpoints require valid credentials
   - Health check endpoint (`/api/health`) may optionally remain public for monitoring

2. **Credentials stored as environment variables**
   - `AUTH_USERNAME` - the username
   - `AUTH_PASSWORD` - the password
   - Optionally store in GCP Secret Manager alongside other secrets

3. **Local development bypasses auth**
   - When `REQUIRE_AUTH` is not set or `false`, no authentication required
   - No changes to local development workflow

4. **Browser handles credential prompt**
   - Backend returns `401 Unauthorized` with `WWW-Authenticate: Basic` header
   - Browser shows native login dialog
   - Credentials cached for browser session

## User Flow

1. User navigates to frontend URL
2. Frontend makes API call to backend
3. Backend returns `401 Unauthorized`
4. Browser shows native Basic Auth dialog
5. User enters shared credentials (e.g., `secret_user` / `secret_password`)
6. Browser retries request with `Authorization: Basic <base64>` header
7. Backend validates credentials → returns response
8. Browser caches credentials for session (subsequent requests work automatically)

## Acceptance Criteria

- [ ] Backend returns 401 for unauthenticated requests when `REQUIRE_AUTH=true`
- [ ] Backend accepts valid Basic Auth credentials and processes requests
- [ ] Backend rejects invalid credentials with 401
- [ ] Local development works without authentication (no env var set)
- [ ] GCP deployment script updated to set `REQUIRE_AUTH=true` and credential env vars
- [ ] Health endpoint (`/api/health`) remains accessible for monitoring (optional)

## Technical Requirements

### Backend Changes (FastAPI)

Add middleware or dependency to `backend/main.py`:

```python
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if not os.getenv("REQUIRE_AUTH"):
        return True
    
    correct_username = secrets.compare_digest(
        credentials.username, 
        os.getenv("AUTH_USERNAME", "")
    )
    correct_password = secrets.compare_digest(
        credentials.password, 
        os.getenv("AUTH_PASSWORD", "")
    )
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True
```

### Deployment Changes (GCP/deploy.sh)

Update backend deployment to include auth env vars:

```bash
gcloud run deploy "${BACKEND_SERVICE}" \
    ...
    --set-env-vars="...,REQUIRE_AUTH=true,AUTH_USERNAME=${AUTH_USERNAME},AUTH_PASSWORD=${AUTH_PASSWORD}" \
    ...
```

Or use GCP Secrets:
```bash
--set-secrets="...,AUTH_USERNAME=auth-username:latest,AUTH_PASSWORD=auth-password:latest"
```

### Environment Variables

| Variable | Local | GCP | Description |
|----------|-------|-----|-------------|
| `REQUIRE_AUTH` | not set | `true` | Enables authentication |
| `AUTH_USERNAME` | not set | `secret_user` | Basic auth username |
| `AUTH_PASSWORD` | not set | `secret_password` | Basic auth password |

## Edge Cases & Error Handling

| Case | Behavior |
|------|----------|
| Missing credentials | Return 401 with `WWW-Authenticate: Basic` header |
| Invalid credentials | Return 401 with `WWW-Authenticate: Basic` header |
| `REQUIRE_AUTH` not set | Skip auth check, allow all requests |
| Empty username/password env vars | Treat as auth enabled but no valid credentials (all requests fail) |

## Out of Scope

- Multiple user accounts
- User management UI
- Password hashing (credentials compared directly)
- Session tokens / JWT
- Rate limiting (could be separate feature)
- Frontend login page (using browser native dialog)
- HTTPS (handled by Cloud Run)

## Security Considerations

- Credentials transmitted over HTTPS (Cloud Run enforces this)
- Use `secrets.compare_digest()` to prevent timing attacks
- Credentials stored in GCP Secret Manager or environment variables
- Single shared credential - acceptable for prototype/demo

## Dependencies

- **Requires:** None
- **Blocks:** None

## Success Metrics

- Unauthenticated requests to GCP backend return 401
- Authenticated users can use the chatbot normally
- No impact on local development workflow

## Implementation Notes

- Estimated ~30 lines of code in backend
- ~5 lines change in deploy.sh
- No frontend changes required (browser handles auth dialog)
