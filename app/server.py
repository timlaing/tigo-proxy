"""Tigo Proxy Server"""

import argparse
import asyncio
import bz2
import csv
import io
import json
import logging
import ssl
import subprocess
import urllib.parse
from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass
from functools import cached_property
from http.server import BaseHTTPRequestHandler
from xml.etree import ElementTree as ET

import aiomqtt

_LOGGER: logging.Logger = logging.getLogger()


@dataclass
class TigoProxyOptions:
    """Data class for Option values"""

    tigo_server: str
    tigo_port: int
    max_read: int

    mqtt_host: str
    mqtt_user: str
    mqtt_password: str
    mqtt_port: int = 1883


class TigoCsvDataProcessor:
    """Class to handle the processing of the CSV data"""

    def __init__(self, data: bytes, peer: tuple) -> None:
        self.peer: tuple = peer
        self.reader = csv.DictReader(io.StringIO(data.decode("utf-8")), dialect="unix")


class TigoPanelDataProcessor(TigoCsvDataProcessor):
    """Class to handle the processing of the Panel data"""

    panel_name_cache: set[str] = set()

    field_names: dict[str, dict] = {
        "Vin": {
            "device_class": "voltage",
            "unit_of_measurement": "V",
        },
        "Iin": {
            "device_class": "current",
            "unit_of_measurement": "A",
        },
        "Temp": {
            "device_class": "temperature",
            "unit_of_measurement": "°C",
        },
        "Pwm": {
            "entity_category": "diagnostic",
        },
        "Status": {
            "entity_category": "diagnostic",
        },
        "Flags": {
            "entity_category": "diagnostic",
        },
        "RSSI": {
            "device_class": "signal_strength",
            "entity_category": "diagnostic",
            "unit_of_measurement": "dBm",
        },
        "BRSSI": {
            "device_class": "signal_strength",
            "entity_category": "diagnostic",
            "unit_of_measurement": "dBm",
        },
        # "ID": {},
        "Vout": {
            "device_class": "voltage",
            "unit_of_measurement": "V",
        },
        "Details": {
            "entity_category": "diagnostic",
        },
        "Pin": {
            "device_class": "power",
            "unit_of_measurement": "W",
        },
    }

    panel_field_prefix: str = "LMU"

    @cached_property
    def panel_count(self) -> int:
        """returns the number of panels"""
        return len(self.panel_names)

    @cached_property
    def panel_names(self) -> list[str]:
        """returns the number of panels"""
        if self.reader.fieldnames:
            return [
                name.split("_")[1]
                for name in self.reader.fieldnames
                if name.endswith("_ID")
            ]

        return []

    @cached_property
    def panels(self) -> dict[str, dict[str, str | int | float]]:
        """Data panel data as a dict"""
        data: dict[str, dict] = {}
        row: dict[str, str | int | float] = list(self.reader)[0]
        for name in self.panel_names:
            data[name] = {}
            for field in self.field_names:
                data[name][field] = row[f"{self.panel_field_prefix}_{name}_{field}"]

        return data

    def extra_fields(self, field_name: str) -> dict[str, str | int | float]:
        """Extra configuration fields"""
        return self.field_names[field_name]

    async def publish(self, config: TigoProxyOptions) -> None:
        """Publish the data via MQTT"""
        panel_names_set: set = set(self.panel_names)

        async with aiomqtt.Client(
            hostname=config.mqtt_host,
            port=config.mqtt_port,
            username=config.mqtt_user,
            password=config.mqtt_password,
        ) as client:

            if set(self.panel_names) != self.panel_name_cache:
                # perform discovery update
                for panel_name in self.panel_name_cache.difference(panel_names_set):
                    for field in self.field_names:
                        await client.publish(
                            topic="homeassistant/sensor/tigo_mqtt/"
                            f"{panel_name.lower()}_{field.lower()}/config"
                        )

                for panel_name in panel_names_set.difference(self.panel_name_cache):
                    for field in self.field_names:
                        data: dict[str, str | int | float | dict] = {
                            "name": f"{field}",
                            "unqiue_id": f"tigo_mqtt_{panel_name.lower()}_{field.lower()}",
                            "device": {
                                "identifiers": [f"tigo_{panel_name.lower()}"],
                                "name": panel_name,
                                "manufacturer": "Tigo",
                                "model": "TS4-A-O",
                                "via_device": f"{self.peer[0]}",
                            },
                            "origin": {
                                "name": "Tigo Proxy",
                                "sw_version": "2024.04.28-2",
                                "support_url": "https://github.com/timlaing/tigo-proxy",
                            },
                            "state_topic": "homeassistant/sensor/tigo_mqtt/state",
                            "value_template": f"{{{{ value_json.{panel_name}.{field} }}}}",
                            "json_attributes_topic": "homeassistant/sensor/tigo_mqtt/state",
                            "json_attributes_template": f"{{{{ value_json.{panel_name}|tojson }}}}",
                            **self.extra_fields(field),
                        }

                        await client.publish(
                            topic="homeassistant/sensor/tigo_mqtt/"
                            f"{panel_name.lower()}_{field.lower()}/config",
                            payload=json.dumps(data),
                        )

                self.panel_name_cache = set(self.panel_names)

            await client.publish(
                topic="homeassistant/sensor/tigo_mqtt/state",
                payload=json.dumps(self.panels),
            )


class TigoCCAServerProxy:
    """Class for Tigo CCA Server Proxy"""

    CERT_FILENAME = "/data/cert.crt"
    KEY_FILENAME = "/data/cert.key"

    def __init__(self, host: str, port: int, config: TigoProxyOptions) -> None:

        self.host: str = host
        self.port: int = port
        self.options: TigoProxyOptions = config

        # if not os.path.exists(self.CERT_FILENAME) and not os.path.exists(
        #     self.KEY_FILENAME
        # ):
        subprocess.run(
            f"openssl req -new -x509 -days 3650 -nodes -out {self.CERT_FILENAME} "
            f"-keyout {self.KEY_FILENAME} -batch",
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

    async def process_data(self, data: bytes, peer: tuple) -> None:
        """Process the data from the connection"""
        try:
            http_data = HTTPRequestParser(data=data)
            _LOGGER.debug(
                "HTTP request: %s %s %s",
                http_data.command,
                http_data.request_version,
                http_data.path,
            )
            url: urllib.parse.ParseResult = urllib.parse.urlparse(http_data.path)
            qs: dict[str, list[str]] = urllib.parse.parse_qs(url.query)
            for x in http_data.headers:
                _LOGGER.debug("HTTP header: %s=%s", x, http_data.headers[x])
            payload_data: bytes = bz2.decompress(http_data.rfile.read())
            if "Source" in qs:
                _LOGGER.info("Source: %s", qs["Source"][0])
            if "Type" in qs:
                payload: str = payload_data.decode("utf-8")
                match qs["Type"][0]:
                    case "csv":
                        # decode csv
                        if "Source" in qs:
                            match qs["Source"][0]:
                                case "panels":
                                    panel_data = TigoPanelDataProcessor(
                                        payload_data, peer
                                    )
                                    _LOGGER.info(
                                        "Panel Count: %d", panel_data.panel_count
                                    )
                                    _LOGGER.info(
                                        "Panel Names: %s", panel_data.panel_names
                                    )
                                    for panel in panel_data.panels.items():
                                        _LOGGER.info("Panel[0] data: %s", panel)
                                        break

                                    await panel_data.publish(self.options)
                                case "Net_Routing":
                                    d = TigoCsvDataProcessor(payload_data, peer)
                                    row = list(d.reader)[0]
                                    _LOGGER.info(row)
                                case "panels_avg":
                                    d = TigoCsvDataProcessor(payload_data, peer)
                                    row = list(d.reader)[0]
                                    _LOGGER.info(row)
                                case _:
                                    _LOGGER.debug(
                                        "Ignoring data for source: %s", qs["Source"][0]
                                    )
                    case "xml":
                        # decode xml
                        xml: ET.Element = ET.fromstring(text=payload)
                        for child in xml:
                            _LOGGER.debug(
                                "XML Info: %s %s %s",
                                child.tag,
                                child.attrib,
                                child.text,
                            )
                    case _:
                        _LOGGER.debug("Unable to process data type: %s", qs["Type"][0])
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _LOGGER.error("exception during parsing of data: %s", exc)

    async def pass_data(
        self,
        prefix: str,
        reader: StreamReader,
        writer: StreamWriter,
        *,
        peer: tuple | None = None,
        process: bool = False,
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
            await self.process_data(connection_data, peer)

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
            self.pass_data(">> ", c_reader, s_writer, peer=addr, process=True),
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

    def __init__(self, data: bytes) -> None:  # pylint: disable=super-init-not-called
        self.raw_data: bytes = data
        raw_lines: list[bytes] = self.raw_data.splitlines(keepends=True)
        self.rfile = io.BytesIO(b"".join(raw_lines[1:]))
        self.raw_requestline: bytes = raw_lines[0]
        self.error: bool = not self.parse_request()

    def send_error(self, code, message=None, explain=None) -> None:
        """Suppress errors"""


async def setup_server(host, port, config: TigoProxyOptions) -> None:
    """Setup the server with cert and key file"""
    proxy = TigoCCAServerProxy(host, port, config)
    await proxy.serve()


def not_empty_string(arg: str) -> str:
    """Verfies the value is not empty"""
    if isinstance(arg, str) and len(arg) > 0:
        return arg
    raise argparse.ArgumentTypeError(f"value is not a valid string [{str}]")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
    )

    parser = argparse.ArgumentParser("Tigo CCA HA Addon Proxy")
    parser.add_argument(
        "-s",
        "--server",
        type=str,
        default="ds205.tigoenergy.com",
        help="The Tigo remote server host",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=443,
        help="The Tigo remote server port",
    )
    parser.add_argument(
        "-r",
        "--maxread",
        type=int,
        default=1024,
        help="The maximum socket read amount (bytes)",
    )
    parser.add_argument(
        "-l",
        "--listen",
        type=int,
        default=1234,
        help="The local listen port",
    )
    parser.add_argument(
        "--mqtt-host",
        help="The MQTT host",
        required=True,
        type=not_empty_string,
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        help="The MQTT port number",
        default=1883,
        required=True,
    )
    parser.add_argument(
        "--mqtt-user",
        help="The MQTT username",
        required=True,
        type=not_empty_string,
    )
    parser.add_argument(
        "--mqtt-password",
        help="The MQTT password",
        required=True,
        type=not_empty_string,
    )
    args: argparse.Namespace = parser.parse_args()

    asyncio.run(
        setup_server(
            "0.0.0.0",
            args.listen,
            TigoProxyOptions(
                tigo_server=args.server,
                tigo_port=args.port,
                max_read=args.maxread,
                mqtt_host=args.mqtt_host,
                mqtt_port=args.mqtt_port,
                mqtt_user=args.mqtt_user,
                mqtt_password=args.mqtt_password,
            ),
        )
    )
