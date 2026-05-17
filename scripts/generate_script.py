"""
Generates a YouTube video script using Claude API based on latest COT data.
Produces both a long-form video script and a 60-second Shorts script.
"""

import anthropic
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def load_cot_data() -> dict:
    with open("data/cot_latest.json") as f:
        return json.load(f)


def pick_featured_pairs(cot_data: dict, count: int = 3) -> list:
    """Pick pairs with most extreme/interesting COT positioning."""
    pairs = cot_data["pairs"]
    # Sort by: extreme positioning first, then by absolute spec net change
    pairs_sorted = sorted(
        pairs,
        key=lambda p: (
            int(p["extreme_positioning"]),
            abs(p.get("spec_net_change", 0)),
        ),
        reverse=True,
    )
    return pairs_sorted[:count]


def build_cot_summary(pairs: list) -> str:
    lines = []
    for p in pairs:
        direction = "CROWDED LONG" if p["spec_net"] > 0 else "CROWDED SHORT"
        lines.append(
            f"- {p['pair']}: Retail speculators are {direction} "
            f"(net {p['spec_net']:+,}, changed {p.get('spec_net_change', 0):+,} this week). "
            f"COT contrarian bias: {p['contrarian_bias']}. "
            f"Extreme positioning: {'YES' if p['extreme_positioning'] else 'No'}."
        )
    return "\n".join(lines)


def generate_longform_script(client: anthropic.Anthropic, cot_summary: str, report_date: str) -> str:
    prompt = f"""You are Dezee, a sharp young forex trader from Lagos who trades the COT (Commitment of Traders) contrarian strategy.
Your YouTube channel teaches retail traders to follow what the BIG MONEY (commercials/banks) is doing — and FADE the crowd.

Today's COT data (report date: {report_date}):
{cot_summary}

Write a compelling YouTube video script (5-7 minutes when read aloud, ~800-1000 words).

Structure:
1. HOOK (15 sec) — shocking stat or question about what retail traders are doing wrong RIGHT NOW
2. INTRO (30 sec) — who you are, what COT is, why it matters
3. COT BREAKDOWN (3-4 min) — go through each pair, explain what retail is doing, what the contrarian trade setup looks like, key levels to watch
4. THE EDGE (1 min) — explain WHY fading the crowd works, reference commercial hedgers as the "smart money"
5. OUTRO + CTA (30 sec) — subscribe, join the Telegram signal group, like the video

Tone: energetic, confident, educational, slightly street/Lagos flavour but professional. No unnecessary fluff.
Use specific numbers from the COT data. Make it feel EXCLUSIVE — like insider knowledge.
Format with clear section labels."""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def generate_shorts_script(client: anthropic.Anthropic, cot_summary: str, report_date: str) -> str:
    prompt = f"""You are Dezee, a forex trader from Lagos who trades COT contrarian strategy.

Today's COT data (report: {report_date}):
{cot_summary}

Write a punchy 60-second YouTube Shorts script.
Pick the SINGLE most interesting pair from the data.

Structure:
- Line 1: Hook question (e.g. "Is retail WRONG about EUR/USD again?")
- Lines 2-4: Quick COT stat — what retail is doing, what that means
- Line 5: The contrarian trade direction
- Line 6: CTA ("Follow for daily COT signals")

Keep it under 120 words. Fast-paced, confident, no filler words."""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def generate_title_and_description(client: anthropic.Anthropic, cot_summary: str, report_date: str) -> dict:
    prompt = f"""Based on this COT forex data for {report_date}:
{cot_summary}

Generate:
1. A YouTube video title (max 60 chars, SEO-optimised, curiosity-driven, includes "COT" or "Commitment of Traders")
2. A YouTube description (150-200 words, includes keywords: COT strategy, forex trading, commitment of traders, smart money, forex signals)
3. 10 YouTube tags (comma-separated)
4. A YouTube Shorts title (max 50 chars, punchy)

Return as JSON with keys: title, description, tags, shorts_title"""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text
    # Extract JSON block if wrapped in markdown
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    os.makedirs("data", exist_ok=True)

    print("Loading COT data...")
    cot_data = load_cot_data()
    featured = pick_featured_pairs(cot_data)
    cot_summary = build_cot_summary(featured)
    report_date = cot_data["pairs"][0]["report_date"] if cot_data["pairs"] else datetime.utcnow().strftime("%Y-%m-%d")

    print("Generating long-form script...")
    longform = generate_longform_script(client, cot_summary, report_date)

    print("Generating Shorts script...")
    shorts = generate_shorts_script(client, cot_summary, report_date)

    print("Generating titles and descriptions...")
    meta = generate_title_and_description(client, cot_summary, report_date)

    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "report_date": report_date,
        "featured_pairs": featured,
        "longform_script": longform,
        "shorts_script": shorts,
        "meta": meta,
    }

    with open("data/video_content.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nVideo title: {meta.get('title', 'N/A')}")
    print(f"Shorts title: {meta.get('shorts_title', 'N/A')}")
    print("Saved to data/video_content.json")


if __name__ == "__main__":
    main()
