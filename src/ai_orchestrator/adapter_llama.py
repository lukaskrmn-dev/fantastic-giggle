"""
adapter_llama.py
Adapter that exposes a "generate" method using llama.cpp via the llama-cpp-python package.
If llama-cpp-python is not installed, import will fail with a clear error.
"""
import os
from typing import Dict, Any

try:
    from llama_cpp import Llama
except Exception as e:
    Llama = None
    _IMPORT_ERROR = e

class LlamaAdapter:
    def __init__(self, model_path: str, **kwargs):
        if Llama is None:
            raise RuntimeError("llama-cpp-python not installed; pip install llama-cpp-python") from _IMPORT_ERROR
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path not found: {model_path}")
        self.model_path = model_path
        # create the model instance; kwargs forwarded to Llama(...)
        self.llm = Llama(model_path=model_path, **kwargs)

    def generate(self, params: Dict[str, Any], peer_id: str = None) -> Dict[str, Any]:
        """
        params: {"prompt": str, "max_tokens": int, ...}
        Returns: {"text": "...", "raw": <provider-response>}
        """
        prompt = params.get("prompt", "")
        max_tokens = int(params.get("max_tokens", 128))
        temperature = float(params.get("temperature", 0.7))
        # llama-cpp-python supports create_completion; the exact API may vary by version
        # try create_completion, then fallback to __call__ behavior
        try:
            resp = self.llm.create_completion(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
            # try to extract text
            text = None
            if isinstance(resp, dict):
                choices = resp.get("choices")
                if choices and isinstance(choices, list):
                    c0 = choices[0]
                    text = c0.get("text") if isinstance(c0, dict) else str(c0)
            if text is None:
                # fallback: str(resp)
                text = str(resp)
        except TypeError:
            # some versions may expect different params
            resp = self.llm(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
            text = str(resp)
        return {"text": text, "raw": resp}
