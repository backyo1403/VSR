"""Join the captured scene clips and lay the soundtrack over them.

Video: clips are already real animation (see capture.py), so this stage only crossfades
them and tops and tails the film.

Audio: three layers on one timeline —
  voice   each scene's narration, delayed to LEAD ms after its own scene appears
  sfx     a bell on each prize line, at the cue times the narration was built around
  music   the synthesised bed, sidechain-ducked by the voice so it drops under speech
          and comes back up in the gaps, instead of sitting at one timid level throughout
"""
import io, json, os, subprocess, sys

HERE   = os.path.dirname(os.path.abspath(__file__))
AUDIO  = os.path.join(HERE, "audio")
CLIPS  = os.path.join(HERE, "clips")
FFDIR  = r"C:\Users\Surface\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"
FFMPEG = os.path.join(FFDIR, "ffmpeg.exe")
FFPROBE= os.path.join(FFDIR, "ffprobe.exe")

FPS  = 24
XF   = 0.60      # crossfade between scenes
LEAD = 350       # must match capture.py: how late the narration starts inside a scene
OUT  = os.path.join(HERE, "VNA_SkyRace_GioiThieu.mp4")


def probe(path, stream=None):
    cmd = [FFPROBE, "-v", "error"]
    if stream:
        cmd += ["-select_streams", stream]
    cmd += ["-show_entries", ("stream=duration" if stream else "format=duration"),
            "-of", "csv=p=0", path]
    return float(subprocess.check_output(cmd).decode().strip().split(",")[0])


def make_ting():
    """A short two-partial bell for the prize reveals."""
    p = os.path.join(AUDIO, "ting.wav")
    if os.path.exists(p):
        return p
    subprocess.run([
        FFMPEG, "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=1568:duration=1.6",
        "-f", "lavfi", "-i", "sine=frequency=2349:duration=1.6",
        "-f", "lavfi", "-i", "sine=frequency=3136:duration=1.6",
        "-filter_complex",
        "[0:a]volume=0.60[a];[1:a]volume=0.30[b];[2:a]volume=0.14[c];"
        "[a][b][c]amix=inputs=3:normalize=0,"
        "afade=t=in:st=0:d=0.004,afade=t=out:st=0.02:d=1.55:curve=exp,"
        "volume=0.9[out]",
        "-map", "[out]", "-ac", "2", "-ar", "48000", p], check=True)
    return p


scenes = json.load(io.open(os.path.join(HERE, "script.json"), encoding="utf-8"))
for s in scenes:
    s["clip"] = os.path.join(CLIPS, s["id"] + ".mp4")
    s["mp3"] = os.path.join(AUDIO, s["id"] + ".mp3")
    if not os.path.exists(s["clip"]):
        sys.exit("missing clip: " + s["clip"])
    s["clipdur"] = probe(s["clip"], "v:0")
    s["voice"] = os.path.exists(s["mp3"])
    cj = os.path.join(AUDIO, s["id"] + ".cues.json")
    s["cues"] = json.load(io.open(cj, encoding="utf-8")) if os.path.exists(cj) else {}

starts, t = [], 0.0
for s in scenes:
    starts.append(t)
    t += s["clipdur"] - XF
total = t + XF

print("timeline:")
for i, s in enumerate(scenes):
    print("  %-16s start %6.2fs  len %5.2fs%s" % (
        s["id"], starts[i], s["clipdur"], "" if s["voice"] else "   (silent)"))
print("  TOTAL %.2fs" % total)

ting = make_ting()

# ---- inputs: clips, then narration mp3s, then music, then the bell
inputs = []
for s in scenes:
    inputs += ["-i", s["clip"]]
voice_idx = {}
n = len(scenes)
k = n
for s in scenes:
    if s["voice"]:
        inputs += ["-i", s["mp3"]]
        voice_idx[s["id"]] = k
        k += 1
music_idx = k
inputs += ["-i", os.path.join(HERE, "music.wav")]
k += 1
ting_idx = k
inputs += ["-i", ting]

filters = []

# ---- video: crossfade chain, then top and tail
prev, acc = "[0:v]", scenes[0]["clipdur"]
for i in range(1, n):
    off = acc - XF
    out = "[x%d]" % i
    filters.append("%s[%d:v]xfade=transition=fade:duration=%.3f:offset=%.3f%s"
                   % (prev, i, XF, off, out))
    prev, acc = out, off + scenes[i]["clipdur"]
filters.append("%sfade=t=in:st=0:d=1.0,fade=t=out:st=%.3f:d=1.2[vout]"
               % (prev, total - 1.2))

# ---- voice
vlabels = []
for i, s in enumerate(scenes):
    if not s["voice"]:
        continue
    ms = int(round((starts[i] + LEAD / 1000.0) * 1000))
    lab = "[v%d]" % i
    filters.append("[%d:a]adelay=%d|%d,aformat=channel_layouts=stereo%s"
                   % (voice_idx[s["id"]], ms, ms, lab))
    vlabels.append(lab)
filters.append("%samix=inputs=%d:duration=longest:normalize=0,volume=1.35[voice]"
               % ("".join(vlabels), len(vlabels)))
filters.append("[voice]asplit=3[voice_mix][voice_key][voice_pad]")
filters.append("[voice_pad]atrim=0:0.01,volume=0[voice_null]")

# ---- bells on the prize lines
prize = next(s for s in scenes if s["id"] == "13_giaithuong")
pstart = starts[scenes.index(prize)]
tlabels = []
filters.append("[%d:a]asplit=%d%s" % (ting_idx, len(prize["cues"]),
                                      "".join("[tsrc%d]" % j for j in range(len(prize["cues"])))))
for j, (cue, cms) in enumerate(sorted(prize["cues"].items(), key=lambda kv: kv[1])):
    at = int(round((pstart + LEAD / 1000.0 + cms / 1000.0) * 1000))
    lab = "[t%d]" % j
    filters.append("[tsrc%d]adelay=%d|%d,volume=%.2f%s" % (j, at, at, 0.34 if j else 0.44, lab))
    tlabels.append(lab)
filters.append("%samix=inputs=%d:duration=longest:normalize=0[sfx]" % ("".join(tlabels), len(tlabels)))

# ---- music, ducked by the voice
filters.append("[%d:a]atrim=0:%.3f,asetpts=N/SR/TB,volume=0.34,"
               "afade=t=out:st=%.3f:d=3.0[musraw]" % (music_idx, total, max(0.0, total - 3.0)))
filters.append("[musraw][voice_key]sidechaincompress="
               "threshold=0.030:ratio=9:attack=18:release=520:makeup=1[musduck]")

filters.append("[voice_mix][sfx][musduck][voice_null]amix=inputs=4:duration=first:normalize=0,"
               "alimiter=limit=0.94,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[aout]")

cmd = [FFMPEG, "-y"] + inputs + [
    "-filter_complex", ";".join(filters),
    "-map", "[vout]", "-map", "[aout]",
    "-c:v", "libx264", "-preset", "medium", "-crf", "21",
    "-pix_fmt", "yuv420p", "-r", str(FPS),
    "-c:a", "aac", "-b:a", "192k", "-ac", "2",
    "-movflags", "+faststart", OUT]

print("joining...")
r = subprocess.run(cmd, capture_output=True)
if r.returncode != 0:
    sys.stderr.write(r.stderr.decode("utf-8", "replace")[-5000:])
    sys.exit(r.returncode)

vdur = probe(OUT, "v:0")
print("wrote %s  %.1f MB  video %.1fs  container %.1fs"
      % (OUT, os.path.getsize(OUT) / 1e6, vdur, probe(OUT)))
if abs(vdur - total) > 1.2:
    sys.exit("video stream %.1fs vs timeline %.1fs" % (vdur, total))
print("OK")
