# EORL Model Profile

| Field | Type | Description |
|---|---|---|
| `profile_name` (Profile Name) | Data |  |
| `provider` (Provider) | Select (openai_compatible / anthropic / deterministic) |  |
| `enabled` (Enabled) | Check |  |
| `base_url` (Base URL) | Data |  |
| `api_key_reference` (API Key Reference) | Data | Key/reference only; resolve the actual secret from site config or environment. |
| `model_name` (Model Name) | Data |  |
| `temperature` (Temperature) | Float |  |
| `top_p` (Top P) | Float |  |
| `max_tokens` (Max Tokens) | Int |  |
| `timeout_seconds` (Timeout (s)) | Int |  |
| `max_retries` (Max Retries) | Int |  |
| `seed_if_supported` (Seed (if supported)) | Int |  |
| `tool_call_mode` (Tool Call Mode) | Data |  |
| `structured_output_mode` (Structured Output Mode) | Data |  |
| `reasoning_mode_if_supported` (Reasoning Mode (if supported)) | Data |  |
| `request_headers_json` (Request Headers (JSON)) | Code |  |
