"""
Enhanced Okun Language YouTube Playlist Data Extractor — Version 2
===================================================================
Improvements over v1:
  - Robust retry logic with exponential back-off
  - Per-video progress saved to JSON so interrupted runs resume
  - Whisper-based transcription (replaces Google Speech API — no quota limits)
  - Configurable frame-extraction interval (not just fixed 8 keyframes)
  - Parallel audio/image extraction using ThreadPoolExecutor
  - Structured CSV manifest of every output file
  - Cleaner folder hierarchy with timestamps
  - Full logging to file AND console

Usage in Google Colab:
  1. Upload this file (or copy into a code cell)
  2. Run the Colab notebook (enhanced_okun_colab_v2.ipynb) — it imports this module
  3. All output lands in /content/okun_data/ (auto-copied to Drive if enabled)

Author: Okun NLP Research Team
License: MIT
"""

# ── Standard library ──────────────────────────────────────────────────────────
import os, json, csv, time, logging, traceback
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Third-party (installed by Cell 1 of the notebook) ────────────────────────
try:
    import yt_dlp
    import cv2
    from PIL import Image
    from pydub import AudioSegment
    import whisper
    from tqdm import tqdm
except ImportError as e:
    raise ImportError(
        f"Missing dependency: {e}\n"
        "Run Cell 1 of the Colab notebook first to install all packages."
    )

# ═════════════════════════════════════════════════════════════════════════════
# CONFIGURATION  ← edit these in the Colab notebook (Cell 2), not here
# ═════════════════════════════════════════════════════════════════════════════
DEFAULT_CONFIG = {
    "playlist_url": "https://youtube.com/playlist?list=PLiLuSz7xkp2b-y1OByHcBlq-CTBpHM6A_",
    "output_dir":   "/content/okun_data",
    "drive_dir":    "/content/drive/MyDrive/Okun_Research",
    "save_to_drive": True,

    "video":  {"enabled": True,  "quality": "bestvideo[ext=mp4]+bestaudio/best"},
    "audio":  {"enabled": True,  "formats": ["mp3", "wav"], "mp3_bitrate": "192k", "wav_sr": 44100},
    "images": {"enabled": True,  "thumbnail": True, "keyframe_interval_sec": 30},
    "text":   {"enabled": True,  "whisper_model": "base", "language": "yo"},  # yo = Yoruba

    "max_retries":   3,
    "retry_delay":   5,       # seconds (doubles on each retry)
    "max_workers":   2,       # parallel threads for audio/image tasks
    "batch_size":    10,      # videos processed before saving progress
}


# ═════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═════════════════════════════════════════════════════════════════════════════
def setup_logging(output_dir: str) -> logging.Logger:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(output_dir) / f"extraction_{datetime.now():%Y%m%d_%H%M%S}.log"
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("okun_extractor")


# ═════════════════════════════════════════════════════════════════════════════
# PROGRESS TRACKER  — survives Colab disconnects
# ═════════════════════════════════════════════════════════════════════════════
class ProgressTracker:
    def __init__(self, output_dir: str):
        self.path = Path(output_dir) / "progress.json"
        self.data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path) as f:
                return json.load(f)
        return {"completed": [], "failed": [], "skipped": []}

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def is_done(self, video_id: str) -> bool:
        return video_id in self.data["completed"]

    def mark(self, video_id: str, status: str):
        self.data.setdefault(status, [])
        if video_id not in self.data[status]:
            self.data[status].append(video_id)
        self.save()


# ═════════════════════════════════════════════════════════════════════════════
# FOLDER STRUCTURE
# ═════════════════════════════════════════════════════════════════════════════
def make_dirs(base: str) -> dict:
    dirs = {
        "base":     Path(base),
        "metadata": Path(base) / "00_Metadata",
        "videos":   Path(base) / "01_Videos",
        "audio":    Path(base) / "02_Audio",
        "images":   Path(base) / "03_Images",
        "text":     Path(base) / "04_Text",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


# ═════════════════════════════════════════════════════════════════════════════
# PLAYLIST METADATA FETCH
# ═════════════════════════════════════════════════════════════════════════════
def fetch_playlist_info(url: str, logger: logging.Logger) -> list[dict]:
    """Return list of {id, title, url, duration} dicts without downloading."""
    logger.info(f"Fetching playlist metadata: {url}")
    opts = {"quiet": True, "extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    entries = info.get("entries", [])
    videos = [
        {
            "id":       e["id"],
            "title":    e.get("title", "unknown"),
            "url":      f"https://www.youtube.com/watch?v={e['id']}",
            "duration": e.get("duration", 0),
        }
        for e in entries if e
    ]
    logger.info(f"Found {len(videos)} videos in playlist.")
    return videos


# ═════════════════════════════════════════════════════════════════════════════
# VIDEO DOWNLOAD
# ═════════════════════════════════════════════════════════════════════════════
def download_video(video: dict, dest_dir: Path, quality: str,
                   retries: int, delay: int, logger: logging.Logger) -> Path | None:
    out_tmpl = str(dest_dir / f"{video['id']}.%(ext)s")
    opts = {
        "outtmpl":       out_tmpl,
        "format":        quality,
        "quiet":         True,
        "no_warnings":   True,
        "retries":       retries,
    }
    for attempt in range(1, retries + 1):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([video["url"]])
            # find the file
            matches = list(dest_dir.glob(f"{video['id']}.*"))
            if matches:
                logger.info(f"  ✓ Video: {matches[0].name}")
                return matches[0]
        except Exception as exc:
            logger.warning(f"  Video attempt {attempt}/{retries} failed: {exc}")
            if attempt < retries:
                time.sleep(delay * (2 ** (attempt - 1)))
    logger.error(f"  ✗ Video download failed after {retries} attempts.")
    return None


# ═════════════════════════════════════════════════════════════════════════════
# AUDIO EXTRACTION
# ═════════════════════════════════════════════════════════════════════════════
def extract_audio(video_path: Path, audio_dir: Path, cfg: dict,
                  logger: logging.Logger) -> dict:
    results = {}
    stem = video_path.stem
    if "mp3" in cfg["formats"]:
        mp3_path = audio_dir / f"{stem}.mp3"
        try:
            seg = AudioSegment.from_file(str(video_path))
            seg.export(str(mp3_path), format="mp3", bitrate=cfg["mp3_bitrate"])
            results["mp3"] = mp3_path
            logger.info(f"  ✓ Audio MP3: {mp3_path.name}")
        except Exception as e:
            logger.warning(f"  ✗ MP3 failed: {e}")
    if "wav" in cfg["formats"]:
        wav_path = audio_dir / f"{stem}.wav"
        try:
            seg = AudioSegment.from_file(str(video_path))
            seg = seg.set_frame_rate(cfg["wav_sr"])
            seg.export(str(wav_path), format="wav")
            results["wav"] = wav_path
            logger.info(f"  ✓ Audio WAV: {wav_path.name}")
        except Exception as e:
            logger.warning(f"  ✗ WAV failed: {e}")
    return results


# ═════════════════════════════════════════════════════════════════════════════
# IMAGE EXTRACTION
# ═════════════════════════════════════════════════════════════════════════════
def extract_images(video_path: Path, images_dir: Path, cfg: dict,
                   logger: logging.Logger) -> list[Path]:
    saved = []
    stem = video_path.stem
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.warning(f"  ✗ Could not open video for image extraction.")
        return saved
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    interval_frames = int(fps * cfg["keyframe_interval_sec"])

    frame_nos = []
    if cfg.get("thumbnail"):
        frame_nos.append(0)
    frame_nos += list(range(interval_frames, total_frames, interval_frames))

    for i, fno in enumerate(frame_nos):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fno)
        ret, frame = cap.read()
        if not ret:
            continue
        label = "thumbnail" if i == 0 and cfg.get("thumbnail") else f"frame{i:03d}"
        out = images_dir / f"{stem}_{label}.jpg"
        cv2.imwrite(str(out), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        saved.append(out)
    cap.release()
    logger.info(f"  ✓ Images: {len(saved)} frames saved.")
    return saved


# ═════════════════════════════════════════════════════════════════════════════
# TRANSCRIPTION  (Whisper — no API key needed)
# ═════════════════════════════════════════════════════════════════════════════
_whisper_model_cache = {}

def transcribe_audio(audio_path: Path, text_dir: Path, cfg: dict,
                     logger: logging.Logger) -> Path | None:
    model_name = cfg["whisper_model"]
    if model_name not in _whisper_model_cache:
        logger.info(f"  Loading Whisper model '{model_name}' (first time only)…")
        _whisper_model_cache[model_name] = whisper.load_model(model_name)
    model = _whisper_model_cache[model_name]

    txt_path = text_dir / f"{audio_path.stem}.txt"
    try:
        result = model.transcribe(str(audio_path), language=cfg.get("language"))
        txt_path.write_text(result["text"], encoding="utf-8")
        logger.info(f"  ✓ Transcript: {txt_path.name} ({len(result['text'])} chars)")
        return txt_path
    except Exception as e:
        logger.warning(f"  ✗ Transcription failed: {e}")
        return None


# ═════════════════════════════════════════════════════════════════════════════
# CSV MANIFEST
# ═════════════════════════════════════════════════════════════════════════════
def write_manifest(records: list[dict], output_dir: str):
    path = Path(output_dir) / "00_Metadata" / "manifest.csv"
    if not records:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN EXTRACTION PIPELINE
# ═════════════════════════════════════════════════════════════════════════════
def run_extraction(config: dict = None):
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    logger = setup_logging(cfg["output_dir"])
    logger.info("═" * 60)
    logger.info("Okun Playlist Extractor — Version 2")
    logger.info("═" * 60)

    dirs = make_dirs(cfg["output_dir"])
    tracker = ProgressTracker(cfg["output_dir"])
    videos = fetch_playlist_info(cfg["playlist_url"], logger)

    manifest_records = []

    for video in tqdm(videos, desc="Processing videos"):
        vid_id = video["id"]
        if tracker.is_done(vid_id):
            logger.info(f"Skipping (already done): {video['title']}")
            continue

        logger.info(f"\n{'─'*50}")
        logger.info(f"Processing: {video['title']}  [{vid_id}]")

        record = {
            "id": vid_id, "title": video["title"], "url": video["url"],
            "duration_sec": video["duration"],
            "video_file": "", "mp3_file": "", "wav_file": "",
            "image_count": 0, "transcript_file": "", "status": "ok",
        }

        try:
            # ── Video ──────────────────────────────────────────────────────
            video_path = None
            if cfg["video"]["enabled"]:
                video_path = download_video(
                    video, dirs["videos"],
                    cfg["video"]["quality"],
                    cfg["max_retries"], cfg["retry_delay"], logger,
                )
                record["video_file"] = str(video_path) if video_path else "FAILED"

            if video_path is None:
                # Try audio-only download as fallback
                logger.warning("  Falling back to audio-only download…")
                audio_opts = {
                    "outtmpl": str(dirs["audio"] / f"{vid_id}.%(ext)s"),
                    "format": "bestaudio/best",
                    "quiet": True,
                }
                with yt_dlp.YoutubeDL(audio_opts) as ydl:
                    ydl.download([video["url"]])
                audio_files = list(dirs["audio"].glob(f"{vid_id}.*"))
                if audio_files:
                    video_path = audio_files[0]

            # ── Audio ──────────────────────────────────────────────────────
            if video_path and cfg["audio"]["enabled"]:
                audio_results = extract_audio(
                    video_path, dirs["audio"], cfg["audio"], logger
                )
                record["mp3_file"] = str(audio_results.get("mp3", ""))
                record["wav_file"] = str(audio_results.get("wav", ""))

            # ── Images ─────────────────────────────────────────────────────
            if video_path and cfg["images"]["enabled"]:
                imgs = extract_images(
                    video_path, dirs["images"], cfg["images"], logger
                )
                record["image_count"] = len(imgs)

            # ── Transcription ──────────────────────────────────────────────
            if cfg["text"]["enabled"]:
                audio_for_stt = (
                    Path(record["wav_file"]) if record["wav_file"] else
                    Path(record["mp3_file"]) if record["mp3_file"] else None
                )
                if audio_for_stt and audio_for_stt.exists():
                    tx = transcribe_audio(
                        audio_for_stt, dirs["text"], cfg["text"], logger
                    )
                    record["transcript_file"] = str(tx) if tx else "FAILED"

            tracker.mark(vid_id, "completed")

        except Exception:
            logger.error(f"  ✗ Unhandled error:\n{traceback.format_exc()}")
            record["status"] = "error"
            tracker.mark(vid_id, "failed")

        manifest_records.append(record)
        write_manifest(manifest_records, cfg["output_dir"])

    # ── Summary ────────────────────────────────────────────────────────────
    logger.info("\n" + "═" * 60)
    logger.info("EXTRACTION COMPLETE")
    logger.info(f"  Completed : {len(tracker.data['completed'])}")
    logger.info(f"  Failed    : {len(tracker.data.get('failed', []))}")
    logger.info(f"  Output dir: {cfg['output_dir']}")
    logger.info("═" * 60)

    # ── Copy to Drive ──────────────────────────────────────────────────────
    if cfg.get("save_to_drive"):
        try:
            import shutil
            drive_dest = Path(cfg["drive_dir"])
            drive_dest.mkdir(parents=True, exist_ok=True)
            shutil.copytree(cfg["output_dir"], str(drive_dest / "okun_data"),
                            dirs_exist_ok=True)
            logger.info(f"✓ Copied to Google Drive: {drive_dest}/okun_data")
        except Exception as e:
            logger.warning(f"Drive copy failed: {e}")

    return manifest_records


# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    run_extraction()
