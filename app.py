import os
import random
import io
import PyPDF2
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# ===== DATABASE CONFIGURATION =====
# Use PostgreSQL from environment variable (Supabase)
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    # Fix deprecated postgres:// scheme
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "a_very_secret_key_12345")

# Initialize Database
db = SQLAlchemy(app)

# ===== USER MODEL =====
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

# ===== AI PROVIDER CLASS =====
class AIProvider:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-70b-versatile"

    def generate(self, prompt, context=""):
        try:
            full_prompt = f"{context}\n{prompt}" if context else prompt
            message = self.client.chat.completions.create(
                messages=[{"role": "user", "content": full_prompt}],
                model=self.model,
                max_tokens=1000,
            )
            return message.choices[0].message.content
        except Exception as e:
            print(f"AI Error: {e}")
            return None

# Initialize AI
ai_assistant = AIProvider(os.environ.get("GROQ_API_KEY", ""))

# ===== ROUTES =====

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not email or not password or not confirm_password:
            flash("All fields are required!", "error")
            return redirect(url_for("signup"))

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for("signup"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists! Please login.", "error")
            return redirect(url_for("login"))

        # Create new user
        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {email}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password!", "error")

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/ai", methods=["GET", "POST"])
@login_required
def ai():
    questions = []
    result = ""

    if request.method == "POST":
        role = request.form.get("role", "").strip()
        
        if not role:
            result = "Please select a profession."
        else:
            prompt = f"Generate 20 professional interview questions for a {role} position. Format as a numbered list."
            ai_response = ai_assistant.generate(prompt)

            if ai_response:
                questions = [q.strip() for q in ai_response.split("\n") if q.strip()][:20]
                result = f"Successfully generated {len(questions)} questions for {role.title()}."
            else:
                result = "AI generation failed. Please try again."

    return render_template("ai.html", questions=questions, result=result)

@app.route("/voice-feedback", methods=["POST"])
@login_required
def voice_feedback():
    data = request.get_json()
    question = data.get("question", "")
    answer = data.get("answer", "")
    role = data.get("role", "")
    
    prompt = f"The candidate is interviewing for a {role} position.\nQuestion: {question}\nCandidate's Answer: {answer}\n\nProvide constructive feedback on their answer (2-3 sentences)."
    feedback = ai_assistant.generate(prompt) or "Could not generate feedback. Please try again."
    
    return jsonify({"feedback": feedback})

@app.route("/roadmap", methods=["GET", "POST"])
@login_required
def roadmap():
    roadmap_content = ""
    role = ""
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        prompt = f"Create a detailed 6-month learning roadmap for a {role}. Include key skills, technologies, and milestones."
        roadmap_content = ai_assistant.generate(prompt) or "Roadmap generation failed."
    return render_template("roadmap.html", roadmap=roadmap_content, role=role)

@app.route("/skill-gap", methods=["GET", "POST"])
@login_required
def skill_gap():
    analysis = ""
    role = ""
    skills = ""
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        skills = request.form.get("skills", "").strip()
        prompt = f"Analyze skill gaps for a {role} position. Current skills: {skills}. Provide recommendations."
        analysis = ai_assistant.generate(prompt) or "Analysis failed."
    return render_template("skill_gap.html", analysis=analysis, role=role, skills=skills)

@app.route("/resume", methods=["GET", "POST"])
@login_required
def resume():
    analysis = ""
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        file = request.files.get("resume")
        if file and role:
            try:
                pdf_reader = PyPDF2.PdfReader(file)
                resume_text = ""
                for page in pdf_reader.pages:
                    resume_text += page.extract_text()
                
                prompt = f"Analyze this resume for a {role} position. Provide strengths, weaknesses, and suggestions.\n\nResume: {resume_text}"
                analysis = ai_assistant.generate(prompt) or "Analysis failed."
            except Exception as e:
                print(f"Resume Error: {e}")
                analysis = "Error reading PDF. Make sure it's a valid PDF file."
        else:
            analysis = "Please provide both a target role and a resume file."
    return render_template("resume.html", analysis=analysis)

@app.route("/jd-matcher", methods=["GET", "POST"])
@login_required
def jd_matcher():
    analysis = ""
    if request.method == "POST":
        jd = request.form.get("jd", "").strip()
        skills = request.form.get("skills", "").strip()
        
        if not jd or not skills:
            analysis = "Please provide both Job Description and your skills."
        else:
            prompt = f"Match the following job description with the user's skills. Provide a match percentage and insights.\n\nJob Description: {jd}\n\nUser Skills: {skills}"
            analysis = ai_assistant.generate(prompt) or "Matching failed."
    return render_template("jd_matcher.html", analysis=analysis)

@app.route("/aptitude", methods=["GET", "POST"])
@login_required
def aptitude():
    questions = []
    topic = ""
    if request.method == "POST":
        topic = request.form.get("topic", "General")
        prompt = f"Generate 5 aptitude test questions for {topic}. Format as numbered questions with options (A, B, C, D)."
        result = ai_assistant.generate(prompt) or "Generation failed."
        questions = result.split('\n') if result else []
    return render_template("aptitude.html", questions=questions, topic=topic)

@app.route("/coding-quiz", methods=["GET", "POST"])
@login_required
def coding_quiz():
    quiz_text = ""
    lang = ""
    if request.method == "POST":
        lang = request.form.get("lang", "Python")
        prompt = f"Generate 5 coding questions for {lang}. Include problem statements and expected outputs."
        quiz_text = ai_assistant.generate(prompt) or "Quiz generation failed."
    return render_template("coding_quiz.html", quiz_text=quiz_text, lang=lang)

@app.route("/readiness", methods=["GET", "POST"])
@login_required
def readiness():
    score_data = ""
    if request.method == "POST":
        r = request.form.get("resume_score", "0")
        a = request.form.get("aptitude_score", "0")
        i = request.form.get("interview_score", "0")
        prompt = f"Calculate overall placement readiness score based on: Resume Score: {r}/100, Aptitude: {a}/100, Interview: {i}/100. Provide feedback."
        score_data = ai_assistant.generate(prompt) or "Calculation failed."
    return render_template("readiness.html", score_data=score_data)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
