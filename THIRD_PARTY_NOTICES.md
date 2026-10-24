# Third-party notices

English | [简体中文](THIRD_PARTY_NOTICES.zh-CN.md)

The MIT license in LICENSE covers this application's source. It does not relicense dependencies, downloaded model weights, or third-party services.

- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx): speech-recognition runtime and source of model-download URLs. Review its upstream license and the specific model release/model card before redistributing weights. Models are downloaded from upstream on demand and are not bundled in this repository or release archive.
- Language groups use SenseVoice Small, Qwen3-ASR 0.6B, and Omnilingual ASR 300M via upstream sherpa-onnx exports. Review the specific downloaded model LICENSE/model card; language coverage and model weights are upstream assets.
- [Qt for Python / PySide6](https://doc.qt.io/qtforpython-6/): native GUI runtime, distributed under its own upstream licensing terms. This project installs the wheel rather than embedding Qt in the source release.
- [Python](https://www.python.org/): standard-library runtime used by the application.
- PipeWire, KDE Plasma/Klipper, and Linux uinput/evdev/hidraw are host platform components; their licenses and distribution are managed by the OS.

Cloud transcription providers and optional coding agents are separate products with their own terms, model licenses, authentication, and billing. No model weights, provider credentials, or agent packages are included in the application release.
