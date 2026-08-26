# -*- coding: utf-8 -*-
"""
Transcription helper for run.ps1.

Takes a 16kHz mono wav, splits long audio into VAD speech segments (capped
under the model input limit), transcribes each segment with FireRedASR2
(LLM in bf16) and writes a merged SRT with global timestamps.

Usage:
    python run_transcribe.py --wav input_16k.wav --model llm \
        --model_dir pretrained_models/FireRedASR2-LLM-L --output out.srt
"""

import argparse
import os
import re
import shutil
import sys
import tempfile
import time

import torch
from faster_whisper.audio import decode_audio
from faster_whisper.vad import VadOptions, get_speech_timestamps
from pydub import AudioSegment

from fireredasr2s.fireredasr2 import FireRedAsr2, FireRedAsr2Config

# FireRedASR2-LLM supports audio up to 40s; AED up to ~60s.
# Keep a safety margin below the hard limit.
MAX_CHUNK_MS = {"llm": 35000, "aed": 55000}
VAD_PARAMS = {
    "threshold": 0.5,
    "neg_threshold": 0.35,
    "min_speech_duration_ms": 0,
    "max_speech_duration_s": float("inf"),
    "min_silence_duration_ms": 250,
    "speech_pad_ms": 200,
}


def ms_to_time_string(ms):
    h = ms // 3600000
    m = (ms // 60000) % 60
    s = (ms // 1000) % 60
    ms_ = ms % 1000
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms_)


def get_segments(wav_path, max_chunk_ms):
    """Return list of (start_ms, end_ms) speech segments."""
    audio = AudioSegment.from_wav(wav_path)
    total_ms = len(audio)
    # Short files: single segment
    if total_ms < 30000:
        return [(0, total_ms)]
    sampling_rate = 16000
    speech_chunks = get_speech_timestamps(
        decode_audio(wav_path, sampling_rate=sampling_rate),
        vad_options=VadOptions(**VAD_PARAMS),
    )
    segs = [
        (int(round(c["start"] / sampling_rate * 1000)),
         int(round(c["end"] / sampling_rate * 1000)))
        for c in speech_chunks
    ]
    if not segs:
        return [(0, total_ms)]
    # Cap any segment longer than the model input limit
    capped = []
    for s, e in segs:
        while e - s > max_chunk_ms:
            capped.append((s, s + max_chunk_ms))
            s += max_chunk_ms
        if e - s > 0:
            capped.append((s, e))
    return capped


def main():
    ap = argparse.ArgumentParser(description="Transcribe wav to SRT with FireRedASR2")
    ap.add_argument("--wav", required=True, help="16kHz mono wav")
    ap.add_argument("--model", default="llm", choices=["llm", "aed"])
    ap.add_argument("--model_dir", required=True)
    ap.add_argument("--output", required=True, help="output SRT path")
    ap.add_argument("--no_gpu", action="store_true")
    args = ap.parse_args()

    use_gpu = torch.cuda.is_available() and not args.no_gpu
    use_half = args.model == "llm"  # LLM needs bf16 to fit consumer VRAM
    cfg = FireRedAsr2Config(
        use_gpu=use_gpu,
        use_half=use_half,
        beam_size=1,
        nbest=1,
        decode_max_len=0,
        softmax_smoothing=1.0,
        aed_length_penalty=0.0,
        eos_penalty=1.0,
        return_timestamp=False,
        decode_min_len=0,
        repetition_penalty=3.0,
        llm_length_penalty=1.0,
        temperature=1.0,
    )

    print("==> loading model (%s) ..." % args.model, flush=True)
    t0 = time.time()
    model = FireRedAsr2.from_pretrained(args.model, args.model_dir, cfg)
    print("==> model loaded in %.1fs" % (time.time() - t0), flush=True)

    segments = get_segments(args.wav, MAX_CHUNK_MS[args.model])
    print("==> %d segment(s) to transcribe" % len(segments), flush=True)

    tmp = tempfile.mkdtemp(prefix="fr2s-")
    try:
        audio = AudioSegment.from_wav(args.wav)
        subs = []  # (start_ms, end_ms, text)
        for i, (s, e) in enumerate(segments):
            chunk_path = os.path.join(tmp, "seg_%d.wav" % i)
            audio[s:e].export(chunk_path, format="wav")
            try:
                res = model.transcribe(["seg%d" % i], [chunk_path])
                text = (res[0].get("text", "") or "").strip() if res else ""
            except Exception as ex:  # keep going on a bad segment
                text = ""
                print("[warn] segment %d failed: %s" % (i, ex), flush=True)
            print("[%d/%d] %s --> %s : %r" % (
                i + 1, len(segments),
                ms_to_time_string(s), ms_to_time_string(e), text), flush=True)
            if text and not re.search(r"(<blank>)|(<sil>)", text):
                subs.append((s, e, text))

        with open(args.output, "w", encoding="utf-8") as f:
            f.write("\n\n".join(
                "%d\n%s --> %s\n%s" % (n, ms_to_time_string(s), ms_to_time_string(e), t)
                for n, (s, e, t) in enumerate(subs, 1)))
        print("OK - subtitle written: %s (%d block(s))" % (args.output, len(subs)), flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
