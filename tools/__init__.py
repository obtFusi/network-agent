from tools.recon.ping_sweep import PingSweepTool
from tools.recon.dns_lookup import DNSLookupTool
from tools.recon.port_scanner import PortScannerTool
from tools.recon.service_detect import ServiceDetectTool
from tools.recon.llmnr_detector import LLMNRDetectorTool
from tools.recon.smb_signing_check import SMBSigningCheckTool
from tools.harvest.kerberoast import KerberoastTool
from tools.poison.llmnr_poisoner import LLMNRPoisonerTool
from tools.web.web_search import WebSearchTool


def get_all_tools():
    """Registry: All available tools."""
    return [
        # Recon (passive)
        PingSweepTool(),
        DNSLookupTool(),
        PortScannerTool(),
        ServiceDetectTool(),
        LLMNRDetectorTool(),
        SMBSigningCheckTool(),
        # Harvest (active)
        KerberoastTool(),
        # Poison (active)
        LLMNRPoisonerTool(),
        # Web (passive)
        WebSearchTool(),
    ]
