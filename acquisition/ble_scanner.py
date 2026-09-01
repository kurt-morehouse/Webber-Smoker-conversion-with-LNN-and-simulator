import logging
from pathlib import Path

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from home_assistant_bluetooth import BluetoothServiceInfo

from acquisition.chefiq_protocol import extract_chefiq_packet
from acquisition.config import AppConfig
from acquisition.probe_service import ProbeService


LOGGER = logging.getLogger(__name__)

DEFAULT_BLUETOOTH_NAME: str = "CQ60"
BLE_SOURCE_NAME: str = "bleak"


class ChefIqScanner:
    def __init__(
        self,
        config: AppConfig,
        probe_service: ProbeService,
        raw_packet_directory: Path | None = None,
    ) -> None:
        self._config = config
        self._probe_service = probe_service
        self._raw_packet_logger = None

        # Keep the diagnostic logger optional so acquisition does not depend
        # on it. This also remains compatible if the diagnostic module is not
        # installed in an older checkout.
        if raw_packet_directory is not None:
            try:
                from acquisition.raw_ble_packet_logger import RawBlePacketLogger

                self._raw_packet_logger = RawBlePacketLogger(
                    raw_packet_directory
                )
            except Exception:
                LOGGER.exception(
                    "Raw BLE packet logging could not be initialized"
                )

        self._scanner = BleakScanner(
            detection_callback=self._detection_callback
        )

    async def start(self) -> None:
        LOGGER.info("Starting Chef iQ BLE scanner")
        await self._scanner.start()

    async def stop(self) -> None:
        LOGGER.info("Stopping Chef iQ BLE scanner")
        await self._scanner.stop()

    def _detection_callback(
        self,
        device: BLEDevice,
        advertisement: AdvertisementData,
    ) -> None:
        manufacturer_data = advertisement.manufacturer_data

        # Protocol recognition is encapsulated in chefiq_protocol.py.
        raw_packet = extract_chefiq_packet(
            manufacturer_data
        )

        if raw_packet is None:
            return

        address = str(device.address)

        bluetooth_name = str(
            advertisement.local_name
            or device.name
            or DEFAULT_BLUETOOTH_NAME
        )

        rssi = int(advertisement.rssi)

        if self._raw_packet_logger is not None:
            try:
                # Support the logger API from the diagnostic drop without
                # making packet capture a prerequisite for acquisition.
                log_method = getattr(
                    self._raw_packet_logger,
                    "log_packet",
                    None,
                )
                if callable(log_method):
                    log_method(
                        address=address,
                        bluetooth_name=bluetooth_name,
                        rssi=rssi,
                        manufacturer_data=manufacturer_data,
                        raw_packet=raw_packet,
                    )
            except Exception:
                LOGGER.exception(
                    "Raw BLE packet logging failed"
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
