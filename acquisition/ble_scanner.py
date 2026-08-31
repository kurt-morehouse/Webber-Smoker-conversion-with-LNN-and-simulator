import logging
from pathlib import Path

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from home_assistant_bluetooth import BluetoothServiceInfo

from acquisition.config import AppConfig
from acquisition.probe_service import ProbeService
from acquisition.raw_ble_packet_logger import RawBlePacketLogger


LOGGER = logging.getLogger(__name__)

DEFAULT_BLUETOOTH_NAME: str = "CQ60"
BLE_SOURCE_NAME: str = "bleak"
RAW_PACKET_FILENAME: str = "raw_ble_packets.csv"


class ChefIqScanner:
    def __init__(
        self,
        config: AppConfig,
        probe_service: ProbeService,
        raw_packet_directory: Path | None = None,
    ) -> None:

        self._config = config
        self._probe_service = probe_service

        self._raw_packet_logger = (
            RawBlePacketLogger(
                Path(raw_packet_directory) / RAW_PACKET_FILENAME,
                config.manufacturer_id,
            )
            if raw_packet_directory is not None
            else None
        )

        self._scanner = BleakScanner(
            detection_callback=self._detection_callback
        )

    async def start(self) -> None:
        LOGGER.info("Starting Chef iQ BLE scanner")
        if self._raw_packet_logger is not None:
            LOGGER.info(
                "Raw BLE packet capture: %s",
                self._raw_packet_logger.path,
            )
        await self._scanner.start()

    async def stop(self) -> None:
        LOGGER.info("Stopping Chef iQ BLE scanner")
        await self._scanner.stop()

    def _detection_callback(
        self,
        device: BLEDevice,
        advertisement: AdvertisementData,
    ) -> None:

        manufacturer_data = (
            advertisement.manufacturer_data
        )

        raw_packet = manufacturer_data.get(
            self._config.manufacturer_id
        )

        if raw_packet is None:
            return

        if (
            len(raw_packet)
            > self._config.max_probe_packet_length_bytes
        ):
            return

        # Important macOS/CoreBluetooth conversion.
        address = str(device.address)

        bluetooth_name = str(
            advertisement.local_name
            or device.name
            or DEFAULT_BLUETOOTH_NAME
        )

        rssi = int(advertisement.rssi)

        # Capture the exact manufacturer payload BEFORE parser processing.
        # Diagnostic logging must never prevent normal acquisition.
        if self._raw_packet_logger is not None:
            try:
                self._raw_packet_logger.record(
                    address=address,
                    bluetooth_name=bluetooth_name,
                    rssi=rssi,
                    raw_packet=raw_packet,
                )
            except Exception:
                LOGGER.exception(
                    "Raw BLE packet logging failed for %s",
                    address,
                )

        service_info = BluetoothServiceInfo(
            name=bluetooth_name,
            address=address,
            rssi=rssi,
            manufacturer_data=manufacturer_data,
            service_data={},
            service_uuids=[],
            source=BLE_SOURCE_NAME,
        )

        self._probe_service.process_advertisement(
            address=address,
            bluetooth_name=bluetooth_name,
            rssi=rssi,
            raw_packet=raw_packet,
            service_info=service_info,
        )
