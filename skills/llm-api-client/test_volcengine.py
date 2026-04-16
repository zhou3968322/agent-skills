#!/usr/bin/env python3
"""
Test script for Volcengine (Doubao) API client
"""

import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from llm_client import LLMClient, LLMError

# API key from user (masked in output)
API_KEY = "b154af20-1f42-43e3-b06e-c603f4a6befd"

def test_text_completion():
    """Test basic text completion"""
    print("=" * 50)
    print("Test 1: Basic Text Completion")
    print("=" * 50)
    
    try:
        client = LLMClient(provider="volcengine", api_key=API_KEY)
        
        response = client.complete(
            messages=[{"role": "user", "content": "Hello, please introduce yourself in one sentence"}],
            model="doubao-seed-2-0-pro-260215",
            temperature=0.7,
            max_tokens=100
        )
        
        print("[OK] Response received")
        print(f"  Model: {response.model}")
        print(f"  Content: {response.content[:100]}...")
        print(f"  Usage: {response.usage}")
        return True
        
    except LLMError as e:
        print(f"[FAIL] Error: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Unexpected error: {type(e).__name__}: {e}")
        return False


def test_multimodal():
    """Test multimodal (image + text) input"""
    print("\n" + "=" * 50)
    print("Test 2: Multimodal (Image + Text)")
    print("=" * 50)
    
    try:
        client = LLMClient(provider="volcengine", api_key=API_KEY)
        
        response = client.complete(
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png"}
                    },
                    {
                        "type": "text",
                        "text": "What do you see in this image?"
                    }
                ]
            }],
            model="doubao-seed-2-0-pro-260215",
            temperature=0.7,
            max_tokens=200
        )
        
        print("[OK] Response received")
        print(f"  Model: {response.model}")
        print(f"  Content: {response.content[:100]}...")
        return True
        
    except LLMError as e:
        print(f"[FAIL] Error: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Unexpected error: {type(e).__name__}: {e}")
        return False


def test_streaming():
    """Test streaming completion"""
    print("\n" + "=" * 50)
    print("Test 3: Streaming Completion")
    print("=" * 50)
    
    try:
        client = LLMClient(provider="volcengine", api_key=API_KEY)
        
        print("Streaming response: ", end="", flush=True)
        full_response = []
        
        for chunk in client.complete_stream(
            messages=[{"role": "user", "content": "Hello"}],
            model="doubao-seed-2-0-pro-260215",
            temperature=0.7,
            max_tokens=50
        ):
            print(chunk, end="", flush=True)
            full_response.append(chunk)
        
        print()  # New line
        print("[OK] Stream completed")
        print(f"  Total length: {len(''.join(full_response))} chars")
        return True
        
    except LLMError as e:
        print(f"\n[FAIL] Error: {e}")
        return False
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {type(e).__name__}: {e}")
        return False


def main():
    print("Volcengine (Doubao) API Client Test")
    print("API Key: ********-****-****-****-************ (masked)")
    
    results = []
    
    # Run tests
    results.append(("Text Completion", test_text_completion()))
    results.append(("Multimodal", test_multimodal()))
    results.append(("Streaming", test_streaming()))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    print(f"\nOverall: {'All tests passed!' if all_passed else 'Some tests failed.'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
