---
name: fireredasr2s-cli
description: >-
  Run the FireRedASR2S command-line tool (python -m fireredasr2s.fireredasr2s_cli)
  in this repo to transcribe wav files with the FireRedASR2-LLM / FireRedASR2-AED
  models and produce result.jsonl, SRT subtitles and/or TextGrid files. Use when
  the user asks for CLI/batch transcription, SRT generation from audio, or
  running ASR outside the web UI.
whenToUse: >-
  The user wants to transcribe audio files through the command line instead of
  the web UI (http://127.0.0.1:5078), generate SRT subtitles from wav files,
  batch-process many audio files, or get word-level timestamps/confidence via
  the FireRedASR2S pipeline (VAD/LID/Punc).
---

# fireredasr2s-cli usage

This repo vendors the official FireRedASR2S package (`fireredasr2s/`) plus a
local `.venv` created with `uv sync`. The CLI lives at
`fireredasr2s/fireredasr2s_cli.py` and is invoked with the venv's Python:

```bash
# Windows (this repo)
.venv\Scripts\python.exe -m fireredasr2s.fireredasr2s_cli <args>

# Linux/macOS
.venv/bin/python -m fireredasr2s.fireredasr2s_cli <args>
```

Run `--help` to see all options:

```bash
.venv\Scripts\python.exe -m fireredasr2s.fireredasr2s_cli --help
```

## What it outputs

The CLI writes, under `--outdir` (default `output/`):

| File | Content |
|---|---|
| `result.jsonl` | one JSON object per wav: `text`, `sentences[]` (start_ms/end_ms/text/asr_confidence/lang), `vad_segments_ms`, `dur_s`, `words[]`, `wav_path` |
| `asr_srt/<name>.srt` | SRT subtitles (`--write_srt 1`, default ON) |
| `asr_tg/<name>.TextGrid` | Praat TextGrid (`--write_textgrid 1`, default ON) |
| `vad_segment/` | per-segment wav clips (`--save_segment 1`) |

So **yes, the CLI outputs SRT natively** — one `.srt` per input wav.

## Model directories in this repo

| Model | Dir | Status |
|---|---|---|
| FireRedASR2-LLM | `pretrained_models/FireRedASR2-LLM-L/` | ✅ downloaded |
| FireRedASR2-AED | `pretrained_models/FireRedASR2-AED-L/` | ❌ not downloaded (see `AED模型下载地址.txt`) |
| FireRedVAD | `pretrained_models/FireRedVAD/VAD` | ❌ not downloaded |
| FireRedLID | `pretrained_models/FireRedLID` | ❌ not downloaded |
| FireRedPunc | `pretrained_models/FireRedPunc` | ❌ not downloaded |

## Examples

### 1. LLM model, ASR only (works with current repo state)

The full system pipeline (VAD/LID/Punc) needs those extra models; disable them
to run with just the ASR model. **Always pass `--asr_use_half 1` for the LLM**
(bf16; fp32 needs ~31 GB VRAM and OOMs on 24/32 GB cards):

```bash
.venv\Scripts\python.exe -m fireredasr2s.fireredasr2s_cli ^
  --wav_path input.wav ^
  --asr_type llm ^
  --asr_model_dir pretrained_models/FireRedASR2-LLM-L ^
  --asr_use_half 1 ^
  --return_timestamp 0 ^
  --enable_vad 0 --enable_lid 0 --enable_punc 0 ^
  --write_srt 1 --write_textgrid 0 ^
  --outdir output
```

Result: `output/result.jsonl` + `output/asr_srt/input.srt`.

### 2. AED model with timestamps + punctuation (needs AED + Punc models)

```bash
.venv\Scripts\python.exe -m fireredasr2s.fireredasr2s_cli ^
  --wav_paths a.wav b.wav ^
  --asr_type aed ^
  --asr_model_dir pretrained_models/FireRedASR2-AED-L ^
  --return_timestamp 1 ^
  --enable_vad 0 --enable_lid 0 --enable_punc 1 ^
  --punc_model_dir pretrained_models/FireRedPunc ^
  --outdir output
```

(AED supports word-level timestamps + confidence; set `--return_timestamp 0`
for the LLM, which does not emit timestamps.)

### 3. Full all-in-one system (all four models downloaded)

Just use the defaults (VAD/LID/Punc on) and point `--asr_type`/`--asr_model_dir`:

```bash
.venv\Scripts\python.exe -m fireredasr2s.fireredasr2s_cli ^
  --wav_dir wav_folder --outdir output
```

### 4. Input variants

- `--wav_path x.wav` — single file
- `--wav_paths a.wav b.wav ...` — several files
- `--wav_dir dir` — every `**/*.wav` under a directory
- `--wav_scp file` — lines of `uttid wav_path`

## Prerequisites / notes

- **Input must be 16 kHz mono PCM wav** (the pipeline asserts `sample_rate == 16000`).
  Convert other formats with the bundled ffmpeg first:
  ```bash
  ffmpeg\ffmpeg.exe -y -i in.mp4 -ac 1 -ar 16000 -c:a pcm_s16le -f wav out.wav
  ```
- **Long audio**: the raw CLI (with `--enable_vad 0`) feeds the WHOLE file as one
  segment, but the LLM only supports input up to 40s — longer files yield an empty
  SRT. For wav/m4a files of any length use `.\run.ps1 <file>` instead: it converts
  to 16k wav, VAD-splits into short segments (max 3s each by default,
  `-MaxDuration` to tune; same faster-whisper VAD the webui uses) and merges one
  SRT with global timestamps.
- The LLM model needs ~18 GB VRAM; stop the web UI server (which caches the
  model) before running the CLI, or you may hit CUDA OOM.
- Output text is lowercased (official FireRedASR2 behavior).
- The web UI (app.py) uses the same `fireredasr2s` backend, so a transcription
  can equally be done via `POST /v1/audio/transcriptions` (`model=LLM`,
  `response_format=srt|json|text`).
- Local patch vs upstream: `fireredasr2s/fireredasr2system.py` uses
  `asr_result.get("confidence", 0.0)` because the LLM branch of
  `FireRedAsr2.transcribe` does not return a `confidence` field (upstream
  `KeyError` when using the LLM in the system pipeline).
