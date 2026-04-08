"""
LinkedIn post generator — Claude creates posts per content pillar.

Rotates through pillars by weekday. Saves to output/linkedin/queue/.
"""

import logging
import random
from datetime import date, datetime
from pathlib import Path

import yaml

from src.agent.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TOPICS_PATH = REPO_ROOT / "config" / "linkedin_topics.yaml"
QUEUE_DIR = REPO_ROOT / "output" / "linkedin" / "queue"

SYSTEM_PROMPT = """You are a LinkedIn ghostwriter for Agam Saraswat, a Data Scientist specializing in Healthcare AI at Humana.

Write as Agam in first person. His voice is: conversational, specific, metric-driven, insightful.

FORMAT RULES:
- 150-250 words
- 3-5 short paragraphs separated by blank lines
- Open with a hook: surprising stat, question, or bold claim
- End with a question or punchy takeaway to drive engagement
- Max 2-3 emojis total (or zero — vary it)
- Include 3-5 relevant hashtags at the end
- No "I'm humbled to announce" or LinkedIn clichés
- Be specific: mention tools, numbers, real outcomes
"""


def load_topics() -> dict:
    """Load LinkedIn topics configuration."""
    with open(TOPICS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_todays_pillar() -> dict:
    """Get the content pillar for today based on weekday."""
    topics = load_topics()
    weekday = date.today().weekday()  # 0=Monday ... 6=Sunday
    pillar = topics.get("pillars", {}).get(weekday, {})
    return pillar


def generate_post(pillar_override: dict | None = None) -> str:
    """
    Generate a LinkedIn post for today's pillar.
    Returns the post text.
    """
    topics = load_topics()
    pillar = pillar_override or get_todays_pillar()

    if not pillar or not pillar.get("name"):
        logger.info("No pillar for today (weekend). Skipping.")
        return ""

    name = pillar["name"]
    description = pillar.get("description", "")
    hashtags = pillar.get("hashtags", [])
    tone = topics.get("tone_guidelines", "")

    # Weekend check
    if "Weekend" in name:
        return f"[Weekend] Consider resharing a past post or engaging with your network."

    prompt = f"""Write a LinkedIn post for today's content pillar.

PILLAR: {name}
DESCRIPTION: {description}
HASHTAGS TO INCLUDE: {' '.join(hashtags)}

TONE GUIDELINES:
{tone}

AGAM'S CONTEXT:
- Currently Data Scientist at Humana working on healthcare AI
- Previously at R-Financial (fintech) and Hexaware (consulting)
- MS Data Analytics from Clark University
- Key achievements: 45% BI load reduction, 20% retention improvement, 12% readmission reduction
- Works with: BERT, spaCy, XGBoost, Snowflake, AWS SageMaker, SHAP

Write the complete post now. Make it feel authentic and specific — not generic.
Vary the structure from typical posts. Be creative with the hook.
"""

    client = ClaudeClient()
    post = client.complete(prompt, system=SYSTEM_PROMPT, temperature=0.8)

    # Save to queue
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    filepath = QUEUE_DIR / f"{today}.md"
    
    metadata = f"""---
date: {today}
pillar: {name}
status: draft
scheduled_time: {_random_post_time()}
---

"""
    filepath.write_text(metadata + post, encoding="utf-8")
    logger.info("Generated LinkedIn post for pillar '%s' → %s", name, filepath)

    return post


def _random_post_time() -> str:
    """Generate a random time between 8-11 AM for posting."""
    hour = random.randint(8, 10)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    pillar = get_todays_pillar()
    print(f"Today's pillar: {pillar.get('name', 'None')}")
    post = generate_post()
    if post:
        print(f"\n{'='*50}")
        print(post)
        print(f"{'='*50}")
