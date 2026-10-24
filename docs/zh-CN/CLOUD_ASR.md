# 云端与局域网语音识别

[English](../CLOUD_ASR.md) | [中文首页](../../README.zh-CN.md)

默认使用本地识别。云端模式先将片段缓存为 PCM，打包成 WAV，再发送给兼容 OpenAI 转写接口的服务，不支持中间识别结果。选择远程地址时音频会离开本机；服务账号、模型权限、费用及可用性需要另行管理。

局域网配置示例：

```json
{
  "asr": {
    "backend": "cloud",
    "base_url": "http://192.168.1.10:8000/v1",
    "model": "whisper-1",
    "language": "zh",
    "timeout": 30
  }
}
```

示例地址需要替换成你的服务器。明文 HTTP 应仅用于可信局域网，或自行配置 HTTPS。服务必须接受 multipart WAV 文件及 model、language 字段，并返回含 `text` 字段的 JSON 或纯文字结果。可使用 whisper.cpp 等实现搭建服务，但需要核对具体 API，不能假定每个服务接口都兼容。

命令行临时覆盖：

```bash
./run.sh --backend cloud --base-url http://192.168.1.10:8000/v1 \
  --cloud-model whisper-1 --language zh
```

`models.json` 中包含 OpenAI、Groq、SiliconFlow 和局域网服务的示例预设。服务模型名称和可用性可能变化。密钥环境变量分别是 `OPENAI_API_KEY`、`GROQ_API_KEY`、`SILICONFLOW_API_KEY`。必须在启动应用的环境中设置；某个终端里导出的变量，不会自动传给从其他位置点击的桌面快捷方式。

默认在 base_url 后添加 `/audio/transcriptions`。使用其他路径时，可在 ASR 配置中提供 `endpoint`，例如特定服务器的 `/inference`。需要纯文字响应时使用 `response_format: "text"`。非认证类临时失败可能重试，401 会直接报错而不重试。

使用托管服务时，应明确设置云端模型，或指定 `--cloud-model`，避免把保存的本地模型名称误传给云端。

安装器会选择本地模型。如果要使用云端，请在本地安装完成后配置云端后端。密钥不要写入仓库文件，分享 `./run.sh --config` 输出前请隐藏凭据。
