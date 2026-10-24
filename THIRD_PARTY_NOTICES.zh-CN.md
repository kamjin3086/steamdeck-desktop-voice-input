# 第三方说明

[English](THIRD_PARTY_NOTICES.md) | [中文首页](README.zh-CN.md)

[LICENSE](LICENSE) 中的 MIT 许可证覆盖本应用源码，不会改变依赖、下载的模型权重或第三方服务的许可条款。正式 MIT 条款请以英文 LICENSE 原文为准。

- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)：语音识别运行时及模型下载地址来源。重新分发权重前，应查看上游许可和具体模型版本或模型卡。模型按需从上游下载，不包含在本仓库或发布源码压缩包中。
- 三组语言方案通过 sherpa-onnx 上游导出使用 SenseVoice Small、Qwen3-ASR 0.6B 和 Omnilingual ASR 300M。具体许可请核对下载模型的 LICENSE 或模型卡，语言覆盖和权重属于上游资源。
- [Qt for Python / PySide6](https://doc.qt.io/qtforpython-6/)：原生 GUI 运行时，适用自己的上游许可。本项目安装其 wheel，而不是将 Qt 嵌入源码发布包。
- [Python](https://www.python.org/)：本应用使用的标准库运行环境。
- PipeWire、KDE Plasma / Klipper、Linux uinput / evdev / hidraw 为主机平台组件，其许可与分发由操作系统管理。

云端语音识别服务和可选编程 agent 是独立产品，有各自的条款、模型许可、认证和计费。应用发布包不包含模型权重、服务凭据或 agent 软件包。
