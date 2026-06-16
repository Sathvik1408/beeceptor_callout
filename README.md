# Beeceptor Demo Tests

End-to-end tests for [Beeceptor](https://beeceptor.com) mock API rules using Playwright.

## Tests

| Test | Scenario | Verifies |
|------|----------|----------|
| Order API | Async callout + Discord webhook callback | 202 response with processing status |
| Dog API | Sync callout proxying to dog.ceo | 200 response with valid image URL |
| Payment API | Async callout + self-callback endpoint | 202 response with payment success |

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Run

```bash
python -m pytest test_beeceptor_demo.py -v
```

Tests run in headed mode (browser visible) and record videos to `videos/`.
