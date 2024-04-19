"""Tigo Proxy Server"""

import asyncio
import io
import json
import logging
import os
import ssl
import subprocess
from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass
from http import client
from http.server import BaseHTTPRequestHandler

_LOGGER: logging.Logger = logging.getLogger()


@dataclass
class TigoProxyOptions:
    """Data class for Option values"""

    tigo_server: str
    tigo_port: int
    max_read: int


class TigoCCAServerProxy:
    """Class for Tigo CCA Server Proxy"""

    CERT_FILENAME = "/data/cert.crt"
    KEY_FILENAME = "/data/cert.key"
    OPTIONS_FILENAME = "/data/options.json"

    def __init__(self, host: str, port: int) -> None:

        self.host: str = host
        self.port: int = port
        if os.path.exists(self.OPTIONS_FILENAME):
            with open(self.OPTIONS_FILENAME, encoding="utf-8") as f:
                self.options = TigoProxyOptions(**json.load(f))

        if not os.path.exists(self.CERT_FILENAME) and not os.path.exists(
            self.KEY_FILENAME
        ):
            subprocess.run(
                f"openssl req -new -x509 -days 365 -nodes -out {self.CERT_FILENAME} "
                "-keyout {self.KEY_FILENAME} -batch",
                shell=True,
                check=False,
            )

        self.ssl_ctx: ssl.SSLContext = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH
        )
        self.ssl_ctx.load_cert_chain(
            certfile=self.CERT_FILENAME,
            keyfile=self.KEY_FILENAME,
        )
        self.server: asyncio.Server | None = None

    async def process_data(self, data: bytes) -> None:
        """Process the data from the connection"""
        http_data = HTTPRequestParser(data=data)
        print(http_data.command, http_data.request_version)
        print(len(http_data.headers))

    async def pass_data(
        self,
        prefix: str,
        reader: StreamReader,
        writer: StreamWriter,
        *,
        process=False,
    ) -> None:
        """Sends data from reader to writer"""
        connection_data: bytes = b""
        while not reader.at_eof():
            data: bytes = await reader.read(self.options.max_read)
            connection_data += data if process else b""
            _LOGGER.debug("%s Data %s", prefix, data)
            try:
                writer.write(data)
                await writer.drain()
                if len(data) == 0:
                    break
            except ConnectionResetError as _:
                _LOGGER.error("%s Connection error", prefix)
                break

        _LOGGER.info("%s Closing connection.", prefix)
        writer.close()
        await writer.wait_closed()
        if process:
            await self.process_data(connection_data)

    async def handle_connection(
        self, c_reader: StreamReader, c_writer: StreamWriter
    ) -> None:
        """Handle new connections to the server"""
        addr = c_writer.get_extra_info("peername")
        _LOGGER.info("Connection established with %s", addr)

        ssl_ctx: ssl.SSLContext = ssl.create_default_context(
            purpose=ssl.Purpose.SERVER_AUTH
        )
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        try:
            s_reader, s_writer = await asyncio.open_connection(
                self.options.tigo_server,
                self.options.tigo_port,
                ssl=ssl_ctx,
            )
        except ConnectionRefusedError:
            _LOGGER.error("Upstream connection failed")
            c_writer.close()
            await c_writer.wait_closed()
            return

        await asyncio.gather(
            self.pass_data(">> ", c_reader, s_writer, process=True),
            self.pass_data(
                "<< ",
                s_reader,
                c_writer,
            ),
        )

    async def serve(self) -> None:
        """Start serving connections"""
        server: asyncio.Server = await asyncio.start_server(
            self.handle_connection,
            self.host,
            self.port,
            ssl=self.ssl_ctx,
        )

        addrs: str = ", ".join(str(sock.getsockname()) for sock in server.sockets)
        _LOGGER.info("Serving on %s", addrs)

        async with server:
            await server.serve_forever()


class HTTPRequestParser(BaseHTTPRequestHandler):
    """Class to suport parsing of HTTP requests"""

    def __init__(self, data: bytes) -> None:
        self.raw_data: bytes = data
        raw_lines: list[bytes] = self.raw_data.splitlines(keepends=True)
        self.rfile = io.BytesIO(b"".join(raw_lines[1:]))
        self.raw_requestline: bytes = raw_lines[0]
        self.error: bool = not self.parse_request()

    def send_error(self, code, message=None, explain=None) -> None:
        """Suppress errors"""


async def setup_server(host, port) -> None:
    """Setup the server with cert and key file"""
    proxy = TigoCCAServerProxy(host, port)
    await proxy.serve()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(setup_server("0.0.0.0", 1234))
    # a = HTTPRequestParser(
    #     data=b"GET / HTTP/1.1\r\nHost: localhost:1234\r\nUser-Agent: curl/8.4.0\r\nAccept: */*\r\n\r\n"
    # )
    # print(a)
