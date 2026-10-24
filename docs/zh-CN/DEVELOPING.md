# 开发与测试

[English](../DEVELOPING.md) | [中文首页](../../README.zh-CN.md)

目标平台是 SteamOS 桌面模式，开发需要 Linux 和 Python 3.10+。运行依赖为 sherpa-onnx、PySide6-Essentials；输入设备 IO、HTTP、模型管理和进程管理使用标准库。安装二进制 wheel，无需编译器。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
```

## 架构

- `desktop.py`：Qt 窗口、绑定确认弹窗、识别子进程、单实例 IPC。
- `main.py`：命令行、音频与触发循环、静音分段、文字注入。
- `audio_stream.py`：常驻 pw-record 子进程和有容量上限的 PCM 缓冲。
- `hidraw.py`、`evdevraw.py`、`trigger.py`、`sources.py`：设备访问与按键状态。
- `binding_capture.py`：GUI 非阻塞候选按键监听，不保存配置。
- `bind.py`：HID 候选评分、命令行两次采集学习、按键显示名称。
- `backends/`：公共识别会话接口、本地 sherpa-onnx、云端或局域网 WAV 请求。
- `models_registry.py`、`models.json`：下载、必要文件检查和可选 SHA-256 校验。
- `inject.py`、`uinput_kbd.py`：键盘注入和 Unicode 剪贴板粘贴。
- `model_dialog.py`、`model_manager.py`：三组语言方案、可取消的模型准备子进程、可见进度与成功后的配置保存。
- `setup.py`、`runtime.py`：安装、快捷方式、按项目副本管理和停止进程。

一次物理长按可以包含多个识别会话。静音或达到 60 秒限制时结束当前会话，但保留按住状态。分段边界应保留音频游标，避免收尾和注入期间的音频被重复读取或遗漏。释放按键时完成最后一段，模型在识别进程中跨会话保持加载。

GUI 开始绑定监听前先暂停识别，只保存候选值，明确确认后才写配置；确认或取消后恢复之前的运行状态。取消和关闭弹窗不得修改绑定。IPC 和进程锁按项目目录区分，不使用宽泛的进程名称匹配。

## 不需要实物输入的自动测试

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -p test_model_switching.py
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -p test_desktop_regressions.py
.venv/bin/python -m unittest discover -s tests -p test_audio_boundaries.py
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -p test_hold_to_talk.py
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -p test_binding_dialog.py
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -p test_desktop_lifecycle.py
.venv/bin/python -m unittest discover -s tests -p test_installation.py
.venv/bin/python tests/test_autostop.py
.venv/bin/python tests/test_bind_detect.py
.venv/bin/python tests/test_trigger_logic.py
.venv/bin/python tests/test_hud.py
.venv/bin/python tests/test_cloud_backend.py
```

部分旧测试在导入时执行，且有些需要真实设备，因此不支持直接无筛选地运行 `unittest discover`。CI 工作流显式选择无需硬件的测试。

`test_streaming.py` 需要已下载的 zh14m 模型及自带 WAV。`smoke.py`、`e2e_inject.py`、`e2e_loop.py`、`spike_qt.py` 属于人工设备或桌面集成检查；注入测试可能向当前桌面输入文字，只应在可丢弃内容的本地图形会话中运行。Offscreen 测试验证生命周期逻辑，不验证实际任务栏行为、麦克风质量或 L5 权限。

## 修改与贡献

代码注释、界面文字、错误提示和测试说明使用英文，同时维护对应的中英文文档。多语言 ASR 或 Unicode 测试样本使用 Unicode 转义，以保留非 ASCII 输入和识别验证。行为修改应配合有针对性的测试，模型、录音、本地凭据和转写日志不得进入版本控制。

添加模型时，在 models.json 中提供上游 URL、目录、语言和流式信息，以及已知的文件哈希。本地适配器目前支持包含 encoder、decoder、joiner 的 transducer 模型，以及包含 encoder、decoder、tokens 的 Whisper 模型。将模型描述为已验证前，应实际加载并识别样例音频。

应用代码贡献采用 MIT。模型和依赖仍适用各自的上游许可证；添加依赖或重新分发资源时应维护[第三方说明](../../THIRD_PARTY_NOTICES.zh-CN.md)。

当前三组后端为 SenseVoice、Qwen3-ASR 和 Omnilingual CTC。旧 transducer / Whisper 保留兼容。Qwen3 需要 conv_frontend、encoder、decoder 和 tokenizer 文件；单文件 SenseVoice / Omnilingual 根据目录元数据选择对应构造器。模型先在临时目录解压和校验，再替换目标目录。窗口关闭和桌面会话退出会停止独立进程组，超时后清理识别进程及录音子进程。
