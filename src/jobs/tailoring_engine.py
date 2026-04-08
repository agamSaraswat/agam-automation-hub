"""
Claude-powered resume tailoring engine.

For each queued job:
  1. Read master resume + schema
  2. Read full job description
  3. Claude extracts JD keywords, scores match, tailors resume + cover letter
  4. Save outputs to output/jobs/YYYY-MM-DD/company_role/
"""

import logging
import re
from datetime import date
from pathlib import Path

import yaml

from src.agent.claude_client import ClaudeClient
from src.jobs.deduplicator import get_todays_queue, update_status

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MASTER_RESUME_PATH = REPO_ROOT / "master_resume" / "agam_master_resume.md"
SCHEMA_PATH = REPO_ROOT / "master_resume" / "resume_schema.yaml"
OUTPUT_BASE = REPO_ROOT / "output" / "jobs"

SYSTEM_PROMPT = """You are an expert ATS resume optimizer and career coach.
You help Agam Saraswat tailor his resume and cover letter for specific job descriptions.

RULES:
- NEVER fabricate experience, skills, or metrics Agam doesn't have.
- Reorder and reword existing bullet points to match JD keywords.
- Emphasize the most relevant skills and experiences.
- Use the same action verbs and keywords from the JD where truthful.
- Cover letter: 250 words max, specific to company + role, references healthcare AI background.
- Be honest about match percentage — if it's low, say so.
"""


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    return text[:60]


def _load_resume() -> str:
    """Load master resume markdown."""
    return MASTER_RESUME_PATH.read_text(encoding="utf-8")


def _load_schema() -> dict:
    """Load resume schema YAML."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def tailor_for_job(
    job: dict,
    client: ClaudeClient | None = None,
) -> dict:
    """
    Tailor resume and cover letter for a single job.

    Returns dict with keys: match_score, resume_md, cover_letter_md,
    jd_keywords, output_dir
    """
    if client is None:
        client = ClaudeClient(temperature=0.3)

    resume_md = _load_resume()
    schema = _load_schema()
    jd_text = job.get("jd_text", "")
    title = job.get("title", "Unknown Role")
    company = job.get("company", "Unknown Company")

    if not jd_text or len(jd_text) < 50:
        logger.warning("Skipping %s @ %s — JD too short", title, company)
        return {"match_score": 0, "error": "JD too short to tailor"}

    # ── Step 1: Extract keywords and score match ──
    analysis_prompt = f"""Analyze this job description for the role of "{title}" at "{company}".

JOB DESCRIPTION:
{jd_text[:4000]}

AGAM'S SKILLS (from resume schema):
{yaml.dump(schema.get('skills', {}), default_flow_style=False)[:2000]}

AGAM'S EXPERIENCE TAGS:
{yaml.dump([b['tags'] for exp in schema.get('experience', []) for b in exp.get('bullets', [])], default_flow_style=False)[:1500]}

Return EXACTLY this format (no markdown fences):
MATCH_SCORE: <number 0-100>
TOP_KEYWORDS:
1. <keyword>
2. <keyword>
3. <keyword>
4. <keyword>
5. <keyword>
6. <keyword>
7. <keyword>
8. <keyword>
9. <keyword>
10. <keyword>
MISSING_SKILLS:
- <skill Agam doesn't have but JD requires>
MATCH_ASSESSMENT: <1-2 sentence honest assessment>
"""
    analysis = client.complete(analysis_prompt, system=SYSTEM_PROMPT, temperature=0.2)

    # Parse match score
    score_match = re.search(r"MATCH_SCORE:\s*(\d+)", analysis)
    match_score = int(score_match.group(1)) if score_match else 50

    # ── Step 2: Generate tailored resume ──
    resume_prompt = f"""Tailor Agam's resume for this specific job.

JOB: {title} at {company}
MATCH SCORE: {match_score}%

JD KEYWORDS ANALYSIS:
{analysis}

MASTER RESUME:
{resume_md}

Instructions:
- Keep the same structure and sections.
- Reorder bullet points so the most JD-relevant ones come first.
- Reword bullets to incorporate JD keywords where truthful.
- Emphasize matching skills in the Skills section.
- Do NOT add skills or experiences Agam doesn't have.
- Output a complete markdown resume.
"""
    tailored_resume = client.complete(resume_prompt, system=SYSTEM_PROMPT, temperature=0.3)

    # ── Step 3: Generate cover letter ──
    cover_prompt = f"""Write a cover letter for Agam Saraswat applying to "{title}" at "{company}".

KEY JD REQUIREMENTS:
{analysis}

MATCH SCORE: {match_score}%

Requirements:
- 250 words maximum
- First person, professional but personable
- Open with why {company} specifically interests Agam
- Reference his healthcare AI background at Humana
- Mention 2-3 specific achievements with metrics that match JD requirements
- Close with enthusiasm and call to action
- Do NOT be generic — be specific to this company and role

Format as plain text, not markdown. Include a proper letter header:
Agam Saraswat
saraswatagam012@gmail.com | (508) 373-4260
Massachusetts, USA
"""
    cover_letter = client.complete(cover_prompt, system=SYSTEM_PROMPT, temperature=0.4)

    # ── Step 4: Save outputs ──
    today = date.today().isoformat()
    slug = f"{_slugify(company)}_{_slugify(title)}"
    out_dir = OUTPUT_BASE / today / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "resume.md").write_text(tailored_resume, encoding="utf-8")
    (out_dir / "cover_letter.md").write_text(cover_letter, encoding="utf-8")
    (out_dir / "match_score.txt").write_text(
        f"Match Score: {match_score}%\n\n{analysis}", encoding="utf-8"
    )

    # Extract keywords section
    kw_section = ""
    if "TOP_KEYWORDS:" in analysis:
        kw_section = analysis.split("TOP_KEYWORDS:")[1].split("MISSING_SKILLS:")[0].strip()
    (out_dir / "jd_keywords.txt").write_text(kw_section, encoding="utf-8")

    logger.info(
        "Tailored: %s @ %s → score %d%% → %s",
        title, company, match_score, out_dir,
    )

    return {
        "match_score": match_score,
        "resume_md": tailored_resume,
        "cover_letter_md": cover_letter,
        "jd_keywords": kw_section,
        "output_dir": str(out_dir),
    }


def run_tailoring() -> int:
    """
    Tailor resumes for all queued jobs today.
    Returns count of tailored jobs.
    """
    queue = get_todays_queue()
    if not queue:
        logger.info("No jobs in today's queue.")
        return 0

    client = ClaudeClient(temperature=0.3)
    tailored_count = 0

    for job in queue:
        if job["status"] != "queued":
            continue

        logger.info("Tailoring for: %s @ %s", job["title"], job["company"])
        result = tailor_for_job(job, client=client)

        if result.get("error"):
            logger.warning("Skipped: %s", result["error"])
            continue

        score = result["match_score"]
        if score < 60:
            logger.warning(
                "Low match (%d%%) for %s @ %s — marked for review",
                score, job["title"], job["company"],
            )
            # Still save it, but log the warning
        
        update_status(job["url"], "tailored")
        tailored_count += 1

    logger.info("Tailoring complete: %d/%d jobs processed", tailored_count, len(queue))
    return tailored_count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    count = run_tailoring()
    print(f"\nTailoring complete. {count} jobs processed.")
