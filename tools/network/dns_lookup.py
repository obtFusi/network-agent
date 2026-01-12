"""DNS Lookup Tool - Exception to private-only policy."""

import ipaddress
import dns.resolver
import dns.reversename
from tools.base import BaseTool


class DNSLookupTool(BaseTool):
    RECORD_TYPES = ["A", "AAAA", "MX", "TXT", "PTR", "NS", "SOA", "CNAME", "SRV"]

    @property
    def name(self) -> str:
        return "dns_lookup"

    @property
    def description(self) -> str:
        return (
            "Performs DNS lookups. Supports A, AAAA, MX, TXT, PTR, NS, SOA, CNAME, SRV. "
            "Unlike scan tools, DNS lookups are allowed on any target (public or private) "
            "as they only query DNS servers, not the targets themselves."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Hostname or IP address (public or private allowed)",
                },
                "record_type": {
                    "type": "string",
                    "enum": ["auto"] + self.RECORD_TYPES,
                    "description": "DNS record type. 'auto': IP->PTR, hostname->A",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 10)",
                },
            },
            "required": ["target"],
        }

    def execute(self, target: str, record_type: str = "auto", timeout: int = 10) -> str:
        # Type-Guards (LLM can send wrong types!)
        if not isinstance(target, str):
            return f"Error: target must be string, got {type(target).__name__}"
        if not isinstance(record_type, str):
            return (
                f"Error: record_type must be string, got {type(record_type).__name__}"
            )
        # timeout bool-check (bool is int subclass!)
        if type(timeout) is not int:
            return f"Error: timeout must be integer, got {type(timeout).__name__}"
        # timeout >= 1 consistent with scan tools
        if timeout < 1:
            return f"Error: timeout must be >= 1, got {timeout}"

        target = target.strip()
        # Normalize FQDN trailing dot (example.com. -> example.com)
        target = target.rstrip(".")
        if not target:
            return "Error: No target specified"

        # Case-insensitive record types (LLMs often send lowercase)
        if record_type != "auto":
            record_type = record_type.upper()

        # Record-type guard - validate before processing
        valid_types = ["auto"] + self.RECORD_TYPES
        if record_type not in valid_types:
            return f"Error: Invalid record type '{record_type}'. Valid: {', '.join(self.RECORD_TYPES)}"

        try:
            # Auto-detect record type
            is_ip = False
            try:
                ipaddress.ip_address(target)
                is_ip = True
            except ValueError:
                pass

            if record_type == "auto":
                record_type = "PTR" if is_ip else "A"

            # PTR-Guard - hostname + PTR is invalid
            if record_type == "PTR" and not is_ip:
                return (
                    f"Error: PTR lookup requires an IP address, not hostname '{target}'. "
                    "Use 'auto' for hostname lookups."
                )

            resolver = dns.resolver.Resolver()
            resolver.timeout = timeout
            resolver.lifetime = timeout

            if record_type == "PTR":
                rev_name = dns.reversename.from_address(target)
                answers = resolver.resolve(rev_name, "PTR")
            else:
                answers = resolver.resolve(target, record_type)

            results = [str(rdata) for rdata in answers]
            return f"DNS Lookup: {target} ({record_type})\n" + "\n".join(
                f"  {r}" for r in results
            )

        except dns.resolver.NXDOMAIN:
            return f"Error: Domain not found: {target}"
        except dns.resolver.NoAnswer:
            return f"Error: No {record_type} records for {target}"
        except dns.resolver.Timeout:
            return f"Error: DNS lookup timed out after {timeout}s"
        except Exception as e:
            return f"Error: {e}"


if __name__ == "__main__":
    import sys

    tool = DNSLookupTool()
    if len(sys.argv) < 2:
        print("Usage: python -m tools.network.dns_lookup <target> [record_type]")
        sys.exit(1)
    print(
        tool.execute(
            target=sys.argv[1],
            record_type=sys.argv[2] if len(sys.argv) > 2 else "auto",
        )
    )
