"""Human-readable metadata for burnout levels, model drivers and recommendations."""

# CBI cut-offs: < 50 low, 50–74 moderate, >= 75 high (Kristensen et al. 2005; Borritz et al. 2006).
LEVELS = [
    {"level": 0, "min": 0, "label": "Low", "color": "#10B981"},
    {"level": 1, "min": 50, "label": "Moderate", "color": "#F59E0B"},
    {"level": 2, "min": 75, "label": "High", "color": "#EF4444"},
]
WARNING_THRESHOLD = 50


def level_for(score: float) -> dict:
    return [lv for lv in LEVELS if score >= lv["min"]][-1]


# `question` / `student_question` drive the check-in form.
# `lever` is a realistic one-step improvement used for "what would help most" suggestions.
# `advice` is shown when the driver is pushing burnout up.
FEATURES = {
    "work_hours_per_day": {
        "label": "Working hours / day", "unit": "h", "min": 0, "max": 24, "step": 0.5,
        "question": "On a typical day, how many hours do you work?",
        "student_question": "On a typical day, how many hours do you spend in class and studying?",
        "lever": -1,
        "advice": "Set a firm daily stop time — long days are one of your strongest load signals.",
    },
    "after_hours_per_week": {
        "label": "After-hours work", "unit": " nights/wk", "min": 0, "max": 7, "step": 1,
        "question": "How many evenings or nights last week did you work late?",
        "student_question": "How many evenings or nights last week did you study late?",
        "lever": -2,
        "advice": "Move late-night work into the day and mute notifications after your stop time.",
    },
    "meetings_per_day": {
        "label": "Meetings / classes", "unit": "/day", "min": 0, "max": 20, "step": 1,
        "question": "How many meetings do you have on a typical day?",
        "student_question": "How many lectures or classes do you have on a typical day?",
        "lever": -1,
        "advice": "Protect two meeting-free focus blocks a day; decline meetings without a clear agenda.",
    },
    "sleep_hours": {
        "label": "Sleep", "unit": "h", "min": 0, "max": 14, "step": 0.5,
        "question": "How many hours do you sleep on a typical night?",
        "lever": 1,
        "advice": "Protect 7–8 hours of sleep; short sleep sharply amplifies exhaustion.",
    },
    "days_off_last_month": {
        "label": "Days off (last month)", "unit": " days", "min": 0, "max": 31, "step": 1,
        "question": "How many full days off (no work at all) did you take last month?",
        "student_question": "How many full days off (no study at all) did you take last month?",
        "lever": 2,
        "advice": "Book real time off in the next few weeks — recovery days matter.",
    },
    "workload": {
        "label": "Workload", "unit": "/5", "min": 1, "max": 5, "step": 1,
        "question": "I have more to do than I can manage. (1 = strongly disagree, 5 = strongly agree)",
        "lever": -1,
        "advice": "List what's on your plate and agree on what can be dropped or delayed.",
    },
    "autonomy": {
        "label": "Autonomy", "unit": "/5", "min": 1, "max": 5, "step": 1,
        "question": "I have control over how and when I do my work. (1–5)",
        "lever": 1,
        "advice": "Ask for more say in how your work is planned — control buffers stress.",
    },
    "support": {
        "label": "Support", "unit": "/5", "min": 1, "max": 5, "step": 1,
        "question": "I get the support I need from my manager. (1–5)",
        "student_question": "I get the support I need from my teachers or mentors. (1–5)",
        "lever": 1,
        "advice": "Request a regular 1:1 focused on workload and wellbeing, not just status.",
    },
    "recognition": {
        "label": "Recognition", "unit": "/5", "min": 1, "max": 5, "step": 1,
        "question": "My effort is noticed and valued. (1–5)",
        "lever": 1,
        "advice": "Share your wins and ask for specific feedback — feeling unseen erodes motivation.",
    },
    "can_disconnect": {
        "label": "Ability to disconnect", "unit": "/5", "min": 1, "max": 5, "step": 1,
        "question": "I can switch off from work in my free time. (1–5)",
        "student_question": "I can switch off from studying in my free time. (1–5)",
        "lever": 1,
        "advice": "Create a shutdown ritual: close apps, write tomorrow's top three, stop checking messages.",
    },
    "role_type": {"label": "Role", "unit": "", "lever": None, "advice": None},
    "remote_work": {"label": "Remote work", "unit": "", "lever": None, "advice": None},
}

PATTERNS = {
    "Frenetic": "Your pattern looks like overwork-driven (frenetic) burnout: high effort with too little recovery.",
    "Under-Challenged": "Your pattern looks like under-challenge: burnout from work that doesn't use or reward you.",
    "Worn-Out": "Your pattern looks like worn-out burnout: sustained pressure with little support or control.",
}


# ── Daily check-in: the 6 drivers with the most influence on the model, asked as single taps ──
# The remaining drivers (meetings, days off, autonomy, recognition) take typical population values.
LIKERT = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"]


def _likert(text: str) -> dict:
    return {"text": text, "options": [{"label": lab, "value": i + 1} for i, lab in enumerate(LIKERT)]}


DAILY = {
    "sleep_hours": {
        "text": "How much did you sleep last night?",
        "options": [{"label": "Under 5h", "value": 4.5}, {"label": "5–6h", "value": 5.5}, {"label": "6–7h", "value": 6.5},
                    {"label": "7–8h", "value": 7.5}, {"label": "8h or more", "value": 8.5}],
    },
    "work_hours_per_day": {
        "text": "How long did you work yesterday?",
        "student_text": "How long did you study yesterday, classes included?",
        "options": [{"label": "Under 6h", "value": 5}, {"label": "6–8h", "value": 7}, {"label": "8–10h", "value": 9},
                    {"label": "10–12h", "value": 11}, {"label": "12h or more", "value": 13}],
    },
    "after_hours_per_week": {
        "text": "How many evenings did you work late this week?",
        "student_text": "How many evenings did you study late this week?",
        "options": [{"label": "None", "value": 0}, {"label": "1–2", "value": 1.5}, {"label": "3–4", "value": 3.5},
                    {"label": "5–6", "value": 5.5}, {"label": "Every night", "value": 7}],
    },
    "workload": _likert("I have more to do than I can manage."),
    "can_disconnect": {**_likert("I can switch off from work in my free time."),
                       "student_text": "I can switch off from studying in my free time."},
    "support": {**_likert("I get the support I need from my manager."),
                "student_text": "I get the support I need from my teachers or mentors."},
}
