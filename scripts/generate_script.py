"""
Generates 3 daily educational Shorts scripts using the 200-topic COT curriculum.
Topics are selected by date so each day gets different content automatically.
All content is professional English only.
"""

import anthropic
import json
import os
import sys
from datetime import date, datetime


VIRAL_HASHTAGS = [
    "#Forex", "#Trading", "#SmartMoney", "#ICT", "#COTReport",
    "#ForexTrading", "#InstitutionalTrading", "#DayTrading",
    "#ContrarianTrading", "#GoldTrading", "#Nasdaq", "#XAUUSD",
    "#GBPUSD", "#EURUSD", "#Liquidity", "#MarketMakers",
    "#PriceAction", "#ForexEducation", "#TradingPsychology", "#TradingStrategy"
]

HOOKS = [
    "Retail traders are trapped again…",
    "Commercials just did something huge.",
    "90% of traders ignore this signal.",
    "Banks are buying while retail is panicking.",
    "This is how institutions really trade.",
    "Most traders will never understand this.",
    "The crowd is always wrong at extremes.",
    "Smart money is quietly doing the opposite.",
    "Retail traders are making this mistake right now.",
    "This one concept separates profitable traders from losing ones.",
]

CTAS = [
    "Follow for weekly institutional analysis.",
    "Comment 'COT' if you want more of this.",
    "Save this before the next big market move.",
    "Follow to trade like institutions, not retail.",
    "Subscribe for daily smart money insights.",
    "Follow for more lessons the banks don't want you to know.",
]


def load_topics() -> list:
    with open("data/topics.json") as f:
        return json.load(f)["topics"]


def pick_topics_for_today(topics: list, count: int = 3) -> list:
    day_number = (date.today() - date(2024, 1, 1)).days
    selected = []
    for i in range(count):
        idx = (day_number * count + i) % len(topics)
        selected.append((idx, topics[idx]))
    return selected


def generate_short_script(client: anthropic.Anthropic, topic: str, hook: str, cta: str) -> str:
    prompt = f"""You are a professional forex trading educator who creates viral YouTube Shorts scripts.
Your channel teaches retail traders about institutional trading, COT reports, and smart money concepts.

STRICT RULES:
- Write ONLY in professional English. No slang, no pidgin.
- Maximum 120 words total (must fit in 45-60 seconds when spoken)
- Follow the EXACT structure below
- Use simple, clear language a beginner can understand
- Make it feel urgent and valuable

TOPIC: {topic}

HOOK (already provided, use this exactly): "{hook}"

STRUCTURE TO FOLLOW:
HOOK: [use the hook provided]
PROBLEM: [1-2 sentences — what mistake retail traders make related to this topic]
INSIGHT: [1-2 sentences — what smart money / commercials actually do]
EXPLANATION: [2-3 sentences — simple explanation of the concept]
LESSON: [1 sentence — the key takeaway]
CTA: "{cta}"

Write the full script now. No labels, no headers — just the flowing script as it would be spoken aloud."""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def generate_caption(client: anthropic.Anthropic, topic: str, script: str) -> str:
    prompt = f"""Write a YouTube Shorts caption for this video about: "{topic}"

The caption should:
- Be 2-3 sentences maximum
- Start with a compelling statement
- End with a question to drive comments
- Be professional English only

Then add these hashtags on a new line:
{' '.join(VIRAL_HASHTAGS[:12])}

Keep it short and punchy."""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def generate_video_title(topic: str) -> str:
    """Generate a short punchy title for the Short."""
    prefixes = [
        "Why ", "How ", "The Truth About ", "What ", "This Is Why ",
        "Institutions Know ", "Smart Money: ", "Stop Ignoring "
    ]
    day = (date.today() - date(2024, 1, 1)).days
    prefix = prefixes[day % len(prefixes)]
    title = f"{prefix}{topic} #Shorts"
    return title[:100]


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    os.makedirs("data", exist_ok=True)

    topics = load_topics()
    today_topics = pick_topics_for_today(topics, count=3)

    print(f"Today's topics: {[t for _, t in today_topics]}")

    day = (date.today() - date(2024, 1, 1)).days
    shorts = []

    for i, (topic_idx, topic) in enumerate(today_topics):
        print(f"\nGenerating Short {i+1}/3: {topic}")
        hook = HOOKS[(day + i * 3) % len(HOOKS)]
        cta  = CTAS[(day + i) % len(CTAS)]

        script  = generate_short_script(client, topic, hook, cta)
        caption = generate_caption(client, topic, script)
        title   = generate_video_title(topic)

        shorts.append({
            "index":      i + 1,
            "topic_idx":  topic_idx,
            "topic":      topic,
            "title":      title,
            "script":     script,
            "caption":    caption,
            "hashtags":   VIRAL_HASHTAGS,
        })

        print(f"  Title: {title}")
        print(f"  Script preview: {script[:80]}...")

    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "date":         date.today().isoformat(),
        "shorts":       shorts,
    }

    with open("data/video_content.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nGenerated {len(shorts)} Shorts scripts. Saved to data/video_content.json")


if __name__ == "__main__":
    main()
