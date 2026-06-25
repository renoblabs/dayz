"""Map config_type -> Parser instance. Single import surface for CLI / MCP."""

from __future__ import annotations

from .parsers.base import ConfigParser
from .parsers.cfgeventspawns_xml import CfgEventSpawnsXmlParser
from .parsers.cfgspawnabletypes_xml import CfgSpawnableTypesXmlParser
from .parsers.expansion_json import ExpansionJsonParser
from .parsers.types_xml import TypesXmlParser


PARSERS: dict[str, ConfigParser] = {
    "types_xml": TypesXmlParser(),
    "cfgspawnabletypes_xml": CfgSpawnableTypesXmlParser(),
    "cfgeventspawns_xml": CfgEventSpawnsXmlParser(),
    "expansion_json": ExpansionJsonParser(),
}


def get_parser(config_type: str) -> ConfigParser:
    if config_type not in PARSERS:
        raise KeyError(f"unknown config_type: {config_type!r}; available: {sorted(PARSERS)}")
    return PARSERS[config_type]
