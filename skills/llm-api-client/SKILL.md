---
name: llm-api-client
description: Unified REST API client for calling various LLM providers (OpenAI, Anthropic, Google, Azure, etc.). Use when you need to interact with AI models through their REST APIs, handle model switching, manage API keys, or standardize LLM requests across different providers.
---

# LLM API Client

Unified interface for calling different LLM providers via REST APIs.

## Supported Providers

- **OpenAI** - GPT-4, GPT-3.5 series
- **Anthropic** - Claude 3 series (Opus, Sonnet, Haiku)
- **Google** - Gemini Pro, Ultra
- **Volcengine (豆包)** - Doubao series models via 火山引擎
- **Azure OpenAI** - GPT models via Azure
- **Local/Custom** - Any OpenAI-compatible endpoint

## Quick Start

### Using the Python Client

```python
from scripts.llm_client import LLMClient

# Initialize client
client = LLMClient(provider="openai", api_key="your-api-key")

# Simple completion
response = client.complete(
    messages=[{"role": "user", "content": "Hello!"}],
    model="gpt-4"
)
print(response["content"])

# Streaming
for chunk in client.complete_stream(
    messages=[{"role": "user", "content": "Tell me a story"}],
    model="gpt-4"
):
    print(chunk, end="")
```

### Using Environment Variables

```python
import os
from scripts.llm_client import LLMClient

# Set API keys as environment variables
os.environ["OPENAI_API_KEY"] = "sk-..."
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."
os.environ["ARK_API_KEY"] = "your-volcengine-key"  # 火山引擎

# Initialize without explicit key (reads from env)
client = LLMClient(provider="openai")  # Uses OPENAI_API_KEY
```

## Provider-Specific Details

See [references/providers.md](references/providers.md) for:
- Provider-specific parameters
- Model name mappings
- Rate limits and quotas
- Authentication methods

### Volcengine (豆包) Example

```python
from scripts.llm_client import LLMClient

client = LLMClient(provider="volcengine", api_key="your-ark-api-key")

# Text-only request
response = client.complete(
    messages=[{"role": "user", "content": "你好！"}],
    model="doubao-seed-2-0-pro-260215"
)
print(response.content)

# Multimodal request (image + text)
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
                "text": "你看见了什么？"
            }
        ]
    }],
    model="doubao-seed-2-0-pro-260215"
)
```

## Advanced Usage

### Custom Base URL

```python
# For Azure or local models
client = LLMClient(
    provider="azure",
    api_key="your-azure-key",
    base_url="https://your-resource.openai.azure.com/"
)
```

### Request Parameters

```python
response = client.complete(
    messages=[{"role": "user", "content": "Hello"}],
    model="gpt-4",
    temperature=0.7,
    max_tokens=1000,
    top_p=1.0,
    frequency_penalty=0.0,
    presence_penalty=0.0,
    stop=["END"]
)
```

### Error Handling

```python
from scripts.llm_client import LLMClient, LLMError, RateLimitError

try:
    response = client.complete(messages=[...], model="gpt-4")
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}")
except LLMError as e:
    print(f"LLM API error: {e}")
```

## Command Line Usage

```bash
# Simple completion
python scripts/llm_client.py --provider openai --model gpt-4 --message "Hello!"

# With system prompt
python scripts/llm_client.py \
    --provider anthropic \
    --model claude-3-opus-20240229 \
    --system "You are a helpful assistant" \
    --message "What is the capital of France?"

# Read from file
python scripts/llm_client.py \
    --provider openai \
    --model gpt-4 \
    --file input.txt \
    --output result.txt

# Volcengine (豆包)
python scripts/llm_client.py \
    --provider volcengine \
    --model doubao-seed-2-0-pro-260215 \
    --message "你好，请介绍一下自己"
```
