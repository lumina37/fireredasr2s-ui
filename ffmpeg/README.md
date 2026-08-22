# ffmpeg 运行依赖（必装）

本项目运行需要 ffmpeg：`app.py` 启动时会把本目录加入 PATH，音频/视频转码、VAD 切分、
字幕生成都依赖它。**克隆仓库后本目录是空的，请自行放入 ffmpeg 可执行文件。**

## 需要放入的文件

保持以下文件名（从 ffmpeg 的 bin 目录复制即可）：

- `ffmpeg.exe`
- `ffprobe.exe`
- 所需的动态库（如 `avcodec-*.dll`、`avformat-*.dll`、`avutil-*.dll`、`swresample-*.dll` 等）

> 提示：如果系统里已安装 ffmpeg，直接把它的 `bin` 目录下所有文件复制到本目录即可；
> 也可以把 ffmpeg.exe 所在目录加入系统 PATH（app.py 优先使用本目录）。

## 下载方式（Windows，任选其一）

1. https://www.gyan.dev/ffmpeg/builds/ — 选择 release essentials build
2. https://github.com/BtbN/FFmpeg-Builds/releases — 选择 win64 且包含 ffprobe 的版本
3. https://ffmpeg.org/download.html — 官方入口

## 验证

在本目录执行：

```
ffmpeg -version
```

能输出版本信息即表示可用。
