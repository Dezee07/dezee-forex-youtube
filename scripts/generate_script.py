"""
Generates 3 daily educational Shorts scripts using the 200-topic COT curriculum.
Topics are selected by date so each day gets different content automatically.
All content is professional English only.
"""

import anthropic
import json
import os
import random
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
    "Commercials are buying while fundamentals turn bullish.",
    "Retail traders missed the macro shift.",
    "Open Interest just confirmed institutional accumulation.",
    "This fundamental change could fuel Gold higher for months.",
    "Why hedge funds are trapped against smart money.",
    "Seasonality and COT now align perfectly.",
    "This is how institutions build massive positions.",
    "The Dollar trend is changing because of this.",
    "Commercials positioned early again.",
    "Why this move could continue for weeks.",
]

CTAS = [
    "Follow for weekly institutional analysis.",
    "Comment 'COT' if you want more of this.",
    "Save this before the next big market move.",
    "Follow to trade like institutions, not retail.",
    "Subscribe for daily smart money insights.",
    "Follow for more lessons the banks don't want you to know.",
    "Drop a comment — what market are you watching right now?",
    "Share this with a trader who needs to see it.",
    "Follow for the edge retail traders will never have.",
]

VIRAL_TITLE_PREFIXES = [
    "Commercials Just Turned Bullish on",
    "Retail Traders Are Trapped Again —",
    "This Signal Changes Everything About",
    "Why Smart Money Is Buying",
    "The Real Reason",
    "Institutions Saw This Move Early —",
    "COT Report Reveals Hidden Truth About",
    "Why Fundamentals Matter More Than Indicators —",
    "How Banks Really Trade",
    "This Is Why Most Traders Lose —",
    "Smart Money Just Did This on",
    "Open Interest Just Revealed",
]


def load_topics() -> list:
    with open("data/topics.json") as f:
        return json.load(f)["topics"]


def pick_topics_for_today(topics: list, count: int = 3) -> list:
    # Seed by date so each day is different but reproducible if re-run
    day_seed = (date.today() - date(2024, 1, 1)).days
    rng = random.Random(day_seed)

    # Split into old (0-199) and new (200+) topics
    old_topics = [(i, t) for i, t in enumerate(topics) if i < 200]
    new_topics = [(i, t) for i, t in enumerate(topics) if i >= 200]

    # Always mix: ~2 from old, ~1 from new (or all old if new list short)
    selected = []
    if new_topics and count >= 2:
        selected += rng.sample(old_topics, min(count - 1, len(old_topics)))
        selected += rng.sample(new_topics, min(1, len(new_topics)))
    else:
        selected = rng.sample(old_topics, min(count, len(old_topics)))

    rng.shuffle(selected)
    return selected[:count]


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
INSIGHT: [1-2 sentences — what smart money / commercials / institutions actually do differently]
EXPLANATION: [2-3 sentences — simple, clear explanation of the concept — if the topic involves seasonality, fundamentals, open interest or macro, explain those specifically]
LESSON: [1 sentence — the single most important takeaway]
CTA: "{cta}"

ADDITIONAL GUIDANCE BY TOPIC TYPE:
- Seasonality topics: explain the seasonal pattern, why it happens, how institutions exploit it
- Fundamentals topics: explain the economic concept simply, link it to currency/market direction
- Open Interest topics: explain what OI rising/falling means for trend strength
- Macro + COT topics: explain how fundamentals and positioning work together

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


def generate_video_title(topic: str, seed: int = 0) -> str:
    rng = random.Random(seed)
    prefix = rng.choice(VIRAL_TITLE_PREFIXES)
    # Shorten topic if needed
    short_topic = topic[:50] if len(topic) > 50 else topic
    title = f"{prefix} {short_topic} #Shorts"
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
        title   = generate_video_title(topic, seed=day + i * 7)

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
