"""Configurable relevance filtering and scoring for scraped jobs."""

from __future__ import annotations

from typing import Any


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def get_relevance_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return normalized relevance filter config with defaults."""
    filters = config.get("filters", {})

    include_titles = filters.get("include_titles") or config.get("target_roles", [])

    return {
        "include_keywords": [_norm(x) for x in filters.get("include_keywords", []) if _norm(x)],
        "exclude_keywords": [_norm(x) for x in filters.get("exclude_keywords", []) if _norm(x)],
        "include_titles": [_norm(x) for x in include_titles if _norm(x)],
        "exclude_titles": [_norm(x) for x in filters.get("exclude_titles", []) if _norm(x)],
        "preferred_locations": [_norm(x) for x in filters.get("preferred_locations", config.get("locations", [])) if _norm(x)],
        "remote_preference": bool(filters.get("remote_preference", True)),
        "minimum_match_threshold": int(filters.get("minimum_match_threshold", 35)),
    }


def evaluate_job_relevance(job: dict[str, Any], relevance_config: dict[str, Any]) -> dict[str, Any]:
    """Score and explain relevance for one job."""
    title = _norm(job.get("title", ""))
    jd_text = _norm(job.get("jd_text", ""))
    location = _norm(job.get("location", ""))
    full_text = f"{title} {jd_text}".strip()

    score = 0
    reasons: list[str] = []
    hard_reject_reasons: list[str] = []

    include_titles = relevance_config.get("include_titles", [])
    exclude_titles = relevance_config.get("exclude_titles", [])
    include_keywords = relevance_config.get("include_keywords", [])
    exclude_keywords = relevance_config.get("exclude_keywords", [])
    preferred_locations = relevance_config.get("preferred_locations", [])
    remote_preference = relevance_config.get("remote_preference", True)
    threshold = relevance_config.get("minimum_match_threshold", 35)

    title_hits = [pattern for pattern in include_titles if pattern in title]
    if title_hits:
        bonus = min(60, 30 + 10 * (len(title_hits) - 1))
        score += bonus
        reasons.append(f"Title match (+{bonus}): {', '.join(title_hits[:3])}")

    keyword_title_hits = [kw for kw in include_keywords if kw in title]
    keyword_jd_hits = [kw for kw in include_keywords if kw in jd_text and kw not in keyword_title_hits]
    if keyword_title_hits:
        bonus = min(25, 8 * len(keyword_title_hits))
        score += bonus
        reasons.append(f"Keyword title match (+{bonus}): {', '.join(keyword_title_hits[:4])}")
    if keyword_jd_hits:
        bonus = min(20, 4 * len(keyword_jd_hits))
        score += bonus
        reasons.append(f"Keyword JD match (+{bonus}): {', '.join(keyword_jd_hits[:4])}")

    location_hits = [loc for loc in preferred_locations if loc in location]
    is_remote = "remote" in location
    if location_hits:
        score += 12
        reasons.append(f"Preferred location match (+12): {', '.join(location_hits[:2])}")
    elif remote_preference and is_remote:
        score += 10
        reasons.append("Remote location preferred (+10)")
    elif remote_preference and not location_hits:
        score -= 6
        reasons.append("Location not preferred (-6)")

    blocked_title_hits = [pattern for pattern in exclude_titles if pattern in title]
    blocked_keyword_hits = [kw for kw in exclude_keywords if kw in full_text]

    if blocked_title_hits:
        hard_reject_reasons.append(f"Blocked title: {', '.join(blocked_title_hits[:3])}")
    if blocked_keyword_hits:
        hard_reject_reasons.append(f"Blocked keyword: {', '.join(blocked_keyword_hits[:3])}")

    keep = not hard_reject_reasons and score >= threshold
    reject_reason = None
    if hard_reject_reasons:
        reject_reason = "; ".join(hard_reject_reasons)
    elif score < threshold:
        reject_reason = f"Match score {score} below threshold {threshold}"

    return {
        "keep": keep,
        "match_score": score,
        "reasons": reasons,
        "reject_reason": reject_reason,
        "config_threshold": threshold,
    }


def apply_relevance_filter(jobs: list[dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply relevance filtering to jobs and return kept + rejected jobs with explanations."""
    relevance_config = get_relevance_config(config)

    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for job in jobs:
        decision = evaluate_job_relevance(job, relevance_config)
        enriched = {**job, **decision}
        if decision["keep"]:
            kept.append(enriched)
        else:
            rejected.append(enriched)

    kept.sort(key=lambda j: j.get("match_score", 0), reverse=True)
    return kept, rejected
