<#
.SYNOPSIS
    Use FireRedASR2S to transcribe a single audio file (wav / m4a) into an SRT subtitle.

.DESCRIPTION
    - Converts the input to 16kHz mono wav (required by FireRedASR2S)
    - Transcribes with FireRedASR2-LLM (bf16); long audio is VAD-split into
      segments under the model input limit and merged into one SRT
    - Writes <input>.srt next to the input by default; override with -OutputPath

.PARAMETER InputFile
    Input audio file (.wav or .m4a).

.PARAMETER OutputPath
    Optional SRT output path; default = same dir as input with .srt extension.

.PARAMETER Model
    Optional model: llm (default, FireRedASR2-LLM) / aed (FireRedASR2-AED, model must be downloaded).

.EXAMPLE
    .\run.ps1 .\audio.wav
    .\run.ps1 -InputFile .\audio.m4a -OutputPath .\subs\audio.srt

.NOTES
    Run `uv sync` first and place ffmpeg per ffmpeg\README.md.
    If execution policy blocks scripts:
        powershell -ExecutionPolicy Bypass -File .\run.ps1 ...
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$InputFile,

    [Parameter(Mandatory = $false)]
    [string]$OutputPath,

    [Parameter(Mandatory = $false)]
    [ValidateSet("llm", "aed")]
    [string]$Model = "llm",

    [Parameter(Mandatory = $false)]
    [double]$MaxDuration = 5.0
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot

# ---------- preflight checks ----------
$InputFile = (Resolve-Path $InputFile -ErrorAction Stop).Path
$ext = [System.IO.Path]::GetExtension($InputFile).ToLower()
if ($ext -notin @(".wav", ".m4a")) {
    throw "Only wav / m4a inputs are supported, got: $ext  ($InputFile)"
}
if (-not (Test-Path "$RepoRoot\.venv\Scripts\python.exe")) {
    throw ".venv not found - run 'uv sync' in the repo directory first"
}
if (-not (Test-Path "$RepoRoot\ffmpeg\ffmpeg.exe")) {
    throw "ffmpeg not found - copy ffmpeg.exe etc. into the repo ffmpeg\ folder (see ffmpeg\README.md)"
}
$modelDir = Join-Path $RepoRoot "pretrained_models\FireRedASR2-$Model-L"
if (-not (Test-Path (Join-Path $modelDir "model.pth.tar"))) {
    throw "Model not found: $modelDir - download it per the 下载地址.txt in that folder"
}
# VRAM hint: the webui keeps the model resident (~18GB) and may starve this run
if (Get-NetTCPConnection -LocalPort 5078 -State Listen -ErrorAction SilentlyContinue) {
    Write-Warning "The webui (http://127.0.0.1:5078) is running and keeps ~18GB VRAM resident; the LLM may OOM. Consider stopping it first."
}

# ---------- output path ----------
if (-not $OutputPath) {
    $OutputPath = [System.IO.Path]::ChangeExtension($InputFile, ".srt")
}
$OutputPath = (New-Object System.IO.FileInfo $OutputPath).FullName

# ---------- temp workspace ----------
$work = Join-Path $env:TEMP ("fireredasr2s-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $work -Force | Out-Null
$wav16k = Join-Path $work "input_16k.wav"

try {
    # ---------- convert to 16kHz mono wav ----------
    Write-Host "==> Converting: $InputFile"
    & "$RepoRoot\ffmpeg\ffmpeg.exe" -y -hide_banner -loglevel error -i $InputFile -ac 1 -ar 16000 -c:a pcm_s16le -f wav $wav16k
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $wav16k)) {
        throw "ffmpeg conversion failed: $InputFile"
    }

    # ---------- transcribe (VAD-split long audio, merge SRT) ----------
    Write-Host "==> Transcribing (model=$Model)..."
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    & "$RepoRoot\.venv\Scripts\python.exe" "$RepoRoot\run_transcribe.py" `
        --wav $wav16k `
        --model $Model `
        --model_dir $modelDir `
        --max_duration $MaxDuration `
        --output $OutputPath
    if ($LASTEXITCODE -ne 0) {
        throw "Transcription failed (exit=$LASTEXITCODE), see logs above"
    }
}
finally {
    Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
}
