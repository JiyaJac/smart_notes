from flask import Flask, render_template, request, jsonify
from groq import Groq
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG ───────────────────────────────────────────────────────────────────
MAX_NOTES_CHARS    = 10_000
MAX_SYLLABUS_CHARS = 2_000
MAX_SUMMARY_CHARS  = 8_000
MAX_FC_CHARS       = 6_000

api_key = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=api_key)
app = Flask(__name__)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

BASE_KEYWORDS = [
    "definition", "define", "defined as", "means", "refers to", "is called",
    "known as", "also called", "termed", "described as",
    "important", "key", "critical", "essential", "significant", "notable",
    "note that", "remember", "must know", "crucial", "fundamental", "core",
    "primary", "main", "major", "vital",
    "theorem", "formula", "equation", "law", "principle", "rule", "axiom",
    "postulate", "theory", "hypothesis", "model", "framework", "concept",
    "algorithm", "proof", "derivation", "lemma", "corollary",
    "example", "e.g", "i.e", "for instance", "such as", "namely",
    "therefore", "thus", "hence", "it follows", "consequently",
    "as a result", "which means", "this shows", "this proves",
    "because", "since", "due to", "caused by", "leads to", "results in",
    "effect", "cause", "impact", "influence", "relationship", "correlation",
    "depends on", "determined by", "affects",
    "step", "process", "method", "procedure", "technique", "approach",
    "function", "purpose", "role", "mechanism", "operation", "workflow",
    "difference", "compare", "contrast", "similar", "unlike", "whereas",
    "however", "on the other hand", "advantage", "disadvantage", "benefit",
    "drawback", "limitation", "versus", "vs",
    "conclusion", "summary", "in summary", "overall", "in conclusion",
    "to summarize", "finally", "in brief",
    "type", "kind", "category", "class", "group", "form", "variant",
    "classification", "taxonomy", "hierarchy",
    "approximately", "equals", "percent", "%", "ratio", "rate", "value",
    "measured", "calculated", "estimated",
]

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "this", "that",
    "these", "those", "it", "its", "as", "if", "so", "not", "no", "nor",
    "yet", "both", "either", "neither", "each", "few", "more", "most",
    "other", "some", "such", "than", "then", "when", "where", "which",
    "who", "whom", "how", "all", "any", "between", "into", "through",
    "during", "before", "after", "above", "below", "up", "down", "out",
    "about", "per", "their", "they", "we", "you", "he", "she", "his",
    "her", "our", "your", "my", "me", "him", "us", "them",
}


def extract_syllabus_keywords(syllabus):
    if not syllabus or not syllabus.strip():
        return []
    keywords = set()
    for line in syllabus.splitlines():
        clean = re.sub(r'^\s*[\-\*\•\d\.\)]+\s*', '', line).strip()
        if not clean:
            continue
        tokens = re.findall(r"[a-zA-Z']+", clean.lower())
        for tok in tokens:
            if len(tok) >= 4 and tok not in _STOP_WORDS:
                keywords.add(tok)
        for n in (2, 3):
            for i in range(len(tokens) - n + 1):
                phrase = " ".join(tokens[i:i + n])
                if any(t not in _STOP_WORDS and len(t) >= 4 for t in tokens[i:i + n]):
                    keywords.add(phrase)
    return list(keywords)


def smart_trim(text, max_chars, syllabus=''):
    text = text.strip()
    if len(text) <= max_chars:
        return text

    syllabus_keywords = extract_syllabus_keywords(syllabus)
    raw_lines = re.split(r'(?<=[.!?])\s+|\n+', text)
    lines = [l.strip() for l in raw_lines if l.strip()]

    if not lines:
        return text[:max_chars]

    def score_line(line):
        lower = line.lower()
        syllabus_hits = sum(1 for kw in syllabus_keywords if kw in lower)
        base_hits     = sum(1 for kw in BASE_KEYWORDS if kw in lower)
        length_bonus  = min(len(line), 300) / 300
        return syllabus_hits * 5 + base_hits * 2 + length_bonus

    scored_lines = [(i, line, score_line(line)) for i, line in enumerate(lines)]

    spread_budget   = int(max_chars * 0.60)
    priority_budget = max_chars - spread_budget

    chunk_size = max(20, len(lines) // 20)
    chunks = [scored_lines[i:i + chunk_size] for i in range(0, len(scored_lines), chunk_size)]

    selected_indices = set()
    selected = []
    total_chars = 0

    for chunk in chunks:
        if not chunk or total_chars >= spread_budget:
            break
        best = max(chunk, key=lambda x: x[2])
        i, line, score = best
        needed = len(line) + 1
        if total_chars + needed <= spread_budget:
            selected.append((i, line))
            selected_indices.add(i)
            total_chars += needed

    remaining_lines = [(i, line, score) for i, line, score in scored_lines
                       if i not in selected_indices]
    remaining_lines.sort(key=lambda x: x[2], reverse=True)

    remaining_budget = max_chars - total_chars
    for i, line, score in remaining_lines:
        if remaining_budget <= 0:
            break
        needed = len(line) + 1
        if needed <= remaining_budget:
            selected.append((i, line))
            remaining_budget -= needed
        elif remaining_budget > 80 and score > 3:
            selected.append((i, line[:remaining_budget].rstrip()))
            remaining_budget = 0

    selected.sort(key=lambda x: x[0])
    return '\n'.join(line for _, line in selected)


def get_notes_from_request():
    data = request.get_json(silent=True) or {}
    syllabus = data.get("syllabus", "").strip()
    notes = smart_trim(data.get("notes", "").strip(), MAX_NOTES_CHARS, syllabus=syllabus)
    return data, notes


# ─── AI CALL ──────────────────────────────────────────────────────────────────
def call_ai(prompt, max_tokens=800, temperature=0.3):
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert academic assistant. "
                    "Always respond with valid JSON only — "
                    "no markdown, no explanation, no extra text."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=30.0,
    )
    return completion.choices[0].message.content


def extract_json(text):
    text = text.strip()
    for pattern in [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'(\[[\s\S]*\]|\{[\s\S]*\})',
    ]:
        match = re.search(pattern, text)
        if match:
            return json.loads(match.group(1))
    return json.loads(text)


# ─── PROMPT BUILDERS ──────────────────────────────────────────────────────────
def build_analyze_prompt(notes, syllabus):
    syllabus_section = (
        syllabus
        if syllabus
        else "Infer key academic topics from the notes themselves and evaluate coverage depth."
    )
    return f"""You are a careful, evidence-based academic evaluator. Your job is to analyze student notes STRICTLY based on what is actually written in them.

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
{syllabus_section}

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


def build_flashcard_prompt(notes):
    return f"""Generate exactly 10 academic flashcards from these student notes.

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


def build_quiz_prompt(notes):
    return f"""Create exactly 8 multiple-choice quiz questions from these student notes.
The questions should test understanding of key concepts, not just recall. Each question must have 4 options (A, B, C, D) with only one correct answer.
They should have different questions each time, even with the same notes. Include a mix of easy, medium, and hard questions.

NOTES:
{notes}

Return ONLY a valid JSON array, no markdown, no extra text:
[
  {{
    "id": 1,
    "question": "Question text?",
    "options": ["A) Option one", "B) Option two", "C) Option three", "D) Option four"],
    "correct_answer": "A",
    "explanation": "Why A is correct",
    "topic": "Topic name",
    "difficulty": "easy"
  }}
]

Rules:
- correct_answer must be exactly one of: A, B, C, or D
- difficulty must be exactly: easy, medium, or hard
- Include 3 easy, 3 medium, 2 hard questions
- Return exactly 8 items"""


def build_evaluate_prompt(score, total, percentage, weak_unique, correct_topics):
    return f"""A student scored {score}/{total} ({percentage}%) on a quiz.
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


def build_summary_prompt(style, notes_excerpt, word_count):
    if style == "brief":
        return f"""Summarize these student notes in a concise TL;DR (4-6 sentences).

NOTES:
{notes_excerpt}

Return ONLY valid JSON:
{{
  "style": "brief",
  "title": "Short descriptive title for these notes",
  "subject_area": "Subject or module name",
  "word_count_estimate": {word_count},
  "brief_summary": "Your 4-6 sentence TL;DR here"
}}"""

    elif style == "detailed":
        return f"""Write a detailed comprehensive summary of these student notes.

NOTES:
{notes_excerpt}

Return ONLY valid JSON:
{{
  "style": "detailed",
  "title": "Short descriptive title",
  "subject_area": "Subject or module name",
  "word_count_estimate": {word_count},
  "brief_summary": "2-sentence overview",
  "detailed_summary": "Full detailed summary in 2-4 paragraphs covering all key concepts",
  "connections": ["How concept A connects to B", "How X relates to Y"]
}}"""

    elif style == "bullet":
        return f"""Extract the most important points from these student notes as bullet points plus key definitions.

NOTES:
{notes_excerpt}

Return ONLY valid JSON:
{{
  "style": "bullet",
  "title": "Short descriptive title",
  "subject_area": "Subject or module name",
  "word_count_estimate": {word_count},
  "brief_summary": "1-2 sentence overview",
  "bullet_summary": ["Key point 1", "Key point 2", "Key point 3", "Key point 4", "Key point 5", "Key point 6", "Key point 7", "Key point 8"],
  "key_definitions": [
    {{"term": "Term name", "definition": "Clear definition from the notes"}},
    {{"term": "Term 2", "definition": "Definition"}}
  ]
}}"""

    elif style == "mindmap":
        return f"""Create a structured mind map from these student notes.

NOTES:
{notes_excerpt}

Return ONLY valid JSON:
{{
  "style": "mindmap",
  "title": "Short descriptive title",
  "subject_area": "Subject or module name",
  "word_count_estimate": {word_count},
  "brief_summary": "1-2 sentence overview",
  "mindmap": {{
    "root": "Central topic name",
    "branches": [
      {{"topic": "Branch 1", "subtopics": ["subtopic a", "subtopic b", "subtopic c"]}},
      {{"topic": "Branch 2", "subtopics": ["subtopic a", "subtopic b"]}}
    ]
  }}
}}

Generate 4-7 branches with 2-5 subtopics each."""

    else:  # "all"
        return f"""Create a comprehensive summary report of these student notes.

NOTES:
{notes_excerpt}

Return ONLY valid JSON (no markdown):
{{
  "style": "all",
  "title": "Descriptive title for these notes",
  "subject_area": "Subject or module name",
  "word_count_estimate": {word_count},
  "brief_summary": "Concise 3-4 sentence TL;DR",
  "detailed_summary": "Full detailed summary in 2-3 paragraphs",
  "bullet_summary": ["Key point 1", "Key point 2", "Key point 3", "Key point 4", "Key point 5", "Key point 6", "Key point 7", "Key point 8"],
  "key_definitions": [
    {{"term": "Term", "definition": "Definition from notes"}},
    {{"term": "Term 2", "definition": "Definition"}}
  ],
  "mindmap": {{
    "root": "Central topic",
    "branches": [
      {{"topic": "Branch 1", "subtopics": ["sub a", "sub b", "sub c"]}},
      {{"topic": "Branch 2", "subtopics": ["sub a", "sub b"]}}
    ]
  }},
  "connections": ["How concept A connects to B", "Relationship between X and Y"],
  "important_dates_or_numbers": [
    {{"value": "1994", "context": "Year something was introduced"}},
    {{"value": "7", "context": "Number of software types"}}
  ],
  "gaps": ["Topic X is mentioned but not explained", "Missing examples for Y"],
  "revision_tips": ["Tip 1", "Tip 2", "Tip 3"]
}}

Generate 4-6 branches in the mindmap."""


# ─── ROUTES ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze_notes():
    data, notes = get_notes_from_request()
    if not notes:
        return jsonify({"error": "Notes content is required"}), 400

    syllabus = smart_trim(data.get("syllabus", "").strip(), MAX_SYLLABUS_CHARS)
    prompt = build_analyze_prompt(notes, syllabus)

    try:
        response = call_ai(prompt, max_tokens=2000)
        result = extract_json(response)
        return jsonify(result)
    except Exception as e:
        app.logger.error("analyze error: %s", e)
        return jsonify({"error": "Analysis failed. Please try again."}), 500


@app.route("/api/flashcards", methods=["POST"])
def generate_flashcards():
    _, notes = get_notes_from_request()
    if not notes:
        return jsonify({"error": "Notes content is required"}), 400

    notes = smart_trim(notes, MAX_FC_CHARS)
    prompt = build_flashcard_prompt(notes)

    try:
        response = call_ai(prompt, max_tokens=2500)
        result = extract_json(response)
        return jsonify(result)
    except Exception as e:
        app.logger.error("flashcard error: %s", e)
        return jsonify({"error": "Flashcard generation failed. Please try again."}), 500


@app.route("/api/quiz", methods=["POST"])
def generate_quiz():
    _, notes = get_notes_from_request()
    if not notes:
        return jsonify({"error": "Notes content is required"}), 400

    prompt = build_quiz_prompt(notes)

    try:
        response = call_ai(prompt, max_tokens=2500)
        result = extract_json(response)
        return jsonify(result)
    except Exception as e:
        app.logger.error("quiz error: %s", e)
        return jsonify({"error": "Quiz generation failed. Please try again."}), 500


@app.route("/api/evaluate-quiz", methods=["POST"])
def evaluate_quiz():
    data = request.get_json(silent=True) or {}
    questions = data.get("questions", [])
    answers = data.get("answers", {})

    if not questions:
        return jsonify({"error": "No questions provided"}), 400

    score = 0
    results = []
    weak_topics = []
    correct_topics = []

    for q in questions:
        qid = str(q["id"])
        user_answer = answers.get(qid, "").strip().upper()
        correct = q.get("correct_answer", "").strip().upper()
        is_correct = user_answer == correct

        if is_correct:
            score += 1
            correct_topics.append(q.get("topic", "General"))
        else:
            weak_topics.append(q.get("topic", "General"))

        results.append({
            "id": q["id"],
            "question": q["question"],
            "user_answer": user_answer,
            "correct_answer": correct,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
            "topic": q.get("topic", ""),
            "difficulty": q.get("difficulty", "medium"),
        })

    total = len(questions)
    percentage = round((score / total) * 100) if total > 0 else 0
    weak_unique = list(set(weak_topics))

    prompt = build_evaluate_prompt(score, total, percentage, weak_unique, correct_topics)

    try:
        ai_response = call_ai(prompt, max_tokens=800)
        ai_feedback = extract_json(ai_response)
    except Exception:
        level = (
            "excellent" if percentage >= 90
            else "good" if percentage >= 70
            else "needs_improvement" if percentage >= 50
            else "critical"
        )
        ai_feedback = {
            "performance_level": level,
            "message": f"You scored {percentage}%. {'Great work!' if percentage >= 70 else 'Keep studying!'}",
            "recommendations": [f"Review {t}" for t in weak_unique[:3]],
            "study_plan": "Focus on weak topics and retake the quiz.",
            "next_steps": ["Re-read notes on weak topics", "Retake the quiz"],
        }

    return jsonify({
        "score": score,
        "total": total,
        "percentage": percentage,
        "results": results,
        "weak_topics": weak_unique,
        "strong_topics": list(set(correct_topics)),
        "ai_feedback": ai_feedback,
    })


@app.route("/api/summarize", methods=["POST"])
def summarize_notes():
    data, notes = get_notes_from_request()
    if not notes:
        return jsonify({"error": "Notes content is required"}), 400

    style = data.get("style", "all")
    notes_excerpt = smart_trim(notes, MAX_SUMMARY_CHARS)
    word_count = len(notes.split())
    prompt = build_summary_prompt(style, notes_excerpt, word_count)

    try:
        response = call_ai(prompt, max_tokens=3000, temperature=0.2)
        result = extract_json(response)
        return jsonify(result)
    except Exception as e:
        app.logger.error("summary error: %s", e)
        return jsonify({"error": "Summary generation failed. Please try again."}), 500


# ─── AI CHAT ROUTE (Nova Assistant) ──────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def ai_chat():
    """
    Powers the Nova AI tutor chat panel.
    Expects: { "system": "...", "messages": [{"role": "user"|"assistant", "content": "..."}] }
    Returns: { "reply": "..." }
    """
    data = request.get_json(silent=True) or {}
    system_prompt = data.get("system", "You are Nova, a friendly AI study tutor. Help students understand topics clearly and encouragingly.")
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    # Sanitize messages — only keep role/content, valid roles only
    clean_messages = []
    for msg in messages[-20:]:  # limit context to last 20 messages
        role = msg.get("role", "")
        content = str(msg.get("content", "")).strip()
        if role in ("user", "assistant") and content:
            clean_messages.append({"role": role, "content": content})

    if not clean_messages:
        return jsonify({"error": "No valid messages provided"}), 400

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                *clean_messages,
            ],
            max_tokens=1000,
            temperature=0.6,
            timeout=30.0,
        )
        reply = completion.choices[0].message.content.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        app.logger.error("chat error: %s", e)
        return jsonify({"error": f"Chat failed: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)