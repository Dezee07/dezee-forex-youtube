"""
Renders a professional forex YouTube video and thumbnail.
- Dark finance-style design with branded colors
- Clean text slides with COT data visualised as bar charts
- AI voiceover via ElevenLabs (fallback: gTTS)
- Generates YouTube thumbnail image
"""

import json
import os
import sys
import textwrap
import requests
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

# Brand colors
BG_DARK      = (8, 12, 24)
BG_CARD      = (16, 22, 42)
GOLD         = (212, 175, 55)
GREEN_BULL   = (0, 200, 100)
RED_BEAR     = (220, 50, 50)
WHITE        = (255, 255, 255)
GREY         = (160, 170, 190)
ACCENT_BLUE  = (30, 120, 220)

W, H         = 1920, 1080
SW, SH       = 1080, 1920   # Shorts dimensions
FPS          = 24
ELEVENLABS   = "https://api.elevenlabs.io/v1"


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_rounded_rect(draw, xy, radius, fill):
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.ellipse([x1, y1, x1 + 2*radius, y1 + 2*radius], fill=fill)
    draw.ellipse([x2 - 2*radius, y1, x2, y1 + 2*radius], fill=fill)
    draw.ellipse([x1, y2 - 2*radius, x1 + 2*radius, y2], fill=fill)
    draw.ellipse([x2 - 2*radius, y2 - 2*radius, x2, y2], fill=fill)


def make_title_slide(title: str, subtitle: str, date_str: str, w=W, h=H) -> np.ndarray:
    img = Image.new("RGB", (w, h), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Top gold bar
    draw.rectangle([(0, 0), (w, 6)], fill=GOLD)

    # Channel name top-left
    font_chan = load_font(32)
    draw.text((60, 30), "DEZEE FOREX  |  COT ANALYSIS", font=font_chan, fill=GOLD)

    # Date top-right
    draw.text((w - 340, 30), date_str, font=font_chan, fill=GREY)

    # Large headline
    font_title = load_font(96, bold=True)
    font_sub   = load_font(48)

    lines = textwrap.wrap(title.upper(), width=28)
    y = 200
    for line in lines:
        draw.text((60, y), line, font=font_title, fill=WHITE)
        y += 110

    # Gold divider
    draw.rectangle([(60, y + 20), (300, y + 26)], fill=GOLD)

    # Subtitle
    y += 60
    for line in textwrap.wrap(subtitle, width=55):
        draw.text((60, y), line, font=font_sub, fill=GREY)
        y += 58

    # Bottom bar
    draw.rectangle([(0, h - 80), (w, h)], fill=BG_CARD)
    font_sm = load_font(30)
    draw.text((60, h - 55), "Subscribe for daily COT signals  •  @D.e.z.e.e", font=font_sm, fill=GOLD)

    return np.array(img)


def make_pair_slide(pair: dict, w=W, h=H) -> np.ndarray:
    img = Image.new("RGB", (w, h), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Top bar
    draw.rectangle([(0, 0), (w, 6)], fill=GOLD)

    is_bearish = pair["contrarian_bias"] == "SHORT"
    signal_color = RED_BEAR if is_bearish else GREEN_BULL
    signal_label = "SELL SIGNAL" if is_bearish else "BUY SIGNAL"

    font_pair  = load_font(90, bold=True)
    font_label = load_font(48, bold=True)
    font_body  = load_font(40)
    font_sm    = load_font(32)
    font_chan  = load_font(28)

    # Pair name
    draw.text((60, 30), pair["pair"], font=font_pair, fill=WHITE)

    # Signal badge
    badge_x = 60 + len(pair["pair"]) * 52 + 40
    draw_rounded_rect(draw, (badge_x, 42, badge_x + 240, 110), 12, signal_color)
    draw.text((badge_x + 20, 52), signal_label, font=font_label, fill=WHITE)

    # Divider
    draw.rectangle([(60, 130), (w - 60, 134)], fill=BG_CARD)

    # Stats cards
    spec_net = pair["spec_net"]
    spec_change = pair.get("spec_net_change", 0)
    comm_net = pair.get("comm_net", 0)

    cards = [
        ("SPECULATOR NET", f"{spec_net:+,}", GREEN_BULL if spec_net > 0 else RED_BEAR),
        ("WEEKLY CHANGE",  f"{spec_change:+,}", GREEN_BULL if spec_change > 0 else RED_BEAR),
        ("COMMERCIAL NET", f"{comm_net:+,}", GREEN_BULL if comm_net > 0 else RED_BEAR),
        ("EXTREME POS.",   "YES" if pair["extreme_positioning"] else "NO",
         RED_BEAR if pair["extreme_positioning"] else GREEN_BULL),
    ]

    card_w = (w - 120 - 60) // 4
    for i, (label, value, color) in enumerate(cards):
        cx = 60 + i * (card_w + 20)
        draw_rounded_rect(draw, (cx, 160, cx + card_w, 320), 16, BG_CARD)
        draw.text((cx + 20, 175), label, font=font_sm, fill=GREY)
        draw.text((cx + 20, 225), value, font=font_label, fill=color)

    # COT positioning bar chart
    bar_y = 360
    draw.text((60, bar_y), "SPECULATOR POSITIONING", font=font_sm, fill=GREY)
    bar_y += 40

    long_pct  = pair.get("spec_pct_long", 50)
    short_pct = pair.get("spec_pct_short", 50)
    total = long_pct + short_pct if (long_pct + short_pct) > 0 else 100
    bar_total_w = w - 120
    long_bar_w = int(bar_total_w * long_pct / total)

    draw.rectangle([(60, bar_y), (60 + long_bar_w, bar_y + 60)], fill=GREEN_BULL)
    draw.rectangle([(60 + long_bar_w, bar_y), (60 + bar_total_w, bar_y + 60)], fill=RED_BEAR)
    draw.text((70, bar_y + 12), f"LONG {long_pct:.1f}%", font=font_sm, fill=WHITE)
    draw.text((60 + bar_total_w - 200, bar_y + 12), f"SHORT {short_pct:.1f}%", font=font_sm, fill=WHITE)

    # Analysis text
    bar_y += 100
    crowded = "CROWDED LONG — retail is overly bullish" if spec_net > 0 else "CROWDED SHORT — retail is overly bearish"
    action = "Contrarian traders look to SELL into strength" if is_bearish else "Contrarian traders look to BUY into weakness"
    smart = "Commercials (banks/hedgers) are positioned OPPOSITE to retail"

    for line in [crowded, action, smart]:
        draw.text((60, bar_y), f"• {line}", font=font_body, fill=WHITE)
        bar_y += 60

    # Extreme warning
    if pair["extreme_positioning"]:
        bar_y += 10
        draw_rounded_rect(draw, (60, bar_y, w - 60, bar_y + 70), 12, (60, 20, 20))
        draw.text((80, bar_y + 15), "⚠  EXTREME POSITIONING ALERT — Highest probability contrarian setup", font=font_body, fill=GOLD)

    # Bottom bar
    draw.rectangle([(0, h - 80), (w, h)], fill=BG_CARD)
    draw.text((60, h - 55), "DEZEE FOREX  •  @D.e.z.e.e  •  Subscribe for daily COT signals", font=font_chan, fill=GOLD)

    return np.array(img)


def make_outro_slide(w=W, h=H) -> np.ndarray:
    img = Image.new("RGB", (w, h), BG_DARK)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (w, 6)], fill=GOLD)

    font_big = load_font(88, bold=True)
    font_med = load_font(52)
    font_sm  = load_font(38)

    draw.text((60, 120), "FOUND THIS USEFUL?", font=font_big, fill=WHITE)
    draw.rectangle([(60, 240), (400, 246)], fill=GOLD)

    items = [
        "SUBSCRIBE for weekly COT analysis every Monday",
        "LIKE the video — it helps the algorithm show this to more traders",
        "COMMENT your thoughts on any of these pairs",
        "JOIN the Telegram group for live trade alerts",
    ]
    y = 280
    for item in items:
        draw.text((60, y), f"→  {item}", font=font_med, fill=GREY)
        y += 80

    draw.rectangle([(60, y + 20), (w - 60, y + 26)], fill=BG_CARD)

    draw.text((60, y + 50), "Next COT report drops every Friday.", font=font_sm, fill=GOLD)
    draw.text((60, y + 100), "Trade the smart money. Not the crowd.", font=font_sm, fill=WHITE)

    draw.rectangle([(0, h - 80), (w, h)], fill=BG_CARD)
    font_chan = load_font(28)
    draw.text((60, h - 55), "DEZEE FOREX  •  @D.e.z.e.e  •  COT Contrarian Strategy", font=font_chan, fill=GOLD)

    return np.array(img)


def make_thumbnail(meta: dict, pairs: list, w=1280, h=720) -> str:
    img = Image.new("RGB", (w, h), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Left gold stripe
    draw.rectangle([(0, 0), (12, h)], fill=GOLD)

    # Background card right side
    draw_rounded_rect(draw, (w // 2, 40, w - 40, h - 40), 20, BG_CARD)

    font_headline = load_font(88, bold=True)
    font_sub      = load_font(42)
    font_sm       = load_font(34)
    font_tag      = load_font(36, bold=True)

    # Main headline (left side)
    headline = meta.get("thumbnail_headline", "SMART MONEY EXPOSED").upper()
    lines = textwrap.wrap(headline, width=14)
    y = 80
    for line in lines:
        draw.text((40, y), line, font=font_headline, fill=WHITE)
        y += 100

    # Gold underline
    draw.rectangle([(40, y + 10), (360, y + 18)], fill=GOLD)

    # Subtext
    subtext = meta.get("thumbnail_subtext", "COT Report Analysis")
    draw.text((40, y + 40), subtext, font=font_sub, fill=GREY)

    # Right side: pair signal cards
    card_x = w // 2 + 30
    card_y = 80
    for pair in pairs[:3]:
        is_sell = pair["contrarian_bias"] == "SHORT"
        color = RED_BEAR if is_sell else GREEN_BULL
        label = "SELL" if is_sell else "BUY"
        draw_rounded_rect(draw, (card_x, card_y, w - 60, card_y + 90), 14, color)
        draw.text((card_x + 20, card_y + 8), pair["pair"], font=font_tag, fill=WHITE)
        draw.text((card_x + 20, card_y + 46), f"{label}  •  Net {pair['spec_net']:+,}", font=font_sm, fill=WHITE)
        card_y += 110

    # COT badge bottom left
    draw_rounded_rect(draw, (40, h - 100, 310, h - 30), 12, GOLD)
    draw.text((60, h - 86), "COT ANALYSIS", font=font_tag, fill=BG_DARK)

    # Channel name
    draw.text((w - 340, h - 55), "@D.e.z.e.e", font=font_sub, fill=GOLD)

    path = "output/thumbnail.jpg"
    img.save(path, "JPEG", quality=95)
    print(f"Thumbnail saved: {path}")
    return path


def generate_voiceover(text: str, path: str) -> bool:
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    # Use a professional male English voice
    voice_id = "TxGEqnHWrfWFTfGW9XjX"  # Josh — deep, authoritative

    if api_key:
        headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
        payload = {
            "text": text[:4500],
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {"stability": 0.6, "similarity_boost": 0.8},
        }
        resp = requests.post(f"{ELEVENLABS}/text-to-speech/{voice_id}",
                             headers=headers, json=payload, timeout=90)
        if resp.status_code == 200:
            with open(path, "wb") as f:
                f.write(resp.content)
            print(f"ElevenLabs voiceover: {path}")
            return True
        else:
            print(f"ElevenLabs error {resp.status_code}: {resp.text[:300]}")

    # Fallback: gTTS
    try:
        from gtts import gTTS
        gTTS(text=text[:4500], lang="en", slow=False).save(path)
        print(f"gTTS voiceover: {path}")
        return True
    except Exception as e:
        print(f"TTS failed: {e}")
        return False


def render_video(slides_arrays: list, durations: list, audio_path: str, out_path: str):
    if not MOVIEPY_OK:
        print("ERROR: moviepy not installed")
        sys.exit(1)

    clips = [ImageClip(arr, duration=dur) for arr, dur in zip(slides_arrays, durations)]
    video = concatenate_videoclips(clips, method="compose")

    if os.path.exists(audio_path):
        audio = AudioFileClip(audio_path)
        dur = min(audio.duration, video.duration)
        video = video.subclip(0, dur).set_audio(audio.subclip(0, dur))

    os.makedirs("output", exist_ok=True)
    video.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac",
                          threads=4, preset="fast", logger=None)
    print(f"Video rendered: {out_path}")


def main():
    with open("data/video_content.json") as f:
        content = json.load(f)

    meta = content["meta"]
    pairs = content["featured_pairs"]
    script = content["longform_script"]
    date_str = f"Week of {content['report_date']}"

    os.makedirs("output", exist_ok=True)
    os.makedirs("assets/audio", exist_ok=True)

    # Generate thumbnail
    make_thumbnail(meta, pairs)

    # Generate voiceover
    audio_path = "assets/audio/voiceover.mp3"
    print("Generating voiceover...")
    generate_voiceover(script, audio_path)

    # Build slides
    title_slide = make_title_slide(meta["title"], meta.get("thumbnail_subtext", "COT Contrarian Analysis"), date_str)
    pair_slides  = [make_pair_slide(p) for p in pairs]
    outro_slide  = make_outro_slide()

    slides   = [title_slide] + pair_slides + [outro_slide]
    # Title 6s, each pair 15s, outro 8s
    durations = [6] + [15] * len(pair_slides) + [8]

    print("Rendering long-form video...")
    render_video(slides, durations, audio_path, "output/longform.mp4")

    # Shorts: title + best pair only (vertical crop simulation using same images)
    print("Rendering Short...")
    short_audio = "assets/audio/shorts_vo.mp3"
    generate_voiceover(content["shorts_script"], short_audio)
    best_pair = pair_slides[0] if pair_slides else title_slide
    shorts_slides    = [title_slide, best_pair, outro_slide]
    shorts_durations = [4, 12, 4]
    render_video(shorts_slides, shorts_durations, short_audio, "output/shorts.mp4")

    print("\nAll rendering complete.")


if __name__ == "__main__":
    main()
