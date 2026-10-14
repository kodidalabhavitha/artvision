#!/usr/bin/env python3
"""ArtVision CLI: add paintings + videos, rebuild the AR page, publish."""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONT = ROOT / "frontend"
ASSETS = FRONT / "assets"
DATA = FRONT / "paintings.json"
MIND = ASSETS / "targets1.mind"
COMPILE_DIR = ROOT / "compile-images"
LIVE_URL = "https://kodidalabhavitha.github.io/artvision/"

PAGE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Art Lens</title>
  <script src="https://aframe.io/releases/1.5.0/aframe.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/mind-ar@1.2.5/dist/mindar-image-aframe.prod.js"></script>
  <style>body { margin: 0; }</style>
</head>
<body>
  <a-scene
    mindar-image="imageTargetSrc: ./assets/targets1.mind; autoStart: true;"
    color-space="sRGB"
    renderer="colorManagement: true, physicallyCorrectLights"
    vr-mode-ui="enabled: false"
    device-orientation-permission-ui="enabled: false">
    <a-assets>
%%VIDEOS%%
    </a-assets>
    <a-camera position="0 0 0" look-controls="enabled: false"></a-camera>
%%TARGETS%%
  </a-scene>
  <script>
    document.querySelectorAll(".painting").forEach(function (t) {
      var v = document.getElementById(t.dataset.video);
      t.addEventListener("targetFound", function () { v.play(); });
      t.addEventListener("targetLost", function () { v.pause(); });
    });
  </script>
</body>
</html>
"""


def run(cmd, check=True):
    return subprocess.run(cmd, cwd=ROOT, check=check)


def image_size(path):
    try:
        out = subprocess.check_output(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)], text=True)
        w = int(re.search(r"pixelWidth: (\d+)", out).group(1))
        h = int(re.search(r"pixelHeight: (\d+)", out).group(1))
        return w, h
    except Exception:
        print("Could not read image size (sips missing); assuming square.")
        return 1, 1


def load():
    if DATA.exists():
        return json.loads(DATA.read_text())
    if (ASSETS / "peacock.jpg").exists():  # adopt your existing first painting
        w, h = image_size(ASSETS / "peacock.jpg")
        return [{"slug": "peacock", "title": "Peacock",
                 "image": "assets/peacock.jpg", "video": "assets/peacock.mp4",
                 "aspect": round(h / w, 4)}]
    return []


def save(items):
    DATA.write_text(json.dumps(items, indent=2) + "\n")


def build():
    items = load()
    save(items)
    videos = "\n".join(
        '      <video id="v-%s" src="./%s" preload="auto" loop="true" '
        'playsinline webkit-playsinline muted></video>' % (p["slug"], p["video"])
        for p in items)
    targets = "\n".join(
        '    <a-entity class="painting" mindar-image-target="targetIndex: %d" data-video="v-%s">\n'
        '      <a-video src="#v-%s" width="1" height="%s" position="0 0 0"></a-video>\n'
        '    </a-entity>' % (i, p["slug"], p["slug"], p["aspect"])
        for i, p in enumerate(items))
    (FRONT / "index.html").write_text(
        PAGE.replace("%%VIDEOS%%", videos).replace("%%TARGETS%%", targets))

    # Numbered copies: alphabetical order in Finder == targetIndex order
    shutil.rmtree(COMPILE_DIR, ignore_errors=True)
    COMPILE_DIR.mkdir()
    for i, p in enumerate(items):
        shutil.copy(FRONT / p["image"], COMPILE_DIR / ("%02d-%s.jpg" % (i, p["slug"])))
    gi = ROOT / ".gitignore"
    text = gi.read_text() if gi.exists() else ""
    if "compile-images/" not in text:
        gi.write_text(text + ("" if text.endswith("\n") or not text else "\n") + "compile-images/\n")
    return items


def check_mind(items):
    if not items:
        return
    if not MIND.exists():
        print("! frontend/assets/targets1.mind is missing.")
    elif MIND.stat().st_mtime < max((FRONT / p["image"]).stat().st_mtime for p in items):
        print("! targets1.mind is older than your newest image: recompile it.")


def steps():
    print("\nRECOMPILE (needed whenever you add a painting):")
    print("  1. Run:  open compile-images")
    print("  2. Open https://hiukim.github.io/mind-ar-js-doc/tools/compile")
    print("  3. Select ALL images in that folder, upload, click Start, then Download compiled")
    print("  4. Save it as frontend/assets/targets1.mind (replace the old file)")
    print("  5. Run:  python3 tools/artvision.py publish -m \"Add painting\"")


def cmd_add(a):
    image, video = Path(a.image).expanduser(), Path(a.video).expanduser()
    for f in (image, video):
        if not f.exists():
            sys.exit("File not found: %s" % f)
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is missing. Run: brew install ffmpeg")
    items = load()
    title = a.title or image.stem
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "painting"
    if any(p["slug"] == slug for p in items):
        sys.exit("'%s' already exists. Use a different --title." % slug)
    ASSETS.mkdir(parents=True, exist_ok=True)

    img_out = ASSETS / (slug + ".jpg")
    if shutil.which("sips"):  # converts HEIC/PNG/etc. to JPEG on macOS
        run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "85",
             str(image), "--out", str(img_out)])
    else:
        shutil.copy(image, img_out)

    vid_out = ASSETS / (slug + ".mp4")
    run(["ffmpeg", "-y", "-i", str(video), "-an", "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-crf", "28", "-vf", "scale='min(720,iw)':-2",
         "-movflags", "+faststart", str(vid_out)])

    w, h = image_size(img_out)
    items.append({"slug": slug, "title": title, "image": "assets/%s.jpg" % slug,
                  "video": "assets/%s.mp4" % slug, "aspect": round(h / w, 4)})
    save(items)
    build()
    print("\nAdded '%s' as target #%d." % (title, len(items) - 1))
    steps()


def cmd_build(a):
    items = build()
    print("Rebuilt frontend/index.html with %d painting(s)." % len(items))
    check_mind(items)
    steps()


def cmd_list(a):
    items = load()
    for i, p in enumerate(items):
        print("#%d  %-20s %s  |  %s" % (i, p["title"], p["image"], p["video"]))
    check_mind(items)


def cmd_publish(a):
    build()
    run(["git", "add", "-A"])
    run(["git", "commit", "-m", a.message], check=False)
    run(["git", "push", "origin", "HEAD"])
    sha = subprocess.check_output(
        ["git", "subtree", "split", "--prefix", "frontend", "HEAD"],
        cwd=ROOT, text=True).strip()
    run(["git", "push", "origin", sha + ":refs/heads/gh-pages", "--force"])
    print("\nPublished. Live in about a minute: " + LIVE_URL)


def main():
    p = argparse.ArgumentParser(description="ArtVision CLI")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add", help="add a painting image + video")
    s.add_argument("image")
    s.add_argument("video")
    s.add_argument("--title")
    s.set_defaults(fn=cmd_add)
    sub.add_parser("build", help="regenerate index.html").set_defaults(fn=cmd_build)
    sub.add_parser("list", help="show all paintings").set_defaults(fn=cmd_list)
    s = sub.add_parser("publish", help="commit, push, and publish to GitHub Pages")
    s.add_argument("-m", "--message", default="Update paintings")
    s.set_defaults(fn=cmd_publish)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
