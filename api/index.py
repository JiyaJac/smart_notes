from flask import Flask, render_template, request, jsonify
import json
import os
import re
import urllib.request


print("HF KEY:", os.environ.get("HUGGINGFACE_API_KEY"))

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, template_folder="../templates")

ANTHROPIC_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")


def call_ai(prompt, max_tokens=500):
    url = "https://api-inference.huggingface.co/models/google/flan-t5-large"

    headers = {
        "Authorization": f"Bearer {os.environ.get('HUGGINGFACE_API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_tokens
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers
    )

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())

    return result[0]["generated_text"]


def extract_json(text):
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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze_notes():
    data = request.json
    notes = data.get("notes", "").strip()
    syllabus = data.get("syllabus", "").strip()

    if not notes:
        return jsonify({"error": "Notes content is required"}), 400

    prompt = f"""You are an expert academic evaluator. Analyze the student notes below against the provided syllabus topics.

STUDENT NOTES:
{notes}

SYLLABUS / EXPECTED TOPICS:
{syllabus if syllabus else "Infer key academic topics from the notes themselves and evaluate coverage depth."}

Return ONLY a valid JSON object with NO markdown formatting, NO extra text:
{{
  "overall_score": 75,
  "completeness": 70,
  "clarity": 80,
  "structure": 75,
  "topics_covered": [
    {{"topic": "Topic Name", "status": "complete", "explanation": "brief assessment"}},
    {{"topic": "Topic Name", "status": "partial", "explanation": "what is missing"}},
    {{"topic": "Topic Name", "status": "missing", "explanation": "not covered at all"}}
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
    notes = data.get("notes", "").strip()

    if not notes:
        return jsonify({"error": "Notes content is required"}), 400

    prompt = f"""Generate 10 high-quality academic flashcards from these student notes for active recall study.

NOTES:
{notes}

Return ONLY a valid JSON array (NO markdown, NO extra text):
[
  {{"id": 1, "front": "Clear question", "back": "Detailed answer", "topic": "Topic name", "difficulty": "easy"}},
  {{"id": 2, "front": "...", "back": "...", "topic": "...", "difficulty": "medium"}},
  {{"id": 3, "front": "...", "back": "...", "topic": "...", "difficulty": "hard"}}
]

Rules: difficulty must be easy/medium/hard. Mix all levels. Test understanding not memorization."""

    try:
        response = call_ai(prompt, max_tokens=2500)
        result = extract_json(response)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Flashcard generation failed: {str(e)}"}), 500


@app.route("/api/quiz", methods=["POST"])
def generate_quiz():
    data = request.json
    notes = data.get("notes", "").strip()

    if not notes:
        return jsonify({"error": "Notes content is required"}), 400

    prompt = f"""Create 8 multiple-choice quiz questions from these student notes.

NOTES:
{notes}

Return ONLY a valid JSON array (NO markdown, NO extra text):
[
  {{
    "id": 1,
    "question": "Question text?",
    "options": ["A) Option one", "B) Option two", "C) Option three", "D) Option four"],
    "correct": "A",
    "explanation": "Why A is correct",
    "topic": "Topic name",
    "difficulty": "easy"
  }}
]

Rules: correct must be A/B/C/D. difficulty must be easy/medium/hard. Include 3 easy, 3 medium, 2 hard."""

    try:
        response = call_ai(prompt, max_tokens=2500)
        result = extract_json(response)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Quiz generation failed: {str(e)}"}), 500


@app.route("/api/evaluate-quiz", methods=["POST"])
def evaluate_quiz():
    data = request.json
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
        correct = q.get("correct", "").strip().upper()
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
            "difficulty": q.get("difficulty", "medium")
        })

    total = len(questions)
    percentage = round((score / total) * 100) if total > 0 else 0
    weak_unique = list(set(weak_topics))

    prompt = f"""Student quiz results: {score}/{total} ({percentage}%)
Weak topics: {', '.join(weak_unique) if weak_unique else 'None'}
Strong topics: {', '.join(set(correct_topics)) if correct_topics else 'None'}

Return ONLY valid JSON (NO markdown):
{{
  "performance_level": "good",
  "message": "Personalized encouraging message",
  "recommendations": ["Specific recommendation 1", "Specific recommendation 2", "Tip 3"],
  "study_plan": "Concrete 2-3 sentence study plan",
  "next_steps": ["Step 1", "Step 2"]
}}
performance_level: excellent(90-100%), good(70-89%), needs_improvement(50-69%), critical(below 50%)"""

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
        "score": score, "total": total, "percentage": percentage,
        "results": results, "weak_topics": weak_unique,
        "strong_topics": list(set(correct_topics)), "ai_feedback": ai_feedback
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
