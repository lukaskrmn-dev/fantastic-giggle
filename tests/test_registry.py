"""
Simple tests for registry and peer basics.
"""
import os
import tempfile
import asyncio
from ai_orchestrator import __version__
from ai_orchestrator.registry import publish_peer, list_peers, remove_peer, REGISTRY_DIR


def test_registry_publish_list_and_remove(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setenv('AI_ORCH_REGISTRY', td)
        # publish a peer
        publish_peer('test-a', {'id': 'test-a', 'token': 'tok'})
        peers = list_peers()
        assert 'test-a' in peers
        # remove
        remove_peer('test-a')
        peers2 = list_peers()
        assert 'test-a' not in peers2
