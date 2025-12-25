import os
from datetime import date
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from openai import OpenAI
from upstash_redis import Redis

app = Flask(__name__)

# ✅ REQUIRED FOR RENDER / PROXIES
app.config["TRUST_PROXY_HEADERS"] = True

# 🔒 LOCKED CORS — only your sites can call the backend
CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "https://asklit.online",
                "https://www.asklit.online",
                "http://localhost:3000"
            ]
        }
    }
)

# 🔑 API KEYS
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")

if not OPENAI_API_KEY or not GOOGLE_BOOKS_API_KEY:
    raise RuntimeError("Missing API keys in environment variables")

# 🔑 REDIS (PERSISTENT STORAGE)
REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

if not REDIS_URL or not REDIS_TOKEN:
    raise RuntimeError("Missing Upstash Redis credentials")

redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)

client = OpenAI(api_key=OPENAI_API_KEY)

DAILY_LIMIT = 10


# ✅ GET REAL CLIENT IP
def get_client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


# ✅ PERSISTENT DAILY RATE LIMIT (24h rolling window)
def check_rate_limit(ip):
    today = str(date.today())
    key = f"rate_limit:{ip}:{today}"

    count = redis.get(key)

    if count is None:
        redis.set(key, 1, ex=86400)  # 24 hours
        return True

    if int(count) >= DAILY_LIMIT:
        return False

    redis.incr(key)
    return True

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200



def search_google_books_for_quote(query):
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": query,
        "key": GOOGLE_BOOKS_API_KEY,
        "printType": "books",
        "maxResults": 5
    }

    response = requests.get(url, params=params)
    data = response.json()
    books = []

    if response.status_code == 200 and "items" in data:
        for volume in data["items"]:
            volume_info = volume.get("volumeInfo", {})
            search_info = volume.get("searchInfo", {})
            access_info = volume.get("accessInfo", {})

            if access_info.get("viewability") not in {
                "PARTIAL", "ALL_PAGES", "FULL", "SAMPLE"
            }:
                continue

            quote = (search_info.get("textSnippet") or "").replace("...", "").strip()
            if not quote:
                continue

            books.append({
                "title": volume_info.get("title", "Unknown Title"),
                "quote": quote,
                "link": volume_info.get("previewLink", "https://books.google.com/"),
                "published_date": volume_info.get("publishedDate", "Unknown")
            })

    if not books:
        return [{
            "title": None,
            "quote": "No previewable books with snippets found.",
            "link": None,
            "published_date": None
        }]

    books.sort(key=lambda b: (b["title"] or "").lower())
    return books


@app.route("/chat", methods=["POST"])
def chat():
    ip = get_client_ip()

    if not check_rate_limit(ip):
        return jsonify({
            "error": "Daily request limit reached (10 per day). Try again tomorrow."
        }), 429

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Empty message"}), 400

    prompt = (
        "Extract a short keyword-based search query for books.\n"
        "Rules:\n"
        "- 3 to 5 words max\n"
        "- lowercase\n"
        "- no punctuation\n"
        "- return ONLY the keywords\n\n"
        f'User message: "{message}"'
    )

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    query = response.output_text.strip()
    books = search_google_books_for_quote(query)

    return jsonify({
        "reply": f"Here are some books I found for: '{query}'",
        "query": query,
        "books": books
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
