import os
from datetime import date
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from openai import OpenAI

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")

if not OPENAI_API_KEY or not GOOGLE_BOOKS_API_KEY:
    raise RuntimeError("Missing API keys in environment variables")

client = OpenAI(api_key=OPENAI_API_KEY)

DAILY_LIMIT = 10
usage = {}  # { ip: { "date": YYYY-MM-DD, "count": int } }


def check_rate_limit(ip):
    today = str(date.today())
    if ip not in usage or usage[ip]["date"] != today:
        usage[ip] = {"date": today, "count": 0}

    if usage[ip]["count"] >= DAILY_LIMIT:
        return False

    usage[ip]["count"] += 1
    return True


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

            if access_info.get("viewability") not in ["PARTIAL", "ALL_PAGES", "FULL", "SAMPLE"]:
                continue

            title = volume_info.get("title", "Unknown Title")
            quote = (search_info.get("textSnippet") or "").replace("...", "").strip()
            link = volume_info.get("previewLink", "https://books.google.com/")
            published_date = volume_info.get("publishedDate", "9999")

            if quote:
                books.append({
                    "title": title,
                    "quote": quote,
                    "link": link,
                    "published_date": published_date
                })

    if not books:
        return [{
            "quote": "No previewable books with snippets found.",
            "title": None,
            "link": None,
            "published_date": None
        }]

    books.sort(key=lambda b: (b["title"] or "").lower())
    return books


@app.route("/chat", methods=["POST"])
def chat():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)

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
