import json
from pathlib import Path
from flask import Flask, render_template, request

app = Flask(__name__)

DATA_FILE = Path("candidates.jsonl")


# -------------------------------------------------
# Data Loading
# -------------------------------------------------

def load_candidates():
    """
    Load every candidate from candidates.jsonl into memory.
    """
    candidates = {}

    if not DATA_FILE.exists():
        return candidates

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            candidate = json.loads(line)
            cid = candidate.get("candidate_id")

            if cid:
                candidates[cid] = candidate

    return candidates


CANDIDATES = load_candidates()


# -------------------------------------------------
# Helper Functions
# -------------------------------------------------

def format_label(text):
    """
    Convert snake_case keys into readable labels.
    Example:
    profile_views_received_30d
    ->
    Profile Views Received 30d
    """
    if not text:
        return ""

    text = text.replace("_", " ")
    return text.title()


def is_number(value):
    return isinstance(value, (int, float))


def is_boolean(value):
    return isinstance(value, bool)


def build_skill_table(candidate):
    """
    Sort skills alphabetically.
    """

    skills = candidate.get("skills", [])

    return sorted(
        skills,
        key=lambda x: x.get("name", "").lower()
    )


def build_skill_assessment(candidate):
    """
    Convert skill assessment dict into list for template.
    """

    rr = candidate.get("redrob_signals", {})

    assessment = rr.get("skill_assessment_scores", {})

    rows = []

    for skill, score in assessment.items():
        try:
            score = float(score)
        except Exception:
            continue

        rows.append({
            "skill": skill,
            "score": score
        })

    rows.sort(key=lambda x: x["score"], reverse=True)

    return rows


def recruiter_metrics(candidate):
    """
    Cards shown in Recruiter Metrics section.

    Only include if present.
    """

    rr = candidate.get("redrob_signals", {})

    metric_map = {
        "profile_views_received_30d": "Profile Views",
        "applications_submitted_30d": "Applications",
        "connection_count": "Connections",
        "search_appearance_30d": "Search Appearance",
        "saved_by_recruiters_30d": "Saved by Recruiters",
        "github_activity_score": "GitHub Activity"
    }

    metrics = []

    for key, label in metric_map.items():
        if key in rr:
            metrics.append({
                "label": label,
                "value": rr[key]
            })

    return metrics


def recruiter_signals(candidate):
    """
    Dynamically display every numeric or boolean signal.

    Excludes sections already displayed separately.
    """

    rr = candidate.get("redrob_signals", {})

    excluded = {
        "skill_assessment_scores",
        "expected_salary_range_inr_lpa"
    }

    signals = []

    for key, value in rr.items():

        if key in excluded:
            continue

        if is_number(value) or is_boolean(value):

            signals.append({
                "label": format_label(key),
                "value": value
            })

    return signals


def companies_worked(candidate):
    history = candidate.get("career_history", [])

    companies = []

    for item in history:
        company = item.get("company")
        if company and company not in companies:
            companies.append(company)

    return companies


# -------------------------------------------------
# Routes
# -------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():

    candidate = None
    error = None

    candidate_id = ""

    if request.method == "POST":

        candidate_id = request.form.get(
            "candidate_id",
            ""
        ).strip()

        candidate = CANDIDATES.get(candidate_id)

        if candidate is None:
            error = "Candidate not found."

    context = {
        "candidate": candidate,
        "candidate_id": candidate_id,
        "error": error,
        "skills_table": build_skill_table(candidate) if candidate else [],
        "skill_assessment": build_skill_assessment(candidate) if candidate else [],
        "recruiter_metrics": recruiter_metrics(candidate) if candidate else [],
        "recruiter_signals": recruiter_signals(candidate) if candidate else [],
        "companies_worked": companies_worked(candidate) if candidate else [],
        "json_data": json.dumps(candidate, indent=4) if candidate else ""
    }

    return render_template("index.html", **context)


# -------------------------------------------------
# Main
# -------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)