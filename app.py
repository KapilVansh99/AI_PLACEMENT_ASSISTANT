import os
import random
import io
import PyPDF2
from flask import Flask, render_template, request
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# --- AI Provider Class ---
class AIProvider:
    def __init__(self, api_type="groq"):
        self.api_type = api_type
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            self.client = Groq(api_key=api_key)
        else:
            print("Error: GROQ_API_KEY not found in .env!")

    def generate(self, system_prompt, user_prompt):
        if not self.client:
            return None
        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"AI Error Detail: {e}")
            return None

ai_assistant = AIProvider(api_type="groq")

# --- Routes ---
@app.route("/")
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/ai", methods=["GET", "POST"])
def ai():
    questions = []
    result = ""
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        if role:
            system_p = "You are an AI Interview Assistant. Generate 20 unique interview questions for the given role. Give only questions, one per line, no numbers."
            user_p = f"Generate 20 interview questions for a {role}."
            ai_response = ai_assistant.generate(system_p, user_p)
            if ai_response:
                questions = [q.strip() for q in ai_response.split("\n") if q.strip()][:20]
                result = f"Generated {len(questions)} questions for {role.title()}."
            else:
                result = "AI failed. Try again."
    return render_template("ai.html", questions=questions, result=result)

@app.route("/roadmap", methods=["GET", "POST"])
def roadmap():
    roadmap_data = ""
    role = ""
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        system_p = "Create a detailed career roadmap for the given role using Markdown."
        roadmap_data = ai_assistant.generate(system_p, f"Roadmap for {role}")
    return render_template("roadmap.html", roadmap=roadmap_data, role=role)

@app.route("/skill-gap", methods=["GET", "POST"])
def skill_gap():
    analysis = ""
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        skills = request.form.get("skills", "").strip()
        system_p = "Analyze the skill gap for the target role and suggest improvements using Markdown."
        analysis = ai_assistant.generate(system_p, f"Role: {role}, My Skills: {skills}")
    return render_template("skill_gap.html", analysis=analysis)

@app.route("/resume", methods=["GET", "POST"])
def resume():
    analysis = ""
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        file = request.files.get("resume")
        if file and role:
            pdf_reader = PyPDF2.PdfReader(file)
            text = "".join([p.extract_text() for p in pdf_reader.pages])
            system_p = f"Analyze this resume for a {role} position. Give ATS score and suggestions in Markdown."
            analysis = ai_assistant.generate(system_p, text)
    return render_template("resume.html", analysis=analysis)

@app.route("/jd-matcher", methods=["GET", "POST"])
def jd_matcher():
    analysis = ""
    if request.method == "POST":
        jd = request.form.get("jd", "").strip()
        skills = request.form.get("skills", "").strip()
        system_p = "Match the JD with skills and give percentage and missing skills in Markdown."
        analysis = ai_assistant.generate(system_p, f"JD: {jd}, Skills: {skills}")
    return render_template("jd_matcher.html", analysis=analysis)

@app.route("/aptitude", methods=["GET", "POST"])
def aptitude():
    questions = []
    if request.method == "POST":
        topic = request.form.get("topic", "General").strip()
        system_p = "Generate 10 aptitude questions for the topic in Markdown."
        ai_response = ai_assistant.generate(system_p, topic)
        if ai_response: questions = [ai_response]
    return render_template("aptitude.html", questions=questions)

@app.route("/coding-quiz", methods=["GET", "POST"])
def coding_quiz():
    quiz_text = ""
    if request.method == "POST":
        lang = request.form.get("lang", "Python").strip()
        system_p = "Generate 5 coding questions for the language in Markdown."
        quiz_text = ai_assistant.generate(system_p, lang)
    return render_template("coding_quiz.html", quiz_text=quiz_text)

@app.route("/readiness", methods=["GET", "POST"])
def readiness():
    score_data = ""
    if request.method == "POST":
        r = request.form.get("resume_score", 0)
        a = request.form.get("aptitude_score", 0)
        i = request.form.get("interview_score", 0)
        system_p = "Calculate placement readiness based on these scores and give a report in Markdown."
        score_data = ai_assistant.generate(system_p, f"Resume: {r}, Aptitude: {a}, Interview: {i}")
    return render_template("readiness.html", score_data=score_data)

@app.route("/logout")
def logout(): return "Logged out!"

if __name__ == "__main__":
    app.run(debug=True)
