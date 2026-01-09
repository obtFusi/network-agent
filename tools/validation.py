"""
Input-Validierung für Network Agent Tools.

Guardrails auf Tool-Ebene: Validiert Input bevor Befehle ausgeführt werden.
Schützt vor Injection, zu großen Scans und ungültigen Eingaben.
"""

import ipaddress
import re
from typing import Tuple

# Standard-Limits
DEFAULT_MAX_HOSTS = 65536  # /16 Netzwerk
DANGEROUS_CHARS = re.compile(r"[;&|`$(){}\\<>\n\r]")
NMAP_OPTION_PATTERN = re.compile(r"^-")


def validate_network(
    network: str, max_hosts: int = DEFAULT_MAX_HOSTS, allow_public: bool = True
) -> Tuple[bool, str, str]:
    """
    Validiert Netzwerk-Input für Scan-Tools.

    Args:
        network: Netzwerk in CIDR-Notation (z.B. "192.168.1.0/24")
        max_hosts: Maximale Anzahl Hosts im Netzwerk
        allow_public: Ob öffentliche IPs erlaubt sind

    Returns:
        Tuple (valid, error_message, normalized_network)
        - valid: True wenn Input gültig
        - error_message: Fehlerbeschreibung (leer wenn valid)
        - normalized_network: Normalisiertes Netzwerk (z.B. "192.168.1.0/24")
    """
    # Input säubern
    network = network.strip()

    if not network:
        return False, "Kein Netzwerk angegeben", ""

    # 1. Injection-Check: Keine gefährlichen Shell-Zeichen
    if DANGEROUS_CHARS.search(network):
        return False, "Ungültige Zeichen im Input (mögliche Injection)", ""

    # 2. Keine nmap-Optionen (beginnt mit -)
    if NMAP_OPTION_PATTERN.match(network):
        return False, "Input darf nicht mit '-' beginnen (keine nmap-Optionen)", ""

    # 3. Keine Leerzeichen (könnten zusätzliche Argumente sein)
    if " " in network or "\t" in network:
        return False, "Input darf keine Leerzeichen enthalten", ""

    # 4. CIDR-Parsing mit Python's ipaddress Modul
    try:
        # strict=False erlaubt "192.168.1.1/24" -> normalisiert zu "192.168.1.0/24"
        net = ipaddress.ip_network(network, strict=False)
    except ValueError as e:
        return False, f"Ungültiges Netzwerk-Format: {e}", ""

    # 5. Host-Limit prüfen
    num_hosts = net.num_addresses
    if num_hosts > max_hosts:
        return (
            False,
            f"Netzwerk zu groß: {num_hosts:,} Hosts (Maximum: {max_hosts:,}). "
            f"Verwende ein kleineres Subnetz, z.B. /{net.prefixlen + 4}",
            "",
        )

    # 6. Private IP Check (optional)
    if not allow_public and not net.is_private:
        return (
            False,
            f"Nur private Netzwerke erlaubt. {net} ist ein öffentliches Netzwerk.",
            "",
        )

    # 7. Spezielle Netzwerke warnen/blocken
    if net.is_loopback:
        # Loopback erlauben, aber normalisieren
        pass
    elif net.is_multicast:
        return False, "Multicast-Netzwerke können nicht gescannt werden", ""
    elif net.is_reserved:
        return False, "Reservierte Netzwerke können nicht gescannt werden", ""

    # Alles OK - normalisiertes Netzwerk zurückgeben
    normalized = str(net)
    return True, "", normalized


def validate_port_list(ports: str) -> Tuple[bool, str, str]:
    """
    Validiert eine Port-Liste für Scan-Tools.

    Args:
        ports: Komma-separierte Ports oder Ranges (z.B. "22,80,443" oder "1-1024")

    Returns:
        Tuple (valid, error_message, normalized_ports)
    """
    ports = ports.strip()

    if not ports:
        return False, "Keine Ports angegeben", ""

    # Injection-Check
    if DANGEROUS_CHARS.search(ports):
        return False, "Ungültige Zeichen in Port-Liste", ""

    # Nur erlaubte Zeichen: Ziffern, Komma, Bindestrich
    if not re.match(r"^[\d,\-]+$", ports):
        return (
            False,
            "Port-Liste darf nur Ziffern, Kommas und Bindestriche enthalten",
            "",
        )

    # Einzelne Ports/Ranges validieren
    for part in ports.split(","):
        part = part.strip()
        if "-" in part:
            # Range: "1-1024"
            try:
                start, end = part.split("-")
                start, end = int(start), int(end)
                if not (1 <= start <= 65535 and 1 <= end <= 65535):
                    return (
                        False,
                        f"Port außerhalb des gültigen Bereichs (1-65535): {part}",
                        "",
                    )
                if start > end:
                    return False, f"Ungültige Port-Range: {part}", ""
            except ValueError:
                return False, f"Ungültige Port-Range: {part}", ""
        else:
            # Einzelner Port
            try:
                port = int(part)
                if not 1 <= port <= 65535:
                    return (
                        False,
                        f"Port außerhalb des gültigen Bereichs (1-65535): {port}",
                        "",
                    )
            except ValueError:
                return False, f"Ungültiger Port: {part}", ""

    return True, "", ports


def sanitize_hostname(hostname: str) -> Tuple[bool, str, str]:
    """
    Validiert einen Hostnamen.

    Args:
        hostname: Hostname oder IP-Adresse

    Returns:
        Tuple (valid, error_message, sanitized_hostname)
    """
    hostname = hostname.strip()

    if not hostname:
        return False, "Kein Hostname angegeben", ""

    # Injection-Check
    if DANGEROUS_CHARS.search(hostname):
        return False, "Ungültige Zeichen im Hostname", ""

    # Keine Leerzeichen
    if " " in hostname or "\t" in hostname:
        return False, "Hostname darf keine Leerzeichen enthalten", ""

    # Versuche als IP zu parsen
    try:
        ip = ipaddress.ip_address(hostname)
        return True, "", str(ip)
    except ValueError:
        pass

    # Hostname-Validierung (RFC 1123)
    if len(hostname) > 253:
        return False, "Hostname zu lang (max 253 Zeichen)", ""

    # Erlaubte Zeichen: a-z, 0-9, Bindestrich, Punkt
    if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$", hostname):
        return False, "Ungültiger Hostname", ""

    return True, "", hostname.lower()
