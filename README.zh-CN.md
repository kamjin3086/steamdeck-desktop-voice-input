# Steam Deck Desktop Voice Input

[English](README.md) | 简体中文

按住一个按键说话，将识别出的文字输入 Steam Deck 上当前获得焦点的输入区域。

面向使用 KDE Plasma 和 PipeWire 的 **SteamOS 桌面模式（Desktop Mode）**。可用于聊天框、浏览器表单、编辑器、终端提示符，以及本机编程 agent 的输入框。**目前不支持游戏模式（Gaming Mode）**；其他 Linux 桌面环境属于实验性使用范围。

程序在本机运行，可通过任务栏重新打开，默认使用 **L5（左背键）**。长按持续听写，释放取消激活。说话停顿时会自动完成当前片段并输入文字；保持按住即可继续，不用松开再按。释放按键会结束录音并处理剩余语音，**不会撤销已经输入的文字**。

## 功能

- 使用 sherpa-onnx 在本机识别语音，按需下载语言方案对应的模型。
- 按住持续识别、静音分段，以及按下激活键之后开始的音频采集。
- 原生 Qt 窗口、任务栏图标、可用时显示系统托盘、同一目录单实例运行。
- 弹窗重新绑定激活按键，点击 **Confirm（确定）** 才保存，**Cancel（取消）** 保留原绑定。
- 安装脚本支持重复运行，检查并修复依赖、校验和加载模型。
- 自动创建桌面快捷方式，另提供停止脚本。
- 可选接入兼容 OpenAI 接口的云端或局域网语音识别服务。

中文版文档对应当前版本；应用界面、命令行提示和代码注释仍使用英文。文中保留界面上的英文按钮名称，方便对照操作。

## 环境要求

- Steam Deck 处于 **SteamOS 桌面模式**，麦克风可用。
- Python 3.10 或更新版本并支持 `venv`、Bash，以及 Git；也可以下载源码 ZIP。
- PipeWire 的 `pw-record`；可选提示音使用 `pw-play`。
- 当前用户可以读取手柄或输入设备，并写入 `/dev/uinput`。
- KDE Klipper 配合 `qdbus` / `qdbus6`，或 `wl-copy`，用于粘贴中文等 Unicode 文字。
- 首次安装依赖和所选模型时需要联网。

安装器只使用项目中的 `.venv/`、`models/`，以及当前用户的配置和桌面目录。不使用 sudo、不安装系统包，也不解锁 SteamOS 根文件系统。设备权限可能随 SteamOS 版本及登录会话变化；安装器会报告未满足的条件，不会将其误报为安装成功。

## 手动安装

切换到桌面模式，打开 Konsole：

```bash
mkdir -p ~/Applications
cd ~/Applications
git clone https://github.com/kamjin3086/steamdeck-desktop-voice-input.git
cd steamdeck-desktop-voice-input
./init.sh
```

安装器自动安装默认 SenseVoice，不需要选择模型。安装器会在桌面和应用菜单创建 **Steam Deck Voice Input** 快捷方式，设备检查通过后启动应用。

也可以在 Dolphin 文件管理器中打开项目目录，双击 **Init.desktop**，或右键选择执行。KDE 首次可能要求标记为可信后运行。请将 `Init.desktop` 保留在 `init.sh` 旁边，它会根据自身位置定位安装脚本。如果 ZIP 解压后丢失执行权限，可在终端运行 `bash init.sh`。

### 选择语音识别语言

首次运行 `./init.sh` 自动使用 **常用语言 / SenseVoice**。以后可直接在界面点击 **Change model / languages（更换模型或语言）**，选择以下三组：

| 语言方案 | 覆盖范围 | 识别引擎 | 下载量约为 |
| --- | --- | --- | --- |
| 常用语言，默认推荐 | 中文、英语、粤语、日语、韩语 | SenseVoice Small INT8 | 163 MB |
| 全球主要语言 | 30 种主要语言，包含中英文、法语、德语、西班牙语、俄语、泰语等 | Qwen3-ASR 0.6B INT8 | 879 MB |
| 更多语言 | 1600+ 种语言，包含大量小语种 | Omnilingual ASR 300M INT8 | 293 MB |

选择后可以看到语言范围、特点、引擎、上游文档链接、安装状态和下载大小估算。点击 **Download and switch（下载并切换）**；已经安装的模型则显示 **Use this model（使用此模型）**。弹窗会显示已下载字节和百分比，以及解压、校验、加载等阶段。仅在加载成功后保存选择；失败或取消会保留原模型。已下载模型保存在本机，再次切回无需重新下载。

以后启动及重复安装均沿用已选择的模型，也保留自定义按键。三个选项按语言覆盖范围区分，不表示准确率等级。包含中英文的方案仍应使用相同的中英混合录音验收；不能仅因支持两种语言就保证混说效果。覆盖语言更多也不代表中文识别更准或在 Deck 上更快。

旧 Zipformer / Whisper 安装保留兼容性，但不额外增加 GUI 选项。新安装及 GUI 统一使用上述三组。语言范围依据上游说明：[SenseVoice](https://k2-fsa.github.io/sherpa/onnx/sense-voice/pretrained.html)、[Qwen3-ASR](https://k2-fsa.github.io/sherpa/onnx/qwen3-asr/pretrained.html)、[Omnilingual](https://k2-fsa.github.io/sherpa/onnx/omnilingual-asr/models.html)。

模型按需下载。模型和依赖适用各自的许可证，本仓库的 MIT 许可证覆盖应用代码。详见[第三方说明](THIRD_PARTY_NOTICES.zh-CN.md)。

## 让 agent 帮你安装

可以将下面这段话发给**运行在你的 Steam Deck 上**的 agent：

> 请在这台 Steam Deck 的桌面模式下安装 https://github.com/kamjin3086/steamdeck-desktop-voice-input 。先阅读 AGENTS.md 和 docs/zh-CN/AGENT_INSTALL.md，使用项目提供的安装脚本，保留已有按键绑定，验证桌面快捷方式、模型加载和设备权限。使用默认 SenseVoice 即可，之后我会在 GUI 中按语言需要切换。需要我亲自按键或说话的步骤请明确告知，没有实际测试就不要声称麦克风或 L5 已验证可用。

[Agent 专用安装指南](docs/zh-CN/AGENT_INSTALL.md)提供无人值守安装命令、修复流程和完成判据。初次安装无需决定具体模型，默认 SenseVoice 支持中英文等五种语言。

## 日常使用

1. 双击 **Steam Deck Voice Input**，等待状态显示 **Ready**。
2. 点击需要输入文字的区域，使其获得焦点。
3. 按住 **L5** 说话，释放后结束。停顿时保持按住即可继续听写；每个完成的片段会输入当前焦点区域。
4. 最小化窗口后程序继续运行，点击任务栏图标可重新打开。点击窗口 **X** 或 **Quit application（退出应用）** 都会停止应用，允许桌面注销及切回游戏模式；需要保持运行时请使用最小化。

更换按键：点击 **Rebind button（重新绑定按键）**，按下想使用的键盘或手柄按键；背键请按住约半秒后松开。检查弹窗中显示的候选按键，点击 **Confirm（确定）** 保存。点击 **Cancel（取消）** 或关闭弹窗会保留原绑定。监听期间识别暂停；如果原先正在运行，完成或取消后会恢复。

```bash
./desktop.sh                        # 打开应用或显示已有窗口
./stop.sh                           # 停止本目录对应的窗口和识别进程
./init.sh                           # 修复，保留已选模型
./init.sh --no-launch                 # 安装并检查，不自动启动
./run.sh --meter                     # 命令行运行，显示录音电平
./run.sh --help                      # 查看命令行选项
```

快捷方式指向项目所在目录。移动目录后，重新运行 `init.sh` 更新快捷方式。重复安装保留自定义按键；重复启动会显示已有窗口；重复停止是安全的。

## 通过语音指挥本机 agent

建议在机器上安装一个编程 agent，例如 [Pi](https://github.com/earendil-works/pi)，并按它自己的文档完成安装和认证。在桌面模式下打开运行 agent 的终端，点击它的输入区域，然后按住 L5 口述指令。检查识别文字后，由你自行提交。

例如，可以要求 agent 整理项目文件、修改脚本或排查错误。它能完成哪些任务取决于自身的工具和权限；操作桌面应用还需要相应的桌面自动化工具。本项目负责把语音变成输入文字，本身不会执行口述命令，也不会安装其他 agent。

## 配置、隐私与限制

配置保存在 `~/.config/voice-input/config.json`。本地模型安装后可离线工作；选择云端或局域网后端时，音频会发送到你配置的服务地址，本地模式不会向该地址发送音频。界面日志会显示识别文字，可选诊断日志也可能包含转写内容。

ASCII 文字通过 uinput 模拟键盘输入，中文等 Unicode 文字通过剪贴板粘贴。Unicode 输入会短暂占用剪贴板，默认随后恢复。多数可编辑区域可以使用，但拒绝模拟输入或粘贴的应用、特权窗口和部分安全输入框可能无法接收。说话时请保持目标输入框获得焦点。本项目没有接入输入法框架；当前三组模型均在停顿或释放时识别片段；旧流式模型也可能显示中间结果，真正输入的都是完成的片段。默认关闭激活和释放提示音，避免扬声器声音被转写。可选命令行 `--beep` 会在采集边界之前播放激活提示音、识别收尾之后播放释放提示音。新一次长按不包含激活之前的录音。

背键报告和设备权限可能随固件、Steam Input 或 SteamOS 更新而变化。默认 L5 映射来自已测试过的 Deck 布局，布局不同时请重新绑定。单段录音上限为 60 秒，持续按住时会自动进入下一段，以限制识别内存占用。过慢的解码可能超过滚动音频缓冲容量，长时间听写应使用快于实时的后端。

首个开源版本包含窗口生命周期和按键绑定等自动测试，以及真实本地模型解码验证。本次发布验证运行在没有 Deck 手柄的 Linux Wayland 开发机上，L5、麦克风、任务栏交互和真实输入仍需在你的 Deck 上验收。此前设备上的观察不构成对所有 SteamOS 版本的兼容保证。

## 更多中文文档

- [Agent 安装与验证](docs/zh-CN/AGENT_INSTALL.md)
- [配置说明](docs/zh-CN/CONFIG.md)
- [故障排查](docs/zh-CN/TROUBLESHOOTING.md)
- [云端与局域网识别](docs/zh-CN/CLOUD_ASR.md)
- [开发与测试](docs/zh-CN/DEVELOPING.md)
- [路线图](docs/zh-CN/ROADMAP.md)
- [更新日志](CHANGELOG.zh-CN.md)
- [第三方说明](THIRD_PARTY_NOTICES.zh-CN.md)

## 许可证

[MIT](LICENSE)，Copyright (c) 2026 kamjin3086。正式许可条款见英文 LICENSE 原文。
