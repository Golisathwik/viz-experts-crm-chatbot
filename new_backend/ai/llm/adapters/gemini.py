import httpx
import json
from typing import AsyncGenerator, List, Dict, Any, Optional
from new_backend.ai.llm.adapters.base import BaseAIAdapter

class GeminiAdapter(BaseAIAdapter):
    def _build_payload(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        
        # 1. Standardize messages into input list by combining system_prompt, history (messages), and current prompt
        input_messages = []
        if system_prompt:
            input_messages.append({"role": "system", "content": system_prompt})
        if messages:
            input_messages.extend(messages)
        if prompt:
            input_messages.append({"role": "user", "content": prompt})

        # 2. Map and separate system instruction and user/model contents
        contents = []
        system_instruction = None
        
        for msg in input_messages:
            role = msg.get("role")
            content = msg.get("content") or msg.get("message") or ""
            
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            else:
                mapped_role = "model" if role == "assistant" else "user"
                contents.append({
                    "role": mapped_role,
                    "parts": [{"text": content}]
                })
        
        # 3. Merge consecutive same-role messages for Gemini API validation compliance
        merged_contents = []
        for item in contents:
            if not merged_contents:
                merged_contents.append(item)
            else:
                last = merged_contents[-1]
                if last["role"] == item["role"]:
                    last_text = last["parts"][0]["text"]
                    item_text = item["parts"][0]["text"]
                    last["parts"][0]["text"] = last_text + "\n" + item_text
                else:
                    merged_contents.append(item)
                    
        payload = {
            "contents": merged_contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        if system_instruction:
            payload["systemInstruction"] = system_instruction
            
        # Check if the prompt/system_prompt suggests JSON output
        is_json_requested = False
        if "json" in prompt.lower():
            is_json_requested = True
        elif system_prompt and "json" in system_prompt.lower():
            is_json_requested = True

        if is_json_requested and self.config.get("supports_json", False):
            payload["generationConfig"]["responseMimeType"] = "application/json"
            
        return payload

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024
    ) -> str:
        payload = self._build_payload(prompt, system_prompt, messages, temperature, max_tokens)
        
        # Build URL
        url = f"{self.config.get('base_url', 'https://generativelanguage.googleapis.com/v1beta')}/models/{self.model}:generateContent?key={self.api_key}"
        
        payload_str = json.dumps(payload)
        history_len = len(messages) if messages else 0
        crm_size = len(system_prompt) if system_prompt else 0
        
        # Mask the API key in the printed URL to protect security
        masked_url = url.split("?")[0] + "?key=***"
        
        print("\n--- Provider Call Info ---", flush=True)
        print(f"Final Request URL: {masked_url}", flush=True)
        print(f"Model Name: {self.model}", flush=True)
        print(f"Payload Size: {len(payload_str)} bytes", flush=True)
        print(f"Number of History Messages: {history_len}", flush=True)
        print(f"CRM Context Size: {crm_size} characters", flush=True)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            
            print(f"Response Status Code: {response.status_code}", flush=True)
            print(f"Response Body: {response.text[:500]}", flush=True)
            print("---------------------------\n", flush=True)
            
            if response.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"Gemini API Error: {response.status_code} - {response.text}",
                    request=response.request,
                    response=response
                )
                
            result = response.json()
            try:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                raise ValueError(f"Unexpected response structure from Gemini API: {result}") from e

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        payload = self._build_payload(prompt, system_prompt, messages, temperature, max_tokens)
        
        # Build URL for stream
        url = f"{self.config.get('base_url', 'https://generativelanguage.googleapis.com/v1beta')}/models/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        
        payload_str = json.dumps(payload)
        history_len = len(messages) if messages else 0
        crm_size = len(system_prompt) if system_prompt else 0
        
        # Mask key in URL
        masked_url = url.split("?")[0] + "?alt=sse&key=***"
        
        print("\n--- Provider Call Info (Stream) ---", flush=True)
        print(f"Final Request URL: {masked_url}", flush=True)
        print(f"Model Name: {self.model}", flush=True)
        print(f"Payload Size: {len(payload_str)} bytes", flush=True)
        print(f"Number of History Messages: {history_len}", flush=True)
        print(f"CRM Context Size: {crm_size} characters", flush=True)
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            ) as response:
                print(f"Response Status Code: {response.status_code}", flush=True)
                if response.status_code != 200:
                    error_bytes = await response.aread()
                    error_text = error_bytes.decode('utf-8', errors='ignore')
                    print(f"Response Body: {error_text[:500]}", flush=True)
                    print("---------------------------\n", flush=True)
                    raise httpx.HTTPStatusError(
                        f"Gemini API Stream Error: {response.status_code} - {error_text}",
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
                        try:
                            data_json = json.loads(data_str)
                            if "error" in data_json:
                                raise RuntimeError(f"Gemini API Stream Error: {data_json['error'].get('message')}")
                            if "candidates" in data_json:
                                candidates = data_json["candidates"]
                                if candidates and "content" in candidates[0]:
                                    parts = candidates[0]["content"]["parts"]
                                    if parts and "text" in parts[0]:
                                        yield parts[0]["text"]
                                        has_yielded = True
                        except Exception as e:
                            if isinstance(e, RuntimeError):
                                raise e
                            pass
                if not has_yielded:
                    raise RuntimeError("Gemini API Stream yielded no content")
