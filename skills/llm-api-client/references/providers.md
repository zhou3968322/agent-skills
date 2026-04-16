# LLM Provider Reference

Detailed information for each supported LLM provider.

## OpenAI

**Environment Variable:** `OPENAI_API_KEY`

### Supported Models

| Model | Context | Description |
|-------|---------|-------------|
| gpt-4o | 128K | Latest multimodal model (flagship) |
| gpt-4o-mini | 128K | Smaller, faster, cheaper version |
| gpt-4-turbo | 128K | GPT-4 Turbo with vision |
| gpt-4 | 8K | Original GPT-4 |
| gpt-3.5-turbo | 16K | Fast and cost-effective |

### Parameters

```python
client.complete(
    messages=[...],
    model="gpt-4o",
    temperature=0.7,          # 0.0 - 2.0
    max_tokens=4096,          # Max output tokens
    top_p=1.0,                # Nucleus sampling
    frequency_penalty=0.0,    # -2.0 to 2.0
    presence_penalty=0.0,     # -2.0 to 2.0
    stop=None,                # Stop sequences
    response_format=None      # { "type": "json_object" }
)
```

### Special Features

- **JSON Mode:** Set `response_format={"type": "json_object"}`
- **Function Calling:** Use `tools` parameter
- **Vision:** Pass image URLs in message content

---

## Anthropic (Claude)

**Environment Variable:** `ANTHROPIC_API_KEY`

### Supported Models

| Model | Context | Description |
|-------|---------|-------------|
| claude-3-opus-20240229 | 200K | Most powerful Claude 3 |
| claude-3-sonnet-20240229 | 200K | Balanced performance |
| claude-3-haiku-20240307 | 200K | Fastest Claude 3 |
| claude-3-5-sonnet-20240620 | 200K | Claude 3.5 Sonnet |

### Parameters

```python
client.complete(
    messages=[...],
    model="claude-3-opus-20240229",
    temperature=0.7,          # 0.0 - 1.0
    max_tokens=4096,          # Required for Anthropic
    top_p=None,               # 0.0 - 1.0
    stop=None,                # List of stop sequences
    system=None               # System prompt (optional)
)
```

### Notes

- `max_tokens` is **required** for Anthropic
- System prompt can be passed via `system` parameter or first message with role "system"
- Stop sequences should be a list of strings

---

## Google (Gemini)

**Environment Variable:** `GOOGLE_API_KEY`

### Supported Models

| Model | Context | Description |
|-------|---------|-------------|
| gemini-1.5-pro | 1M | Advanced multimodal model |
| gemini-1.5-flash | 1M | Fast multimodal model |
| gemini-1.0-pro | 32K | Text-only tasks |
| gemini-1.0-pro-vision | 16K | Multimodal (deprecated) |

### Parameters

```python
client.complete(
    messages=[...],
    model="gemini-1.5-pro",
    temperature=0.7,          # 0.0 - 1.0
    max_tokens=None,          # Max output tokens
    top_p=1.0,                # 0.0 - 1.0
    top_k=None                # Top-k sampling
)
```

### Notes

- Messages use "model" role instead of "assistant"
- No native system prompt support (prepend to first user message)

---

## Volcengine (豆包)

**Environment Variable:** `ARK_API_KEY`

**Base URL:** `https://ark.cn-beijing.volces.com/api/v3`

### Supported Models

| Model | Context | Description |
|-------|---------|-------------|
| doubao-seed-2-0-pro-260215 | 200K | Doubao Seed 2.0 Pro |
| doubao-pro-32k | 32K | Doubao Pro 32K |
| doubao-pro-128k | 128K | Doubao Pro 128K |
| doubao-lite-32k | 32K | Doubao Lite 32K |
| doubao-lite-128k | 128K | Doubao Lite 128K |
| doubao-vision-pro-32k | 32K | Doubao Vision Pro |
| doubao-1.5-pro-32k | 32K | Doubao 1.5 Pro |
| doubao-1.5-lite-32k | 32K | Doubao 1.5 Lite |

### Parameters

```python
client.complete(
    messages=[...],
    model="doubao-seed-2-0-pro-260215",
    temperature=0.7,          # 0.0 - 1.0
    max_tokens=4096,          # Max output tokens
    top_p=1.0,                # Nucleus sampling
)
```

### Multimodal (Vision) Support

Volcengine supports image inputs with text:

```python
response = client.complete(
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {"url": "https://example.com/image.png"}
            },
            {
                "type": "text",
                "text": "描述这张图片"
            }
        ]
    }],
    model="doubao-vision-pro-32k"  # Use vision model
)
```

### Setup

Get your API key from [Volcengine Ark Console](https://console.volcengine.com/ark/):

```python
client = LLMClient(
    provider="volcengine",  # or "doubao"
    api_key="your-ark-api-key"
)
```

Or set environment variable:
```bash
export ARK_API_KEY="your-ark-api-key"
```

---

## Azure OpenAI

**Environment Variable:** `AZURE_OPENAI_API_KEY`

### Setup

Requires `base_url` pointing to your Azure OpenAI endpoint:

```python
client = LLMClient(
    provider="openai",  # Azure is OpenAI-compatible
    api_key="your-azure-key",
    base_url="https://your-resource.openai.azure.com/openai/deployments/your-deployment"
)
```

### Parameters

Same as OpenAI, but use your Azure deployment name as the model.

---

## Local/Custom Endpoints

For local models (Ollama, llama.cpp, etc.) or custom OpenAI-compatible APIs:

```python
client = LLMClient(
    provider="openai",
    api_key="not-needed",  # Or your API key
    base_url="http://localhost:11434/v1"  # Ollama example
)

response = client.complete(
    messages=[{"role": "user", "content": "Hello"}],
    model="llama2"  # Model name depends on your setup
)
```

---

## Error Handling

```python
from scripts.llm_client import LLMClient, LLMError, RateLimitError, AuthenticationError

client = LLMClient(provider="openai")

try:
    response = client.complete(messages=[...], model="gpt-4")
except RateLimitError as e:
    # Retry after rate limit
    print(f"Rate limited. Retry after: {e.retry_after}")
except AuthenticationError as e:
    # Invalid API key
    print(f"Authentication failed: {e}")
except LLMError as e:
    # Other API errors
    print(f"API error: {e}")
```

---

## Rate Limits

| Provider | Free Tier | Paid Tier |
|----------|-----------|-----------|
| OpenAI | 3 RPM | 3,500-10,000 RPM |
| Anthropic | Limited | Variable |
| Google | 60 QPM | Up to 1,000 QPM |

Note: Rate limits vary by model and account tier.
