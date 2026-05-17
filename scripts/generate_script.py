"""
Generates a YouTube video script using Claude API based on latest COT data.
All content is in professional English.
"""

import anthropic
import json
import os
import sys
from datetime import datetime


def load_cot_data() -> dict:
    with open("data/cot_latest.json") as f:
        return json.load(f)


def pick_featured_pairs(cot_data: dict, count: int = 3) -> list:
    pairs = cot_data["pairs"]
    return sorted(
        pairs,
        key=lambda p: (int(p["extreme_positioning"]), abs(p.get("spec_net_change", 0))),
        reverse=True,
    )[:count]


def build_cot_summary(pairs: list) -> str:
    lines = []
    for p in pairs:
        direction = "CROWDED LONG" if p["spec_net"] > 0 else "CROWDED SHORT"
        lines.append(
            f"- {p['pair']}: Speculators are {direction} "
            f"(net {p['spec_net']:+,}, change this week: {p.get('spec_net_change', 0):+,}). "
            f"Contrarian signal: {p['contrarian_bias']}. "
            f"Extreme positioning: {'YES' if p['extreme_positioning'] else 'No'}."
        )
    return "\n".join(lines)


def generate_longform_script(client: anthropic.Anthropic, cot_summary: str, report_date: str) -> str:
    prompt = f"""You are a professional forex trading educator who specialises in the COT (Commitment of Traders) contrarian strategy.
You run a YouTube channel that teaches traders how to read institutional positioning and trade against the retail crowd.

IMPORTANT: Write ONLY in clear, professional English. No slang, no pidgin, no regional dialect.

Today's COT data (CFTC report date: {report_date}):
{cot_summary}

Write a compelling, well-structured YouTube video script (5-7 minutes when read aloud, approximately 900 words).

FORMAT:
[HOOK] (15 seconds)
- Open with a powerful, specific statistic about what retail traders are doing wrong this week
- Example: "Right now, retail traders are sitting on their most crowded long position in EUR/USD in 6 months — and historically, that is a sell signal."

[INTRO] (30 seconds)
- Brief, confident introduction: who you are, what the COT report is, why it gives you an edge over 95% of retail traders

[COT BREAKDOWN] (3-4 minutes)
- Cover each featured currency pair in detail
- State the exact speculator net position and weekly change
- Explain what this positioning means: who is crowded, who is on the other side (commercials/smart money)
- Give the contrarian trade direction and what price levels to watch
- Use specific numbers from the data

[THE SMART MONEY EDGE] (1 minute)
- Explain the commercial hedger vs speculator dynamic
- Why fading extreme retail positioning has a statistical edge
- Keep this educational and grounded in logic

[CALL TO ACTION] (30 seconds)
- Ask viewers to subscribe, like, and comment their thoughts on the pairs covered
- Mention a Telegram signal group for live trade alerts

Tone: Confident, analytical, educational. Like a professional fund manager teaching a masterclass — not hype, not entertainment. Pure value."""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def generate_shorts_script(client: anthropic.Anthropic, cot_summary: str, report_date: str) -> str:
    prompt = f"""You are a professional forex educator specialising in COT analysis.

IMPORTANT: Write ONLY in clear, professional English.

COT data (report: {report_date}):
{cot_summary}

Write a punchy 60-second YouTube Shorts script. Pick the single most interesting pair.

FORMAT:
Line 1: Hook — one powerful question or statement (e.g. "Retail traders are more bullish on the Euro than they have been all year. Here is why that is actually a sell signal.")
Lines 2-5: Quick COT breakdown — what retail is doing, what the numbers say, what the smart money trade is
Line 6: Call to action ("Subscribe for daily COT analysis")

Under 120 words. Confident and professional. No hype words."""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def generate_meta(client: anthropic.Anthropic, cot_summary: str, report_date: str) -> dict:
    prompt = f"""Based on this COT forex analysis for week of {report_date}:
{cot_summary}

Generate the following in JSON format:
1. "title": YouTube video title (max 65 characters, SEO-optimised, professional, includes "COT" — no clickbait)
2. "description": YouTube description (200 words, includes keywords: COT report, commitment of traders, forex trading strategy, smart money forex, institutional forex)
3. "tags": list of 15 YouTube tags as an array
4. "shorts_title": YouTube Shorts title (max 55 characters, ends with #Shorts)
5. "thumbnail_headline": 4-6 word bold headline for the video thumbnail (e.g. "BANKS ARE SELLING THE EURO")
6. "thumbnail_subtext": 1 short line for thumbnail subtext (e.g. "COT Report Analysis | Week of May 17")

Return valid JSON only, no markdown."""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
        if text.startswith("json"):
            text = text[4:].strip()
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

    print("Generating titles, description, tags...")
    meta = generate_meta(client, cot_summary, report_date)

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

    print(f"\nTitle: {meta.get('title')}")
    print(f"Thumbnail: {meta.get('thumbnail_headline')}")
    print("Saved to data/video_content.json")


if __name__ == "__main__":
    main()
