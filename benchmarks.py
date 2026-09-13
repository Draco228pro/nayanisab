"""NayaNisab's subject-agnostic benchmark framework.

The dimensions are intentionally broad enough for university subjects across Pakistan.
The AI maps the uploaded curriculum to subject-specific evidence within each dimension.
This is a prototype decision-support framework, not an accreditation standard.
"""

BENCHMARKS = [
    {"id": "core", "name": "Disciplinary Core & Fundamentals", "weight": 14,
     "signals": "Foundational concepts, theories, methods and core knowledge that a graduate of the chosen subject should understand."},
    {"id": "outcomes", "name": "Learning Outcomes & Progression", "weight": 10,
     "signals": "Clear outcomes, logical progression from foundational to advanced learning, prerequisites and appropriate level of difficulty."},
    {"id": "current", "name": "Current Tools, Methods & Practices", "weight": 12,
     "signals": "Contemporary tools, methods, standards, techniques, professional practices or technologies relevant to the chosen subject."},
    {"id": "industry", "name": "Industry / Professional Readiness", "weight": 10,
     "signals": "Workplace relevance, professional practice, practical problem solving, projects, field exposure, employability and transferable professional skills."},
    {"id": "practical", "name": "Practical Application & Experience", "weight": 10,
     "signals": "Laboratories, fieldwork, clinical/practical work, projects, simulations, case studies, experiments or other authentic application opportunities."},
    {"id": "digital", "name": "Digital & Data Fluency", "weight": 8,
     "signals": "Appropriate use of digital tools, data, computational methods, information literacy, digital workflows or technology relevant to the subject."},
    {"id": "research", "name": "Research, Innovation & Critical Thinking", "weight": 9,
     "signals": "Research methods, evidence-based reasoning, experimentation, critical analysis, problem framing, innovation and independent inquiry."},
    {"id": "global", "name": "Global / International Alignment", "weight": 9,
     "signals": "Alignment with internationally relevant knowledge, professional expectations, standards, contemporary global practice and transferable competencies."},
    {"id": "future", "name": "Emerging Trends & Future Readiness", "weight": 8,
     "signals": "Important emerging developments, future-facing competencies and the ability to adapt to fast-changing knowledge or practice in the subject."},
    {"id": "ethics", "name": "Ethics, Safety & Societal Impact", "weight": 5,
     "signals": "Professional ethics, safety, responsible practice, regulation, sustainability, social impact and risk awareness where relevant to the subject."},
    {"id": "assessment", "name": "Assessment & Evidence of Competence", "weight": 5,
     "signals": "Assessment methods that genuinely demonstrate the intended learning outcomes, including authentic tasks, projects, practical assessment or other appropriate evidence."},
]

TOTAL_WEIGHT = sum(x["weight"] for x in BENCHMARKS)


def score_band(score: float) -> dict:
    score = max(0, min(100, float(score)))
    if score < 50:
        return {"label": "HIGH WARNING", "headline": "Major modernisation required", "action": "Immediate priority"}
    if score <= 80:
        return {"label": "IMPROVEMENT REQUIRED", "headline": "Important areas should be strengthened", "action": "Mandatory improvement"}
    return {"label": "FUTURE-READY", "headline": "Core alignment is strong", "action": "Optional enhancement"}
