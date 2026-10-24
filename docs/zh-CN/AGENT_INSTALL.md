# 使用 agent 安装或修复

[English](../AGENT_INSTALL.md) | [中文首页](../../README.zh-CN.md)

当用户把仓库链接交给你，要求安装本项目时，请按此流程操作。目标机器应为用户处于**桌面模式**的 Steam Deck。远程 agent 可以准备文件，但最终 GUI 和音频检查必须在用户的图形会话中进行。目前不支持游戏模式。

## 1. 检查目标环境

检查系统、架构、Python、桌面会话和已有项目目录：

```bash
uname -m
cat /etc/os-release
python3 --version
printf 'Desktop: %s; session: %s\n' "${XDG_CURRENT_DESKTOP:-unknown}" "${XDG_SESSION_TYPE:-unknown}"
command -v pw-record
```

选择用户可写目录，例如 `~/Applications/steamdeck-desktop-voice-input`。若目录已存在，更新前先检查远程地址和工作区状态，保留本地修改。优先复用现有安装，避免意外创建多个副本。单实例锁按项目目录区分，不同目录可以各运行一个实例。

完成条件：明确目标机器、会话和安装目录。如果实际运行在另一台机器或无图形会话的 SSH 环境中，报告设备可用性之前应说明这一限制。

## 2. 安装默认语言方案

首次安装自动使用 SenseVoice，支持中文、英语、粤语、日语和韩语。安装时不必询问用户选哪一个模型。以后可在 GUI 中选择“常用语言（SenseVoice）”“全球主要语言（Qwen3-ASR）”“更多语言（Omnilingual ASR）”三组。

首次安装：

```bash
mkdir -p ~/Applications
cd ~/Applications
git clone https://github.com/kamjin3086/steamdeck-desktop-voice-input.git
cd steamdeck-desktop-voice-input
VOICE_INPUT_NO_PAUSE=1 bash init.sh --no-launch
```

重复安装保留之前在界面选中的本地模型。用户明确要求恢复默认时可使用 `--model sensevoice`；其他 `--model` 参数属于高级命令行覆盖，不是安装必选项。三个 GUI 方案默认自动识别语言。

安装器会检查和修复 `.venv`、安装二进制 Python 依赖、下载并校验所选模型、实际加载模型、保留已有激活按键、创建或修复桌面及应用菜单快捷方式，然后检查设备条件。有效的模型文件会复用，不要为安装一个模型而下载所有模型。

PyPI 连通性有问题时，可以使用用户认可的 `PIP_INDEX_URL`。下载失败不代表安装成功，应处理问题并重新运行相同命令。即使软件和模型已经安装，只要设备条件未满足，脚本仍会返回非零退出码。

完成条件：安装器退出码为零；或者明确记录剩余阻塞项，区分“软件已安装”和“设备已可用”。

## 3. 验证软件与快捷方式

```bash
.venv/bin/python -m pip check
./run.sh models verify sensevoice
./run.sh --config
./run.sh --model sensevoice --language auto test-asr /path/to/user-approved-16khz-mono-pcm16.wav
```

请替换为实际选用的模型和语言。只有存在合适且用户同意使用的音频文件时才做文件识别测试。音频需要为 16 kHz、单声道、PCM16 WAV，不要虚构测试通过的结果。`models verify` 在清单提供哈希时检查哈希，否则检查所需模型文件。安装器还会加载识别器，但这不能证明所有语音都能正确转写。

使用 `xdg-user-dir DESKTOP` 定位实际桌面目录，包括中文路径。确认 `voice-input.desktop` 存在、可执行，并指向当前项目。环境已有 `desktop-file-validate` 时可以使用，不必要求用户为此安装额外工具。

如果用户把云端密钥直接写进配置，`./run.sh --config` 可能包含它。仅在本机检查，汇报时隐藏凭据。优先使用[云端说明](CLOUD_ASR.md)中的环境变量。

完成条件：依赖、所选模型校验与加载、保存的配置、桌面快捷方式均已检查。

## 4. 在图形会话中验收

运行 `./desktop.sh`。确认窗口打开、有任务栏入口、最小化后保持运行，重复启动会显示已有窗口。

请用户点击一个可丢弃内容的输入框，按住 L5 说两句话，中间停顿但保持按住，最后释放。检查两句话只输入一次、停顿后仍能继续录音、释放后结束本次录音。切换获得焦点的输入区域后，后续识别文字应进入新的目标区域。如果已经自定义按键，请使用当前绑定，而不是假定仍为 L5。

验证 **Change model / languages** 显示三组及语言说明，选择尚未安装的模型时有明确下载进度和阶段状态。取消或失败应保留原选择，成功后应持久保存，切回已有模型应复用缓存。用窗口 X 关闭时应用应退出，最小化则应保持运行。

验证更换按键时，点击 **Rebind button**，检查候选标签，先测试 **Cancel** 保留原绑定。用户确实希望更换时再操作一次并选择 **Confirm**，然后验证新按键能触发真实录音。重新运行安装器后自定义绑定应继续保留。

无界面或 offscreen 测试无法证明物理按键、麦克风质量、桌面焦点及真实输入可用。只请用户完成工具无法代劳的实际步骤。

完成条件：实机检查通过；或者在交付说明中明确标注尚未验证的项目。

## 5. 停止或交付

```bash
./stop.sh
./stop.sh
```

当前目录对应进程退出后，两次停止都应成功。如果用户希望保持运行，再启动 `./desktop.sh`。如果以前主动安装过旧版 systemd 用户服务，切换到 GUI 启动前按[故障排查](TROUBLESHOOTING.md)停用。

交付时说明安装路径、模型和语言、当前激活按键、快捷方式位置、已做检查、待完成的实机验收以及停止方法。默认 **L5：长按使用，释放取消激活**。释放会完成剩余语音识别，不会撤销已经输入的文字。
