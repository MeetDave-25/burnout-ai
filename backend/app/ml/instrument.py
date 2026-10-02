"""Copenhagen Burnout Inventory (CBI) — validated burnout questionnaire.

Kristensen, Borritz, Villadsen & Christensen (2005), Work & Stress 19(3). The CBI is in the
public domain. We use the Personal (6 items) and Work-related (7 items) scales; students get
the study-related wording adapted from the CBI-Student version (Campos et al., 2011).

Answers are 0–4 where 4 is the most burnt-out option; each answer maps to 0/25/50/75/100
and a scale score is the mean of its answered items (at least half must be answered).
"""

FREQUENCY = ["Never / almost never", "Seldom", "Sometimes", "Often", "Always"]
DEGREE = ["To a very low degree", "To a low degree", "Somewhat", "To a high degree", "To a very high degree"]

PERSONAL = [
    ("p1", "How often do you feel tired?", FREQUENCY),
    ("p2", "How often are you physically exhausted?", FREQUENCY),
    ("p3", "How often are you emotionally exhausted?", FREQUENCY),
    ("p4", "How often do you think: \"I can't take it anymore\"?", FREQUENCY),
    ("p5", "How often do you feel worn out?", FREQUENCY),
    ("p6", "How often do you feel weak and susceptible to illness?", FREQUENCY),
]

WORK = [
    ("w1", "Is your work emotionally exhausting?", DEGREE),
    ("w2", "Do you feel burnt out because of your work?", DEGREE),
    ("w3", "Does your work frustrate you?", DEGREE),
    ("w4", "Do you feel worn out at the end of the working day?", FREQUENCY),
    ("w5", "Are you exhausted in the morning at the thought of another day at work?", FREQUENCY),
    ("w6", "Do you feel that every working hour is tiring for you?", FREQUENCY),
    ("w7", "Do you have enough energy for family and friends during leisure time?", FREQUENCY),
]

STUDY = [
    ("w1", "Are your studies emotionally exhausting?", DEGREE),
    ("w2", "Do you feel burnt out because of your studies?", DEGREE),
    ("w3", "Do your studies frustrate you?", DEGREE),
    ("w4", "Do you feel worn out at the end of a day of classes or studying?", FREQUENCY),
    ("w5", "Are you exhausted in the morning at the thought of another day of studies?", FREQUENCY),
    ("w6", "Do you feel that every hour of studying is tiring for you?", FREQUENCY),
    ("w7", "Do you have enough energy for family and friends during leisure time?", FREQUENCY),
]

REVERSED = {"w7"}  # "enough energy" — a high answer means LESS burnout
PERSONAL_IDS = [i for i, _, _ in PERSONAL]
WORK_IDS = [i for i, _, _ in WORK]
ALL_IDS = PERSONAL_IDS + WORK_IDS


def questionnaire(role_type: str) -> dict:
    work_items, work_name = (STUDY, "Study-related burnout") if role_type == "student" else (WORK, "Work-related burnout")

    def items(spec):
        # Options are listed in natural reading order; `value` is what to send back.
        return [
            {"id": i, "text": text, "options": [
                {"label": label, "value": (v if i not in REVERSED else 4 - v)} for v, label in enumerate(opts)
            ]}
            for i, text, opts in spec
        ]

    return {
        "name": "Copenhagen Burnout Inventory",
        "citation": "Kristensen et al. (2005), Work & Stress 19(3):192–207. Public domain.",
        "scales": [
            {"id": "personal", "name": "Personal burnout", "items": items(PERSONAL)},
            {"id": "work", "name": work_name, "items": items(work_items)},
        ],
    }


def _scale(answers: dict[str, int], ids: list[str]) -> float | None:
    vals = [answers[i] * 25 for i in ids if i in answers]
    return round(sum(vals) / len(vals), 1) if len(vals) * 2 >= len(ids) else None


def weekly_items() -> list[dict]:
    """The weekly measure: the 6-item CBI Personal burnout scale (validated on its own)."""
    return [{"id": i, "text": text, "options": [{"label": label, "value": v} for v, label in enumerate(opts)]}
            for i, text, opts in PERSONAL]


def score(answers: dict[str, int]) -> dict | None:
    """Return {personal, work, overall} or None if too few items were answered.

    If only the Personal scale was answered (the weekly measure), overall = personal and work is None.
    Answers must already be oriented so that 4 = most burnt out (the `value`s from `questionnaire`).
    """
    unknown = set(answers) - set(ALL_IDS)
    if unknown:
        raise ValueError(f"Unknown CBI items: {sorted(unknown)}")
    if any(not 0 <= v <= 4 for v in answers.values()):
        raise ValueError("CBI answers must be between 0 and 4")
    personal, work = _scale(answers, PERSONAL_IDS), _scale(answers, WORK_IDS)
    if personal is None:
        return None
    if work is None:
        return {"personal": personal, "work": None, "overall": personal}
    return {"personal": personal, "work": work, "overall": round((personal + work) / 2, 1)}
