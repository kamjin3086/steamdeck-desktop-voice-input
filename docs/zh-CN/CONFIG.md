# 配置说明

[English](../CONFIG.md) | [中文首页](../../README.zh-CN.md)

配置文件为 `~/.config/voice-input/config.json`。优先级为：命令行选项 > 保存的配置 > 默认值。运行 `./run.sh --help` 查看当前参数，`./run.sh --config` 查看生效配置。分享配置输出前请隐藏 API 密钥。

```json
{
  "trigger": {"source": "hidraw", "report_id": 1, "byte": 9, "bit": 7},
  "asr": {"backend": "local", "model": "sensevoice", "num_threads": 2, "language": "auto"},
  "auto_stop": {"enabled": true, "silence_ms": 600, "threshold": 0.02}
}
```

## 激活按键

仅当尚无绑定时，安装器才设置默认 L5。界面重新绑定弹窗只在点击 **Confirm** 后保存，**Cancel** 保留原绑定。

| 来源 | 配置项 | 用途 |
| --- | --- | --- |
| `hidraw` | `report_id`、`byte`、`bit` | Deck 原始按键报告，包含背键 |
| `evdev-key` | Linux 输入 `code` | 键盘或手柄按键 |
| `evdev-abs` | Linux 轴 `code` | 使用按下和释放阈值的模拟扳机 |

原测试布局中 L5 为 report 1、byte 9、bit 7；L4 为 report 1、byte 13、bit 1。固件和 Steam Input 可能改变布局，请使用弹窗学习，不要猜测位号。命令行 `./run.sh bind` 是另一套需要终端输入、通过两次采集匹配的 HID 学习流程。

`./run.sh --trigger-key 0x44` 临时使用 F10，`./run.sh calibrate` 输出当前触发状态。evdev 使用 Linux 输入码，不是 Qt 键值或 X11 keycode。

## 本地识别

| 设置 | 默认值 | 含义 |
| --- | --- | --- |
| `backend` | `local` | 使用 sherpa-onnx |
| `model` | `sensevoice` | models.json 中的模型名 |
| `num_threads` | `2` | CPU 解码线程数 |
| `language` | `auto` | 自动语言检测；旧 Whisper 或云端也可设置 `en` 等语言提示 |
| `provider` | `cpu` | sherpa-onnx 执行后端 |

首次安装无需选择模型，默认 SenseVoice。GUI 的 **Change model / languages** 支持三组语言方案、可见下载进度、取消和加载成功后保存。重复运行安装器保留已选模型。`--model` 和 `--language` 仍可用于高级命令行覆盖。

## 静音与分段限制

`auto_stop.enabled=true` 表示说话后允许静音分段，`silence_ms=600` 是连续静音时长，`threshold=0.02` 是归一化音频峰值阈值。需要更长停顿时可把 silence_ms 提高到 1000–1500；噪声较大时可以提高 threshold。

静音分段会完成当前文字并输入，然后在按键仍按住时开始下一段。关闭此选项后，等待松手或达到 60 秒单段上限才收尾；达到上限时仍会继续下一段，以限制内存占用。最短有效片段为 0.35 秒，新一次长按从激活之后开始，不读取激活前的缓冲；实际延迟还受输入轮询和模型解码影响。

## 云端与局域网

见[云端说明](CLOUD_ASR.md)。后端设置包含 `preset`、`base_url`、`model`、`language`、`timeout`（默认 30 秒）、`response_format`（`json` 或 `text`），以及可选 `endpoint`。推荐使用预设对应的密钥环境变量，而非直接保存 `api_key`。

## 文件位置

| 位置 | 内容 |
| --- | --- |
| 项目 `.venv/` | Python 运行依赖 |
| 项目 `models/` | 下载的模型 |
| `~/.config/voice-input/config.json` | 用户配置 |
| 桌面和用户应用目录中的 `voice-input.desktop` | GUI 快捷方式 |
| 用户运行时目录 `voice-input-<checkout hash>/` | 当前项目副本的锁和 IPC socket |
| 显式指定的 `--partial-log PATH` | 可选转写日志 |

GUI 在内存中保留有行数上限的日志。诊断日志及自行创建的录音可能包含私密语音内容。

## 提示音与关闭

默认不播放提示音。可选 `--beep` 在录音边界之外播放提示音，释放提示音位于最终识别之后。窗口 X 真正退出应用；保持后台运行请使用最小化。
