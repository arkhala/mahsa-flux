#!/usr/bin/env python3
"""
TCP port multiplexer — routes TLS traffic to Xray and plain HTTP to the
subscription server, allowing both services to share a single exposed port.

Detection: the first byte of a TLS record is 0x16 (handshake).
Everything else (e.g. an HTTP method like ``GET``) is forwarded to the
subscription Flask server.
"""

import asyncio
import os
import sys

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "31443"))
XRAY_PORT = int(os.getenv("XRAY_INTERNAL_PORT", "10443"))
SUB_PORT = int(os.getenv("SUB_INTERNAL_PORT", "10080"))


async def pipe(reader, writer):
    """Forward data from *reader* to *writer* until EOF."""
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def handle(client_reader, client_writer):
    """Peek at the first byte and route to the appropriate backend."""
    try:
        header = await asyncio.wait_for(client_reader.read(1), timeout=2)
    except (asyncio.TimeoutError, ConnectionResetError):
        client_writer.close()
        return

    if not header:
        client_writer.close()
        return

    # 0x16 = TLS Handshake record type
    backend_port = XRAY_PORT if header[0] == 0x16 else SUB_PORT

    try:
        backend_reader, backend_writer = await asyncio.open_connection(
            "127.0.0.1", backend_port
        )
    except OSError:
        client_writer.close()
        return

    backend_writer.write(header)
    await backend_writer.drain()

    await asyncio.gather(
        pipe(client_reader, backend_writer),
        pipe(backend_reader, client_writer),
    )


async def main():
    server = await asyncio.start_server(handle, LISTEN_HOST, LISTEN_PORT)
    print(
        f"🔀 Multiplexer listening on :{LISTEN_PORT} "
        f"(TLS→:{XRAY_PORT}, HTTP→:{SUB_PORT})",
        file=sys.stderr,
    )
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
