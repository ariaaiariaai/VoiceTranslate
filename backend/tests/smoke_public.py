"""End-to-end test via the public Cloudflare Tunnel URL."""
import asyncio
import json
import struct
import math

import websockets


async def main():
    uri = "wss://translate.alphapro.one/ws"
    print(f"Connecting to {uri} ...")
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            "type": "hello",
            "mode": "both",
            "tts_engine": "edge_hk",
            "sample_rate": 16000,
        }))
        print("→ sent hello")
        for _ in range(5):
            raw = await asyncio.wait_for(ws.recv(), timeout=15)
            msg = json.loads(raw)
            print(f"← {msg}")
            if msg.get("type") == "ready":
                break
        print("→ streaming 3 s of audio (440 Hz tone) + 1.5 s silence")
        sample_rate = 16000
        for i in range(3):
            samples = [int(0.05 * 32767 * math.sin(2 * math.pi * 440 * (i * sample_rate + n) / sample_rate)) for n in range(sample_rate)]
            await ws.send(struct.pack(f"<{len(samples)}h", *samples))
            await asyncio.sleep(0.2)
        silence = [0] * int(sample_rate * 1.5)
        await ws.send(struct.pack(f"<{len(silence)}h", *silence))
        await asyncio.sleep(1)
        print("→ waiting for transcripts...")
        for _ in range(8):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=60)
                if isinstance(raw, bytes):
                    print(f"← [binary audio, {len(raw)} bytes]")
                else:
                    print(f"← {raw[:200]}")
            except asyncio.TimeoutError:
                print("(timeout)")
                break
        await ws.send(json.dumps({"type": "stop"}))


asyncio.run(main())
