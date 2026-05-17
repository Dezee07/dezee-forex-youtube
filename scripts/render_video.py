"""
Renders 3 educational Shorts videos per day.
Format: 1080x1920 vertical, dark trading style, bold text, male AI voiceover.
"""

import json
import os
import sys
import textwrap
import requests
from datetime import datetime

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

# Brand colors — dark trading aesthetic
BG          = (6, 8, 18)
BG_CARD     = (14, 18, 36)
GOLD        = (212, 175, 55)
GREEN       = (0, 210, 100)
RED         = (220, 45, 45)
WHITE       = (255, 255, 255)
GREY        = (150, 160, 180)
ACCENT      = (30, 100, 220)

SW, SH      = 1080, 1920
FPS         = 24
ELEVENLABS  = "https://api.elevenlabs.io/v1"
# Josh — deep authoritative male voice
VOICE_ID    = "TxGEqnHWrfWFTfGW9XjX"


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def draw_rrect(draw, xy, r, fill):
    x1, y1, x2, y2 = xy
    draw.rectangle([x1+r, y1, x2-r, y2], fill=fill)
    draw.rectangle([x1, y1+r, x2, y2-r], fill=fill)
    for cx, cy in [(x1,y1),(x2-2*r,y1),(x1,y2-2*r),(x2-2*r,y2-2*r)]:
        draw.ellipse([cx, cy, cx+2*r, cy+2*r], fill=fill)


def make_hook_slide(hook: str, topic: str) -> np.ndarray:
    img = Image.new("RGB", (SW, SH), BG)
    draw = ImageDraw.Draw(img)

    # Top gold bar
    draw.rectangle([(0, 0), (SW, 8)], fill=GOLD)

    # Channel tag
    font_tag = load_font(36, bold=True)
    draw.text((40, 30), "DEZEE FOREX", font=font_tag, fill=GOLD)
    draw.text((SW - 280, 30), "COT Education", font=load_font(32), fill=GREY)

    # Topic pill
    font_topic = load_font(34)
    draw_rrect(draw, (40, 90, SW - 40, 155), 12, BG_CARD)
    draw.text((60, 104), topic[:55], font=font_topic, fill=GREY)

    # Big hook text — center of screen
    font_hook = load_font(78, bold=True)
    lines = textwrap.wrap(hook, width=18)
    total_h = len(lines) * 96
    y = (SH // 2) - (total_h // 2) - 100
    for line in lines:
        draw.text((40, y), line, font=font_hook, fill=WHITE)
        y += 96

    # Red accent line under hook
    draw.rectangle([(40, y + 20), (SW - 40, y + 28)], fill=RED)

    # Bottom bar
    draw.rectangle([(0, SH - 100), (SW, SH)], fill=BG_CARD)
    font_sm = load_font(32)
    draw.text((40, SH - 72), "Follow for smart money education ↓", font=font_sm, fill=GOLD)

    return np.array(img)


def make_content_slide(lines_text: list[str], highlight_color=WHITE, slide_num: int = 1, total: int = 3) -> np.ndarray:
    img = Image.new("RGB", (SW, SH), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (SW, 8)], fill=GOLD)

    font_body = load_font(58, bold=True)
    font_sm   = load_font(34)

    # Progress dots
    dot_y = 40
    for i in range(total):
        color = GOLD if i < slide_num else GREY
        draw.ellipse([(SW//2 - total*25 + i*50, dot_y),
                      (SW//2 - total*25 + i*50 + 16, dot_y + 16)], fill=color)

    # Content text — centered vertically
    wrapped = []
    for line in lines_text:
        wrapped.extend(textwrap.wrap(line, width=22))
        wrapped.append("")

    total_h = len(wrapped) * 76
    y = max(120, (SH // 2) - (total_h // 2))

    for line in wrapped:
        if line == "":
            y += 30
            continue
        # Highlight key words in gold
        keywords = ["commercials", "institutions", "smart money", "retail", "banks",
                    "COT", "contrarian", "extreme", "reversal", "trap"]
        color = WHITE
        for kw in keywords:
            if kw.lower() in line.lower():
                color = GOLD
                break
        draw.text((40, y), line, font=font_body, fill=color)
        y += 76

    # Bottom
    draw.rectangle([(0, SH - 100), (SW, SH)], fill=BG_CARD)
    draw.text((40, SH - 72), "@D.e.z.e.e  •  COT Smart Money", font=font_sm, fill=GOLD)

    return np.array(img)


def make_cta_slide(cta: str) -> np.ndarray:
    img = Image.new("RGB", (SW, SH), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (SW, 8)], fill=GOLD)

    font_big = load_font(82, bold=True)
    font_med = load_font(54)
    font_sm  = load_font(38)

    # Central CTA
    y = SH // 2 - 220
    draw.text((40, y), "FOUND THIS\nUSEFUL?", font=font_big, fill=WHITE)
    y += 220

    draw.rectangle([(40, y), (SW - 40, y + 8)], fill=GOLD)
    y += 40

    for line in textwrap.wrap(cta, width=26):
        draw.text((40, y), line, font=font_med, fill=GREY)
        y += 70

    y += 20
    draw_rrect(draw, (40, y, SW - 40, y + 100), 16, GOLD)
    draw.text((SW//2 - 140, y + 22), "SUBSCRIBE NOW", font=font_sm, fill=BG)

    draw.rectangle([(0, SH - 100), (SW, SH)], fill=BG_CARD)
    draw.text((40, SH - 72), "@D.e.z.e.e  •  New video every day", font=font_sm, fill=GOLD)

    return np.array(img)


def make_thumbnail(short: dict, out_path: str):
    img = Image.new("RGB", (SW, SH), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (SW, 10)], fill=GOLD)
    draw.rectangle([(0, SH - 10), (SW, SH)], fill=GOLD)

    font_big = load_font(90, bold=True)
    font_med = load_font(52)
    font_sm  = load_font(38)

    # Hook as headline
    hook_lines = textwrap.wrap(short.get("script", "").split("\n")[0], width=16)
    y = 160
    for line in hook_lines[:4]:
        draw.text((40, y), line, font=font_big, fill=WHITE)
        y += 106

    draw.rectangle([(40, y + 20), (SW - 40, y + 28)], fill=RED)

    # Topic tag
    y += 60
    draw_rrect(draw, (40, y, SW - 40, y + 90), 14, BG_CARD)
    draw.text((60, y + 18), short["topic"][:40], font=font_med, fill=GOLD)

    # Channel
    y_bot = SH - 200
    draw_rrect(draw, (40, y_bot, 380, y_bot + 80), 14, GOLD)
    draw.text((60, y_bot + 14), "DEZEE FOREX", font=font_sm, fill=BG)
    draw.text((40, y_bot + 100), "COT Smart Money Education", font=font_sm, fill=GREY)

    img.save(out_path, "JPEG", quality=95)
    print(f"  Thumbnail: {out_path}")


def generate_voiceover(text: str, out_path: str) -> bool:
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if api_key:
        headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
        for model in ["eleven_turbo_v2_5", "eleven_turbo_v2", "eleven_multilingual_v2"]:
            payload = {
                "text": text,
                "model_id": model,
                "voice_settings": {"stability": 0.55, "similarity_boost": 0.80, "style": 0.2},
            }
            resp = requests.post(f"{ELEVENLABS}/text-to-speech/{VOICE_ID}",
                                 headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                print(f"  ElevenLabs voiceover ({model}): {out_path}")
                return True
            else:
                print(f"  ElevenLabs {model} failed ({resp.status_code}), trying next...")

    # Fallback: gTTS male voice
    try:
        from gtts import gTTS
        gTTS(text=text, lang="en", slow=False).save(out_path)
        print(f"  gTTS voiceover: {out_path}")
        return True
    except Exception as e:
        print(f"  TTS failed: {e}")
        return False


def split_script_into_slides(script: str) -> list[str]:
    """Split a script into 3-4 slide chunks for the video."""
    sentences = [s.strip() for s in script.replace("\n", " ").split(".") if s.strip()]
    slides = []
    chunk = []
    for i, s in enumerate(sentences):
        chunk.append(s + ".")
        if len(chunk) >= 2 or i == len(sentences) - 1:
            slides.append(" ".join(chunk))
            chunk = []
    return slides[:4] if slides else [script]


def render_short(short: dict, output_dir: str, idx: int):
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("assets/audio", exist_ok=True)

    script = short["script"]
    topic  = short["topic"]
    cta_line = script.split(".")[-2] + "." if "." in script else "Follow for more."

    # Generate voiceover
    audio_path = f"assets/audio/short_{idx}.mp3"
    print(f"  Generating voiceover...")
    has_audio = generate_voiceover(script, audio_path)

    # Build slides
    script_slides = split_script_into_slides(script)
    hook_text = script_slides[0] if script_slides else short["topic"]

    slides_data = [make_hook_slide(hook_text, topic)]
    for i, chunk in enumerate(script_slides[1:], 1):
        slides_data.append(make_content_slide([chunk], slide_num=i, total=len(script_slides)))
    slides_data.append(make_cta_slide(cta_line))

    # Durations
    total_dur = 55  # target 55 seconds
    hook_dur  = 5
    cta_dur   = 8
    mid_dur   = max(4, (total_dur - hook_dur - cta_dur) // max(len(slides_data) - 2, 1))
    durations = [hook_dur] + [mid_dur] * (len(slides_data) - 2) + [cta_dur]

    # Render
    clips = [ImageClip(arr, duration=dur) for arr, dur in zip(slides_data, durations)]
    video = concatenate_videoclips(clips, method="compose")

    if has_audio and os.path.exists(audio_path):
        audio = AudioFileClip(audio_path)
        dur   = min(audio.duration, video.duration)
        video = video.subclip(0, dur).set_audio(audio.subclip(0, dur))

    out_path = f"{output_dir}/short_{idx}.mp4"
    video.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac",
                          threads=4, preset="fast", logger=None)
    print(f"  Video: {out_path}")

    # Thumbnail
    make_thumbnail(short, f"{output_dir}/thumb_{idx}.jpg")

    return out_path


def main():
    if not MOVIEPY_OK:
        print("ERROR: moviepy not installed")
        sys.exit(1)

    with open("data/video_content.json") as f:
        content = json.load(f)

    shorts = content["shorts"]
    print(f"Rendering {len(shorts)} Shorts...")

    os.makedirs("output", exist_ok=True)
    paths = []
    for i, short in enumerate(shorts, 1):
        print(f"\n--- Short {i}/{len(shorts)}: {short['topic']} ---")
        path = render_short(short, "output", i)
        paths.append(path)

    print(f"\nAll {len(paths)} Shorts rendered.")


if __name__ == "__main__":
    main()
