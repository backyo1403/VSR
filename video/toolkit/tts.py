"""Narration, synthesised phrase by phrase, plus the cue times that drive the picture.

The service does not emit WordBoundary events for Vietnamese — only one SentenceBoundary
per utterance — so there is no way to ask it when a given word was spoken. Instead each
scene is written as a list of short phrases: every phrase is synthesised on its own, so
its start time in the finished track is known exactly, and a phrase can carry a `cue` that
the animation fires on. That also buys deliberate control of the pauses, which a single
long utterance does not give.

Writes  audio/<id>.mp3          the joined narration for the scene
        audio/<id>.cues.json    {cue name -> ms from the start of the narration}
"""
import asyncio, io, json, os, subprocess
import edge_tts

HERE   = os.path.dirname(os.path.abspath(__file__))
OUT    = os.path.join(HERE, "audio")
PARTS  = os.path.join(OUT, "parts")
FFDIR  = r"C:\Users\Surface\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"
FFMPEG = os.path.join(FFDIR, "ffmpeg.exe")
FFPROBE= os.path.join(FFDIR, "ffprobe.exe")

# NamMinh is the Hanoi-standard male voice, and the only male vi-VN neural voice on offer.
VOICE = "vi-VN-NamMinhNeural"
RATE  = "+8%"
PITCH = "-3Hz"

os.makedirs(PARTS, exist_ok=True)


def dur(path):
    out = subprocess.check_output([FFPROBE, "-v", "error", "-show_entries",
                                   "format=duration", "-of", "csv=p=0", path])
    return float(out.decode().strip()) * 1000.0


async def synth(text, path):
    c = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await c.save(path)


async def main():
    scenes = json.load(io.open(os.path.join(HERE, "script.json"), encoding="utf-8"))
    for s in scenes:
        segs = s.get("segments") or []
        if not segs:
            print("silent  %s" % s["id"])
            continue

        paths, cues, at = [], {}, 0.0
        for i, seg in enumerate(segs):
            p = os.path.join(PARTS, "%s_%02d.mp3" % (s["id"], i))
            await synth(seg["t"], p)
            if seg.get("cue"):
                cues[seg["cue"]] = round(at)
            at += dur(p) + float(seg.get("gap", 160))
            paths.append((p, float(seg.get("gap", 160))))

        # join with the gaps baked in, as one re-encode rather than a concat of mp3s:
        # mp3 frames do not line up on exact millisecond boundaries and concatenating them
        # would let the cue times drift away from the audio over a long scene
        inputs, filt, labels = [], [], []
        for i, (p, gap) in enumerate(paths):
            inputs += ["-i", p]
            filt.append("[%d:a]apad=pad_dur=%.3f[s%d]" % (i, gap / 1000.0, i))
            labels.append("[s%d]" % i)
        filt.append("%sconcat=n=%d:v=0:a=1[out]" % ("".join(labels), len(paths)))
        outp = os.path.join(OUT, s["id"] + ".mp3")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error"] + inputs +
                       ["-filter_complex", ";".join(filt), "-map", "[out]",
                        "-c:a", "libmp3lame", "-q:a", "2", outp], check=True)

        json.dump(cues, io.open(os.path.join(OUT, s["id"] + ".cues.json"), "w",
                                encoding="utf-8"), ensure_ascii=False)
        print("ok      %-16s %6.2fs  %d phrases  cues=%s" % (
            s["id"], dur(outp) / 1000.0, len(segs),
            ",".join("%s@%.1fs" % (k, v / 1000.0) for k, v in cues.items()) or "-"))


asyncio.run(main())
