import os
import random
import io
import PyPDF2
from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# --- AI Provider Class (Flexible Architecture) ---
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
            # Latest Stable Model
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

# AI initialize kr diya
ai_assistant = AIProvider(api_type="groq")

# --- Fallback Question Bank (for when AI fails) ---
fallback_questions = {
    "data analyst": [
        "What is data cleaning and why is it important?",
        "Explain the difference between a data warehouse and a data lake.",
        "How do you handle missing values in a dataset?",
        "What is SQL and how is it used in data analysis?",
        "Describe a time you used data to solve a problem.",
        "What are KPIs and how do you define them?",
        "Explain the concept of ETL.",
        "What is the purpose of data visualization?",
        "How do you ensure data quality?",
        "What is A/B testing?",
        "What is a pivot table in Excel?",
        "Explain regression analysis.",
        "What is a dashboard and what makes a good one?",
        "How do you present complex data to non-technical stakeholders?",
        "What are the ethical considerations in data analysis?",
        "Describe your experience with Python or R for data analysis.",
        "What is statistical significance?",
        "How do you approach a new data analysis project?",
        "What is the difference between correlation and causation?",
        "What is business intelligence?"
    ],
    "python developer": [
        "Explain the difference between a list and a tuple in Python.",
        "What is a decorator in Python? Provide an example.",
        "How does Python\'s garbage collection work?",
        "What is the GIL (Global Interpreter Lock) in Python?",
        "Explain inheritance and polymorphism in Python with examples.",
        "What are generators and iterators in Python?",
        "How do you handle exceptions in Python?",
        "What is a virtual environment and why is it used?",
        "Explain the use of `*args` and `**kwargs`.",
        "What is Flask and how does it differ from Django?",
        "Describe a situation where you used a lambda function.",
        "What are metaclasses in Python?",
        "How do you optimize Python code for performance?",
        "Explain context managers in Python.",
        "What is `__init__.py` in Python?",
        "How do you perform file I/O in Python?",
        "What is the purpose of `self` in Python class methods?",
        "Explain the concept of closures in Python.",
        "What is the difference between `==` and `is` in Python?",
        "How do you implement multithreading in Python?"
    ],
    "web developer": [
        "Explain the box model in CSS.",
        "What is the difference between `localStorage` and `sessionStorage`?",
        "Describe responsive web design and how to implement it.",
        "What is the DOM and how do you interact with it using JavaScript?",
        "Explain the concept of Promises in JavaScript.",
        "What is the difference between `null` and `undefined` in JavaScript?",
        "How do you optimize website performance?",
        "What is a CSS preprocessor and why would you use one?",
        "Explain the event loop in JavaScript.",
        "What is the purpose of `async/await`?",
        "Describe the difference between SEO and SEM.",
        "What are web components?",
        "Explain the concept of CORS.",
        "What is a CDN and why is it used?",
        "How do you ensure web accessibility?",
        "What is the difference between `display: flex` and `display: grid`?",
        "Explain the concept of RESTful APIs.",
        "What are server-side rendering (SSR) and client-side rendering (CSR)?",
        "How do you handle authentication in web applications?",
        "What is a single-page application (SPA)?"
    ],
    "aptitude": [
        "If a train travels at 60 km/h, how long does it take to travel 240 km?",
        "A can do a piece of work in 10 days and B in 15 days. How long will they take to complete it together?",
        "What is 15% of 200?",
        "If 5 men can build a wall in 10 days, how many days will 10 men take to build the same wall?",
        "Find the missing number in the series: 2, 4, 8, 16, __.",
        "A clock gains 5 minutes every hour. If it is set correctly at 12 PM, what time will it show at 3 PM the same day?",
        "What is the average of the first 50 natural numbers?",
        "If the selling price of 10 articles is equal to the cost price of 11 articles, find the profit percentage.",
        "A sum of money doubles itself in 5 years at simple interest. In how many years will it become four times?",
        "What is the probability of rolling a 6 on a fair six-sided die?",
        "If a car covers a distance of 100 km in 2 hours, what is its speed?",
        "The sum of two numbers is 25 and their difference is 5. Find the numbers.",
        "What is the next letter in the series: A, C, E, G, __?",
        "A student scored 75% in an exam. If the maximum marks were 80, what was his score?",
        "If a circle has a radius of 7 cm, what is its circumference?",
        "What is the square root of 144?",
        "A mixture of 20 liters of milk and water contains 10% water. How much more water should be added to make the water content 25%?",
        "What is the value of \'x\' if 2x + 5 = 15?",
        "If all dogs are animals and all animals have four legs, then all dogs have four legs. Is this statement logically sound?",
        "What is the capital of France?"
    ],
    "coding": [
        "Write a Python function to reverse a string.",
        "Explain the concept of recursion with an example.",
        "Write a SQL query to find the second highest salary.",
        "How do you implement a stack using an array?",
        "Write a JavaScript function to check if a number is prime.",
        "Explain the difference between `==` and `===` in JavaScript.",
        "What is an API and how does it work?",
        "Write a Python program to find the factorial of a number.",
        "Explain the concept of object-oriented programming (OOP).",
        "How do you handle errors in a C++ program?",
        "Write a Java program to sort an array.",
        "What is a linked list?",
        "Explain the concept of dynamic programming.",
        "Write a Python script to read and write to a file.",
        "What is version control and why is Git important?",
        "How do you optimize a database query?",
        "Write a simple HTML structure for a webpage.",
        "Explain the concept of asynchronous programming.",
        "What is the purpose of unit testing?",
        "Write a CSS rule to center a div horizontally and vertically."
    ]
}

# --- Flask Routes ---
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
        
        if not role:
            result = "Please select a profession."
        else:
            system_p = "You are an AI Interview Assistant. Generate 20 unique interview questions for the given role. Give only questions, one per line, no numbers."
            user_p = f"Generate 20 interview questions for a {role}."

            ai_response = ai_assistant.generate(system_p, user_p)

            if ai_response:
                questions = [q.strip() for q in ai_response.split("\n") if q.strip()][:20]
                result = f"Successfully generated {len(questions)} questions for {role.title()} (via AI)."
            else:
                questions = random.sample(fallback_questions.get(role, ["No questions available."]), min(20, len(fallback_questions.get(role, []))))
                result = "AI failed. Showing fallback questions."

    return render_template("ai.html", questions=questions, result=result)

# 2. Career Roadmap Generator
@app.route("/roadmap", methods=["GET", "POST"])
def roadmap():
    roadmap_data = ""
    role = ""
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        system_p = "You are a Career Counselor. Create a detailed step-by-step career roadmap for the given role. Include Essential Skills, Learning Path, and Tools. Use Markdown for formatting."
        user_p = f"Create a detailed career roadmap for a {role} position."
        
        ai_response = ai_assistant.generate(system_p, user_p)
        if ai_response:
            roadmap_data = ai_response
        else:
            roadmap_data = "AI failed to generate roadmap. Please try again."
    
    return render_template("roadmap.html", roadmap=roadmap_data, role=role)

# 3. Skill Gap Analyzer
@app.route("/skill-gap", methods=["GET", "POST"])
def skill_gap():
    analysis = ""
    role = ""
    skills = ""
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        skills = request.form.get("skills", "").strip()
        system_p = "You are a Skill Gap Analyst. Compare the user\'s current skills with the requirements for the target role. Identify missing skills and suggest resources to bridge the gap. Use Markdown."
        user_p = f"Target Role: {role}\nMy Current Skills: {skills}"
        
        ai_response = ai_assistant.generate(system_p, user_p)
        if ai_response:
            analysis = ai_response
        else:
            analysis = "AI failed to analyze skill gap. Please try again."
    
    return render_template("skill_gap.html", analysis=analysis, role=role, skills=skills)

# 4. Resume Analyzer
@app.route("/resume", methods=["GET", "POST"])
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
                
                system_p = f"You are an Expert Resume Reviewer. Analyze the resume for a {role} position. Provide an ATS Score (0-100), Strengths, Weaknesses, and Missing Keywords. Use Markdown."
                user_p = f"Resume Text: {resume_text}\n\nTarget Role: {role}"
                ai_response = ai_assistant.generate(system_p, user_p)
                if ai_response:
                    analysis = ai_response
                else:
                    analysis = "AI failed to analyze resume. Please try again."
            except Exception as e:
                print(f"Resume Error: {e}")
                analysis = "Error reading PDF. Make sure it\'s a valid PDF file."
        else:
            analysis = "Please provide both a target role and a resume file."
    return render_template("resume.html", analysis=analysis)

# 5. Job Description (JD) Matcher
@app.route("/jd-matcher", methods=["GET", "POST"])
def jd_matcher():
    analysis = ""
    if request.method == "POST":
        jd = request.form.get("jd", "").strip()
        skills = request.form.get("skills", "").strip()
        
        if not jd or not skills:
            analysis = "Please provide both Job Description and your skills."
        else:
            system_p = "You are a Technical Recruiter. Match the Job Description with the User\'s Skills. Provide a Match Percentage, Matching Skills, and Missing Skills. Use Markdown."
            user_p = f"Job Description: {jd}\n\nMy Skills: {skills}"
            ai_response = ai_assistant.generate(system_p, user_p)
            if ai_response:
                analysis = ai_response
            else:
                analysis = "AI failed to perform JD matching. Please try again."
    return render_template("jd_matcher.html", analysis=analysis)

# 6. AI Aptitude Test
@app.route("/aptitude", methods=["GET", "POST"])
def aptitude():
    questions = []
    if request.method == "POST":
        topic = request.form.get("topic", "General Aptitude").strip()
        system_p = "You are an Aptitude Examiner. Generate 10 unique aptitude questions for the given topic. Provide questions and options (if applicable). Use Markdown for formatting."
        user_p = f"Generate 10 aptitude questions on the topic: {topic}."
        
        ai_response = ai_assistant.generate(system_p, user_p)
        if ai_response:
            questions = [q.strip() for q in ai_response.split("\n") if q.strip()]
        else:
            questions = random.sample(fallback_questions.get("aptitude", ["No aptitude questions available."]), min(10, len(fallback_questions.get("aptitude", []))))
    return render_template("aptitude.html", questions=questions, topic=topic)

# 7. AI Coding Quiz
@app.route("/coding-quiz", methods=["GET", "POST"])
def coding_quiz():
    quiz_text = ""
    if request.method == "POST":
        lang = request.form.get("lang", "Python").strip()
        system_p = "You are a Coding Interviewer. Generate 5 coding quiz questions for the given programming language. Include a problem statement and expected output. Use Markdown for formatting."
        user_p = f"Generate 5 coding quiz questions for {lang}."
        
        ai_response = ai_assistant.generate(system_p, user_p)
        if ai_response:
            quiz_text = ai_response
        else:
            quiz_text = random.sample(fallback_questions.get("coding", ["No coding quiz available."]), min(5, len(fallback_questions.get("coding", []))))
            quiz_text = "\n".join(quiz_text) # Join fallback questions for display
    return render_template("coding_quiz.html", quiz_text=quiz_text, lang=lang)

# 8. Placement Readiness Score
@app.route("/readiness", methods=["GET", "POST"])
def readiness():
    score_data = ""
    if request.method == "POST":
        resume_score = request.form.get("resume_score", 0)
        aptitude_score = request.form.get("aptitude_score", 0)
        interview_score = request.form.get("interview_score", 0)
        
        system_p = "You are a Placement Officer. Based on the scores provided, calculate a final Readiness Percentage and provide a detailed feedback report with action items. Use Markdown."
        user_p = f"Resume Score: {resume_score}/100, Aptitude Score: {aptitude_score}/100, Interview Score: {interview_score}/100. Calculate my placement readiness."
        
        ai_response = ai_assistant.generate(system_p, user_p)
        if ai_response:
            score_data = ai_response
        else:
            score_data = "AI failed to calculate readiness score. Please try again."
    return render_template("readiness.html", score_data=score_data)

# 9. AI Voice Interview Feedback
@app.route("/voice-feedback", methods=["POST"])
def voice_feedback():
    data = request.get_json()
    role = data.get("role", "").strip()
    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()
    
    if not all([role, question, answer]):
        return jsonify({"feedback": "Please provide role, question, and answer."}), 400
    
    system_p = f"You are an Expert Interview Coach for {role} positions. Evaluate the candidate\'s answer to the interview question. Provide: 1) Score (0-10), 2) Strengths, 3) Areas for improvement, 4) Suggested better answer. Keep it concise and encouraging. Use Markdown."
    user_p = f"Interview Question: {question}\n\nCandidate\'s Answer: {answer}"
    
    ai_response = ai_assistant.generate(system_p, user_p)
    if ai_response:
        feedback = ai_response
    else:
        feedback = "AI failed to generate feedback. Please try again."
    
    return jsonify({"feedback": feedback})

@app.route("/logout")
def logout():
    return "Logged out successfully!"

if __name__ == "__main__":
    app.run(debug=True)
