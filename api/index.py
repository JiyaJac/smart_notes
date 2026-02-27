from flask import Flask, render_template, request, jsonify
from groq import Groq
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

if not os.environ.get("GROQ_API_KEY"):
    raise Exception("❌ GROQ_API_KEY not found in .env")

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

app = Flask(__name__, template_folder="../templates")


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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze_notes():
    data = request.json
    notes = trim_text(data.get("notes", "").strip(), max_chars=10000)    
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
        # FIX: changed "correct" to "correct_answer"
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
            "correct_answer": correct,  # Also fix this key for consistency
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
            "topic": q.get("topic", ""),
            "difficulty": q.get("difficulty", "medium")
        })

    total = len(questions)
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
