import httpx
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class ResultsApiClient:
    """
    HTTP-клиент для отправки результатов обработки ML-задач обратно в API.
    """
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.results_endpoint = f"{self.base_url}/api/v1/requests/results"

    async def post_result(self, payload: Dict[str, Any]) -> int:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.results_endpoint,
                json=payload,
                timeout=self.timeout
            )
            return response.status_code
