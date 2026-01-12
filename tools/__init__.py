from tools.network.ping_sweep import PingSweepTool
from tools.network.dns_lookup import DNSLookupTool
from tools.network.port_scanner import PortScannerTool
from tools.network.service_detect import ServiceDetectTool


def get_all_tools():
    """Registry: All available tools."""
    return [
        PingSweepTool(),
        DNSLookupTool(),
        PortScannerTool(),
        ServiceDetectTool(),
    ]
