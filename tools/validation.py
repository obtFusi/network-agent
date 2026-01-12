"""
Input validation for Network Agent Tools.

Guardrails at tool level: Validates input before commands are executed.
Protects against injection, oversized scans, and invalid inputs.
"""

import ipaddress
import re
import shutil
import socket
from typing import List, Tuple

# Standard limits
DEFAULT_MAX_HOSTS_DISCOVERY = 65536  # /16 for ping_sweep
DEFAULT_MAX_HOSTS_PORTSCAN = 256  # /24 for port_scan/service_detect
MAX_PORTS = 1000

DANGEROUS_CHARS = re.compile(r"[;&|`$(){}\\<>\n\r]")
NMAP_OPTION_PATTERN = re.compile(r"^-")

# v5.2: Reserved/special ranges that should not be scanned
BLOCKED_NETWORKS = [
    ipaddress.ip_network("169.254.0.0/16"),  # Link-Local
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT (Carrier-Grade NAT)
]


def require_nmap() -> Tuple[bool, str]:
    """v5.4: Centralized nmap availability check. Call BEFORE any nmap-dependent logic."""
    if not shutil.which("nmap"):
        return False, "Error: nmap not found. Please install nmap."
    return True, ""


def _is_blocked_ip(ip: ipaddress.IPv4Address) -> Tuple[bool, str]:
    """v5.2: Check if IP is in blocked ranges (Link-Local, CGNAT)."""
    for net in BLOCKED_NETWORKS:
        if ip in net:
            if net == ipaddress.ip_network("169.254.0.0/16"):
                return True, "Link-Local addresses (169.254.x.x) cannot be scanned"
            if net == ipaddress.ip_network("100.64.0.0/10"):
                return True, "CGNAT addresses (100.64.x.x) cannot be scanned"
    return False, ""


def _is_blocked_network(net: ipaddress.IPv4Network) -> Tuple[bool, str]:
    """v5.3: Check if CIDR overlaps with blocked ranges (Link-Local, CGNAT)."""
    for blocked in BLOCKED_NETWORKS:
        if net.overlaps(blocked):
            if blocked == ipaddress.ip_network("169.254.0.0/16"):
                return True, "Network overlaps with Link-Local range (169.254.0.0/16)"
            if blocked == ipaddress.ip_network("100.64.0.0/10"):
                return True, "Network overlaps with CGNAT range (100.64.0.0/10)"
    return False, ""


def _is_excluded_ip(ip: ipaddress.IPv4Address, exclude_list: List[str]) -> bool:
    """Checks if IP is in exclude list (single IPs or networks)."""
    for excluded in exclude_list:
        try:
            net = ipaddress.ip_network(excluded, strict=False)
            if ip in net:
                return True
        except ValueError:
            try:
                if ip == ipaddress.ip_address(excluded):
                    return True
            except ValueError:
                pass
    return False


def _is_excluded_network(net: ipaddress.IPv4Network, exclude_list: List[str]) -> bool:
    """Checks if network overlaps with exclude list."""
    for excluded in exclude_list:
        try:
            excluded_net = ipaddress.ip_network(excluded, strict=False)
            if net.overlaps(excluded_net):
                return True
        except ValueError:
            try:
                if ipaddress.ip_address(excluded) in net:
                    return True
            except ValueError:
                pass
    return False


def resolve_and_validate(
    target: str,
    allow_public: bool = False,
    exclude_list: List[str] = None,
    max_hosts: int = DEFAULT_MAX_HOSTS_PORTSCAN,
) -> Tuple[bool, str, List[str]]:
    """
    Resolves hostname and validates ALL resulting IPs.
    Returns: (valid, error, list_of_ips_or_cidr)

    Note: IPv6 is explicitly blocked. Only IPv4 targets are allowed.
    Allowed hostname chars: RFC-1123 (a-z, 0-9, hyphen, dot).
    """
    # v5.7: Input type guard for direct function usage
    if not isinstance(target, str):
        return (
            False,
            f"Validation error: target must be string, got {type(target).__name__}",
            [],
        )

    target = target.strip()
    # v5.3: Normalize FQDN trailing dot (example.com. -> example.com)
    target = target.rstrip(".")
    exclude_list = exclude_list or []

    if not target:
        return False, "Validation error: No target specified", []

    # v5.4: Whitespace-Check EARLY - blocks "192.168.1.1  --foo" injection
    if " " in target or "\t" in target:
        return False, "Validation error: target must not contain whitespace", []

    if DANGEROUS_CHARS.search(target):
        return False, "Validation error: Invalid characters in target", []

    # Try as single IP FIRST (more common case)
    try:
        ip = ipaddress.ip_address(target)
        # Block IPv6 explicitly
        if ip.version == 6:
            return False, "Validation error: IPv6 not supported, use IPv4", []
        # v5.2: Block Link-Local and CGNAT
        blocked, reason = _is_blocked_ip(ip)
        if blocked:
            return False, f"Validation error: {reason}", []
        if not allow_public and not ip.is_private and not ip.is_loopback:
            return False, f"Validation error: Public IP not allowed: {target}", []
        if _is_excluded_ip(ip, exclude_list):
            return False, f"Validation error: Target is excluded: {target}", []
        return True, "", [str(ip)]
    except ValueError:
        pass

    # Try as CIDR
    try:
        net = ipaddress.ip_network(target, strict=False)
        # Block IPv6 explicitly
        if net.version == 6:
            return False, "Validation error: IPv6 not supported, use IPv4", []
        if net.is_multicast:
            return False, "Validation error: Multicast networks cannot be scanned", []
        # v5.3: Check blocked networks BEFORE size/public checks
        blocked, reason = _is_blocked_network(net)
        if blocked:
            return False, f"Validation error: {reason}", []
        if net.num_addresses > max_hosts:
            return (
                False,
                f"Validation error: Network too large: {net.num_addresses} hosts (max: {max_hosts})",
                [],
            )
        if not allow_public and not net.is_private and not net.is_loopback:
            return False, f"Validation error: Public network not allowed: {target}", []
        if _is_excluded_network(net, exclude_list):
            return False, "Validation error: Target overlaps with excluded network", []
        return True, "", [str(net)]
    except ValueError:
        pass

    # Hostname: Resolve and validate ALL IPs
    if len(target) > 253:
        return False, "Validation error: Hostname too long", []
    if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$", target):
        return False, "Validation error: Invalid hostname format", []

    try:
        # Use getaddrinfo for proper resolution, filter to IPv4 only
        addrinfo = socket.getaddrinfo(
            target, None, socket.AF_INET
        )  # AF_INET = IPv4 only
    except socket.gaierror:
        addrinfo = []  # Fall through to AAAA-only check

    if not addrinfo:
        # v5.3: Check if hostname has ONLY IPv6 addresses (AAAA-only)
        try:
            addrinfo_v6 = socket.getaddrinfo(target, None, socket.AF_INET6)
            if addrinfo_v6:
                return (
                    False,
                    f"Validation error: Hostname {target} has only IPv6 addresses (AAAA records). IPv6 not supported.",
                    [],
                )
        except socket.gaierror:
            pass
        return False, f"Validation error: Could not resolve hostname: {target}", []

    # v5.2: Extract unique IPs with order-preserving dedup (not sorted)
    ips = list(dict.fromkeys(info[4][0] for info in addrinfo))

    # Check max_hosts limit for hostnames (v5.1 fix)
    if len(ips) > max_hosts:
        return (
            False,
            f"Validation error: Hostname resolves to too many IPs: {len(ips)} (max: {max_hosts})",
            [],
        )

    for ip_str in ips:
        ip = ipaddress.ip_address(ip_str)
        # v5.2: Block Link-Local and CGNAT for hostnames too
        blocked, reason = _is_blocked_ip(ip)
        if blocked:
            return (
                False,
                f"Validation error: Hostname {target} resolves to blocked IP {ip_str} ({reason})",
                [],
            )
        if not allow_public and not ip.is_private and not ip.is_loopback:
            return (
                False,
                f"Validation error: Hostname {target} resolves to public IP {ip_str}",
                [],
            )
        if _is_excluded_ip(ip, exclude_list):
            return (
                False,
                f"Validation error: Hostname {target} resolves to excluded IP {ip_str}",
                [],
            )

    return True, "", ips


def count_ports(ports: str) -> int:
    """Counts ports in port string. Note: Duplicates counted separately (documented)."""
    count = 0
    for part in ports.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                count += end - start + 1
            except ValueError:
                count += 1  # Will be caught in validation
        else:
            count += 1
    return count


def validate_port_list(ports: str) -> Tuple[bool, str, str]:
    """
    Validates a port list for scan tools.

    Args:
        ports: Comma-separated ports or ranges (e.g., "22,80,443" or "1-1024")

    Returns:
        Tuple (valid, error_message, normalized_ports)
    """
    # v5.7: Input type guard for direct function usage
    if not isinstance(ports, str):
        return (
            False,
            f"Validation error: ports must be string, got {type(ports).__name__}",
            "",
        )

    # v5.1: Normalize whitespace - remove all spaces/tabs
    ports = ports.strip().replace(" ", "").replace("\t", "")

    if not ports:
        return False, "Validation error: Empty port string not allowed", ""

    # Injection-Check
    if DANGEROUS_CHARS.search(ports):
        return False, "Validation error: Invalid characters in port list", ""

    # Only allowed chars: digits, comma, hyphen (v5.1: NO whitespace in regex!)
    if not re.match(r"^[\d,\-]+$", ports):
        return (
            False,
            "Validation error: Port list may only contain digits, commas, and hyphens",
            "",
        )

    # Validate individual ports/ranges
    for part in ports.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            # Range: "1-1024"
            try:
                parts = part.split("-")
                if len(parts) != 2:
                    return False, f"Validation error: Invalid port range: {part}", ""
                start, end = int(parts[0]), int(parts[1])
                if not (1 <= start <= 65535 and 1 <= end <= 65535):
                    return (
                        False,
                        f"Validation error: Port outside valid range (1-65535): {part}",
                        "",
                    )
                if start > end:
                    return False, f"Validation error: Invalid port range: {part}", ""
            except ValueError:
                return False, f"Validation error: Invalid port range: {part}", ""
        else:
            # Single port
            try:
                port = int(part)
                if not 1 <= port <= 65535:
                    return (
                        False,
                        f"Validation error: Port outside valid range (1-65535): {port}",
                        "",
                    )
            except ValueError:
                return False, f"Validation error: Invalid port: {part}", ""

    # Port count limit (v5.1)
    port_count = count_ports(ports)
    if port_count > MAX_PORTS:
        return (
            False,
            f"Validation error: Too many ports: {port_count} (max: {MAX_PORTS})",
            "",
        )

    return True, "", ports


def validate_network(
    network: str,
    max_hosts: int = DEFAULT_MAX_HOSTS_DISCOVERY,
    allow_public: bool = True,
) -> Tuple[bool, str, str]:
    """
    Validates network input for scan tools.
    DEPRECATED: Use resolve_and_validate() instead for hostname support.

    Args:
        network: Network in CIDR notation (e.g., "192.168.1.0/24")
        max_hosts: Maximum number of hosts in network
        allow_public: Whether public IPs are allowed

    Returns:
        Tuple (valid, error_message, normalized_network)
    """
    # Clean input
    network = network.strip()

    if not network:
        return False, "No network specified", ""

    # 1. Injection-Check: No dangerous shell characters
    if DANGEROUS_CHARS.search(network):
        return False, "Invalid characters in input (possible injection)", ""

    # 2. No nmap options (starts with -)
    if NMAP_OPTION_PATTERN.match(network):
        return False, "Input must not start with '-' (no nmap options)", ""

    # 3. No whitespace (could be additional arguments)
    if " " in network or "\t" in network:
        return False, "Input must not contain whitespace", ""

    # 4. CIDR parsing with Python's ipaddress module
    try:
        # strict=False allows "192.168.1.1/24" -> normalizes to "192.168.1.0/24"
        net = ipaddress.ip_network(network, strict=False)
    except ValueError as e:
        return False, f"Invalid network format: {e}", ""

    # 5. Host limit check
    num_hosts = net.num_addresses
    if num_hosts > max_hosts:
        return (
            False,
            f"Network too large: {num_hosts:,} hosts (maximum: {max_hosts:,}). "
            f"Use a smaller subnet, e.g., /{net.prefixlen + 4}",
            "",
        )

    # 6. Private IP check (optional)
    if not allow_public and not net.is_private:
        return (
            False,
            f"Only private networks allowed. {net} is a public network.",
            "",
        )

    # 7. Warn/block special networks
    if net.is_loopback:
        # Allow loopback, but normalize
        pass
    elif net.is_multicast:
        return False, "Multicast networks cannot be scanned", ""
    elif net.is_reserved:
        return False, "Reserved networks cannot be scanned", ""

    # All OK - return normalized network
    normalized = str(net)
    return True, "", normalized


def sanitize_hostname(hostname: str) -> Tuple[bool, str, str]:
    """
    Validates a hostname.
    DEPRECATED: Use resolve_and_validate() instead.

    Args:
        hostname: Hostname or IP address

    Returns:
        Tuple (valid, error_message, sanitized_hostname)
    """
    hostname = hostname.strip()

    if not hostname:
        return False, "No hostname specified", ""

    # Injection-Check
    if DANGEROUS_CHARS.search(hostname):
        return False, "Invalid characters in hostname", ""

    # No whitespace
    if " " in hostname or "\t" in hostname:
        return False, "Hostname must not contain whitespace", ""

    # Try parsing as IP
    try:
        ip = ipaddress.ip_address(hostname)
        return True, "", str(ip)
    except ValueError:
        pass

    # Hostname validation (RFC 1123)
    if len(hostname) > 253:
        return False, "Hostname too long (max 253 characters)", ""

    # Allowed characters: a-z, 0-9, hyphen, dot
    if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$", hostname):
        return False, "Invalid hostname", ""

    return True, "", hostname.lower()
