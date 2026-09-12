"""End-to-end WebSocket smoke test.

Connects to the backend, sends a hello, then streams ~5 seconds of
synthetic PCM (just a 440 Hz tone — no real speech) to verify the
protocol round-trip. The STT will likely output nothing or garbage
without real speech, but we expect a transcript message back.
"""
import asyncio
import json
import sys

import websockets


async def main():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as ws:
        # 1) Send hello
        await ws.send(json.dumps({
            "type": "hello",
            "mode": "both",
            "tts_engine": "edge_hk",
            "sample_rate": 16000,
        }))
        print("→ sent hello")

        # 2) Wait for ready
        for _ in range(5):
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            msg = json.loads(raw)
            print(f"← {msg}")
            if msg.get("type") == "ready":
                break

        # 3) Send 3 × 1-second speech-like chunks + 1.5 s silence to trigger VAD
        print("→ streaming 3 s of audio (440 Hz tone) + 1.5 s silence")
        import struct
        import math
        sample_rate = 16000
        for i in range(3):
            samples = []
            for n in range(sample_rate):
                t = (i * sample_rate + n) / sample_rate
                v = int(0.05 * 32767 * math.sin(2 * math.pi * 440 * t))
                samples.append(v)
            await ws.send(struct.pack(f"<{len(samples)}h", *samples))
            print(f"  speech chunk {i+1}/3")
            await asyncio.sleep(0.2)

        # 1.5 s silence (zeros)
        silence_samples = [0] * int(sample_rate * 1.5)
        await ws.send(struct.pack(f"<{len(silence_samples)}h", *silence_samples))
        print("  silence chunk sent")
        await asyncio.sleep(1)

        # 4) Wait for any transcripts / errors (up to 60 s)
        for _ in range(8):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=60)
                if isinstance(raw, bytes):
                    print(f"← [binary, {len(raw)} bytes]")
                else:
                    print(f"← {raw[:300]}")
            except asyncio.TimeoutError:
                print("(timeout waiting for response)")
                break
        await ws.send(json.dumps({"type": "stop"}))


asyncio.run(main())
