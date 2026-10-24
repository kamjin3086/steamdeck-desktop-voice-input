# 故障排查

[English](../TROUBLESHOOTING.md) | [中文首页](../../README.zh-CN.md)

请在 **SteamOS 桌面模式**下使用，目前不支持游戏模式。

## 安装或启动失败

重新运行 `./init.sh --no-launch`。安装器会修复缺失的 Python 依赖，校验并加载所选模型，更新桌面快捷方式。报告问题时请保留终端错误输出，并隐藏凭据和私密转写。

- **Python 或 venv 不可用：**检查 `python3 --version` 和 `python3 -m venv --help`，需要 Python 3.10+ 并支持 venv。
- **下载失败：**检查 PyPI 和 sherpa-onnx GitHub 模型下载地址的连通性，可用认可的 `PIP_INDEX_URL` 指定镜像。重跑会复用已完成的模型；中断的压缩包下载需要重新开始。
- **没有匹配的二进制 wheel：**依赖必须提供对应 Python 和架构的 wheel。优先使用 Deck 支持的 Python，不要在只读 SteamOS 上尝试源码编译。
- **Qt 插件错误：**从本机图形会话启动，保留 Qt 错误输出，检查 `WAYLAND_DISPLAY` / `DISPLAY`。`QT_QPA_PLATFORM=offscreen` 仅供测试，不代表窗口能在真实桌面显示。
- **移动目录后快捷方式失效：**在新位置重跑安装器。`Init.desktop` 必须与 `init.sh` 在同一目录。ZIP 解压后丢失执行权限时，用 `bash init.sh`。

## 按键无法激活

查看界面显示的当前按键，使用 **Rebind button** 重新绑定。背键请按住约半秒后释放，**Confirm** 保存，**Cancel** 保留原绑定。`./run.sh calibrate` 可以区分触发层问题和识别问题。

Steam Input 可能消费或重映射某个按键。背键使用原始 HID 报告，普通按键使用 evdev。`/dev/hidraw*` 与 `/dev/input/event*` 的可读权限取决于桌面会话。请在当前登录用户的图形会话中运行；权限检查失败时检查相应会话及设备 ACL，安装器不会修改全局设备权限。

非 Deck 开发机通常会报告缺少 Deck 手柄，这是设备条件未满足，而不是模型安装失败。

## 没有声音、识别差或语言不对

在 Plasma 音频设置中检查麦克风选择和增益，避免音量过大导致削波。使用 `./run.sh --meter --debug` 查看电平，需要时通过 `--mic <PipeWire节点>` 选择音源。拔插或切换麦克风后可能需要重启应用。

默认 SenseVoice 支持中、英、粤、日、韩。其他主要语言可在 GUI 中选择 Qwen3-ASR，对应“全球主要语言”；更多小语种可选 Omnilingual ASR，对应“更多语言”。覆盖更广不意味着识别更准，中英混合仍需实测。

停顿时正常行为是输入已完成片段，并在持续按住时继续录音。分段过早可提高 `auto_stop.silence_ms`。录音意外停止时，查看日志是否有进程异常或设备故障。

## 日志里有文字，但输入框没有收到

说话时保持目标输入框获得焦点。ASCII 使用 uinput，Unicode 使用剪贴板粘贴；检查 `/dev/uinput` 可写，并且 Klipper（`qdbus` / `qdbus6`）或 `wl-copy` 可用。部分应用、安全输入框、特权窗口会拒绝模拟输入或粘贴。测试终端提示符前，先使用一个可丢弃内容的编辑器输入框。

Unicode 输入会短暂替换剪贴板，默认用完恢复。排查剪贴板同步问题时可用 `--no-restore-clipboard`。

## 重复输入或旧后台服务

同一项目副本会避免重复实例，但不同目录和旧服务仍可能同时处理按键。运行 `./stop.sh` 停止当前目录对应的程序。

如果以前主动安装过可选的旧版 systemd 用户服务，使用 GUI 启动前先停用：

```bash
systemctl --user disable --now voice-input.service
```

这个可选服务只运行命令行后台进程，不会创建 GUI，标准安装器不会启用它。停用后，如需移除单元，删除 `~/.config/systemd/user/voice-input.service`，再运行 `systemctl --user daemon-reload`。

## 提交问题

提供 SteamOS 和桌面版本、Python 版本、模型和语言、激活来源、复现方法及隐藏敏感信息后的日志。说明普通编辑器输入框是否可用；安装失败时附上退出码。不要发布不愿公开的 API 密钥、原始录音或转写内容。

## 按 L5 又打开绑定弹窗，或提示音被识别

升级到当前版本：界面操作按钮不再接受 Space/Enter 等映射按键触发，默认关闭提示音，新一轮录音不读取激活前缓冲。可选提示音也放在采集边界之外。关闭窗口 X 现在会退出；最小化仍可后台运行。
