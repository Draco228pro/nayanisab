from benchmarks import BENCHMARKS, TOTAL_WEIGHT, score_band


def calculate_overall_score(dimension_scores: list[dict]) -> float:
    lookup = {x.get("id"): float(x.get("score", 0)) for x in dimension_scores}
    weighted = 0.0
    for b in BENCHMARKS:
        weighted += lookup.get(b["id"], 0) * b["weight"]
    return round(weighted / TOTAL_WEIGHT, 1)


def normalise_dimension_scores(items: list[dict]) -> list[dict]:
    out = []
    for b in BENCHMARKS:
        match = next((x for x in items if x.get("id") == b["id"]), {})
        raw = match.get("score", 0)
        try:
            score = max(0, min(100, float(raw)))
        except Exception:
            score = 0
        out.append({
            "id": b["id"],
            "name": b["name"],
            "weight": b["weight"],
            "score": score,
            "status": "Strong" if score >= 81 else "Needs improvement" if score >= 50 else "High gap",
            "evidence": str(match.get("evidence", "Not clearly evidenced in the uploaded curriculum.")),
            "missing": str(match.get("missing", "No specific gap recorded.")),
            "priority": str(match.get("priority", "Medium")),
        })
    return out


def build_summary(result: dict) -> dict:
    dims = result.get("dimension_scores", [])
    score = calculate_overall_score(dims)
    return {"score": score, "band": score_band(score), "dimensions": normalise_dimension_scores(dims)}
