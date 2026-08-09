from typing import AsyncGenerator, List, Dict, Any, Optional

class BaseAIAdapter:
    def __init__(self, model: str, config: Dict[str, Any], api_key: str):
        self.model = model
        self.config = config
        self.api_key = api_key

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024
    ) -> str:
        """
        Executes a completion. Returns the response string.
        """
        raise NotImplementedError

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """
        Streams completion text chunks.
        """
        raise NotImplementedError
        yield
