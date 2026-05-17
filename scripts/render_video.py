"""
Renders a forex YouTube video from the generated script.
Creates a slideshow-style video with:
- Animated text overlays showing COT data
- Background forex chart images from Pexels
- AI voiceover via ElevenLabs TTS
- Subtitle burn-in for watch time / accessibility
"""

import json
import os
import sys
import requests
import textwrap
from pathlib import Path
from datetime import datetime

try:
    from moviepy.editor import (
        ImageClip, AudioFileClip, CompositeVideoClip,
        TextClip, concatenate_videoclips, ColorClip,
    )
    from moviepy.config import change_settings
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


ELEVENLABS_API = "https://api.elevenlabs.io/v1"
PEXELS_API = "https://api.pexels.com/v1"
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
FPS = 24


def fetch_background_images(query: str, count: int = 8) -> list[str]:
    """Fetch forex-related background images from Pexels."""
    api_key = os.environ.get("PEXELS_API_KEY", "")
    if not api_key:
        print("PEXELS_API_KEY not set — using solid colour backgrounds")
        return []

    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": count, "orientation": "landscape"}
    resp = requests.get(f"{PEXELS_API}/search", headers=headers, params=params, timeout=15)
    if resp.status_code != 200:
        return []

    photos = resp.json().get("photos", [])
    paths = []
    os.makedirs("assets/images", exist_ok=True)
    for i, photo in enumerate(photos):
        url = photo["src"]["large2x"]
        img_path = f"assets/images/bg_{i}.jpg"
        r = requests.get(url, timeout=15)
        with open(img_path, "wb") as f:
            f.write(r.content)
        paths.append(img_path)
    return paths


def generate_voiceover(text: str, output_path: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> bool:
    """Generate voiceover using ElevenLabs. Falls back to gTTS if unavailable."""
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if api_key:
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        resp = requests.post(
            f"{ELEVENLABS_API}/text-to-speech/{voice_id}",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            print(f"  ElevenLabs voiceover saved: {output_path}")
            return True
        else:
            print(f"  ElevenLabs error {resp.status_code}: {resp.text[:200]}")

    # Fallback: gTTS
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(output_path)
        print(f"  gTTS voiceover saved: {output_path}")
        return True
    except Exception as e:
        print(f"  TTS fallback failed: {e}")
        return False


def create_slide_image(
    title: str,
    body: str,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    bg_color: tuple = (10, 10, 30),
    accent_color: tuple = (0, 200, 100),
) -> np.ndarray:
    """Create a slide image with title and body text."""
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Gradient-style top bar
    for y in range(80):
        alpha = int(255 * (1 - y / 80))
        draw.line([(0, y), (width, y)], fill=accent_color)

    # Title
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 42)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = font_title

    title_wrapped = "\n".join(textwrap.wrap(title, width=40))
    draw.text((80, 120), title_wrapped, font=font_title, fill=(255, 255, 255))

    # Body text
    body_wrapped = "\n".join(textwrap.wrap(body, width=60))
    draw.text((80, 320), body_wrapped, font=font_body, fill=(200, 220, 200))

    # Bottom accent bar
    draw.rectangle([(0, height - 10), (width, height)], fill=accent_color)

    # Watermark
    draw.text((width - 300, height - 60), "@D.e.z.e.e | YouTube", font=font_body, fill=(100, 120, 100))

    return np.array(img)


def build_slides_from_script(script: str, pairs: list) -> list[dict]:
    """Split script into slides for the video."""
    slides = []

    # Slide 1: Hook/Title
    slides.append({
        "title": "COT CONTRARIAN FOREX ANALYSIS",
        "body": f"What retail traders are doing WRONG this week\nReport: {datetime.utcnow().strftime('%B %d, %Y')}",
        "duration": 5,
    })

    # Slides 2-N: One per featured pair
    for pair in pairs:
        direction = "CROWDED LONG — Banks SELLING" if pair["spec_net"] > 0 else "CROWDED SHORT — Banks BUYING"
        slides.append({
            "title": f"{pair['pair']} — {direction}",
            "body": (
                f"Retail Net Position: {pair['spec_net']:+,}\n"
                f"Weekly Change: {pair.get('spec_net_change', 0):+,}\n"
                f"Extreme Positioning: {'YES' if pair['extreme_positioning'] else 'No'}\n\n"
                f"COT Contrarian Signal: {pair['contrarian_bias']}"
            ),
            "duration": 12,
        })

    # Final slide: CTA
    slides.append({
        "title": "FOLLOW FOR DAILY COT SIGNALS",
        "body": "Subscribe | Like | Join the Telegram Signal Group\n@D.e.z.e.e on YouTube",
        "duration": 5,
    })

    return slides


def render_video(content: dict, output_path: str, is_shorts: bool = False):
    if not MOVIEPY_AVAILABLE or not PIL_AVAILABLE:
        print("ERROR: moviepy or Pillow not installed. Run: pip install moviepy Pillow")
        sys.exit(1)

    w = SHORTS_WIDTH if is_shorts else VIDEO_WIDTH
    h = SHORTS_HEIGHT if is_shorts else VIDEO_HEIGHT

    script = content["longform_script"] if not is_shorts else content["shorts_script"]
    pairs = content["featured_pairs"]
    slides = build_slides_from_script(script, pairs)

    # Generate voiceover
    os.makedirs("assets/audio", exist_ok=True)
    audio_path = "assets/audio/voiceover.mp3"
    print("Generating voiceover...")
    generate_voiceover(script[:4000], audio_path)  # ElevenLabs limit

    # Build video clips
    clips = []
    for slide in slides:
        img_array = create_slide_image(slide["title"], slide["body"], w, h)
        clip = ImageClip(img_array, duration=slide["duration"])
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")

    # Add audio if generated
    if os.path.exists(audio_path):
        audio = AudioFileClip(audio_path)
        if audio.duration < video.duration:
            video = video.subclip(0, audio.duration)
        else:
            audio = audio.subclip(0, video.duration)
        video = video.set_audio(audio)

    os.makedirs("output", exist_ok=True)
    print(f"Rendering video to {output_path}...")
    video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="fast",
        logger=None,
    )
    print(f"Video rendered: {output_path}")


def main():
    with open("data/video_content.json") as f:
        content = json.load(f)

    render_video(content, "output/longform.mp4", is_shorts=False)
    render_video(content, "output/shorts.mp4", is_shorts=True)


if __name__ == "__main__":
    main()
