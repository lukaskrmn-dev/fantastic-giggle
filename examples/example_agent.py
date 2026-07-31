"""
examples/example_agent.py
Example agent that exposes 'greet', 'announce', and 'generate' (llama) RPCs.
Usage:
    python -m examples.example_agent <agent_name> [--model /path/to/model.bin]
"""
import asyncio
import sys
import argparse
from ai_orchestrator.peer import Peer
from ai_orchestrator.registry import list_peers

try:
    from ai_orchestrator.adapter_llama import LlamaAdapter
except Exception:
    LlamaAdapter = None

async def handle_greet(params, peer_id):
    name = params.get("name", "friend")
    return {"message": f"Hello, {name}! (from {peer_id})"}

async def handle_announce(params, peer_id):
    print(f"[{peer_id}] ANNOUNCE: {params}")
    return {"ok": True}

def make_generate(adapter: LlamaAdapter):
    async def _generate(params, peer_id):
        # adapter.generate is sync in this adapter; run in executor if expensive
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, adapter.generate, params, peer_id)
        return resp
    return _generate

async def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--model", help="Path to llama.cpp-compatible model file (for generate)", default=None)
    parser.add_argument("--host", help="Host for TCP server fallback", default="127.0.0.1")
    parser.add_argument("--port", help="Port for TCP server fallback (0 means ephemeral)", type=int, default=0)
    args = parser.parse_args(argv)

    ssl_ctx = None
    # if you want TLS for TCP, create an ssl.SSLContext and pass it to Peer(..., ssl_context=ssl_ctx)
    p = Peer(args.name, ssl_context=ssl_ctx)
    # register simple methods
    p.register_method("greet", handle_greet)
    p.register_method("announce", handle_announce)

    if args.model:
        adapter = LlamaAdapter(model_path=args.model)
        p.register_method("generate", make_generate(adapter))
        print("Llama adapter loaded for model:", args.model)
    else:
        # placeholder generate that responds with an error
        async def _no_model(params, peer_id):
            raise RuntimeError("no_model_loaded")
        p.register_method("generate", _no_model)

    meta = await p.start(host=args.host, port=args.port)
    print("Started peer:", meta)

    async def ann_loop():
        while True:
            await asyncio.sleep(8.0)
            try:
                await p.broadcast_event("announce", {"from": p.id, "name": p.name})
            except Exception:
                pass

    asyncio.create_task(ann_loop())

    async def repl():
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            cmd = line.strip()
            if not cmd:
                continue
            parts = cmd.split()
            if parts[0] == "greet" and len(parts) >= 3:
                peer_id = parts[1]
                whom = " ".join(parts[2:])
                try:
                    res = await p.call_peer(peer_id, "greet", {"name": whom})
                    print("Response:", res)
                except Exception as e:
                    print("Error:", e)
            elif parts[0] == "generate" and len(parts) >= 3:
                peer_id = parts[1]
                prompt = " ".join(parts[2:])
                try:
                    res = await p.call_peer(peer_id, "generate", {"prompt": prompt, "max_tokens": 128})
                    print("Generate result:", res.get("text") if isinstance(res, dict) else res)
                except Exception as e:
                    print("Error:", e)
            elif parts[0] == "peers":
                print(list_peers())
            elif parts[0] == "quit":
                await p.stop()
                break
            else:
                print("Commands: greet <peer_id> <name> | generate <peer_id> <prompt> | peers | quit")

    await repl()

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
