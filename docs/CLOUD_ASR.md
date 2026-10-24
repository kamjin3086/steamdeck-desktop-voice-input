# Cloud and LAN transcription

English | [简体中文](zh-CN/CLOUD_ASR.md)

Local mode is the default. Cloud mode buffers a segment as PCM, packages it as WAV, and sends it to an OpenAI-compatible transcription endpoint. It has no partial-transcript support. Audio leaves the machine when you select a remote endpoint; provider accounts, model access, costs, and availability are managed separately.

Example LAN configuration:

```json
{
  "asr": {
    "backend": "cloud",
    "base_url": "http://192.168.1.10:8000/v1",
    "model": "whisper-1",
    "language": "en",
    "timeout": 30
  }
}
```

The LAN address is an example; replace it with your own server. Use a trusted local network for plain HTTP or configure HTTPS. Servers must accept a multipart WAV file with the model/language fields and return JSON with a `text` field or a plain text response. A compatible server may be built with whisper.cpp or another transcription implementation; check that server's API rather than assuming every endpoint is compatible.

CLI override:

```bash
./run.sh --backend cloud --base-url http://192.168.1.10:8000/v1 \
  --cloud-model whisper-1 --language en
```

`models.json` provides example presets for OpenAI, Groq, SiliconFlow, and a LAN service. Preset model names and provider availability can change. Environment variables are `OPENAI_API_KEY`, `GROQ_API_KEY`, and `SILICONFLOW_API_KEY` respectively. Set them in the environment that launches the app; a variable exported in one terminal is not automatically inherited by a desktop shortcut launched elsewhere.

The default URL appends `/audio/transcriptions` to base_url. Supply `endpoint` in the ASR configuration for a different route, such as a server-specific `/inference` endpoint. Use `response_format: "text"` when required. A non-authentication transient failure may be retried; a 401 is reported without retrying.

For a hosted preset, ensure the cloud model is explicitly selected in your ASR configuration or use `--cloud-model`. Saved local model names should not be sent to a hosted service by accident.

The installer selects a local model. To keep using a cloud configuration, configure it after local installation. Keep API keys outside repository files and redact `./run.sh --config` output before sharing it.
