#!/usr/bin/env python3
"""
Unified LLM API Client

Supports: OpenAI, Anthropic, Google (Gemini), Azure OpenAI, 
Volcengine (Doubao), and OpenAI-compatible endpoints
"""

import argparse
import json
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Union


class LLMError(Exception):
    """Base exception for LLM client errors"""
    pass


class RateLimitError(LLMError):
    """Rate limit exceeded"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class AuthenticationError(LLMError):
    """API key invalid or missing"""
    pass


@dataclass
class Message:
    role: str
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class CompletionResponse:
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    raw_response: Optional[Dict] = None


class BaseProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
    
    @abstractmethod
    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> CompletionResponse:
        pass
    
    @abstractmethod
    def complete_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> Generator[str, None, None]:
        pass


class OpenAIProvider(BaseProvider):
    """OpenAI API provider"""
    
    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url or self.DEFAULT_BASE_URL)
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key, base_url=self.base_url)
        except ImportError:
            raise LLMError("OpenAI package not installed. Run: pip install openai")
    
    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs
    ) -> CompletionResponse:
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stop=stop,
                **kwargs
            )
            
            return CompletionResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else {},
                raw_response=response.model_dump() if hasattr(response, 'model_dump') else None
            )
        except Exception as e:
            self._handle_error(e)
    
    def complete_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            self._handle_error(e)
    
    def _handle_error(self, error: Exception):
        """Convert provider errors to LLMError types"""
        error_str = str(error).lower()
        
        if "rate limit" in error_str:
            raise RateLimitError(str(error))
        elif "authentication" in error_str or "api key" in error_str:
            raise AuthenticationError(str(error))
        else:
            raise LLMError(str(error))


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider"""
    
    DEFAULT_BASE_URL = "https://api.anthropic.com"
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url or self.DEFAULT_BASE_URL)
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key, base_url=self.base_url)
        except ImportError:
            raise LLMError("Anthropic package not installed. Run: pip install anthropic")
    
    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: Optional[float] = None,
        stop: Optional[List[str]] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> CompletionResponse:
        try:
            # Separate system message if present
            system_msg = system
            chat_messages = messages
            
            if not system_msg and messages and messages[0]["role"] == "system":
                system_msg = messages[0]["content"]
                chat_messages = messages[1:]
            
            # Convert messages to Anthropic format
            anthropic_messages = []
            for msg in chat_messages:
                if msg["role"] == "user":
                    anthropic_messages.append({"role": "user", "content": msg["content"]})
                elif msg["role"] == "assistant":
                    anthropic_messages.append({"role": "assistant", "content": msg["content"]})
            
            params = {
                "model": model,
                "messages": anthropic_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            if system_msg:
                params["system"] = system_msg
            if top_p is not None:
                params["top_p"] = top_p
            if stop:
                params["stop_sequences"] = stop
            
            response = self.client.messages.create(**params)
            
            return CompletionResponse(
                content=response.content[0].text if response.content else "",
                model=response.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                } if response.usage else {}
            )
        except Exception as e:
            self._handle_error(e)
    
    def complete_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> Generator[str, None, None]:
        try:
            system_msg = None
            chat_messages = messages
            
            if messages and messages[0]["role"] == "system":
                system_msg = messages[0]["content"]
                chat_messages = messages[1:]
            
            anthropic_messages = []
            for msg in chat_messages:
                if msg["role"] == "user":
                    anthropic_messages.append({"role": "user", "content": msg["content"]})
                elif msg["role"] == "assistant":
                    anthropic_messages.append({"role": "assistant", "content": msg["content"]})
            
            params = {
                "model": model,
                "messages": anthropic_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
            
            if system_msg:
                params["system"] = system_msg
            
            with self.client.messages.stream(**params) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            self._handle_error(e)
    
    def _handle_error(self, error: Exception):
        error_str = str(error).lower()
        
        if "rate limit" in error_str:
            raise RateLimitError(str(error))
        elif "authentication" in error_str or "api key" in error_str:
            raise AuthenticationError(str(error))
        else:
            raise LLMError(str(error))


class GeminiProvider(BaseProvider):
    """Google Gemini API provider"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.genai = genai
        except ImportError:
            raise LLMError("Google GenerativeAI package not installed. Run: pip install google-generativeai")
    
    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        **kwargs
    ) -> CompletionResponse:
        try:
            # Convert messages to Gemini format
            gemini_messages = []
            for msg in messages:
                if msg["role"] == "user":
                    gemini_messages.append({"role": "user", "parts": [msg["content"]]})
                elif msg["role"] == "model" or msg["role"] == "assistant":
                    gemini_messages.append({"role": "model", "parts": [msg["content"]]})
            
            model_instance = self.genai.GenerativeModel(model)
            
            generation_config = self.genai.types.GenerationConfig(
                temperature=temperature,
                top_p=top_p,
                max_output_tokens=max_tokens
            )
            
            chat = model_instance.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
            response = chat.send_message(
                gemini_messages[-1]["parts"][0] if gemini_messages else "",
                generation_config=generation_config
            )
            
            return CompletionResponse(
                content=response.text,
                model=model,
                usage={}
            )
        except Exception as e:
            self._handle_error(e)
    
    def complete_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> Generator[str, None, None]:
        try:
            gemini_messages = []
            for msg in messages:
                if msg["role"] == "user":
                    gemini_messages.append({"role": "user", "parts": [msg["content"]]})
                elif msg["role"] == "model" or msg["role"] == "assistant":
                    gemini_messages.append({"role": "model", "parts": [msg["content"]]})
            
            model_instance = self.genai.GenerativeModel(model)
            chat = model_instance.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
            
            response = chat.send_message(
                gemini_messages[-1]["parts"][0] if gemini_messages else "",
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            self._handle_error(e)
    
    def _handle_error(self, error: Exception):
        error_str = str(error).lower()
        
        if "rate limit" in error_str or "quota" in error_str:
            raise RateLimitError(str(error))
        elif "api key" in error_str:
            raise AuthenticationError(str(error))
        else:
            raise LLMError(str(error))


class VolcengineProvider(BaseProvider):
    """
    Volcengine (字节火山引擎 / Doubao) API provider
    
    API Docs: https://www.volcengine.com/docs/82379
    """
    
    DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url or self.DEFAULT_BASE_URL)
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise LLMError("requests package not installed. Run: pip install requests")
    
    def _build_content(self, content: Union[str, List[Dict]]) -> Union[str, List[Dict]]:
        """Build content field supporting multimodal input"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return content
        return str(content)
    
    def complete(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        **kwargs
    ) -> CompletionResponse:
        try:
            url = f"{self.base_url}/chat/completions"
            
            # Convert messages to Volcengine format
            volc_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                # Handle multimodal content (list of content items)
                if isinstance(content, list):
                    formatted_content = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                formatted_content.append({
                                    "type": "text",
                                    "text": item.get("text", "")
                                })
                            elif item.get("type") in ("image_url", "image"):
                                image_url = item.get("image_url", {}).get("url", "") if isinstance(item.get("image_url"), dict) else item.get("image_url", "")
                                formatted_content.append({
                                    "type": "image_url",
                                    "image_url": {"url": image_url}
                                })
                    content = formatted_content if formatted_content else ""
                
                volc_messages.append({"role": role, "content": content})
            
            payload = {
                "model": model,
                "messages": volc_messages,
                "temperature": temperature,
                "top_p": top_p,
            }
            
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            # Add any additional parameters
            for key in ["stream", "stop", "frequency_penalty", "presence_penalty", "tools", "tool_choice"]:
                if key in kwargs:
                    payload[key] = kwargs[key]
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = self.requests.post(url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            data = response.json()
            
            # Extract usage info
            usage = {}
            if "usage" in data:
                usage = {
                    "prompt_tokens": data["usage"].get("prompt_tokens", 0),
                    "completion_tokens": data["usage"].get("completion_tokens", 0),
                    "total_tokens": data["usage"].get("total_tokens", 0)
                }
            
            return CompletionResponse(
                content=data["choices"][0]["message"]["content"],
                model=data.get("model", model),
                usage=usage,
                raw_response=data
            )
            
        except self.requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                raise RateLimitError(f"Rate limit exceeded: {e}")
            elif e.response.status_code == 401:
                raise AuthenticationError(f"Authentication failed: {e}")
            else:
                raise LLMError(f"API error: {e}")
        except Exception as e:
            raise LLMError(f"Request failed: {e}")
    
    def complete_stream(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        **kwargs
    ) -> Generator[str, None, None]:
        try:
            url = f"{self.base_url}/chat/completions"
            
            # Convert messages
            volc_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if isinstance(content, list):
                    formatted_content = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                formatted_content.append({
                                    "type": "text",
                                    "text": item.get("text", "")
                                })
                            elif item.get("type") in ("image_url", "image"):
                                image_url = item.get("image_url", {}).get("url", "") if isinstance(item.get("image_url"), dict) else item.get("image_url", "")
                                formatted_content.append({
                                    "type": "image_url",
                                    "image_url": {"url": image_url}
                                })
                    content = formatted_content if formatted_content else ""
                
                volc_messages.append({"role": role, "content": content})
            
            payload = {
                "model": model,
                "messages": volc_messages,
                "temperature": temperature,
                "top_p": top_p,
                "stream": True
            }
            
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = self.requests.post(url, json=payload, headers=headers, stream=True, timeout=120)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                            
        except self.requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                raise RateLimitError(f"Rate limit exceeded: {e}")
            elif e.response.status_code == 401:
                raise AuthenticationError(f"Authentication failed: {e}")
            else:
                raise LLMError(f"API error: {e}")
        except Exception as e:
            raise LLMError(f"Request failed: {e}")


class LLMClient:
    """Unified LLM client supporting multiple providers"""
    
    PROVIDERS = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GeminiProvider,
        "gemini": GeminiProvider,
        "volcengine": VolcengineProvider,
        "doubao": VolcengineProvider,
    }
    
    ENV_KEYS = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "volcengine": "ARK_API_KEY",
        "doubao": "ARK_API_KEY",
    }
    
    def __init__(
        self,
        provider: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize LLM client
        
        Args:
            provider: Provider name (openai, anthropic, google, gemini)
            api_key: API key (if not provided, reads from environment variable)
            base_url: Custom base URL for the API
        """
        provider = provider.lower()
        
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}. Supported: {list(self.PROVIDERS.keys())}")
        
        # Get API key from environment if not provided
        if api_key is None:
            env_key = self.ENV_KEYS.get(provider)
            if env_key:
                api_key = os.environ.get(env_key)
        
        if not api_key:
            raise ValueError(f"API key required for {provider}. Provide directly or set {self.ENV_KEYS.get(provider)} environment variable.")
        
        self.provider_name = provider
        self.provider = self.PROVIDERS[provider](api_key, base_url)
    
    def complete(
        self,
        messages: Union[str, List[Dict[str, str]]],
        model: str,
        **kwargs
    ) -> CompletionResponse:
        """
        Send a completion request
        
        Args:
            messages: Either a string (single user message) or list of message dicts
            model: Model name to use
            **kwargs: Additional provider-specific parameters
        
        Returns:
            CompletionResponse object
        """
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        
        return self.provider.complete(messages, model, **kwargs)
    
    def complete_stream(
        self,
        messages: Union[str, List[Dict[str, str]]],
        model: str,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Send a streaming completion request
        
        Args:
            messages: Either a string (single user message) or list of message dicts
            model: Model name to use
            **kwargs: Additional provider-specific parameters
        
        Yields:
            Text chunks as they arrive
        """
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        
        yield from self.provider.complete_stream(messages, model, **kwargs)
    
    @classmethod
    def list_supported_providers(cls) -> List[str]:
        """Return list of supported provider names"""
        return list(cls.PROVIDERS.keys())


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="LLM API Client")
    parser.add_argument("--provider", required=True, choices=LLMClient.list_supported_providers(),
                       help="LLM provider to use")
    parser.add_argument("--model", required=True, help="Model name")
    parser.add_argument("--message", "-m", help="User message")
    parser.add_argument("--system", "-s", help="System message")
    parser.add_argument("--file", "-f", help="Read message from file")
    parser.add_argument("--output", "-o", help="Write response to file")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature (default: 0.7)")
    parser.add_argument("--max-tokens", type=int, help="Max tokens")
    parser.add_argument("--stream", action="store_true", help="Stream response")
    parser.add_argument("--api-key", help="API key (or set env var)")
    
    args = parser.parse_args()
    
    # Get message content
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()
    elif args.message:
        content = args.message
    else:
        # Read from stdin
        content = sys.stdin.read()
    
    # Build messages
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": content})
    
    # Initialize client
    try:
        client = LLMClient(provider=args.provider, api_key=args.api_key)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Make request
    try:
        params = {
            "temperature": args.temperature
        }
        if args.max_tokens:
            params["max_tokens"] = args.max_tokens
        
        if args.stream:
            output = ""
            for chunk in client.complete_stream(messages, args.model, **params):
                print(chunk, end="", flush=True)
                output += chunk
            print()  # Final newline
            
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
        else:
            response = client.complete(messages, args.model, **params)
            
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(response.content)
            else:
                print(response.content)
            
            # Print usage info to stderr
            if response.usage:
                print(f"\n[Usage: {response.usage}]", file=sys.stderr)
    
    except LLMError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
