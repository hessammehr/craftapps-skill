#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10.1", "imageio-ffmpeg>=0.5"]
# ///
"""Record a coding agent driving VectorCraft and turn it into a captioned demo video.

  record_demo.py launch [--port 12346]
      start a clean VectorCraft (its own throwaway profile: no recent files or user documents) with a
      control port, sized 1600×1000 for recording (macOS path; pass --app for elsewhere)
  record_demo.py claude OUT PROMPT.md [PROMPT2.md …] [--port 12346] [--claude PATH] [--model M]
      for each prompt: log it, run `claude -p` (stream-json; follow-up prompts --continue the session)
      while sampling the VectorCraft window; Claude's messages and tool calls become the captions
  record_demo.py record OUT [--port 12346] [--interval 1.0]
      only sample the window (until OUT/STOP exists or Ctrl-C), for sessions driven some other way.
      Point CRAFT_LOG at OUT/events.jsonl so craft.py logs calls, and mark prompts/narration/results with
      `craft.py note --prompt|--result|TEXT`
  record_demo.py compose OUT --out demo.mp4 [--gif demo.gif] [--speed 6] [--title T] [--footer F]
      intro → for each prompt: typed prompt card, time-lapse with captions, result card → outro

OUT holds frames/<unix time>.jpg (window screenshots, 1920 px wide) and events.jsonl
({t, type: prompt|note|call|result, text|command|path}). Video encoding uses the ffmpeg binary that
the imageio-ffmpeg wheel ships, so nothing besides uv is needed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "craftapps" / "scripts"))
W, H, FPS = 1280, 800, 30


# ----------------------------------------------------------------------------- recording
def sampler(out: Path, port: int, interval: float, stop: threading.Event, a_app: str = "vectorcraft"):
    from craft import Craft, CraftError as VCError

    vc = Craft(a_app, port=port)
    (out / "frames").mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp()) / "shot.png"
    last = None
    while not stop.is_set() and not (out / "STOP").exists():
        t0 = time.time()
        try:
            vc.call("ui.screenshot", {"path": str(tmp)})
            im = Image.open(tmp).convert("RGB")
            im = im.resize((1920, round(im.height * 1920 / im.width)), Image.LANCZOS)
            h = hashlib.md5(im.resize((160, 100)).tobytes()).hexdigest()
            if h != last:  # unchanged windows are skipped, so idle time costs nothing
                im.save(out / "frames" / f"{t0:.3f}.jpg", quality=88)
                last = h
        except (VCError, OSError) as e:
            print("screenshot failed:", e, file=sys.stderr)
        stop.wait(max(0.0, interval - (time.time() - t0)))


def log(out: Path, ev: dict):
    with open(out / "events.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.time(), **ev}, ensure_ascii=False) + "\n")


def cmd_record(a):
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "STOP").unlink(missing_ok=True)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    print(f"recording; export CRAFT_LOG={out / 'events.jsonl'}; stop with: touch {out / 'STOP'}")
    try:
        sampler(out, a.port, a.interval, stop)
    except KeyboardInterrupt:
        pass


def cmd_claude(a):
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    th = threading.Thread(target=sampler, args=(out, a.port, a.interval, stop), daemon=True)
    th.start()
    env = dict(os.environ, VECTORCRAFT_CONTROL_PORT=str(a.port), CRAFT_LOG=str(out / "events.jsonl"))
    work = out / "work"
    work.mkdir(exist_ok=True)
    try:
        for i, pf in enumerate(a.prompts):
            prompt = Path(pf).read_text().strip()
            log(out, {"type": "prompt", "text": prompt})
            cmd = [a.claude, "-p", prompt, "--output-format", "stream-json", "--verbose",
                   "--allowedTools", *a.allow]
            if i:
                cmd.append("--continue")
            if a.model:
                cmd += ["--model", a.model]
            with subprocess.Popen(cmd, cwd=work, env=env, stdout=subprocess.PIPE, text=True) as p, \
                    open(out / f"claude-{i + 1}.jsonl", "w") as raw:
                for line in p.stdout:
                    raw.write(line)
                    try:
                        ev = json.loads(line)
                    except ValueError:
                        continue
                    for c in (ev.get("message") or {}).get("content") or []:
                        if ev.get("type") == "assistant" and c.get("type") == "text" and c["text"].strip():
                            log(out, {"type": "note", "text": c["text"].strip()})
                        elif ev.get("type") == "assistant" and c.get("type") == "tool_use":
                            inp = c.get("input") or {}
                            log(out, {"type": "tool", "text": inp.get("description") or inp.get("command") or c["name"]})
            time.sleep(2)
    finally:
        stop.set()
        th.join()


def cmd_launch(a):
    prof = Path(tempfile.mkdtemp(prefix="vectorcraft-demo-profile-"))
    env = dict(os.environ, VECTORCRAFT_CONFIG_DIR=str(prof))
    subprocess.Popen([a.app, "--control", str(a.port)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    from craft import Craft, CraftError as VCError

    vc = Craft("vectorcraft", port=a.port)
    for _ in range(60):
        try:
            vc.call("ui.inspect")
            break
        except VCError:
            time.sleep(1)
    vc.call("ui.resize", {"width": 1600, "height": 1000})
    vc.call("ui.focus")
    print(f"VectorCraft ready on port {a.port} (profile {prof})")


# ----------------------------------------------------------------------------- composing
def font(size, mono=False, bold=False):
    names = (["Menlo.ttc", "DejaVuSansMono.ttf", "Consolas.ttf"] if mono else
             (["HelveticaNeue.ttc", "Helvetica.ttc", "DejaVuSans-Bold.ttf", "arialbd.ttf"] if bold else
              ["HelveticaNeue.ttc", "Helvetica.ttc", "DejaVuSans.ttf", "arial.ttf"]))
    dirs = ["/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/usr/share/fonts/truetype/dejavu",
            "C:/Windows/Fonts"]
    for n in names:
        for d in dirs:
            p = Path(d) / n
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size, index=1 if bold and p.suffix == ".ttc" else 0)
                except OSError:
                    continue
    return ImageFont.load_default(size)


BG, FG, ACCENT, DIM = (24, 26, 33), (236, 238, 242), (217, 119, 87), (150, 155, 168)


def card_intro(title, subtitle):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((W // 2, H // 2 - 30), title, font=font(56, bold=True), fill=FG, anchor="mm")
    d.text((W // 2, H // 2 + 40), subtitle, font=font(26), fill=DIM, anchor="mm")
    return im


def card_prompt(text, shown, label):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((80, 110, W - 80, H - 110), radius=18, fill=(34, 37, 46), outline=(60, 64, 76), width=2)
    for i, c in enumerate([(237, 106, 94), (245, 191, 79), (98, 197, 84)]):
        d.ellipse((108 + i * 26, 132, 124 + i * 26, 148), fill=c)
    d.text((W // 2, 140), label, font=font(20), fill=DIM, anchor="mm")
    f = font(25, mono=True)
    lines = []
    for para in text[:shown].split("\n"):
        lines += textwrap.wrap(para, 68) or [""]
    y = 190
    for i, ln in enumerate(lines[-16:]):
        d.text((120, y), ("> " if i == 0 else "  ") + ln, font=f, fill=ACCENT if i == 0 else FG)
        y += 34
    if shown < len(text) or int(time.time() * 2) % 2:
        d.rectangle((120 + 15 * (len(lines[-1]) + 2), y - 34 + 4, 120 + 15 * (len(lines[-1]) + 2) + 12, y - 6), fill=FG)
    return im


def card_result(path, caption):
    im = Image.new("RGB", (W, H), (245, 246, 248))
    art = Image.open(path).convert("RGBA")
    k = min((W - 120) / art.width, (H - 170) / art.height)
    art = art.resize((max(1, int(art.width * k)), max(1, int(art.height * k))), Image.LANCZOS)
    x, y = (W - art.width) // 2, (H - 70 - art.height) // 2 + 10
    bg = Image.new("RGBA", art.size, (255, 255, 255, 255))
    im.paste(Image.alpha_composite(bg, art).convert("RGB"), (x, y))
    d = ImageDraw.Draw(im)
    d.rectangle((x - 1, y - 1, x + art.width, y + art.height), outline=(200, 203, 210))
    d.text((W // 2, H - 45), caption, font=font(24, bold=True), fill=(40, 42, 50), anchor="mm")
    return im


def crop(frame: Image.Image, box):
    """box: fractions (x0, y0, x1, y1) of the window to keep, e.g. the canvas without the side panels."""
    if not box:
        return frame
    w, h = frame.size
    return frame.crop((round(box[0] * w), round(box[1] * h), round(box[2] * w), round(box[3] * h)))


def overlay(frame: Image.Image, caption: str, sub: str, badge: str):
    im = frame.copy()
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    d.rectangle((0, H - 92, W, H), fill=(14, 15, 20, 225))
    lines = textwrap.wrap(caption, 92)[:2]
    for i, ln in enumerate(lines):
        d.text((24, H - 84 + i * 30), ln, font=font(24), fill=FG)
    if sub:
        d.text((W - 24, H - 20), sub, font=font(16, mono=True), fill=DIM, anchor="rb")
    d.rounded_rectangle((W - 150, 14, W - 14, 50), radius=10, fill=(217, 119, 87, 235))
    d.text((W - 82, 32), badge, font=font(19, bold=True), fill=(255, 255, 255), anchor="mm")
    return Image.alpha_composite(im.convert("RGBA"), o).convert("RGB")


def cmd_compose(a):
    import imageio_ffmpeg

    out = Path(a.out_dir).resolve()
    events = [json.loads(l) for l in (out / "events.jsonl").read_text().splitlines() if l.strip()]
    frames = sorted((float(p.stem), p) for p in (out / "frames").glob("*.jpg"))
    prompts = [e for e in events if e["type"] == "prompt"]
    if not prompts:
        sys.exit("no prompt events in events.jsonl")
    writer = imageio_ffmpeg.write_frames(a.out, (W, H), fps=FPS, codec="libx264", quality=None,
                                         output_params=["-crf", "22", "-preset", "slow",
                                                        "-movflags", "+faststart"])
    writer.send(None)

    def emit(im, seconds):
        b = im.tobytes()
        for _ in range(max(1, round(seconds * FPS))):
            writer.send(b)

    emit(card_intro(a.title, a.subtitle), 2.5)
    for i, pe in enumerate(prompts):
        t0 = pe["t"]
        t1 = prompts[i + 1]["t"] if i + 1 < len(prompts) else float("inf")
        label = f"Prompt {i + 1}" if len(prompts) > 1 else "Prompt"
        txt = pe["text"]
        n = len(txt)
        steps = max(1, int(min(6.0, n / 45) * FPS))  # type at ≤6 s
        for s in range(steps + 1):
            writer.send(card_prompt(txt, int(n * s / steps), label).tobytes())
        emit(card_prompt(txt, n, label), 1.8)
        seg = [(t, p) for t, p in frames if t0 <= t < t1]
        evs = [e for e in events if t0 <= e["t"] < t1]
        real = (seg[-1][0] - seg[0][0]) if len(seg) > 1 else 0
        for j, (t, p) in enumerate(seg):
            nxt = seg[j + 1][0] if j + 1 < len(seg) else t + 1
            dur = min(max((nxt - t) / a.speed, 0.12), 1.2)
            notes = [e for e in evs if e["t"] <= t and e["type"] in ("note", "tool")]
            calls = [e for e in evs if e["t"] <= t and e["type"] == "call" and e.get("command")]
            cap = notes[-1]["text"] if notes else "…"
            sub = f"vc ▸ {calls[-1]['command']}" if calls else ""
            emit(overlay(crop(Image.open(p).convert("RGB"), a.crop), cap, sub, f"×{a.speed:g} speed"), dur)
        res = [e for e in evs if e["type"] == "result" and Path(e.get("path", "")).exists()]
        if res:
            emit(card_result(res[-1]["path"], f"Result {i + 1}" + (f" — {res[-1]['caption']}" if res[-1].get('caption') else "")), 3.5)
        print(f"segment {i + 1}: {len(seg)} frames over {real:.0f} s real time")
    emit(card_intro(a.footer, a.footer_sub), 3.0)
    writer.close()
    print("wrote", a.out)
    if a.gif:
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        vf = f"fps={a.gif_fps},scale={a.gif_width}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4"
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", a.out, "-vf", vf, a.gif], check=True)
        print("wrote", a.gif, f"({Path(a.gif).stat().st_size / 1e6:.1f} MB)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("launch")
    p.add_argument("--port", type=int, default=12346)
    p.add_argument("--app", default="/Applications/VectorCraft.app/Contents/MacOS/VectorCraft")
    p = sp.add_parser("record")
    p.add_argument("out")
    p.add_argument("--port", type=int, default=12346)
    p.add_argument("--interval", type=float, default=1.0)
    p = sp.add_parser("claude")
    p.add_argument("out")
    p.add_argument("prompts", nargs="+")
    p.add_argument("--port", type=int, default=12346)
    p.add_argument("--interval", type=float, default=1.0)
    p.add_argument("--claude", default="claude")
    p.add_argument("--model")
    p.add_argument("--allow", nargs="+", default=["Bash(uv run:*)", "Bash(ls:*)", "Bash(mkdir:*)", "Read", "Write", "Edit", "Skill"])
    p = sp.add_parser("compose")
    p.add_argument("out_dir")
    p.add_argument("--out", required=True)
    p.add_argument("--gif")
    p.add_argument("--gif-width", type=int, default=720)
    p.add_argument("--gif-fps", type=int, default=10)
    p.add_argument("--speed", type=float, default=6)
    p.add_argument("--crop", type=lambda v: tuple(float(x) for x in v.split(",")), metavar="X0,Y0,X1,Y1",
                   help="part of the window to show, as fractions (keep 16:10, e.g. 0,0.08,0.78,0.86)")
    p.add_argument("--title", default="VectorCraft agent skill")
    p.add_argument("--subtitle", default="from a plain-language prompt to a publication figure")
    p.add_argument("--footer", default="github.com/hessammehr/craftapps-skill")
    p.add_argument("--footer-sub", default="an agent skill for the Craft apps")
    a = ap.parse_args()
    {"launch": cmd_launch, "record": cmd_record, "claude": cmd_claude, "compose": cmd_compose}[a.cmd](a)


if __name__ == "__main__":
    main()
