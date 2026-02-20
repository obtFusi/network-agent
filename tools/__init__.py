from tools.recon.ping_sweep import PingSweepTool
from tools.recon.dns_lookup import DNSLookupTool
from tools.recon.port_scanner import PortScannerTool
from tools.recon.service_detect import ServiceDetectTool
from tools.web.web_search import WebSearchTool


def get_all_tools():
    """Registry: All available tools."""
    return [
        PingSweepTool(),
        DNSLookupTool(),
        PortScannerTool(),
        ServiceDetectTool(),
        WebSearchTool(),
    ]
