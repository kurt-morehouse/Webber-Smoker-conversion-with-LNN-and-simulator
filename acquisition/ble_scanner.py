import logging

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from home_assistant_bluetooth import BluetoothServiceInfo

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
    ) -> None:

        self._config = config
        self._probe_service = probe_service

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
