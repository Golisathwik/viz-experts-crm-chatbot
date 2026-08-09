import httpx
import json
from typing import AsyncGenerator, List, Dict, Any, Optional
from new_backend.ai.llm.adapters.base import BaseAIAdapter

class GroqAdapter(BaseAIAdapter):
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        if messages:
            payload_messages.extend(messages)
        if prompt:
            payload_messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Check if the prompt/system_prompt suggests JSON output
        # If so, and the model supports it, enable JSON response format
        is_json_requested = False
        if "json" in prompt.lower():
            is_json_requested = True
        elif system_prompt and "json" in system_prompt.lower():
            is_json_requested = True

        if is_json_requested and self.config.get("supports_json", False):
            payload["response_format"] = {"type": "json_object"}

        url = "https://api.groq.com/openai/v1/chat/completions"
        payload_str = json.dumps(payload)
        history_len = len(messages) if messages else 0
        crm_size = len(system_prompt) if system_prompt else 0
        
        print("\n--- Provider Call Info ---", flush=True)
        print(f"Final Request URL: {url}", flush=True)
        print(f"Model Name: {self.model}", flush=True)
        print(f"Payload Size: {len(payload_str)} bytes", flush=True)
        print(f"Number of History Messages: {history_len}", flush=True)
        print(f"CRM Context Size: {crm_size} characters", flush=True)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            print(f"Response Status Code: {response.status_code}", flush=True)
            print(f"Response Body: {response.text[:500]}", flush=True)
            print("---------------------------\n", flush=True)
            
            if response.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"Groq API Error: {response.status_code} - {response.text}",
                    request=response.request,
                    response=response
                )
                
            result = response.json()
            return result["choices"][0]["message"]["content"]

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        if messages:
            payload_messages.extend(messages)
        if prompt:
            payload_messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        url = "https://api.groq.com/openai/v1/chat/completions"
        payload_str = json.dumps(payload)
        history_len = len(messages) if messages else 0
        crm_size = len(system_prompt) if system_prompt else 0
        
        print("\n--- Provider Call Info (Stream) ---", flush=True)
        print(f"Final Request URL: {url}", flush=True)
        print(f"Model Name: {self.model}", flush=True)
        print(f"Payload Size: {len(payload_str)} bytes", flush=True)
        print(f"Number of History Messages: {history_len}", flush=True)
        print(f"CRM Context Size: {crm_size} characters", flush=True)

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            ) as response:
                print(f"Response Status Code: {response.status_code}", flush=True)
                if response.status_code != 200:
                    error_bytes = await response.aread()
                    error_text = error_bytes.decode('utf-8', errors='ignore')
                    print(f"Response Body: {error_text[:500]}", flush=True)
                    print("---------------------------\n", flush=True)
                    raise httpx.HTTPStatusError(
                        f"Groq API Stream Error: {response.status_code} - {error_text}",
                        request=response.request,
                        response=response
                    )
                else:
                    print("Response Body: [Streaming Response Started]", flush=True)
                    print("---------------------------\n", flush=True)
                
                has_yielded = False
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data_json = json.loads(data_str)
                            if "error" in data_json:
                                raise RuntimeError(f"Groq API Stream Error: {data_json['error'].get('message')}")
                            delta = data_json["choices"][0]["delta"]
                            if "content" in delta:
                                yield delta["content"]
                                has_yielded = True
                        except Exception as e:
                            if isinstance(e, RuntimeError):
                                raise e
                            pass
                if not has_yielded:
                    raise RuntimeError("Groq API Stream yielded no content")
