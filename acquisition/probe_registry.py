import logging

from acquisition.config import ProbeDefinition


LOGGER = logging.getLogger(__name__)

UNKNOWN_PROBE_PREFIX: str = "Unknown Probe"


class ProbeRegistry:
    def __init__(
        self,
        definitions: tuple[ProbeDefinition, ...],
    ) -> None:
        self._definitions = definitions
        self._reported_unknown_addresses: set[str] = set()

    def friendly_name_for(self, address: str) -> str:
        normalized_address = address.upper()

        for definition in self._definitions:
            fragment = definition.match_fragment.upper()

            if fragment in normalized_address:
                return definition.friendly_name

        if address not in self._reported_unknown_addresses:
            LOGGER.warning(
                "Unknown Chef iQ probe discovered: %s",
                address,
            )
            self._reported_unknown_addresses.add(address)

        return f"{UNKNOWN_PROBE_PREFIX} {address[-8:]}"
