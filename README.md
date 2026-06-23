# AskLit — Backend

**AskLit is a free, open-source research tool that answers plain-English questions with real books instead of AI-generated text.**

Ask it something like *"How does the Federal Reserve control inflation?"* and instead of handing you a confident paragraph that may or may not be true, AskLit returns links to actual published books on the topic — each one opened to a relevant preview snippet on Google Books, so you can read the source and verify the information yourself.

Live at **[asklit.online](https://asklit.online)**.

This repository contains the backend service.

## Why this exists

Large language models are everywhere now, and they're genuinely useful — but they also confidently produce information that's subtly or completely wrong. For students, researchers, and anyone trying to actually *learn* something, that's a real problem. You can't cite a chatbot, and you can't always tell when it's making things up.

AskLit takes a deliberately different approach. It uses AI for the one thing AI is reliably good at — understanding what you're asking and turning it into a good search — and then gets out of the way. The answer doesn't come from a model. It comes from books written by people who know the subject. You read the actual source, in context, and decide for yourself.

The goal is academic honesty by design: route people *toward* primary sources rather than substituting for them. It's a small tool with a specific belief behind it — that the antidote to AI misinformation isn't less technology, it's pointing technology at verifiable human knowledge.

## How it works

1. The user submits a question in plain English.
2. An LLM extracts a concise keyword search query from that question (3–5 words, no fluff).
3. That query is sent to the **Google Books API**, filtered to volumes with readable previews.
4. The service returns a ranked list of books, each with a title, publication date, a relevant text snippet, and a direct preview link — so the user can jump straight to the part of the book that matters.

A per-IP daily rate limit (backed by Redis) keeps the free public service from being abused.

## Tech stack

- **Python** + **Flask** — web service
- **Google Books API** — source of truth for results
- **OpenAI API** — keyword extraction from natural-language questions
- **Upstash Redis** — persistent, rolling 24-hour rate limiting per IP
- Deployed on **Render**

## Running locally

```bash
# 1. Clone and enter the repo
git clone https://github.com/Max-is-awsome/ask-lit-backend.git
cd ask-lit-backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set the required environment variables (see below)

# 4. Run
python main.py
```

The service starts on port `5001` by default (override with the `PORT` env var).

### Required environment variables

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Keyword extraction |
| `GOOGLE_BOOKS_API_KEY` | Book search |
| `UPSTASH_REDIS_REST_URL` | Rate-limit storage |
| `UPSTASH_REDIS_REST_TOKEN` | Rate-limit storage auth |

### Endpoints

- `GET /health` — health check, returns `ok`
- `POST /chat` — body `{ "message": "your question" }`, returns the reply, the extracted query, and the list of books

## Status

AskLit is live and maintained. It's a personal project built and run solo, available free to anyone, with no ads, no accounts, and no funding behind it — just something I think should exist.

## License

Open source. See [LICENSE](LICENSE) for details.
