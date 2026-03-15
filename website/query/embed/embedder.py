"""
Wrapper around Ollama nomic-embed-text for generating 768d embeddings.
"""
import sys
from pathlib import Path
import httpx
from typing import Union

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "website"))
from query.config import OLLAMA_BASE_URL, EMBED_MODEL, EMBED_DIM


class Embedder:
    def __init__(self, model: str = EMBED_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url
        self._client = httpx.Client(timeout=60.0)

    def embed(self, text: str) -> list[float]:
        """Embed a single string. Returns 768-dim float list."""
        response = self._client.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]

    def embed_batch(self, texts: list[str], verbose: bool = False) -> list[list[float]]:
        """Embed a list of strings."""
        embeddings = []
        for i, text in enumerate(texts):
            if verbose and i % 50 == 0:
                print(f"  Embedding {i}/{len(texts)}...")
            embeddings.append(self.embed(text))
        return embeddings

    def health_check(self) -> bool:
        try:
            response = self._client.get(f"{self.base_url}/api/tags", timeout=5.0)
            models = [m["name"] for m in response.json().get("models", [])]
            return any(self.model in m for m in models)
        except Exception:
            return False
