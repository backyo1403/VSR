"""Render every scene to its own clip by stepping the page one frame at a time.

Each worker drives its own headless Edge on virtual time and pipes JPEG frames straight
into an ffmpeg process, so nothing lands on disk except the finished clip. Scenes are
independent, so four run at once — a single-threaded pass over ~5,600 frames takes the
better part of an hour.
"""
import io, json, os, subprocess, sys, threading, time, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import Browser

HERE   = os.path.dirname(os.path.abspath(__file__))
AUDIO  = os.path.join(HERE, "audio")
CLIPS  = os.path.join(HERE, "clips")
FFDIR  = r"C:\Users\Surface\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"
FFMPEG = os.path.join(FFDIR, "ffmpeg.exe")
FFPROBE= os.path.join(FFDIR, "ffprobe.exe")

FPS   = 24          # also a touch more filmic than 30
LEAD  = 350     # ms of scene before the narration starts
TAIL  = 520     # ms of scene after it ends
PAR   = 2          # measured: 4 workers thrash this 4-core box and halve throughput

os.makedirs(CLIPS, exist_ok=True)
_print_lock = threading.Lock()


def log(*a):
    with _print_lock:
        print(*a, flush=True)


def probe_ms(path):
    out = subprocess.check_output([FFPROBE, "-v", "error", "-show_entries",
                                   "format=duration", "-of", "csv=p=0", path])
    return float(out.decode().strip()) * 1000.0


def build_stage():
    """base.html (app minus the Firebase tags) + driver.html, rebuilt every run."""
    base = io.open(os.path.join(HERE, "stage", "base.html"), encoding="utf-8").read()
    drv = io.open(os.path.join(HERE, "driver.html"), encoding="utf-8").read()
    i = base.rindex("</body>")
    io.open(os.path.join(HERE, "stage", "stage.html"), "w", encoding="utf-8").write(
        base[:i] + drv + base[i:])


def plan():
    scenes = json.load(io.open(os.path.join(HERE, "script.json"), encoding="utf-8"))
    for s in scenes:
        mp3 = os.path.join(AUDIO, s["id"] + ".mp3")
        s["speech"] = probe_ms(mp3) if os.path.exists(mp3) else 0.0
        s["cues"] = {}
        cj = os.path.join(AUDIO, s["id"] + ".cues.json")
        if os.path.exists(cj):
            s["cues"] = json.load(io.open(cj, encoding="utf-8"))
        need = (LEAD + s["speech"] + TAIL) if s["speech"] else 0
        s["dur"] = max(s.get("minDur", 0), need)
        s["frames"] = int(round(s["dur"] / 1000.0 * FPS))
        s["clip"] = os.path.join(CLIPS, s["id"] + ".mp4")
    return scenes


def render(s):
    url = ("file:///" + HERE.replace("\\", "/") + "/stage/stage.html"
           + "?scene=" + s["id"]
           + "&lead=" + str(LEAD)
           + "&cues=" + urllib.parse.quote(json.dumps(s["cues"])))

    ff = subprocess.Popen(
        [FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
         "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
         "-pix_fmt", "yuv420p", "-r", str(FPS), s["clip"]],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    b = Browser(os.path.join(HERE, "cdpprofile"))
    t0 = time.time()
    try:
        b.load(url)
        if not b.eval("window.__vidReady === true"):
            # the scene builds on load; give it more settled virtual time if it is slow
            b.advance(1500)
        b.eval("window.__vidStart()")
        step = 1000.0 / FPS
        for i in range(s["frames"]):
            b.advance(step)
            ff.stdin.write(b.shot_jpeg())
            if i and i % 90 == 0:
                log("    %-14s %4d/%4d" % (s["id"], i, s["frames"]))
    finally:
        try:
            ff.stdin.close()
        except Exception:
            pass
        ff.wait()
        b.close()
    log("  clip %-14s %4d frames  %5.1f MB  %5.1f min" % (
        s["id"], s["frames"], os.path.getsize(s["clip"]) / 1e6, (time.time() - t0) / 60))


def main():
    build_stage()
    scenes = plan()
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    if only:
        scenes = [s for s in scenes if s["id"] in only]
    if "--resume" in sys.argv:
        # a run can take well over an hour on this machine; keep finished clips
        keep = [s for s in scenes if os.path.exists(s["clip"]) and os.path.getsize(s["clip"]) > 0]
        for s in keep:
            log("  have  %-16s (skipping)" % s["id"])
        scenes = [s for s in scenes if s not in keep]

    total = sum(s["frames"] for s in scenes)
    log("scenes: %d   frames: %d   ~%.1fs of video" % (len(scenes), total, total / FPS))
    for s in scenes:
        log("  %-16s %6.2fs  %4d frames  cues=%s" % (
            s["id"], s["dur"] / 1000.0, s["frames"], ",".join(s["cues"].keys()) or "-"))

    queue = list(scenes)
    lock = threading.Lock()
    errors = []

    def worker():
        while True:
            with lock:
                if not queue:
                    return
                s = queue.pop(0)
            # a dropped socket costs the whole scene, so give each one a second go
            for attempt in (1, 2, 3):
                try:
                    render(s)
                    break
                except Exception as e:
                    log("  attempt %d failed for %s: %r" % (attempt, s["id"], e))
                    if attempt == 3:
                        errors.append((s["id"], repr(e)))

    threads = [threading.Thread(target=worker) for _ in range(min(PAR, len(scenes)))]
    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    log("capture done in %.1f min" % ((time.time() - t0) / 60))
    if errors:
        sys.exit("failed: " + repr(errors))


if __name__ == "__main__":
    main()
