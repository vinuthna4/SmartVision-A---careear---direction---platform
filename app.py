from flask import Flask, render_template, request, jsonify, send_from_directory, session
import json, os, csv, datetime
import matplotlib.pyplot as plt
import numpy as np

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "smartvision-secret-key"

DATA_PATH = os.path.join("data", "career_data_detailed.json")
SUB_PATH = "submissions.csv"
IMG_DIR = os.path.join("static", "images")
os.makedirs(IMG_DIR, exist_ok=True)

# Load careers
with open(DATA_PATH, "r", encoding="utf-8") as f:
    careers = json.load(f)

def save_submission(entry):
    header = ["timestamp","education","interest","skills","marks","duration_years","exam_willing"]
    exists = os.path.exists(SUB_PATH)
    with open(SUB_PATH, "a", newline='', encoding="utf-8") as csvf:
        writer = csv.writer(csvf)
        if not exists:
            writer.writerow(header)
        writer.writerow([
            datetime.datetime.now().isoformat(),
            entry.get("education",""),
            entry.get("interest",""),
            entry.get("skills",""),
            entry.get("marks",""),
            entry.get("duration",""),
            entry.get("exam_willing","")
        ])

def generate_chart(suggestions, filename="chart.png"):
    labels = [s["field"] for s in suggestions]
    base = np.linspace(60, 85, len(labels)) + np.random.rand(len(labels))*10
    plt.figure(figsize=(6,3))
    plt.barh(labels[::-1], base[::-1])
    plt.xlabel("Relative Demand Score")
    plt.tight_layout()
    path = os.path.join(IMG_DIR, filename)
    plt.savefig(path)
    plt.close()
    return path

INTEREST_KEYWORDS = {
    "engineering": ["engineer","code","coding","program","robot","math","physics","technology","computer","cse","ece","civil","mechanical"],
    "medical": ["bio","biology","neat","neet","medical","doctor","nurse","pharmacy","medicine","mbbs","health","biotech"],
    "commerce": ["commerce","account","accounting","finance","money","business","bank","ca","bcom"],
    "arts": ["arts","history","political","psychology","journalism","creative","design","music","literature"],
    "law": ["law","legal","lawyer","advocate","court","clat"],
    "agriculture": ["agri","farm","agriculture","horticulture"],
    "defense": ["nda","defense","army","navy","airforce","police","serve","soldier"]
}

def keyword_score(text, keywords):
    t = (text or "").lower()
    for k in keywords:
        if k in t:
            return 1
    return 0

def compute_recommendations(payload):
    education = payload.get("education")
    interest_text = payload.get("interest","").lower()
    skills_text = payload.get("skills","").lower()
    marks = int(payload.get("marks") or 50)
    duration = int(payload.get("duration") or 4)
    exam_willing = payload.get("exam_willing","yes").lower() in ["yes","true","y"]

    group_key = "after_10th" if education == "10th" else "after_inter"
    pool = careers[group_key]

    scored = []
    for path in pool:
        score = 0
        for cat, keys in INTEREST_KEYWORDS.items():
            if keyword_score(interest_text, keys):
                if cat in path.get("field","").lower():
                    score += 40
                elif keyword_score(skills_text, keys):
                    score += 10
        if marks >= 75:
            score += 10
        elif marks >= 60:
            score += 5
        if duration <= 2:
            if any(k in path.get("field","").lower() for k in ["diploma","iti","vocational","certificate","paramedical"]):
                score += 20
        else:
            score += 5
        if not exam_willing and any(ex.get("name","").lower() in ["jee","neet","nta","nd a","nda","clat"] for ex in path.get("exams",[])):
            score -= 15
        if any(k in interest_text for k in path.get("field","").lower().split()):
            score += 5
        scored.append({"path": path, "score": score})

    scored_sorted = sorted(scored, key=lambda x: x["score"], reverse=True)
    top = [s["path"] for s in scored_sorted[:3]]
    return top

@app.route("/")
def index():
    profile = session.get("profile")
    print("Session profile:", profile) 
    return render_template("index.html", profile=profile)

@app.route("/logout")
def logout():
    session.pop("profile", None)
    return render_template("index.html")

@app.route("/options", methods=["POST"])
def options_route():
    education = request.form.get("education")
    key = "after_10th" if education == "10th" else "after_inter"
    paths = careers.get(key, [])
    return render_template("options.html", education=education, paths=paths)

@app.route("/roadmap", methods=["POST"])
def roadmap_route():
    education = request.form.get("education")
    field = request.form.get("field")
    key = "after_10th" if education == "10th" else "after_inter"
    chosen = next((p for p in careers[key] if p["field"] == field), None)
    if not chosen:
        return "Roadmap not found", 404
    return render_template("roadmap.html", field=field, roadmap=chosen.get("roadmap",[]), exams=chosen.get("exams",[]), education=education)

@app.route("/quiz")
def quiz_page():
    return render_template("quiz.html")

@app.route("/api/quiz", methods=["POST"])
def api_quiz():
    payload = request.json or {}
    try:
        save_submission(payload)
    except Exception as e:
        print("save error:", e)
    top = compute_recommendations(payload)
    chart_path = generate_chart(top, filename="career_chart.png")
    return jsonify({
        "recommended": top[0] if top else {},
        "suggestions": top,
        "chart": chart_path.replace("\\","/")
    })

@app.route('/static/images/<path:filename>')
def images(filename):
    return send_from_directory(IMG_DIR, filename)

@app.route("/profile", methods=["POST"])
def profile():
    profile_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "username": request.form.get("username"),
        "name": request.form.get("name"),
        "education": request.form.get("education"),
        "interests": request.form.get("interests"),
        "skills": request.form.get("skills"),
        "marks": request.form.get("marks"),
        "exam_willing": request.form.get("exam_willing"),
        "phone": request.form.get("phone number"),
        "password": request.form.get("password"),
    }
    with open("user_profiles.csv", "a", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=profile_data.keys())
        if f.tell() == 0:
            writer.writeheader()
        writer.writerow(profile_data)
    session["profile"] = profile_data
    return render_template("index.html", profile=profile_data)

from scraper import get_exam_updates

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    with open("user_profiles.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["username"] == username and row["password"] == password:
                session["profile"] = row
                return redirect("/")  # ← Redirect to homepage

    return render_template("index.html", login_error="Invalid username or password")


if __name__ == "__main__":
    app.run(debug=True)
