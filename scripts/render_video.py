"""
Renders 3 educational Shorts videos per day.
Format: 1080x1920 vertical, AI-generated backgrounds, bold text overlays, male voiceover.
Uses Pollinations AI for free background image generation.
"""

import json
import os
import sys
import textwrap
import requests
import time
from urllib.parse import quote
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

# Colors
GOLD    = (212, 175, 55)
GREEN   = (0, 220, 100)
RED     = (220, 40, 40)
WHITE   = (255, 255, 255)
BLACK   = (0, 0, 0)
DARK    = (8, 10, 20)

SW, SH  = 1080, 1920
FPS     = 24

ELEVENLABS = "https://api.elevenlabs.io/v1"
# Adam — confirmed free-tier deep male voice
VOICE_ID   = "pNInz6obpgDQGcFmaJgB"

# Image prompts per topic category
IMAGE_PROMPTS = {
    "commercial":  "dramatic dark trading floor with glowing screens banks forex professional cinematic 8k",
    "retail":      "lone trader stressed at computer screens red market crash dramatic cinematic",
    "reversal":    "dramatic stock chart reversal candle neon glow dark background cinematic 4k",
    "liquidity":   "deep ocean dark water with gold light beams institutional forex cinematic",
    "psychology":  "human brain glowing neural network financial charts dark dramatic cinematic",
    "gold":        "gold bars shining dramatic dark background forex market cinematic 8k",
    "default":     "professional forex trading desk multiple monitors glowing charts dark cinematic dramatic 8k",
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold
            else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def get_image_prompt(topic: str) -> str:
    topic_lower = topic.lower()
    for key, prompt in IMAGE_PROMPTS.items():
        if key in topic_lower:
            return prompt
    return IMAGE_PROMPTS["default"]


def fetch_ai_background(topic: str, seed: int = 42) -> Image.Image:
    """Fetch AI-generated background from Pollinations AI (free, no API key)."""
    prompt = get_image_prompt(topic)
    encoded = quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true&seed={seed}&model=flux"

    print(f"  Fetching AI background image...")
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=45)
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content)).convert("RGB")
                img = img.resize((SW, SH), Image.LANCZOS)
                print(f"  AI background fetched.")
                return img
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            time.sleep(3)

    # Fallback: dark gradient
    print("  Using fallback dark background.")
    img = Image.new("RGB", (SW, SH), DARK)
    draw = ImageDraw.Draw(img)
    for y in range(SH):
        darkness = int(20 + 10 * (y / SH))
        draw.line([(0, y), (SW, y)], fill=(darkness, darkness + 5, darkness + 15))
    return img


def darken_image(img: Image.Image, factor: float = 0.35) -> Image.Image:
    """Darken image so text is readable on top."""
    enhancer = ImageEnhance.Brightness(img)
    return enhancer.enhance(factor)


def add_vignette(img: Image.Image) -> Image.Image:
    """Add dark vignette edges for cinematic look."""
    vignette = Image.new("RGB", img.size, (0, 0, 0))
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = img.width // 2, img.height // 2
    for r in range(min(cx, cy), 0, -1):
        alpha = int(255 * (1 - r / min(cx, cy)) ** 1.5)
        draw.ellipse([(cx-r, cy-r), (cx+r, cy+r)], fill=alpha)
    vignette.putalpha(mask)
    result = img.copy()
    result.paste(vignette, mask=mask)
    return result


def draw_text_with_shadow(draw, pos, text, font, fill, shadow_offset=4):
    x, y = pos
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 180))
    draw.text((x, y), text, font=font, fill=fill)


def make_hook_slide(hook: str, topic: str, bg_img: Image.Image) -> np.ndarray:
    img = darken_image(bg_img.copy(), 0.3)
    draw = ImageDraw.Draw(img)

    font_tag  = load_font(38, bold=True)
    font_hook = load_font(82, bold=True)
    font_sm   = load_font(36)

    # Top gold bar
    draw.rectangle([(0, 0), (SW, 10)], fill=GOLD)

    # Channel tag pill
    draw.rectangle([(0, 20), (SW, 110)], fill=(0, 0, 0, 150))
    draw.text((40, 32), "DEZEE FOREX", font=font_tag, fill=GOLD)
    draw.text((SW - 340, 32), "Smart Money Education", font=load_font(32), fill=WHITE)

    # Hook text — large, bold, centered vertically
    lines = textwrap.wrap(hook.upper(), width=20)
    total_h = len(lines) * 100
    y = (SH // 2) - (total_h // 2) - 60
    for line in lines:
        draw_text_with_shadow(draw, (40, y), line, font_hook, WHITE)
        y += 100

    # Gold underline
    draw.rectangle([(40, y + 16), (SW - 40, y + 26)], fill=GOLD)

    # Topic label
    draw.rectangle([(0, SH - 140), (SW, SH - 80)], fill=(0, 0, 0, 160))
    draw.text((40, SH - 130), topic, font=font_sm, fill=GOLD)

    # Bottom CTA bar
    draw.rectangle([(0, SH - 80), (SW, SH)], fill=GOLD)
    draw.text((SW//2 - 240, SH - 68), "FOLLOW FOR MORE  ↓", font=font_tag, fill=BLACK)

    return np.array(img)


def make_content_slide(text: str, bg_img: Image.Image, is_key_slide: bool = False) -> np.ndarray:
    img = darken_image(bg_img.copy(), 0.25)
    draw = ImageDraw.Draw(img)

    font_body = load_font(64, bold=True)
    font_sm   = load_font(36)

    draw.rectangle([(0, 0), (SW, 10)], fill=GOLD)

    # Semi-transparent content box
    box_y1 = SH // 2 - 350
    box_y2 = SH // 2 + 350
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([(20, box_y1), (SW - 20, box_y2)], fill=(0, 0, 0, 160))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Text inside box
    lines = textwrap.wrap(text, width=22)
    total_h = len(lines) * 82
    y = (SH // 2) - (total_h // 2)
    for line in lines:
        # Highlight COT keywords in gold
        keywords = ["commercial", "institution", "smart money", "retail", "bank",
                    "COT", "contrarian", "extreme", "reversal", "trap", "liquidity"]
        color = WHITE
        for kw in keywords:
            if kw.lower() in line.lower():
                color = GOLD
                break
        draw_text_with_shadow(draw, (50, y), line, font_body, color)
        y += 82

    # Red accent if key insight
    if is_key_slide:
        draw.rectangle([(40, box_y2 + 10), (SW - 40, box_y2 + 18)], fill=RED)

    draw.rectangle([(0, SH - 80), (SW, SH)], fill=GOLD)
    draw.text((SW//2 - 200, SH - 68), "@D.e.z.e.e  •  COT Education", font=font_sm, fill=BLACK)

    return np.array(img)


def make_cta_slide(cta: str, bg_img: Image.Image) -> np.ndarray:
    img = darken_image(bg_img.copy(), 0.2)
    draw = ImageDraw.Draw(img)

    font_big  = load_font(90, bold=True)
    font_med  = load_font(58, bold=True)
    font_sm   = load_font(40)

    draw.rectangle([(0, 0), (SW, 10)], fill=GOLD)

    # Dark overlay
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([(0, SH//2 - 400), (SW, SH - 90)], fill=(0, 0, 0, 170))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    y = SH // 2 - 360
    draw_text_with_shadow(draw, (50, y), "FOUND THIS", font_big, WHITE)
    draw_text_with_shadow(draw, (50, y + 100), "USEFUL?", font_big, GOLD)

    draw.rectangle([(50, y + 218), (SW - 50, y + 228)], fill=RED)

    y += 260
    for line in textwrap.wrap(cta, width=24):
        draw_text_with_shadow(draw, (50, y), line, font_med, WHITE)
        y += 72

    # Subscribe button
    y += 20
    draw.rectangle([(50, y), (SW - 50, y + 110)], fill=GOLD)
    draw.text((SW//2 - 200, y + 22), "SUBSCRIBE NOW ↑", font=font_sm, fill=BLACK)

    draw.rectangle([(0, SH - 80), (SW, SH)], fill=GOLD)
    draw.text((SW//2 - 220, SH - 68), "New video posted daily", font=font_sm, fill=BLACK)

    return np.array(img)


def make_thumbnail(short: dict, bg_img: Image.Image, out_path: str):
    img = darken_image(bg_img.copy(), 0.28)
    draw = ImageDraw.Draw(img)

    font_big  = load_font(96, bold=True)
    font_med  = load_font(54, bold=True)
    font_sm   = load_font(38)
    font_tag  = load_font(40, bold=True)

    # Top bar
    draw.rectangle([(0, 0), (SW, 12)], fill=GOLD)

    # Script first line as hook
    script_lines = short.get("script", "").strip().split("\n")
    hook = script_lines[0] if script_lines else short["topic"]
    hook = hook[:80]

    # Dark overlay top section
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([(0, 0), (SW, 600)], fill=(0, 0, 0, 150))
    ov_draw.rectangle([(0, SH - 280), (SW, SH)], fill=(0, 0, 0, 170))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Channel tag
    draw.rectangle([(30, 25), (370, 100)], fill=GOLD)
    draw.text((50, 36), "DEZEE FOREX", font=font_tag, fill=BLACK)

    # Hook text — large and bold
    lines = textwrap.wrap(hook.upper(), width=18)
    y = 130
    for line in lines[:4]:
        draw_text_with_shadow(draw, (30, y), line, font_big, WHITE)
        y += 108

    # Gold underline
    draw.rectangle([(30, y + 10), (SW - 30, y + 20)], fill=GOLD)

    # Topic at bottom
    draw.text((30, SH - 240), short["topic"], font=font_med, fill=GOLD)
    draw.text((30, SH - 170), "COT Smart Money Education", font=font_sm, fill=WHITE)

    # Bottom bar
    draw.rectangle([(0, SH - 90), (SW, SH)], fill=GOLD)
    draw.text((SW//2 - 160, SH - 78), "@D.e.z.e.e", font=font_tag, fill=BLACK)

    img.save(out_path, "JPEG", quality=95)
    print(f"  Thumbnail saved: {out_path}")


def generate_voiceover(text: str, out_path: str) -> bool:
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if api_key:
        # Try confirmed free-tier male voices in order
        male_voices = [
            ("pNInz6obpgDQGcFmaJgB", "Adam"),     # Deep male, free tier
            ("ErXwobaYiN019PkySvjV", "Antoni"),    # Male, free tier
            ("VR6AewLTigWG4xSOukaG", "Arnold"),    # Male, free tier
        ]
        for voice_id, name in male_voices:
            for model in ["eleven_turbo_v2_5", "eleven_multilingual_v2"]:
                headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
                payload = {
                    "text": text,
                    "model_id": model,
                    "voice_settings": {"stability": 0.6, "similarity_boost": 0.75},
                }
                resp = requests.post(
                    f"{ELEVENLABS}/text-to-speech/{voice_id}",
                    headers=headers, json=payload, timeout=60,
                )
                if resp.status_code == 200:
                    with open(out_path, "wb") as f:
                        f.write(resp.content)
                    print(f"  Voiceover: {name} ({model})")
                    return True
                else:
                    print(f"  {name}/{model} failed ({resp.status_code}), trying next...")

    # Fallback: gTTS — male-sounding (use en-us which is deeper)
    try:
        from gtts import gTTS
        gTTS(text=text, lang="en", tld="com", slow=False).save(out_path)
        print(f"  gTTS voiceover saved.")
        return True
    except Exception as e:
        print(f"  TTS error: {e}")
        return False


def split_script(script: str) -> list[str]:
    sentences = [s.strip() + "." for s in script.replace("\n", " ").split(".") if s.strip()]
    slides, chunk = [], []
    for i, s in enumerate(sentences):
        chunk.append(s)
        if len(chunk) >= 2 or i == len(sentences) - 1:
            slides.append(" ".join(chunk))
            chunk = []
    return slides[:4] or [script]


def render_short(short: dict, output_dir: str, idx: int):
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("assets/audio", exist_ok=True)

    topic  = short["topic"]
    script = short["script"]

    # Fetch ONE AI background image for all slides in this Short
    bg = fetch_ai_background(topic, seed=idx * 13 + 7)

    # Voiceover
    audio_path = f"assets/audio/short_{idx}.mp3"
    has_audio  = generate_voiceover(script, audio_path)

    # Build slides
    parts = split_script(script)
    hook_text = parts[0] if parts else topic
    cta_line  = parts[-1] if len(parts) > 1 else "Follow for more smart money education."

    slides_arrays = [make_hook_slide(hook_text, topic, bg)]
    for i, chunk in enumerate(parts[1:-1], 1):
        slides_arrays.append(make_content_slide(chunk, bg, is_key_slide=(i == 1)))
    if len(parts) > 1:
        slides_arrays.append(make_cta_slide(cta_line, bg))

    # Durations: 55 sec total target
    hook_d = 6
    cta_d  = 8
    n_mid  = max(len(slides_arrays) - 2, 0)
    mid_d  = max(5, (55 - hook_d - cta_d) // max(n_mid, 1))
    if len(slides_arrays) == 1:
        durations = [55]
    elif len(slides_arrays) == 2:
        durations = [hook_d, cta_d]
    else:
        durations = [hook_d] + [mid_d] * n_mid + [cta_d]

    # Render video
    clips = [ImageClip(arr, duration=d) for arr, d in zip(slides_arrays, durations)]
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
    make_thumbnail(short, bg, f"{output_dir}/thumb_{idx}.jpg")

    return out_path


def main():
    if not MOVIEPY_OK:
        print("ERROR: moviepy not installed")
        sys.exit(1)

    with open("data/video_content.json") as f:
        content = json.load(f)

    shorts = content["shorts"]
    print(f"Rendering {len(shorts)} Shorts with AI backgrounds...")
    os.makedirs("output", exist_ok=True)

    rendered = 0
    for i, short in enumerate(shorts, 1):
        print(f"\n--- Short {i}/{len(shorts)}: {short['topic']} ---")
        try:
            render_short(short, "output", i)
            rendered += 1
        except Exception as e:
            print(f"  ERROR rendering Short {i}: {e}")
            import traceback; traceback.print_exc()

    if rendered == 0:
        print("ERROR: No Shorts rendered — aborting.")
        sys.exit(1)
    print(f"\n{rendered}/{len(shorts)} Shorts rendered.")


if __name__ == "__main__":
    main()
