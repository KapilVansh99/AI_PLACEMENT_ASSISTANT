import os
import random
import io
import PyPDF2
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "a_very_secret_key_12345")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# --- Database Helper ---
def get_db_connection():
    # Render par path issue na ho isliye absolute path use kar rahe hain
    db_path = os.path.join(os.path.dirname(__file__), "users.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()
    print("✅ Database initialized and table created!")

# App start hote hi table banana
init_db()

# --- User Model ---
class User(UserMixin):
    def __init__(self, id, email, password):
        self.id = id
        self.email = email
        self.password = password

    @staticmethod
    def get(user_id):
        conn = get_db_connection()
        user_data = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        if user_data:
            return User(user_data["id"], user_data["email"], user_data["password"])
        return None

    @staticmethod
    def get_by_email(email):
        conn = get_db_connection()
        user_data = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user_data:
            return User(user_data["id"], user_data["email"], user_data["password"])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

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
            print("Error: GROQ_API_KEY not found!")

    def generate(self, system_prompt, user_prompt):
        if not self.client: return None
        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.7, max_tokens=1024
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"AI Error: {e}")
            return None

ai_assistant = AIProvider()

# --- Fallback Data ---
fallback_questions = {
    "data analyst": ["What is data cleaning?", "Explain SQL joins.", "What is a pivot table?"],
    "python developer": ["List vs Tuple?", "What are decorators?", "Explain GIL."],
    "web developer": ["CSS Box Model?", "JS Promises?", "What is DOM?"],
    "aptitude": ["Train speed 60km/h, 240km distance?", "A=10 days, B=15 days, together?"],
    "coding": ["Reverse a string in Python.", "Check prime number in JS."]
}

# --- Routes ---
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
        try:
            conn = get_db_connection()
            conn.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_pw))
            conn.commit()
            conn.close()
            flash("Account created! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already exists.", "error")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.get_by_email(email)
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid credentials.", "error")
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/ai", methods=["GET", "POST"])
@login_required
def ai():
    questions, result = [], ""
    if request.method == "POST":
        role = request.form.get("role", "")
        ai_res = ai_assistant.generate("Generate 20 interview questions.", f"Role: {role}")
        if ai_res:
            questions = [q.strip() for q in ai_res.split("\n") if q.strip()][:20]
            result = f"AI Generated {len(questions)} questions."
        else:
            questions = fallback_questions.get(role, ["No questions."])
            result = "AI Failed. Showing fallback."
    return render_template("ai.html", questions=questions, result=result)

@app.route("/roadmap", methods=["GET", "POST"])
@login_required
def roadmap():
    roadmap_data, role = "", ""
    if request.method == "POST":
        role = request.form.get("role", "")
        roadmap_data = ai_assistant.generate("Create a career roadmap.", f"Role: {role}") or "AI Failed."
    return render_template("roadmap.html", roadmap=roadmap_data, role=role)

@app.route("/skill-gap", methods=["GET", "POST"])
@login_required
def skill_gap():
    analysis, role, skills = "", "", ""
    if request.method == "POST":
        role, skills = request.form.get("role", ""), request.form.get("skills", "")
        analysis = ai_assistant.generate("Analyze skill gap.", f"Role: {role}, Skills: {skills}") or "AI Failed."
    return render_template("skill_gap.html", analysis=analysis, role=role, skills=skills)

@app.route("/resume", methods=["GET", "POST"])
@login_required
def resume():
    analysis = ""
    if request.method == "POST":
        role, file = request.form.get("role", ""), request.files.get("resume")
        if file:
            pdf = PyPDF2.PdfReader(file)
            text = "".join([p.extract_text() for p in pdf.pages])
            analysis = ai_assistant.generate("Analyze resume.", f"Role: {role}, Text: {text}") or "AI Failed."
    return render_template("resume.html", analysis=analysis)

@app.route("/jd-matcher", methods=["GET", "POST"])
@login_required
def jd_matcher():
    analysis = ""
    if request.method == "POST":
        jd, skills = request.form.get("jd", ""), request.form.get("skills", "")
        analysis = ai_assistant.generate("Match JD and Skills.", f"JD: {jd}, Skills: {skills}") or "AI Failed."
    return render_template("jd_matcher.html", analysis=analysis)

@app.route("/aptitude", methods=["GET", "POST"])
@login_required
def aptitude():
    questions, topic = [], ""
    if request.method == "POST":
        topic = request.form.get("topic", "General")
        ai_res = ai_assistant.generate("Generate 10 aptitude questions.", f"Topic: {topic}")
        questions = [q.strip() for q in ai_res.split("\n") if q.strip()] if ai_res else fallback_questions["aptitude"]
    return render_template("aptitude.html", questions=questions, topic=topic)

@app.route("/coding-quiz", methods=["GET", "POST"])
@login_required
def coding_quiz():
    quiz_text, lang = "", ""
    if request.method == "POST":
        lang = request.form.get("lang", "Python")
        quiz_text = ai_assistant.generate("Generate 5 coding questions.", f"Lang: {lang}") or "AI Failed."
    return render_template("coding_quiz.html", quiz_text=quiz_text, lang=lang)

@app.route("/readiness", methods=["GET", "POST"])
@login_required
def readiness():
    score_data = ""
    if request.method == "POST":
        r, a, i = request.form.get("resume_score", 0), request.form.get("aptitude_score", 0), request.form.get("interview_score", 0)
        score_data = ai_assistant.generate("Calculate readiness.", f"R:{r}, A:{a}, I:{i}") or "AI Failed."
    return render_template("readiness.html", score_data=score_data)

@app.route("/voice-feedback", methods=["POST"])
@login_required
def voice_feedback():
    data = request.get_json()
    fb = ai_assistant.generate("Evaluate interview answer.", f"Q: {data['question']}, A: {data['answer']}") or "AI Failed."
    return jsonify({"feedback": fb})

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
