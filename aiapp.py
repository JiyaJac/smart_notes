from flask import Flask, render_template, request, jsonify
from groq import Groq
import json
import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

if not os.environ.get("GROQ_API_KEY"):
    raise Exception("❌ GROQ_API_KEY not found in .env")

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

app = Flask(__name__, template_folder="../templates")


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def trim_text(text, max_chars=6000):
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[Text truncated for processing]"


def call_ai(prompt, max_tokens=800):
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are an expert academic assistant. Always respond with valid JSON only — no markdown, no explanation, no extra text."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens,
        temperature=0.3
    )
    return completion.choices[0].message.content


def extract_json(text):
    text = text.strip()
    match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if match:
        return json.loads(match.group(1))
    match = re.search(r'```\s*([\s\S]*?)\s*```', text)
    if match:
        return json.loads(match.group(1))
    match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', text)
    if match:
        return json.loads(match.group(1))
    return json.loads(text)


def fetch_url_content(url):
    """
    Fetches a URL and extracts clean readable text.
    Returns (title, text, error).
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None, None, "URL must start with http:// or https://"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return None, None, "Request timed out. The URL took too long to respond."
    except requests.exceptions.ConnectionError:
        return None, None, "Could not connect to the URL. Check if the link is accessible."
    except requests.exceptions.HTTPError as e:
        return None, None, f"HTTP error {e.response.status_code}: The page could not be retrieved."
    except Exception as e:
        return None, None, f"Failed to fetch URL: {str(e)}"

    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type and "text/plain" not in content_type:
        return None, None, f"Unsupported content type: {content_type}. Only HTML and plain-text pages are supported."

    soup = BeautifulSoup(response.text, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "noscript", "iframe", "svg",
                     "button", "input", "select", "textarea"]):
        tag.decompose()

    main_content = (
        soup.find("article") or
        soup.find("main") or
        soup.find(id=re.compile(r"content|main|article|post|body", re.I)) or
        soup.find(class_=re.compile(r"content|main|article|post|entry|body", re.I))
    )

    raw = main_content if main_content else soup
    text = raw.get_text(separator="\n", strip=True)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    if len(text) < 100:
        return None, None, (
            "Could not extract enough readable text from the page. "
            "It may be JavaScript-rendered or behind a login."
        )

    return title, text, None


# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Fetch URL text ────────────────────────────────────────────────────────────
@app.route("/api/fetch-url", methods=["POST"])
def fetch_url_route():
    data = request.json
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400

    title, text, error = fetch_url_content(url)
    if error:
        return jsonify({"error": error}), 422

    return jsonify({
        "title": title,
        "text": trim_text(text, max_chars=6000),
        "char_count": len(text),
        "truncated": len(text) > 6000,
    })


# ── Deep analysis of a URL / blog ─────────────────────────────────────────────
@app.route("/api/analyze-url", methods=["POST"])
def analyze_url():
    data  = request.json
    url   = (data.get("url")   or "").strip()
    focus = (data.get("focus") or "").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    title, text, error = fetch_url_content(url)
    if error:
        return jsonify({"error": error}), 422

    trimmed = trim_text(text, max_chars=6000)

    focus_instruction = (
        f'\nThe user specifically wants to focus on: "{focus}"\n'
        if focus else ""
    )

    prompt = f"""You are an expert content analyst. Analyse the article/blog content below and return a detailed JSON report.
{focus_instruction}
PAGE TITLE: {title}
URL: {url}

CONTENT:
{trimmed}

Return ONLY a valid JSON object, no markdown, no extra text:
{{
  "page_title": "exact page title",
  "content_type": "article | blog | documentation | news | tutorial | research | other",
  "overall_score": 82,
  "readability": 80,
  "depth": 75,
  "credibility": 70,
  "summary": "3-4 sentence summary of the main content and its key message",
  "key_topics": ["topic 1", "topic 2", "topic 3", "topic 4", "topic 5"],
  "key_points": ["Main point 1", "Main point 2", "Main point 3", "Main point 4", "Main point 5"],
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "target_audience": "Who this content is written for",
  "takeaways": ["Actionable takeaway 1", "Actionable takeaway 2", "Actionable takeaway 3"],
  "suggested_questions": ["Follow-up question 1?", "Follow-up question 2?", "Follow-up question 3?"]
}}"""

    try:
        response = call_ai(prompt, max_tokens=2000)
        result   = extract_json(response)
        result["url"]        = url
        result["char_count"] = len(text)
        result["truncated"]  = len(text) > 6000
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


# ── ✨ NEW: Summarize notes ────────────────────────────────────────────────────
@app.route("/api/summarize", methods=["POST"])
def summarize_notes():
    """
    Accepts student notes (and an optional 'style' parameter) and returns
    a structured summary with multiple formats:
      - brief     : 2-3 sentence TL;DR
      - detailed  : section-by-section breakdown
      - bullet    : concise bullet-point list
      - mindmap   : hierarchical topic tree
    """
    data   = request.json
    notes  = trim_text((data.get("notes") or "").strip(), max_chars=10000)
    style  = (data.get("style") or "all").strip().lower()   # brief | detailed | bullet | mindmap | all

    if not notes:
        return jsonify({"error": "Notes content is required"}), 400

    valid_styles = {"brief", "detailed", "bullet", "mindmap", "all"}
    if style not in valid_styles:
        return jsonify({"error": f"Invalid style. Choose from: {', '.join(valid_styles)}"}), 400

    prompt = f"""You are an expert academic summariser. Read the student notes below carefully and produce a rich summary.

STUDENT NOTES:
{notes}

Return ONLY a valid JSON object, no markdown, no extra text:
{{
  "title": "Auto-generated title that captures the main subject",
  "subject_area": "e.g. Biology | Computer Science | History | etc.",
  "word_count_estimate": 450,
  "brief_summary": "A crisp 2-3 sentence TL;DR of the entire notes.",
  "detailed_summary": "A thorough paragraph-style summary (6-10 sentences) covering all major ideas, concepts, and connections found in the notes.",
  "bullet_summary": [
    "Key point 1 — with enough context to be meaningful",
    "Key point 2",
    "Key point 3",
    "Key point 4",
    "Key point 5",
    "Key point 6"
  ],
  "mindmap": {{
    "root": "Central Topic",
    "branches": [
      {{
        "topic": "Branch 1",
        "subtopics": ["subtopic A", "subtopic B", "subtopic C"]
      }},
      {{
        "topic": "Branch 2",
        "subtopics": ["subtopic D", "subtopic E"]
      }},
      {{
        "topic": "Branch 3",
        "subtopics": ["subtopic F", "subtopic G", "subtopic H"]
      }}
    ]
  }},
  "key_definitions": [
    {{"term": "Term 1", "definition": "Plain-English definition"}},
    {{"term": "Term 2", "definition": "Plain-English definition"}}
  ],
  "important_dates_or_numbers": [
    {{"value": "1905", "context": "Year Einstein published the special theory of relativity"}}
  ],
  "connections": [
    "How concept A relates to concept B",
    "Why topic X is important for understanding topic Y"
  ],
  "gaps": [
    "Area that seems incomplete or missing detail",
    "Another area that could use more depth"
  ],
  "revision_tips": [
    "Practical tip 1 for studying this material",
    "Practical tip 2"
  ]
}}

Rules:
- Be accurate — only summarise what is actually in the notes
- important_dates_or_numbers may be an empty array [] if none are present
- key_definitions should list 2-6 terms; if none are defined, return []
- connections should have 2-4 items
- gaps should have 1-3 items"""

    try:
        response = call_ai(prompt, max_tokens=3000)
        result   = extract_json(response)

        # If the caller only wants a specific style, trim the response
        style_keys = {
            "brief":    ["title", "subject_area", "brief_summary"],
            "detailed": ["title", "subject_area", "detailed_summary", "key_definitions", "connections"],
            "bullet":   ["title", "subject_area", "bullet_summary", "key_definitions"],
            "mindmap":  ["title", "subject_area", "mindmap"],
        }
        if style != "all":
            result = {k: result[k] for k in style_keys[style] if k in result}

        result["style"] = style
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Summarisation failed: {str(e)}"}), 500


# ─── EXISTING ROUTES ──────────────────────────────────────────────────────────

@app.route("/api/analyze", methods=["POST"])
def analyze_notes():
    data = request.json
    notes = trim_text(data.get("notes", "").strip())
    syllabus = trim_text(data.get("syllabus", "").strip(), max_chars=2000)

    if not notes:
        return jsonify({"error": "Notes content is required"}), 400

    prompt = f"""You are a careful, evidence-based academic evaluator. Your job is to analyze student notes STRICTLY based on what is actually written in them.

CRITICAL RULES:
1. ONLY mark a topic as "missing" if there is ZERO mention of it anywhere in the notes
2. ONLY mark a topic as "partial" if it is mentioned but lacks depth or detail
3. Mark a topic as "complete" if it is clearly explained, even briefly
4. Do NOT assume topics are missing just because they aren't explained in detail
5. Re-read the notes carefully before deciding any topic is "missing"
6. If a concept is mentioned even once with some explanation, it is at minimum "partial"
7. Be GENEROUS — students often use shorthand or bullet points

STUDENT NOTES:
{notes}

SYLLABUS / EXPECTED TOPICS:
{syllabus if syllabus else "Infer key academic topics from the notes themselves and evaluate coverage depth."}

Before scoring, mentally scan the notes for each topic. Only then produce the JSON.

Return ONLY a valid JSON object, no markdown, no extra text:
{{
  "overall_score": 75,
  "completeness": 70,
  "clarity": 80,
  "structure": 75,
  "topics_covered": [
    {{"topic": "Topic Name", "status": "complete", "explanation": "briefly state what the notes say about this"}},
    {{"topic": "Topic Name", "status": "partial", "explanation": "what is present and what specific detail is missing"}},
    {{"topic": "Topic Name", "status": "missing", "explanation": "confirm it is truly absent from the notes"}}
  ],
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "improvement_suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"],
  "summary": "2-3 sentence honest summary of the notes quality"
}}"""

    try:
        response = call_ai(prompt, max_tokens=2000)
        result = extract_json(response)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@app.route("/api/flashcards", methods=["POST"])
def generate_flashcards():
    data = request.json
    notes = trim_text(data.get("notes", "").strip())

    if not notes:
        return jsonify({"error": "Notes content is required"}), 400

    prompt = f"""Generate exactly 10 academic flashcards from these student notes.

NOTES:
{notes}

Return ONLY a valid JSON array, no markdown, no extra text:
[
  {{"id": 1, "front": "Clear question", "back": "Detailed answer", "topic": "Topic name", "difficulty": "easy"}},
  {{"id": 2, "front": "question", "back": "answer", "topic": "topic", "difficulty": "medium"}},
  {{"id": 3, "front": "question", "back": "answer", "topic": "topic", "difficulty": "hard"}}
]

Rules:
- difficulty must be exactly: easy, medium, or hard
- Generate a mix of all three difficulty levels
- Test understanding, not just memorization
- Return exactly 10 items"""

    try:
        response = call_ai(prompt, max_tokens=2500)
        result = extract_json(response)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Flashcard generation failed: {str(e)}"}), 500


@app.route("/api/quiz", methods=["POST"])
def generate_quiz():
    data = request.json
    notes = trim_text(data.get("notes", "").strip())

    if not notes:
        return jsonify({"error": "Notes content is required"}), 400

    prompt = f"""Create exactly 8 multiple-choice quiz questions from these student notes.

NOTES:
{notes}

Return ONLY a valid JSON array, no markdown, no extra text:
[
  {{
    "id": 1,
    "question": "Question text?",
    "options": {{"A": "First option text", "B": "Second option text", "C": "Third option text", "D": "Fourth option text"}},
    "correct_answer": "A",
    "explanation": "Why A is correct",
    "topic": "Topic name",
    "difficulty": "easy"
  }}
]

Rules:
- correct_answer must be exactly one of: A, B, C, or D  (use key "correct_answer", NOT "correct")
- options must be a JSON object with keys A, B, C, D — NOT an array
- Do NOT include "A)" or "B)" prefixes in the option text — just the plain text
- difficulty must be exactly: easy, medium, or hard
- Include 3 easy, 3 medium, 2 hard questions
- Return exactly 8 items"""

    try:
        response = call_ai(prompt, max_tokens=2500)
        result = extract_json(response)

        letters = ["A", "B", "C", "D"]
        for q in result:
            if "correct" in q and "correct_answer" not in q:
                q["correct_answer"] = q.pop("correct")

            ca = str(q.get("correct_answer", "")).strip().upper()
            if len(ca) > 1:
                ca = ca[0]
            q["correct_answer"] = ca

            opts = q.get("options", {})
            if isinstance(opts, list):
                clean = {}
                for i, letter in enumerate(letters):
                    if i < len(opts):
                        text = re.sub(r'^[A-D][)\.\-]\s*', '', str(opts[i])).strip()
                        clean[letter] = text
                q["options"] = clean
            elif isinstance(opts, dict):
                q["options"] = {
                    k: re.sub(r'^[A-D][)\.\-]\s*', '', str(v)).strip()
                    for k, v in opts.items()
                }

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Quiz generation failed: {str(e)}"}), 500


@app.route("/api/evaluate-quiz", methods=["POST"])
def evaluate_quiz():
    data = request.json
    questions = data.get("questions", [])
    answers   = data.get("answers", {})

    if not questions:
        return jsonify({"error": "No questions provided"}), 400

    score = 0
    results = []
    weak_topics = []
    correct_topics = []

    for q in questions:
        qid = q["id"]
        user_answer = (
            answers.get(str(qid)) or answers.get(qid) or ""
        ).strip().upper()

        correct = str(q.get("correct_answer", q.get("correct", ""))).strip().upper()
        is_correct = bool(user_answer) and user_answer == correct

        if is_correct:
            score += 1
            correct_topics.append(q.get("topic", "General"))
        else:
            weak_topics.append(q.get("topic", "General"))

        results.append({
            "id": qid,
            "question": q["question"],
            "user_answer": user_answer,
            "correct_answer": correct,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
            "topic": q.get("topic", ""),
            "difficulty": q.get("difficulty", "medium")
        })

    total      = len(questions)
    percentage = round((score / total) * 100) if total > 0 else 0
    weak_unique = list(set(weak_topics))

    prompt = f"""A student scored {score}/{total} ({percentage}%) on a quiz.
Weak topics: {', '.join(weak_unique) if weak_unique else 'None'}
Strong topics: {', '.join(set(correct_topics)) if correct_topics else 'None'}

Return ONLY valid JSON, no markdown:
{{
  "performance_level": "good",
  "message": "Personalized encouraging message based on their score",
  "recommendations": ["Specific recommendation 1", "Specific recommendation 2", "Tip 3"],
  "study_plan": "Concrete 2-3 sentence study plan targeting weak areas",
  "next_steps": ["Step 1", "Step 2"]
}}

performance_level must be one of: excellent (90-100%), good (70-89%), needs_improvement (50-69%), critical (below 50%)"""

    try:
        ai_response = call_ai(prompt, max_tokens=800)
        ai_feedback = extract_json(ai_response)
    except Exception:
        level = "excellent" if percentage >= 90 else "good" if percentage >= 70 else "needs_improvement" if percentage >= 50 else "critical"
        ai_feedback = {
            "performance_level": level,
            "message": f"You scored {percentage}%. {'Great work!' if percentage >= 70 else 'Keep studying!'}",
            "recommendations": [f"Review {t}" for t in weak_unique[:3]],
            "study_plan": "Focus on weak topics and retake the quiz.",
            "next_steps": ["Re-read notes on weak topics", "Retake the quiz"]
        }

    return jsonify({
        "score": score,
        "total": total,
        "percentage": percentage,
        "results": results,
        "weak_topics": weak_unique,
        "strong_topics": list(set(correct_topics)),
        "ai_feedback": ai_feedback
    })



@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Multi-turn AI tutor chat.
    Expects: { system: str, messages: [{role, content}] }
    Returns: { reply: str }
    """
    data = request.json
    system_prompt = data.get("system", "You are Nova, a helpful AI study tutor.")
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    groq_messages = [{"role": "system", "content": system_prompt}] + [
        {"role": m["role"], "content": m["content"]}
        for m in messages[-20:]
    ]

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=groq_messages,
            max_tokens=1000,
            temperature=0.6,
        )
        reply = completion.choices[0].message.content
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": f"Chat failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)