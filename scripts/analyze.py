"""Generate a local scorekeeper's review page for a behind-home-plate recording."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parent
import imageio_ffmpeg

FPS = 5


def decode(source, args):
    return subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i",
                           str(source), *args, "-"], check=True, stdout=subprocess.PIPE).stdout


def motion(source):
    # Decode in batches to keep memory bounded for doubleheaders.
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(source),
           "-vf", f"fps={FPS},scale=160:90", "-pix_fmt", "gray", "-f", "rawvideo", "-"]
    values = []
    previous = None
    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as proc:
        while raw := proc.stdout.read(160 * 90 * 100):
            frames = np.frombuffer(raw, np.uint8).reshape(-1, 90, 160).astype(np.int16)
            if previous is None:
                previous = frames[:1]
            change = abs(np.diff(np.concatenate([previous, frames]), axis=0)) > 22
            previous = frames[-1:]
            regions = [change[:, 37:57, 39:65], change[:, 38:54, 64:107],
                       change[:, 35:46, 75:132]]
            values.extend(np.stack([r.mean(axis=(1, 2)) for r in regions], axis=1))
        if proc.wait():
            raise RuntimeError("Video decode failed")
    return np.array(values)


def rank(values):
    # Mid-ranks keep silent or static stretches from receiving strong scores.
    ordered = np.sort(values)
    return (np.searchsorted(ordered, values) + np.searchsorted(ordered, values, side="right")) / (2 * len(values))


def candidates(source):
    field = motion(source)
    n = len(field)
    audio = decode(source, ["-map", "0:a:0?", "-ac", "1", "-ar", "8000", "-f", "s16le"]) if has_audio(source) else b""
    samples = np.frombuffer(audio, "<i2").astype(float)
    evidence = np.zeros(n)
    if len(samples):
        usable = (len(samples) // 1600) * 1600
        if usable:
            blocks = samples[:usable].reshape(-1, 1600)
            # Transient strength relative to other 10 ms slices in the same window.
            levels = np.sqrt(np.mean(np.diff(blocks, axis=1, prepend=blocks[:, :1]).reshape(-1, 20, 80)**2, axis=2))
            transient = levels.max(axis=1) / (30 + np.median(levels, axis=1))
            k = min(n, len(transient))
            evidence[:k] = rank(transient[:k])
    plate, lane, distant = [rank(x) for x in field.T]
    follow = np.maximum.reduce([np.pad(lane, (0, 15))[i:i+n] for i in range(2, 16)])
    field_after = np.maximum.reduce([np.pad(distant, (0, 15))[i:i+n] for i in range(2, 16)])
    impact = np.maximum.reduce([np.pad(evidence, (2, 2))[i:i+n] for i in range(5)])
    score = .46 * plate + .28 * follow + .13 * field_after + .13 * impact
    if not len(samples):
        score /= .87
    peaks = []
    suppressed = np.zeros(n, bool)
    for i in np.argsort(-score):
        if score[i] < .78:
            break
        if suppressed[i]:
            continue
        peaks.append((i / FPS, round(100 * score[i])))
        suppressed[max(0, i-8*FPS):i+8*FPS+1] = True
    return n / FPS, sorted(peaks)


def has_audio(source):
    info = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(source)],
                          capture_output=True).stderr
    return b"Audio:" in info


def windows(duration, peaks):
    rows = []
    end = 0
    def gap(stop):
        nonlocal end
        while end < stop:
            limit = min(stop, end + 45)
            rows.append(dict(start=end, end=limit, peak=None, confidence=None))
            end = limit
    for peak, confidence in peaks:
        start = max(0, peak - 5)
        gap(start)
        stop = min(duration, peak + 12)
        rows.append(dict(start=start, end=stop, peak=peak, confidence=confidence))
        end = max(end, stop)
    gap(duration)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("game")
    args = parser.parse_args()
    source = args.video.resolve()
    duration, peaks = candidates(source)
    rows = windows(duration, peaks)
    data = dict(game=args.game, video=source.name, duration=duration, rows=rows)
    template = (ROOT / "review.template.html").read_text(encoding="utf8")
    payload = json.dumps(data, ensure_ascii=False).replace("<", r"\u003c")
    output = source.with_name(source.stem + "-review.html")
    output.write_text(template.replace("__GAME_DATA__", payload), encoding="utf8")
    print(output, duration, len(peaks), len(rows))
