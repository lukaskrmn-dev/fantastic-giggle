"""
registry.py
Secure filesystem registry for brokerless discovery.
"""
import json
import os
import uuid
from pathlib import Path
from typing import Dict, Optional

REGISTRY_DIR = Path(os.environ.get("AI_ORCH_REGISTRY", Path.home() / ".local" / "share" / "ai-orchestrator"))
REGISTRY_DIR_MODE = 0o700
PEER_FILE_MODE = 0o600


def ensure_registry_dir():
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    try:
        REGISTRY_DIR.chmod(REGISTRY_DIR_MODE)
    except Exception:
        # best-effort; on some filesystems this may fail
        pass


def peer_filename(peer_id: str) -> Path:
    return REGISTRY_DIR / f"{peer_id}.json"


def publish_peer(peer_id: str, metadata: Dict):
    """
    Atomically publish peer metadata to the registry directory.
    metadata is a JSON-serializable dict and should include 'id' and 'token' fields.
    """
    ensure_registry_dir()
    fn = peer_filename(peer_id)
    tmp = fn.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False)
    # atomic replace
    os.replace(tmp, fn)
    try:
        fn.chmod(PEER_FILE_MODE)
    except Exception:
        pass


def remove_peer(peer_id: str):
    fn = peer_filename(peer_id)
    try:
        fn.unlink()
    except FileNotFoundError:
        pass


def load_peer(peer_id: str) -> Optional[Dict]:
    fn = peer_filename(peer_id)
    if not fn.exists():
        return None
    try:
        with open(fn, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def list_peers() -> Dict[str, Dict]:
    ensure_registry_dir()
    out = {}
    for p in REGISTRY_DIR.glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            peer_id = p.stem
            out[peer_id] = data
        except Exception:
            continue
    return out
