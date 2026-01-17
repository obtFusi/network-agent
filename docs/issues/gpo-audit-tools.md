# GPO Audit Tools - GitHub Issue Definitionen

> Vollständige Issue-Beschreibungen für alle GPO-Audit Tools im Network-Agent Projekt.
> Jedes Issue ist implementierungsbereit mit Requirements, Architektur, und Verification.

---

## Übersicht: Tool-Kategorien

| Kategorie | Tools | Priorität |
|-----------|-------|-----------|
| **Enumeration** | gpo_enum, ldap_gpo_query | P1 (Basis) |
| **Verification** | smb_signing_check, llmnr_detector, wdigest_check, credential_guard_check, laps_auditor | P1 (Kernfunktion) |
| **Misconfiguration** | gpo_link_analyzer, gpo_scope_validator, gpo_filter_checker | P2 (Erweitert) |
| **Compliance** | password_policy_auditor, firewall_auditor, bitlocker_auditor | P2 (Compliance) |

---

# ENUMERATION TOOLS

---

## Issue #1: GPO Enumeration via LDAP

### Metadata
```
Title: [Feature] GPO Enumeration via LDAP (gpo_enum)
Labels: type:feature, priority:high, status:backlog, component:tools, attack-phase:reconnaissance
Milestone: v0.8.0 - AD Audit Capabilities
Assignee: -
Estimate: 3-5 days
```

### Beschreibung

**Was ist das Tool?**
Ein LDAP-basiertes Tool zur Enumeration aller Group Policy Objects (GPOs) in einer Active Directory Domain. Funktioniert remote von Linux/macOS ohne Windows-Installation.

**Warum brauchen wir das?**
- GPO-Enumeration ist der erste Schritt bei AD-Assessments
- Zeigt die "Soll-Konfiguration" aus Admin-Sicht
- Identifiziert Security-relevante GPOs (Password Policy, Firewall, etc.)
- Basis für alle weiteren GPO-Checks (Verlinkung, Wirksamkeit)

**Was kann es?**
- Alle GPO-Objekte aus AD auslesen
- GPO-Namen, GUIDs, Erstellungsdatum, Änderungsdatum
- Verlinkungen zu OUs/Sites/Domain anzeigen
- SYSVOL-Pfade für tiefere Analyse
- WMI-Filter Zuordnungen
- Security Filtering (wer kann die GPO lesen/anwenden)

### Requirements

#### Credentials
| Level | Funktionsumfang |
|-------|-----------------|
| **Domain User** (Minimum) | Alle GPO-Objekte lesen, Verlinkungen, WMI-Filter |
| **Kein Account** | Nicht möglich (LDAP erfordert Authentifizierung) |

#### Software-Abhängigkeiten
```
ldap3>=2.9.1          # LDAP Client Library
python-dateutil       # Timestamp Parsing
```

#### Netzwerk-Anforderungen
| Port | Protokoll | Zweck | Fallback |
|------|-----------|-------|----------|
| 389 | LDAP | Standard AD Query | - |
| 636 | LDAPS | Verschlüsselt (bevorzugt) | Port 389 |
| 3268 | GC | Global Catalog (Multi-Domain) | Port 389 |

#### Firewall-Regeln
```
Attacker → Domain Controller: TCP 389, 636, 3268
```

### Architektur

#### Dateistruktur
```
tools/
└── audit/
    └── gpo/
        ├── __init__.py
        ├── gpo_enum.py          # Hauptmodul
        ├── ldap_client.py       # LDAP Connection Handling
        └── models.py            # GPO Dataclasses
```

#### Klassendesign
```python
# tools/audit/gpo/gpo_enum.py

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class GPOLink:
    """Eine GPO-Verlinkung zu einer OU/Site/Domain"""
    target_dn: str              # CN=Computers,DC=corp,DC=local
    target_type: str            # OU | Site | Domain
    link_enabled: bool
    enforced: bool              # "No Override" Flag
    link_order: int             # Reihenfolge bei mehreren GPOs

@dataclass
class GPOObject:
    """Vollständiges GPO-Objekt"""
    name: str                   # "Disable LLMNR"
    guid: str                   # {12345678-1234-...}
    dn: str                     # CN={GUID},CN=Policies,CN=System,DC=...
    created: datetime
    modified: datetime
    version_user: int           # User-Teil Version
    version_computer: int       # Computer-Teil Version
    sysvol_path: str            # \\domain\SYSVOL\...\{GUID}
    wmi_filter: Optional[str]   # Verknüpfter WMI Filter
    links: List[GPOLink]        # Alle Verlinkungen
    flags: int                  # 0=enabled, 1=user disabled, 2=computer disabled, 3=all disabled

class GPOEnumerator:
    """
    Enumeriert GPOs via LDAP aus Active Directory.

    Requires: Domain User credentials
    """

    def __init__(self,
                 dc_ip: str,
                 domain: str,
                 username: str,
                 password: str,
                 use_ssl: bool = True):
        """
        Args:
            dc_ip: IP des Domain Controllers
            domain: FQDN der Domain (corp.local)
            username: Domain User (user oder user@domain oder DOMAIN\\user)
            password: Passwort
            use_ssl: LDAPS verwenden (Port 636)
        """
        self.dc_ip = dc_ip
        self.domain = domain
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self._conn = None

    def connect(self) -> bool:
        """Stellt LDAP-Verbindung her"""
        pass

    def enumerate_all(self) -> List[GPOObject]:
        """
        Enumeriert alle GPOs in der Domain.

        Returns:
            Liste aller GPO-Objekte mit Verlinkungen
        """
        pass

    def get_gpo_by_name(self, name: str) -> Optional[GPOObject]:
        """Sucht GPO nach Name (case-insensitive)"""
        pass

    def get_gpo_by_guid(self, guid: str) -> Optional[GPOObject]:
        """Sucht GPO nach GUID"""
        pass

    def get_unlinked_gpos(self) -> List[GPOObject]:
        """
        Findet GPOs die erstellt aber nicht verlinkt wurden.

        Security Finding: Oft "vergessene" Security-GPOs
        """
        pass

    def get_disabled_gpos(self) -> List[GPOObject]:
        """Findet deaktivierte GPOs"""
        pass

    def get_gpos_for_ou(self, ou_dn: str) -> List[GPOObject]:
        """Alle GPOs die auf eine bestimmte OU wirken"""
        pass

    def export_to_json(self, gpos: List[GPOObject], path: str) -> None:
        """Exportiert Ergebnisse als JSON für Reports"""
        pass
```

#### LDAP Queries
```python
# Base DN für GPO Container
GPO_CONTAINER = "CN=Policies,CN=System,{domain_dn}"

# Alle GPOs auflisten
QUERY_ALL_GPOS = "(objectClass=groupPolicyContainer)"

# GPO Attribute die wir brauchen
GPO_ATTRIBUTES = [
    "displayName",           # Human-readable Name
    "name",                  # GUID ohne Klammern
    "gPCFileSysPath",        # SYSVOL Pfad
    "gPCFunctionalityVersion",
    "versionNumber",         # User + Computer Version kombiniert
    "flags",                 # Enabled/Disabled Status
    "whenCreated",
    "whenChanged",
    "gPCWQLFilter",          # WMI Filter Referenz
]

# GPO Links finden (in OUs gespeichert, nicht in GPO selbst!)
QUERY_GPO_LINKS = "(gPLink=*)"
LINK_ATTRIBUTES = ["distinguishedName", "gPLink", "gPOptions"]
```

### Implementation Steps

```markdown
1. [ ] LDAP Client Wrapper erstellen (ldap_client.py)
   - Connection mit Kerberos/NTLM
   - SSL/TLS Support
   - Reconnect bei Timeout
   - Paged Results für große ADs

2. [ ] GPO Dataclasses definieren (models.py)
   - GPOObject, GPOLink, WMIFilter
   - JSON Serialization
   - __str__ für CLI Output

3. [ ] Core Enumeration implementieren (gpo_enum.py)
   - enumerate_all()
   - LDAP Query für GPO Container
   - Parsing der Attribute

4. [ ] Link Resolution implementieren
   - Alle OUs mit gPLink Attribut finden
   - gPLink String parsen ([LDAP://...;0])
   - Link zu GPO-Objekt zuordnen

5. [ ] Analyse-Funktionen
   - get_unlinked_gpos()
   - get_disabled_gpos()
   - get_gpos_for_ou()

6. [ ] CLI Integration
   - Neuer Command: gpo enum
   - Output Formatierung (Table, JSON)
   - Filter-Optionen

7. [ ] Agent Integration
   - Tool-Definition für LLM
   - Natural Language Queries
```

### Verification / Acceptance Criteria

#### Unit Tests
```python
# tests/tools/audit/gpo/test_gpo_enum.py

def test_parse_gpo_link_string():
    """gPLink Attribut korrekt parsen"""
    link_str = "[LDAP://CN={guid},CN=Policies,...;0][LDAP://...;2]"
    links = parse_gpo_links(link_str)
    assert len(links) == 2
    assert links[0].enforced == False  # ;0
    assert links[1].enforced == True   # ;2

def test_gpo_version_parsing():
    """Version Number in User/Computer Teil splitten"""
    # versionNumber ist 32-bit: High 16 = User, Low 16 = Computer
    version = 0x00050003  # User=5, Computer=3
    user, computer = parse_version(version)
    assert user == 5
    assert computer == 3

def test_disabled_flags():
    """GPO Disabled Flags korrekt interpretieren"""
    assert is_user_disabled(1) == True
    assert is_computer_disabled(2) == True
    assert is_fully_disabled(3) == True
```

#### Integration Tests (gegen Test-AD)
```python
@pytest.mark.integration
def test_enumerate_against_goad():
    """Test gegen GOAD Lab"""
    enum = GPOEnumerator(
        dc_ip="192.168.56.10",
        domain="north.sevenkingdoms.local",
        username="samwell.tarly",
        password="Heartsbane"
    )
    enum.connect()
    gpos = enum.enumerate_all()

    # GOAD hat vordefinierte GPOs
    assert len(gpos) >= 5
    assert any(g.name == "Default Domain Policy" for g in gpos)

@pytest.mark.integration
def test_find_unlinked_gpos():
    """Unverlinkte GPOs in GOAD finden"""
    # GOAD hat absichtlich unverlinkte GPOs
    unlinked = enum.get_unlinked_gpos()
    assert len(unlinked) >= 1
```

#### Manual Verification
```bash
# 1. Tool ausführen
docker run --rm network-agent:test \
    python cli.py gpo enum \
    --dc 192.168.56.10 \
    --domain north.sevenkingdoms.local \
    --user samwell.tarly \
    --password Heartsbane

# 2. Erwarteter Output:
# GPO Enumeration Results
# =======================
# Found 12 GPOs in north.sevenkingdoms.local
#
# Name                          GUID                                    Links  Status
# ─────────────────────────────────────────────────────────────────────────────────────
# Default Domain Policy         {31B2F340-...}                          1      Enabled
# Disable LLMNR                 {A1B2C3D4-...}                          0      ⚠ NOT LINKED
# ...

# 3. Vergleich mit Windows (auf DC):
Get-GPO -All | Select DisplayName, Id, GpoStatus
# Output muss identisch sein
```

### Dependencies
- Issue #X: LDAP Client Base Library (falls noch nicht vorhanden)
- Issue #Y: Credential Management für AD Accounts

### Risks / Considerations

| Risiko | Mitigation |
|--------|------------|
| Große ADs mit 1000+ GPOs | Paged Results, Timeout erhöhen |
| LDAP Signing Required | Signing in ldap3 aktivieren |
| Kerberos-only Umgebung | Kerberos Auth implementieren (später) |
| Nested OUs (10+ Level) | Rekursive Link-Resolution |

### Definition of Done
- [ ] Alle Unit Tests grün
- [ ] Integration Test gegen GOAD erfolgreich
- [ ] CLI Command funktioniert
- [ ] Agent kann "Liste alle GPOs auf" ausführen
- [ ] JSON Export für Reports
- [ ] README/CHANGELOG aktualisiert

---

## Issue #2: SYSVOL GPO Content Parser

### Metadata
```
Title: [Feature] SYSVOL GPO Content Parser (sysvol_parser)
Labels: type:feature, priority:high, status:backlog, component:tools
Milestone: v0.8.0 - AD Audit Capabilities
Estimate: 2-3 days
```

### Beschreibung

**Was ist das Tool?**
Parsed den Inhalt von GPOs aus dem SYSVOL Share. GPO-Objekte im AD enthalten nur Metadaten - die eigentlichen Einstellungen liegen als Dateien in SYSVOL.

**Warum brauchen wir das?**
- GPO-Einstellungen auslesen (Registry, Scripts, Preferences)
- Credentials in GPP (Group Policy Preferences) finden - klassischer Pentest-Fund!
- Scheduled Tasks und Login Scripts analysieren
- Software Installation Pakete identifizieren

**Was kann es?**
- SYSVOL via SMB mounten/lesen
- Registry.pol Dateien parsen
- GPP XML Dateien parsen (inkl. cpassword Decryption!)
- Scripts extrahieren (Logon, Logoff, Startup, Shutdown)
- Scheduled Tasks auslesen

### Requirements

#### Credentials
| Level | Funktionsumfang |
|-------|-----------------|
| **Domain User** | Voller Lesezugriff auf SYSVOL |
| **Kein Account** | Nur bei Anonymous SYSVOL (selten, Fehlkonfiguration) |

#### Software-Abhängigkeiten
```
impacket>=0.11.0      # SMB Client
pycryptodome>=3.19    # AES für cpassword Decryption
```

#### Netzwerk-Anforderungen
| Port | Protokoll | Zweck |
|------|-----------|-------|
| 445 | SMB | SYSVOL Share Zugriff |

### Architektur

```python
# tools/audit/gpo/sysvol_parser.py

@dataclass
class GPPCredential:
    """Gefundene Credentials in Group Policy Preferences"""
    username: str
    cpassword: str          # Verschlüsselter Wert
    password: str           # Entschlüsselt!
    source_file: str        # Wo gefunden
    gpo_name: str

@dataclass
class GPOScript:
    """Script aus GPO"""
    script_type: str        # Logon, Logoff, Startup, Shutdown
    script_path: str
    script_content: str     # Wenn lesbar
    parameters: str

class SYSVOLParser:
    """
    Parsed GPO-Inhalte aus SYSVOL Share.

    Requires: Domain User + SMB Port 445
    """

    def __init__(self, dc_ip: str, domain: str, username: str, password: str):
        pass

    def parse_gpo(self, gpo_guid: str) -> dict:
        """
        Parsed alle Inhalte einer GPO.

        Returns:
            {
                "registry_settings": [...],
                "scripts": [...],
                "preferences": [...],
                "credentials": [...],  # CRITICAL FINDINGS!
                "scheduled_tasks": [...]
            }
        """
        pass

    def find_gpp_credentials(self) -> List[GPPCredential]:
        """
        Sucht in ALLEN GPOs nach cpassword Feldern.

        MS14-025 - GPP Credentials sind mit bekanntem Key verschlüsselt!
        AES Key ist öffentlich dokumentiert.

        Returns:
            Liste aller gefundenen (und entschlüsselten) Credentials
        """
        pass

    def decrypt_cpassword(self, cpassword: str) -> str:
        """
        Entschlüsselt GPP cpassword.

        Der AES-256 Key ist von Microsoft veröffentlicht:
        4e9906e8fcb66cc9faf49310620ffee8f496e806cc057990209b09a433b66c1b
        """
        pass

    def extract_scripts(self, gpo_guid: str) -> List[GPOScript]:
        """Extrahiert alle Scripts aus einer GPO"""
        pass
```

### Security Finding: GPP Credentials

```python
# KRITISCHER FUND - Automatisch als HIGH severity melden!

# Der AES Key für cpassword ist öffentlich bekannt (MS14-025):
GPP_AES_KEY = bytes.fromhex(
    "4e9906e8fcb66cc9faf49310620ffee8f496e806cc057990209b09a433b66c1b"
)

def decrypt_cpassword(cpassword: str) -> str:
    """
    Entschlüsselt Group Policy Preferences cpassword.

    Hintergrund:
    - Vor MS14-025 (2014) konnten Admins Passwörter in GPPs speichern
    - Diese wurden mit AES verschlüsselt, aber der Key ist bekannt
    - Jeder Domain User kann SYSVOL lesen
    - → Jeder Domain User kann diese Passwörter entschlüsseln

    Auch nach dem Patch liegen alte GPPs oft noch im SYSVOL!
    """
    from Crypto.Cipher import AES
    import base64

    cpassword += "=" * (4 - len(cpassword) % 4)  # Padding
    encrypted = base64.b64decode(cpassword)

    cipher = AES.new(GPP_AES_KEY, AES.MODE_CBC, iv=b'\x00'*16)
    decrypted = cipher.decrypt(encrypted)

    # PKCS7 Padding entfernen
    return decrypted[:-decrypted[-1]].decode('utf-16-le')
```

### Verification

```bash
# Test gegen GOAD (hat absichtlich GPP Credentials)
python cli.py gpo credentials \
    --dc 192.168.56.10 \
    --domain north.sevenkingdoms.local \
    --user samwell.tarly \
    --password Heartsbane

# Erwarteter Output:
# ⚠️  CRITICAL: GPP Credentials Found!
# ════════════════════════════════════
#
# GPO: "Local Admin Password"
# File: \\...\Groups\Groups.xml
# Username: .\Administrator
# Password: SuperSecretPassword123!
#
# RECOMMENDATION: Delete GPP files containing cpassword immediately!
```

### Definition of Done
- [ ] SYSVOL via SMB lesbar
- [ ] Registry.pol Parser funktioniert
- [ ] GPP cpassword Decryption funktioniert
- [ ] Scripts werden extrahiert
- [ ] Integration mit gpo_enum (GUID → Inhalte)

---

# VERIFICATION TOOLS

---

## Issue #3: SMB Signing Checker

### Metadata
```
Title: [Feature] SMB Signing Security Checker (smb_signing_check)
Labels: type:feature, priority:critical, status:backlog, component:tools, attack-phase:enumeration
Milestone: v0.8.0 - AD Audit Capabilities
Estimate: 1-2 days
```

### Beschreibung

**Was ist das Tool?**
Prüft ob SMB Signing auf Zielsystemen aktiviert und erzwungen ist. Ohne SMB Signing sind SMB Relay Angriffe möglich.

**Warum brauchen wir das?**
- SMB Relay ist einer der effektivsten AD-Angriffe
- GPO kann "SMB Signing Required" konfigurieren - aber wirkt es?
- Viele Legacy-Systeme haben SMB Signing deaktiviert
- Unterschied zwischen "Enabled" und "Required" ist kritisch

**Security Impact:**
- SMB Signing Disabled/Not Required → SMB Relay möglich → Domain Admin in Minuten
- Besonders kritisch auf Domain Controllern

### Requirements

#### Credentials
| Level | Funktionsumfang |
|-------|-----------------|
| **Keine Credentials!** | Voller Funktionsumfang |

Das ist der Vorteil: Wir brauchen KEINE Credentials um SMB Signing zu prüfen!

#### Software-Abhängigkeiten
```
# Option 1: nmap (bereits vorhanden)
nmap mit smb2-security-mode Script

# Option 2: Pure Python
impacket>=0.11.0
```

#### Netzwerk-Anforderungen
| Port | Protokoll | Zweck |
|------|-----------|-------|
| 445 | SMB | SMB Negotiation |

### Architektur

```python
# tools/audit/smb/smb_signing_check.py

from dataclasses import dataclass
from enum import Enum
from typing import List

class SMBSigningStatus(Enum):
    """SMB Signing Status"""
    REQUIRED = "required"           # Signing erzwungen - sicher
    ENABLED = "enabled"             # Signing möglich aber nicht erzwungen - VULNERABLE!
    DISABLED = "disabled"           # Signing deaktiviert - VULNERABLE!
    NOT_SUPPORTED = "not_supported" # SMBv1 only oder Error
    UNKNOWN = "unknown"

@dataclass
class SMBSigningResult:
    """Ergebnis eines SMB Signing Checks"""
    target: str
    port: int
    smb_version: str            # SMBv2, SMBv3
    signing_status: SMBSigningStatus
    message_signing: bool        # Signing enabled
    signing_required: bool       # Signing required
    is_dc: bool                  # Ist Domain Controller?
    risk_level: str              # CRITICAL, HIGH, MEDIUM, LOW, OK
    relay_vulnerable: bool       # Kann für Relay genutzt werden?

class SMBSigningChecker:
    """
    Prüft SMB Signing Konfiguration auf Zielsystemen.

    Requires: Netzwerkzugriff Port 445 - KEINE Credentials!
    """

    def __init__(self, use_nmap: bool = True):
        """
        Args:
            use_nmap: True = nmap Script, False = impacket
        """
        self.use_nmap = use_nmap

    def check_single(self, target: str, port: int = 445) -> SMBSigningResult:
        """
        Prüft SMB Signing auf einem Ziel.

        Args:
            target: IP oder Hostname
            port: SMB Port (default 445)

        Returns:
            SMBSigningResult mit allen Details
        """
        pass

    def check_multiple(self, targets: List[str]) -> List[SMBSigningResult]:
        """Prüft mehrere Ziele parallel"""
        pass

    def check_subnet(self, subnet: str) -> List[SMBSigningResult]:
        """
        Scannt Subnet nach SMB und prüft Signing.

        Args:
            subnet: CIDR Notation (192.168.1.0/24)
        """
        pass

    def _check_via_nmap(self, target: str, port: int) -> SMBSigningResult:
        """Implementierung via nmap"""
        # nmap --script smb2-security-mode -p 445 target
        pass

    def _check_via_impacket(self, target: str, port: int) -> SMBSigningResult:
        """Implementierung via impacket (Pure Python)"""
        # SMB Negotiation und Capabilities prüfen
        pass

    def _determine_risk(self, result: SMBSigningResult) -> str:
        """
        Bestimmt Risiko-Level basierend auf Ergebnis.

        CRITICAL: DC ohne Required Signing
        HIGH: Server ohne Required Signing
        MEDIUM: Workstation ohne Required Signing
        OK: Signing Required
        """
        pass
```

### nmap Integration

```python
def _check_via_nmap(self, target: str, port: int) -> SMBSigningResult:
    """
    Verwendet nmap smb2-security-mode Script.

    Output Beispiel:
    | smb2-security-mode:
    |   3.1.1:
    |_    Message signing enabled but not required
    """
    import subprocess
    import re

    cmd = [
        "nmap", "-Pn", "-p", str(port),
        "--script", "smb2-security-mode",
        target
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout

    # Parsing
    if "Message signing enabled and required" in output:
        return SMBSigningResult(
            target=target,
            signing_status=SMBSigningStatus.REQUIRED,
            signing_required=True,
            relay_vulnerable=False,
            risk_level="OK"
        )
    elif "Message signing enabled but not required" in output:
        return SMBSigningResult(
            target=target,
            signing_status=SMBSigningStatus.ENABLED,
            signing_required=False,
            relay_vulnerable=True,  # VULNERABLE!
            risk_level="HIGH"
        )
    # ... weitere Cases
```

### Verification

#### Unit Tests
```python
def test_parse_nmap_output_required():
    """Parsing: Signing Required"""
    output = """
    | smb2-security-mode:
    |   3.1.1:
    |_    Message signing enabled and required
    """
    result = parse_nmap_smb_output(output)
    assert result.signing_required == True
    assert result.relay_vulnerable == False

def test_parse_nmap_output_not_required():
    """Parsing: Signing Not Required - VULNERABLE"""
    output = """
    | smb2-security-mode:
    |   3.1.1:
    |_    Message signing enabled but not required
    """
    result = parse_nmap_smb_output(output)
    assert result.signing_required == False
    assert result.relay_vulnerable == True
```

#### Integration Test
```bash
# Gegen GOAD testen (hat Systeme mit/ohne SMB Signing)
python cli.py smb signing-check --subnet 192.168.56.0/24

# Erwarteter Output:
# SMB Signing Analysis
# ====================
#
# Target              SMB Version  Signing      Risk      Relay?
# ─────────────────────────────────────────────────────────────
# 192.168.56.10 (DC)  SMBv3.1.1    Required     OK        No
# 192.168.56.22       SMBv3.1.1    Not Required HIGH      Yes ⚠️
# 192.168.56.23       SMBv2.1      Not Required HIGH      Yes ⚠️
#
# Summary: 2 of 3 systems vulnerable to SMB Relay!
```

#### Vergleich mit GPO
```bash
# 1. GPO sagt "SMB Signing Required":
Get-GPO "SMB Security" | Get-GPOReport -ReportType HTML

# 2. Tool sagt "Not Required" auf einigen Systemen
# → GPO wirkt nicht! (Scope-Problem, WMI-Filter, etc.)
```

### Definition of Done
- [ ] nmap-basierte Implementierung funktioniert
- [ ] Subnet-Scan möglich
- [ ] Korrekte Risk-Level Zuweisung
- [ ] DC-Detection (höheres Risiko)
- [ ] Output zeigt Relay-Vulnerability klar an
- [ ] Integration mit GPO-Audit ("GPO sagt X, Realität ist Y")

---

## Issue #4: LLMNR/NBT-NS/mDNS Detector

### Metadata
```
Title: [Feature] LLMNR/NBT-NS/mDNS Protocol Detector (protocol_detector)
Labels: type:feature, priority:critical, status:backlog, component:tools, attack-phase:initial-access
Milestone: v0.8.0 - AD Audit Capabilities
Estimate: 2-3 days
```

### Beschreibung

**Was ist das Tool?**
Passives Sniffing Tool das erkennt ob LLMNR, NBT-NS (NetBIOS) und mDNS im Netzwerk aktiv sind. Diese Protokolle ermöglichen Name Resolution Poisoning Angriffe.

**Warum brauchen wir das?**
- LLMNR/NBT-NS Poisoning ist oft der erste erfolgreiche Angriff in AD
- GPO kann diese Protokolle deaktivieren - aber wirkt es?
- Passiver Test: Wir sniffen nur, greifen nicht an
- Unterschied zu Responder: Wir analysieren, Responder greift an

**Security Impact:**
- LLMNR/NBT-NS aktiv → Responder kann NetNTLMv2 Hashes abfangen → Credential Theft

### Requirements

#### Credentials
| Level | Funktionsumfang |
|-------|-----------------|
| **Keine Credentials!** | Voller Funktionsumfang |
| **Root/sudo** | Erforderlich für Raw Socket Sniffing |

#### Software-Abhängigkeiten
```
scapy>=2.5.0          # Packet Sniffing
```

#### Netzwerk-Anforderungen
| Anforderung | Details |
|-------------|---------|
| Layer 2 Access | Muss im gleichen Broadcast-Domain sein |
| Promiscuous Mode | Für vollständiges Sniffing |
| Root/sudo | Raw Sockets erfordern Privilegien |

#### Container-Anforderungen
```yaml
# Docker benötigt:
cap_add:
  - NET_RAW          # Raw Sockets
  - NET_ADMIN        # Promiscuous Mode
network_mode: host   # Oder macvlan für LAN-Zugriff
```

### Architektur

```python
# tools/audit/protocols/protocol_detector.py

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Callable
from scapy.all import sniff, DNSQR, UDP

class ProtocolType(Enum):
    LLMNR = "llmnr"         # Port 5355
    NETBIOS_NS = "nbt-ns"   # Port 137
    MDNS = "mdns"           # Port 5353

@dataclass
class ProtocolDetection:
    """Ein erkanntes Protokoll-Paket"""
    protocol: ProtocolType
    timestamp: datetime
    source_ip: str
    source_mac: str
    query_name: str          # Was wurde gesucht?
    is_response: bool        # Query oder Response?

@dataclass
class ProtocolAnalysis:
    """Analyse-Ergebnis für ein Netzwerk"""
    interface: str
    duration_seconds: int
    llmnr_active: bool
    netbios_active: bool
    mdns_active: bool
    unique_sources: List[str]  # IPs die diese Protokolle nutzen
    detections: List[ProtocolDetection]
    risk_assessment: str

class ProtocolDetector:
    """
    Passiver Detector für LLMNR/NBT-NS/mDNS.

    Requires: Root/sudo, gleiches Subnet, NET_RAW capability
    """

    def __init__(self, interface: str):
        """
        Args:
            interface: Netzwerk-Interface (eth0, ens33, etc.)
        """
        self.interface = interface
        self.detections: List[ProtocolDetection] = []

    def analyze(self,
                duration: int = 60,
                callback: Optional[Callable] = None) -> ProtocolAnalysis:
        """
        Snifft für gegebene Dauer und analysiert Protokolle.

        Args:
            duration: Sniffing-Dauer in Sekunden (default: 60)
            callback: Optional callback für Echtzeit-Updates

        Returns:
            Vollständige Analyse der erkannten Protokolle
        """
        pass

    def _packet_handler(self, packet) -> None:
        """Verarbeitet ein Paket und extrahiert relevante Infos"""
        pass

    def _is_llmnr(self, packet) -> bool:
        """Prüft ob Paket LLMNR ist (UDP 5355)"""
        return UDP in packet and packet[UDP].dport == 5355

    def _is_netbios(self, packet) -> bool:
        """Prüft ob Paket NetBIOS-NS ist (UDP 137)"""
        return UDP in packet and packet[UDP].dport == 137

    def _is_mdns(self, packet) -> bool:
        """Prüft ob Paket mDNS ist (UDP 5353)"""
        return UDP in packet and packet[UDP].dport == 5353

    def get_vulnerable_hosts(self) -> List[str]:
        """
        Gibt IPs zurück die vulnerable Protokolle nutzen.

        Diese Hosts würden auf Responder-Poisoning reinfallen!
        """
        pass

    def compare_with_gpo(self,
                         gpo_says_disabled: bool) -> dict:
        """
        Vergleicht Sniffing-Ergebnis mit GPO-Konfiguration.

        Args:
            gpo_says_disabled: True wenn GPO LLMNR deaktivieren soll

        Returns:
            {
                "gpo_config": "LLMNR Disabled",
                "reality": "LLMNR ACTIVE on 5 hosts",
                "match": False,
                "finding": "GPO not effective!"
            }
        """
        pass
```

### Scapy BPF Filter

```python
# Effizienter BPF Filter für relevante Protokolle
BPF_FILTER = "udp and (port 5355 or port 137 or port 5353)"

def analyze(self, duration: int = 60) -> ProtocolAnalysis:
    """Snifft nach LLMNR/NBT-NS/mDNS"""

    packets = sniff(
        iface=self.interface,
        filter=BPF_FILTER,
        timeout=duration,
        prn=self._packet_handler,
        store=True
    )

    # Analyse
    llmnr_hosts = set()
    netbios_hosts = set()
    mdns_hosts = set()

    for pkt in packets:
        if self._is_llmnr(pkt):
            llmnr_hosts.add(pkt[IP].src)
        elif self._is_netbios(pkt):
            netbios_hosts.add(pkt[IP].src)
        elif self._is_mdns(pkt):
            mdns_hosts.add(pkt[IP].src)

    return ProtocolAnalysis(
        interface=self.interface,
        duration_seconds=duration,
        llmnr_active=len(llmnr_hosts) > 0,
        netbios_active=len(netbios_hosts) > 0,
        mdns_active=len(mdns_hosts) > 0,
        unique_sources=list(llmnr_hosts | netbios_hosts | mdns_hosts),
        risk_assessment=self._assess_risk(llmnr_hosts, netbios_hosts)
    )
```

### Verification

#### Unit Tests
```python
def test_llmnr_detection():
    """LLMNR Paket wird erkannt"""
    # Craft LLMNR packet
    pkt = IP(dst="224.0.0.252")/UDP(dport=5355)/...

    detector = ProtocolDetector("eth0")
    assert detector._is_llmnr(pkt) == True

def test_netbios_detection():
    """NetBIOS-NS Paket wird erkannt"""
    pkt = IP()/UDP(dport=137)/...

    detector = ProtocolDetector("eth0")
    assert detector._is_netbios(pkt) == True
```

#### Integration Test
```bash
# 1. Detector starten (als root)
sudo python cli.py protocol analyze \
    --interface eth0 \
    --duration 120

# 2. Auf anderem System LLMNR Query auslösen:
ping nonexistent-host-12345

# 3. Erwarteter Output:
# Protocol Analysis (120 seconds on eth0)
# ═══════════════════════════════════════
#
# Protocol      Active?   Hosts
# ───────────────────────────────────────
# LLMNR         YES ⚠️    192.168.1.10, 192.168.1.15, 192.168.1.22
# NetBIOS-NS    YES ⚠️    192.168.1.10, 192.168.1.15
# mDNS          YES       192.168.1.10 (often legitimate)
#
# Risk Assessment: HIGH
# 3 hosts would respond to LLMNR/NBT-NS poisoning
#
# Recommendation: Disable LLMNR via GPO:
# Computer Config → Admin Templates → Network → DNS Client
# → Turn off multicast name resolution = Enabled
```

#### Vergleich mit GPO
```bash
# GPO sagt LLMNR ist deaktiviert:
# Registry: HKLM\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient
#           EnableMulticast = 0

# Aber Detector findet LLMNR Traffic von 5 Hosts
# → GPO nicht auf alle Systeme angewendet!
```

### Definition of Done
- [ ] LLMNR Detection funktioniert
- [ ] NetBIOS-NS Detection funktioniert
- [ ] mDNS Detection funktioniert
- [ ] Root-Check vor Ausführung
- [ ] Docker mit NET_RAW funktioniert
- [ ] Live-Output während Sniffing
- [ ] Vergleich mit GPO-Config möglich

---

## Issue #5: WDigest Credential Caching Checker

### Metadata
```
Title: [Feature] WDigest Credential Caching Checker (wdigest_check)
Labels: type:feature, priority:high, status:backlog, component:tools, attack-phase:credential-access
Milestone: v0.8.0 - AD Audit Capabilities
Estimate: 2 days
```

### Beschreibung

**Was ist das Tool?**
Prüft ob WDigest Credential Caching auf Windows-Systemen aktiviert ist. Bei aktiviertem WDigest speichert Windows Klartext-Passwörter im Speicher.

**Warum brauchen wir das?**
- WDigest aktiviert → Mimikatz kann Klartext-Passwörter dumpen
- GPO kann WDigest deaktivieren (KB2871997)
- Legacy-Systeme haben WDigest oft noch aktiviert
- Kritisch für Lateral Movement Assessment

**Security Impact:**
- WDigest aktiviert + Local Admin = Klartext-Passwörter aller eingeloggten User

### Requirements

#### Credentials
| Level | Funktionsumfang |
|-------|-----------------|
| **Local Admin** | Vollständig (Remote Registry Query) |
| **Domain Admin** | Bulk-Check über alle Systeme |
| **Domain User** | Nur GPO-Konfiguration prüfen (LDAP), nicht tatsächlichen Status |

#### Software-Abhängigkeiten
```
impacket>=0.11.0      # Remote Registry, WMI
```

#### Netzwerk-Anforderungen
| Port | Protokoll | Zweck |
|------|-----------|-------|
| 445 | SMB | Remote Registry |
| 135 | RPC | WMI (Alternative) |

### Architektur

```python
# tools/audit/windows/wdigest_check.py

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class WDigestStatus(Enum):
    DISABLED = "disabled"           # UseLogonCredential = 0 → Sicher
    ENABLED = "enabled"             # UseLogonCredential = 1 → VULNERABLE
    NOT_CONFIGURED = "not_configured"  # Key fehlt → Default abhängig von OS
    UNKNOWN = "unknown"             # Konnte nicht prüfen

@dataclass
class WDigestResult:
    """Ergebnis eines WDigest Checks"""
    target: str
    status: WDigestStatus
    registry_value: Optional[int]   # 0, 1, oder None
    os_version: Optional[str]       # Windows Version
    default_behavior: str           # Was ist der Default für diese OS Version?
    is_vulnerable: bool
    risk_level: str
    remediation: str

class WDigestChecker:
    """
    Prüft WDigest Credential Caching Status.

    Requires: Local Admin on target (für Remote Registry)
    """

    # Registry Key Location
    WDIGEST_KEY = r"SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest"
    WDIGEST_VALUE = "UseLogonCredential"

    def __init__(self, username: str, password: str, domain: str = ""):
        """
        Args:
            username: Admin User
            password: Passwort
            domain: Domain (optional für Local Admin)
        """
        self.username = username
        self.password = password
        self.domain = domain

    def check_single(self, target: str) -> WDigestResult:
        """
        Prüft WDigest Status auf einem System.

        Liest Remote Registry:
        HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest
        → UseLogonCredential (DWORD)

        0 = Disabled (sicher)
        1 = Enabled (vulnerable)
        Key fehlt = OS Default
        """
        pass

    def check_multiple(self, targets: List[str]) -> List[WDigestResult]:
        """Prüft mehrere Systeme parallel"""
        pass

    def _read_remote_registry(self, target: str, key: str, value: str) -> Optional[int]:
        """
        Liest Registry-Wert via Remote Registry Service.

        Verwendet impacket rrp (Remote Registry Protocol)
        """
        pass

    def _get_os_version(self, target: str) -> Optional[str]:
        """Ermittelt Windows Version für Default-Behavior"""
        pass

    def _determine_vulnerability(self, value: Optional[int], os_version: str) -> bool:
        """
        Bestimmt ob System vulnerable ist.

        Default-Verhalten nach OS:
        - Windows 8.1+ / Server 2012 R2+: Default DISABLED
        - Windows 7/8 / Server 2008/2012: Default ENABLED!
        """
        if value == 0:
            return False  # Explizit disabled
        if value == 1:
            return True   # Explizit enabled

        # Key fehlt → OS Default
        if "Windows 7" in os_version or "Server 2008" in os_version:
            return True   # Default enabled auf alten OS
        if "Windows 8.0" in os_version or "Server 2012" in os_version:
            return True   # Ohne R2: Default enabled

        return False  # Neuere OS: Default disabled
```

### impacket Remote Registry

```python
from impacket.dcerpc.v5 import rrp, transport
from impacket.dcerpc.v5.dtypes import NULL

def _read_remote_registry(self, target: str, key: str, value: str) -> Optional[int]:
    """
    Liest Registry via Remote Registry Protocol (MS-RRP).

    Requires: Admin credentials + Remote Registry service running
    """
    # SMB Connection
    smb = SMBConnection(target, target)
    smb.login(self.username, self.password, self.domain)

    # RRP über Named Pipe
    rpctransport = transport.SMBTransport(
        target,
        filename=r'\winreg',
        smb_connection=smb
    )

    dce = rpctransport.get_dce_rpc()
    dce.connect()
    dce.bind(rrp.MSRPC_UUID_RRP)

    # HKLM öffnen
    resp = rrp.hOpenLocalMachine(dce)
    hklm = resp['phKey']

    # Key öffnen
    resp = rrp.hBaseRegOpenKey(dce, hklm, key)
    hkey = resp['phkResult']

    # Wert lesen
    try:
        resp = rrp.hBaseRegQueryValue(dce, hkey, value)
        return resp['lpData']
    except Exception:
        return None  # Key/Value existiert nicht
```

### Verification

```bash
# Gegen Windows-System mit Local Admin
python cli.py wdigest check \
    --target 192.168.1.50 \
    --user Administrator \
    --password P@ssw0rd

# Erwarteter Output:
# WDigest Credential Caching Check
# ════════════════════════════════
#
# Target: 192.168.1.50
# OS: Windows Server 2016
# Registry: HKLM\...\WDigest\UseLogonCredential
#
# Value: 1 (ENABLED)
# Status: ⚠️ VULNERABLE
#
# Risk: HIGH
# Impact: Mimikatz can dump cleartext passwords from memory
#
# Remediation:
# Set registry value to 0 or deploy via GPO:
# Computer Config → Preferences → Windows Settings → Registry
# HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest
# UseLogonCredential = 0 (DWORD)
```

### Definition of Done
- [ ] Remote Registry Read funktioniert
- [ ] OS Version Detection für Defaults
- [ ] Korrekte Vulnerability-Bewertung
- [ ] Bulk-Check über mehrere Systeme
- [ ] Vergleich mit GPO-Konfiguration
- [ ] Remediation-Hinweise im Output

---

## Issue #6: Credential Guard Status Checker

### Metadata
```
Title: [Feature] Credential Guard Status Checker (credguard_check)
Labels: type:feature, priority:medium, status:backlog, component:tools
Milestone: v0.8.0 - AD Audit Capabilities
Estimate: 2 days
```

### Beschreibung

**Was ist das Tool?**
Prüft ob Windows Credential Guard aktiviert ist. Credential Guard schützt Credentials vor Mimikatz und ähnlichen Tools.

**Warum brauchen wir das?**
- Credential Guard ist die beste Defense gegen Credential Dumping
- GPO kann Credential Guard deployen - aber ist es wirklich aktiv?
- Erfordert TPM + UEFI + Secure Boot → oft nicht erfüllt
- Pentester müssen wissen welche Systeme geschützt sind

**Security Impact:**
- Credential Guard aktiv → Mimikatz funktioniert NICHT
- Credential Guard inaktiv trotz GPO → False sense of security

### Requirements

#### Credentials
| Level | Funktionsumfang |
|-------|-----------------|
| **Local Admin** | Vollständig (WMI Query) |
| **Domain User** | Nur GPO prüfen, nicht tatsächlichen Status |

#### Software-Abhängigkeiten
```
impacket>=0.11.0      # WMI Queries
```

#### Hardware-Anforderungen (auf Ziel)
Credential Guard benötigt:
- Windows 10 Enterprise/Education oder Server 2016+
- UEFI Firmware (kein Legacy BIOS)
- Secure Boot aktiviert
- TPM 2.0 (empfohlen)
- Virtualization Extensions (VT-x/AMD-V)

### Architektur

```python
# tools/audit/windows/credguard_check.py

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

class CredGuardStatus(Enum):
    RUNNING = "running"             # VBS aktiv, Credential Guard läuft
    CONFIGURED = "configured"       # Konfiguriert aber nicht aktiv (Reboot nötig?)
    NOT_CONFIGURED = "not_configured"
    NOT_SUPPORTED = "not_supported" # Hardware/OS unterstützt es nicht
    UNKNOWN = "unknown"

@dataclass
class CredGuardResult:
    """Ergebnis eines Credential Guard Checks"""
    target: str
    status: CredGuardStatus
    vbs_running: bool              # Virtualization Based Security aktiv?
    credential_guard_running: bool  # CG spezifisch aktiv?
    secure_boot: bool
    uefi_mode: bool
    os_edition: str                # Enterprise, Pro, etc.
    is_protected: bool             # Effektiv geschützt?
    mimikatz_would_work: bool      # Kann Mimikatz Creds dumpen?
    missing_requirements: List[str]

class CredentialGuardChecker:
    """
    Prüft Credential Guard Status via WMI.

    Requires: Local Admin on target
    """

    def check_single(self, target: str,
                     username: str, password: str) -> CredGuardResult:
        """
        Prüft Credential Guard Status via WMI.

        WMI Query: Win32_DeviceGuard
        - VirtualizationBasedSecurityStatus
        - SecurityServicesConfigured
        - SecurityServicesRunning
        """
        pass

    def _query_wmi(self, target: str, query: str,
                   username: str, password: str) -> dict:
        """
        Führt WMI Query remote aus.

        Verwendet impacket wmiexec
        """
        pass

    def _check_prerequisites(self, target: str,
                            username: str, password: str) -> List[str]:
        """
        Prüft Hardware/Software Voraussetzungen.

        Returns:
            Liste fehlender Requirements
        """
        missing = []

        # Secure Boot prüfen
        # bcdedit über WMI

        # UEFI Mode prüfen
        # Firmware type

        # OS Edition prüfen
        # Muss Enterprise/Education/Server sein

        return missing
```

### WMI Query für DeviceGuard

```python
def _query_device_guard(self, target: str, username: str, password: str) -> dict:
    """
    WMI Query für Win32_DeviceGuard Klasse.

    Returns:
        {
            "VirtualizationBasedSecurityStatus": 2,  # 0=Off, 1=Configured, 2=Running
            "SecurityServicesConfigured": [1, 2],    # 1=CG, 2=HVCI
            "SecurityServicesRunning": [1, 2],       # Was tatsächlich läuft
            "RequiredSecurityProperties": [...],
            "AvailableSecurityProperties": [...]
        }
    """
    # PowerShell über WMI ausführen
    ps_command = """
    $dg = Get-CimInstance -ClassName Win32_DeviceGuard -Namespace root\\Microsoft\\Windows\\DeviceGuard
    $dg | ConvertTo-Json
    """

    # Via impacket wmiexec
    from impacket.examples.wmiexec import WMIEXEC

    executer = WMIEXEC(
        command=f'powershell -Command "{ps_command}"',
        username=username,
        password=password,
        domain="",
        hashes=None,
        aesKey=None,
        share="ADMIN$",
        noOutput=False
    )

    output = executer.run(target)
    return json.loads(output)
```

### Verification

```bash
python cli.py credguard check \
    --target 192.168.1.50 \
    --user Administrator \
    --password P@ssw0rd

# Output wenn NICHT aktiv:
# Credential Guard Status Check
# ═════════════════════════════
#
# Target: 192.168.1.50
# OS: Windows 10 Enterprise 21H2
#
# VBS Status: Not Running
# Credential Guard: NOT ACTIVE ⚠️
# Secure Boot: Yes
# UEFI Mode: Yes
#
# Missing Requirements:
# - Hyper-V not enabled
# - Group Policy not configured
#
# Risk Assessment: HIGH
# Mimikatz WILL work on this system!
#
# Remediation:
# 1. Enable Hyper-V feature
# 2. Configure via GPO: Computer Config → Admin Templates →
#    System → Device Guard → Turn On Virtualization Based Security

# Output wenn AKTIV:
# Credential Guard: RUNNING ✓
# Mimikatz Protection: ACTIVE
# Risk Assessment: LOW
```

### Definition of Done
- [ ] WMI Query für DeviceGuard funktioniert
- [ ] Prerequisites Check (UEFI, SecureBoot, TPM)
- [ ] OS Edition Check (Enterprise required)
- [ ] Klare Aussage "Mimikatz works/doesn't work"
- [ ] Remediation Steps

---

## Issue #7: LAPS Deployment Auditor

### Metadata
```
Title: [Feature] LAPS Deployment Auditor (laps_auditor)
Labels: type:feature, priority:high, status:backlog, component:tools
Milestone: v0.8.0 - AD Audit Capabilities
Estimate: 2-3 days
```

### Beschreibung

**Was ist das Tool?**
Prüft ob Microsoft LAPS (Local Administrator Password Solution) deployed ist und ob die Passwörter tatsächlich rotiert werden.

**Warum brauchen wir das?**
- LAPS verhindert Lateral Movement mit gleichen Local Admin Passwörtern
- GPO kann LAPS deployen - aber sind die Attribute gefüllt?
- Oft wird LAPS deployed aber nie aktiviert
- Pentester müssen wissen: Hat jeder Rechner ein einzigartiges Passwort?

**Security Impact:**
- Ohne LAPS: Ein Local Admin Passwort → Zugriff auf ALLE Workstations
- Mit LAPS: Jedes System hat einzigartiges, rotierendes Passwort

### Requirements

#### Credentials
| Level | Funktionsumfang |
|-------|-----------------|
| **Domain User** | Prüfen ob LAPS Schema vorhanden, Computer-Objekte haben Attribut |
| **LAPS Read Delegation** | Passwort-Werte lesen (zeigt dass LAPS funktioniert) |
| **Domain Admin** | Alle Passwörter lesen, vollständiger Audit |

#### Software-Abhängigkeiten
```
ldap3>=2.9.1          # LDAP Queries
```

### Architektur

```python
# tools/audit/ad/laps_auditor.py

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class LAPSStatus:
    """LAPS Status für einen Computer"""
    computer_name: str
    computer_dn: str
    has_laps_attribute: bool       # ms-Mcs-AdmPwd Attribut existiert
    password_set: bool             # Attribut hat Wert (nicht leer)
    password_expiry: Optional[datetime]  # ms-Mcs-AdmPwdExpirationTime
    password_age_days: Optional[int]
    is_protected: bool             # LAPS effektiv aktiv

@dataclass
class LAPSAuditResult:
    """Gesamtergebnis des LAPS Audits"""
    schema_extended: bool          # LAPS Schema installiert?
    total_computers: int
    laps_enabled_count: int
    laps_disabled_count: int       # Attribut existiert aber leer
    no_laps_count: int             # Kein Attribut
    expired_passwords: int         # Passwort abgelaufen
    coverage_percent: float
    vulnerable_computers: List[str]

class LAPSAuditor:
    """
    Auditiert LAPS Deployment in Active Directory.

    Requires: Domain User (Basis), LAPS Read (vollständig)
    """

    # LAPS Attribute
    LAPS_PWD_ATTR = "ms-Mcs-AdmPwd"
    LAPS_EXPIRY_ATTR = "ms-Mcs-AdmPwdExpirationTime"

    # Windows LAPS (neue Version)
    WLAPS_PWD_ATTR = "msLAPS-Password"
    WLAPS_EXPIRY_ATTR = "msLAPS-PasswordExpirationTime"

    def __init__(self, dc_ip: str, domain: str,
                 username: str, password: str):
        pass

    def check_schema(self) -> bool:
        """
        Prüft ob LAPS Schema in AD installiert wurde.

        Sucht nach ms-Mcs-AdmPwd Attribut im Schema.
        """
        pass

    def audit_all_computers(self) -> LAPSAuditResult:
        """
        Auditiert alle Computer-Objekte auf LAPS Status.

        LDAP Query auf alle Computers, prüft:
        - Hat ms-Mcs-AdmPwd Attribut?
        - Ist Attribut gefüllt?
        - Wann läuft Passwort ab?
        """
        pass

    def get_computers_without_laps(self) -> List[str]:
        """
        Findet Computer ohne LAPS.

        Diese sind vulnerable für Lateral Movement!
        """
        pass

    def get_expired_passwords(self) -> List[LAPSStatus]:
        """
        Findet Computer mit abgelaufenen LAPS Passwörtern.

        Zeigt dass LAPS GPO nicht mehr greift.
        """
        pass

    def can_read_passwords(self) -> bool:
        """
        Testet ob wir Passwörter lesen können.

        Wenn ja: Wir haben LAPS Read Delegation oder sind DA
        """
        pass
```

### LDAP Queries

```python
# Schema Check: LAPS Attribut existiert?
SCHEMA_QUERY = """
(&(objectClass=attributeSchema)(lDAPDisplayName=ms-Mcs-AdmPwd))
"""

# Alle Computer mit LAPS Status
COMPUTER_QUERY = "(objectClass=computer)"
COMPUTER_ATTRS = [
    "cn",
    "distinguishedName",
    "ms-Mcs-AdmPwd",              # Legacy LAPS
    "ms-Mcs-AdmPwdExpirationTime",
    "msLAPS-Password",            # Windows LAPS
    "msLAPS-PasswordExpirationTime"
]

# Computer OHNE LAPS Passwort
NO_LAPS_QUERY = """
(&(objectClass=computer)(!(ms-Mcs-AdmPwd=*)))
"""
```

### Verification

```bash
python cli.py laps audit \
    --dc 192.168.56.10 \
    --domain north.sevenkingdoms.local \
    --user samwell.tarly \
    --password Heartsbane

# Output:
# LAPS Deployment Audit
# ═════════════════════
#
# Schema Status: LAPS Schema Installed ✓
#
# Coverage Analysis:
# ─────────────────────────────────────
# Total Computers:     150
# LAPS Enabled:        120 (80%)
# LAPS Disabled:       15  (10%)  ⚠️
# No LAPS Attribute:   15  (10%)  ⚠️
# Expired Passwords:   5   (3%)   ⚠️
#
# Risk Assessment: MEDIUM
# 30 computers are vulnerable to lateral movement with shared admin password
#
# Vulnerable Computers:
# - LEGACY-PC01 (no LAPS)
# - LEGACY-PC02 (no LAPS)
# - DEV-WS01 (password expired)
# ...
#
# Password Read Test: SUCCESS
# (Your account has LAPS read delegation)
#
# Recommendation:
# 1. Deploy LAPS to remaining 15 computers
# 2. Investigate why 5 passwords expired (GPO not applied?)
# 3. Review LAPS delegation (we shouldn't have read access as regular user)
```

### Definition of Done
- [ ] Schema Check funktioniert
- [ ] Computer-Enumeration mit LAPS Status
- [ ] Coverage-Statistik
- [ ] Expired Password Detection
- [ ] Permission Check (können wir Passwörter lesen?)
- [ ] Windows LAPS (neue Version) Support

---

# MISCONFIGURATION DETECTION

---

## Issue #8: GPO Link Analyzer

### Metadata
```
Title: [Feature] GPO Link Analyzer - Find Unlinked GPOs (gpo_link_analyzer)
Labels: type:feature, priority:high, status:backlog, component:tools
Milestone: v0.8.0 - AD Audit Capabilities
Estimate: 1-2 days
```

### Beschreibung

**Was ist das Tool?**
Findet GPOs die erstellt aber nicht verlinkt wurden. Diese "vergessenen" GPOs sind oft Security-GPOs die nie aktiviert wurden.

**Warum brauchen wir das?**
- Klassischer Admin-Fehler: GPO erstellen, vergessen zu verlinken
- Security-GPOs die nie wirkten
- "Wir haben doch eine GPO für LLMNR!" - "Ja, aber nicht verlinkt"

### Requirements

#### Credentials
| Level | Funktionsumfang |
|-------|-----------------|
| **Domain User** | Vollständig |

### Architektur

```python
# tools/audit/gpo/gpo_link_analyzer.py

class GPOLinkAnalyzer:
    """
    Analysiert GPO-Verlinkungen und findet Misconfigurations.

    Requires: Domain User
    """

    def find_unlinked_gpos(self) -> List[GPOObject]:
        """
        Findet GPOs ohne jegliche Verlinkung.

        Diese GPOs wurden erstellt aber nie aktiviert!
        """
        pass

    def find_disabled_links(self) -> List[tuple]:
        """
        Findet GPO-Links die deaktiviert sind.

        Returns:
            [(gpo, ou, reason), ...]
        """
        pass

    def find_orphaned_links(self) -> List[tuple]:
        """
        Findet Links zu gelöschten GPOs.

        Passiert wenn GPO gelöscht wird aber Link-Referenz bleibt.
        """
        pass

    def analyze_link_order(self, ou_dn: str) -> List[dict]:
        """
        Analysiert Link-Reihenfolge auf einer OU.

        Bei mehreren GPOs ist die Reihenfolge wichtig!
        Niedrigere Link Order = höhere Priorität
        """
        pass

    def find_enforced_gpos(self) -> List[GPOObject]:
        """
        Findet GPOs mit "Enforced" Flag.

        Diese überschreiben Block Inheritance.
        """
        pass
```

### Verification

```bash
python cli.py gpo links analyze \
    --dc 192.168.56.10 \
    --domain north.sevenkingdoms.local

# Output:
# GPO Link Analysis
# ═════════════════
#
# ⚠️ Unlinked GPOs (never activated!):
# ─────────────────────────────────────
# - "Disable LLMNR" (created 2023-01-15)
# - "Security Baseline v2" (created 2024-06-01)
#
# ⚠️ Disabled Links:
# ─────────────────────────────────────
# - "Password Policy" → OU=Servers (Link disabled)
#
# Enforced GPOs (override Block Inheritance):
# ─────────────────────────────────────
# - "Domain Security Policy" → Domain Root (Enforced)
```

### Definition of Done
- [ ] Unlinked GPO Detection
- [ ] Disabled Link Detection
- [ ] Orphaned Link Detection
- [ ] Link Order Analyse
- [ ] Enforced GPO Liste

---

## Issue #9: GPO Scope Validator

### Metadata
```
Title: [Feature] GPO Scope Validator - Verify GPO Coverage (gpo_scope_validator)
Labels: type:feature, priority:medium, status:backlog, component:tools
Milestone: v0.8.0 - AD Audit Capabilities
Estimate: 2-3 days
```

### Beschreibung

**Was ist das Tool?**
Validiert ob Security-GPOs alle relevanten Computer erreichen. Findet OUs/Computer die nicht von GPOs abgedeckt sind.

**Warum brauchen wir das?**
- GPO auf "OU=Workstations" verlinkt
- Aber Legacy-Rechner liegen in "OU=Legacy"
- Security-GPO erreicht nicht alle Systeme

### Requirements

#### Credentials
| Level | Funktionsumfang |
|-------|-----------------|
| **Domain User** | Vollständig |

### Architektur

```python
# tools/audit/gpo/gpo_scope_validator.py

@dataclass
class CoverageGap:
    """Eine Lücke in der GPO-Abdeckung"""
    gpo_name: str
    expected_scope: str          # "All Computers" / "All Servers"
    missing_ous: List[str]       # OUs nicht abgedeckt
    missing_computers: List[str] # Spezifische Computer
    reason: str                  # Warum nicht abgedeckt

class GPOScopeValidator:
    """
    Validiert GPO-Abdeckung gegen erwarteten Scope.

    Requires: Domain User
    """

    def validate_coverage(self,
                         gpo_name: str,
                         expected_scope: str) -> CoverageGap:
        """
        Prüft ob GPO alle erwarteten Systeme erreicht.

        Args:
            gpo_name: Name der GPO
            expected_scope: "all_computers" | "all_servers" | "all_workstations" | OU DN
        """
        pass

    def find_uncovered_computers(self, gpo_name: str) -> List[str]:
        """
        Findet Computer die NICHT von der GPO erreicht werden.

        Berücksichtigt:
        - OU-Hierarchie
        - Security Filtering
        - WMI Filter
        - Block Inheritance
        """
        pass

    def simulate_gpo_application(self,
                                 computer_dn: str) -> List[GPOObject]:
        """
        Simuliert welche GPOs auf einen Computer wirken würden.

        "Was würde gpresult auf diesem Computer zeigen?"
        """
        pass
```

### Verification

```bash
python cli.py gpo scope validate \
    --gpo "Disable LLMNR" \
    --expected-scope all_computers

# Output:
# GPO Scope Validation
# ════════════════════
#
# GPO: "Disable LLMNR"
# Expected Scope: All Computers (150)
#
# Coverage Analysis:
# ─────────────────────────────────────
# Covered:     120 computers (80%)
# Not Covered: 30 computers (20%) ⚠️
#
# Missing OUs:
# - OU=Legacy,DC=corp,DC=local (15 computers)
# - OU=Contractors,DC=corp,DC=local (10 computers)
# - OU=Test,DC=corp,DC=local (5 computers)
#
# Recommendation:
# Link GPO to these OUs or move computers to covered OUs
```

### Definition of Done
- [ ] Coverage Calculation funktioniert
- [ ] OU-Hierarchie wird berücksichtigt
- [ ] Security Filtering wird berücksichtigt
- [ ] WMI Filter wird berücksichtigt
- [ ] Simulation für einzelne Computer

---

## Issue #10: GPO Filter Checker

### Metadata
```
Title: [Feature] GPO Filter Checker - WMI & Security Filter Analysis (gpo_filter_checker)
Labels: type:feature, priority:medium, status:backlog, component:tools
Milestone: v0.8.0 - AD Audit Capabilities
Estimate: 2 days
```

### Beschreibung

**Was ist das Tool?**
Analysiert WMI Filter und Security Filtering von GPOs. Findet Filter die unbeabsichtigt Computer ausschließen.

**Warum brauchen wir das?**
- WMI Filter "OS = Windows 10" schließt Windows 11 aus
- Security Filtering ohne "Authenticated Users" blockiert GPO
- Komplexe Filter die niemand versteht

### Requirements

#### Credentials
| Level | Funktionsumfang |
|-------|-----------------|
| **Domain User** | Vollständig |

### Architektur

```python
# tools/audit/gpo/gpo_filter_checker.py

@dataclass
class WMIFilter:
    """WMI Filter Objekt"""
    name: str
    query: str                   # WQL Query
    affected_gpos: List[str]

@dataclass
class FilterIssue:
    """Gefundenes Filter-Problem"""
    gpo_name: str
    filter_type: str             # WMI | Security
    issue: str                   # Beschreibung des Problems
    affected_computers: List[str]
    severity: str

class GPOFilterChecker:
    """
    Analysiert GPO Filter (WMI und Security).

    Requires: Domain User
    """

    def analyze_wmi_filters(self) -> List[WMIFilter]:
        """
        Listet alle WMI Filter und deren Queries auf.
        """
        pass

    def find_problematic_wmi_filters(self) -> List[FilterIssue]:
        """
        Findet WMI Filter die problematisch sein könnten.

        - Veraltete OS Versionen
        - Zu restriktive Queries
        - Syntax-Fehler
        """
        pass

    def analyze_security_filtering(self, gpo_name: str) -> dict:
        """
        Analysiert Security Filtering einer GPO.

        Prüft:
        - Wer hat "Read" Permission? (nötig für Apply)
        - Wer hat "Apply Group Policy" Permission?
        - Fehlt "Authenticated Users"?
        """
        pass

    def find_security_filter_issues(self) -> List[FilterIssue]:
        """
        Findet GPOs mit problematischem Security Filtering.

        - "Authenticated Users" entfernt aber kein Ersatz
        - Computer-Objekte haben kein Read
        - Widersprüchliche Permissions
        """
        pass
```

### Verification

```bash
python cli.py gpo filters analyze

# Output:
# GPO Filter Analysis
# ═══════════════════
#
# WMI Filters:
# ─────────────────────────────────────
# "Windows 10 Only"
#   Query: SELECT * FROM Win32_OperatingSystem WHERE Version LIKE "10.%"
#   Used by: Security Baseline, Office Settings
#   ⚠️ Issue: Does NOT match Windows 11!
#
# Security Filtering Issues:
# ─────────────────────────────────────
# "Security Baseline"
#   ⚠️ "Authenticated Users" removed
#   Only "Domain Computers" has Read
#   Issue: New computers not in group won't get GPO!
```

### Definition of Done
- [ ] WMI Filter Enumeration
- [ ] WMI Query Analyse (veraltete OS Checks)
- [ ] Security Filtering Analyse
- [ ] Missing "Authenticated Users" Detection
- [ ] Empfehlungen für Fixes

---

# COMPLIANCE TOOLS

---

## Issue #11: Password Policy Auditor

### Metadata
```
Title: [Feature] Password Policy Auditor (password_policy_auditor)
Labels: type:feature, priority:medium, status:backlog, component:tools
Milestone: v0.8.0 - AD Audit Capabilities
Estimate: 1-2 days
```

### Beschreibung

**Was ist das Tool?**
Liest die effektive Password Policy aus und vergleicht sie mit Best Practices / Compliance-Anforderungen.

**Warum brauchen wir das?**
- Basis-Check für jedes AD Assessment
- Vergleich mit NIST 800-63B, CIS Benchmark
- Fine-Grained Password Policies berücksichtigen

### Requirements

#### Credentials
| Level | Funktionsumfang |
|-------|-----------------|
| **Domain User** | Domain-weite Default Policy lesen |
| **Domain User** | Fine-Grained Policies auflisten |

### Architektur

```python
# tools/audit/ad/password_policy_auditor.py

@dataclass
class PasswordPolicy:
    """Password Policy Settings"""
    name: str                    # "Default Domain Policy" oder FGPP Name
    min_length: int
    complexity_enabled: bool
    history_count: int           # Wie viele alte Passwörter gespeichert
    max_age_days: int
    min_age_days: int
    lockout_threshold: int
    lockout_duration_minutes: int
    lockout_observation_window: int
    applies_to: List[str]        # Für FGPP: Welche User/Groups

@dataclass
class PolicyCompliance:
    """Vergleich mit Best Practices"""
    policy: PasswordPolicy
    nist_compliant: bool
    cis_compliant: bool
    issues: List[str]            # Gefundene Probleme
    recommendations: List[str]

class PasswordPolicyAuditor:
    """
    Auditiert Password Policies gegen Best Practices.

    Requires: Domain User
    """

    def get_default_policy(self) -> PasswordPolicy:
        """
        Liest Default Domain Password Policy.

        Via LDAP: Domain Root Objekt → pwd* Attribute
        """
        pass

    def get_fine_grained_policies(self) -> List[PasswordPolicy]:
        """
        Liest alle Fine-Grained Password Policies (FGPP).

        Container: CN=Password Settings Container,CN=System,...
        """
        pass

    def check_compliance(self,
                        policy: PasswordPolicy,
                        standard: str = "nist") -> PolicyCompliance:
        """
        Prüft Policy gegen Standard.

        Standards:
        - "nist": NIST 800-63B (modern, längere Passwörter, keine Rotation)
        - "cis": CIS Benchmark (traditionell, komplexität, 90-Tage Rotation)
        - "pci": PCI-DSS Requirements
        """
        pass
```

### Verification

```bash
python cli.py password-policy audit \
    --dc 192.168.56.10 \
    --domain north.sevenkingdoms.local

# Output:
# Password Policy Audit
# ═════════════════════
#
# Default Domain Policy:
# ─────────────────────────────────────
# Minimum Length:     8 characters
# Complexity:         Required
# History:            24 passwords
# Max Age:            90 days
# Lockout Threshold:  5 attempts
# Lockout Duration:   30 minutes
#
# NIST 800-63B Compliance: PARTIAL ⚠️
# - ✓ Minimum 8 characters
# - ⚠️ 90-day rotation not recommended by NIST (use 0 for no expiry)
# - ⚠️ Complexity rules may lead to weaker passwords
#
# CIS Benchmark Compliance: PASS ✓
# - ✓ All requirements met
#
# Fine-Grained Policies:
# ─────────────────────────────────────
# "Admin Password Policy" (applies to: Domain Admins)
#   Length: 16, Complexity: Yes, Max Age: 30 days
#   ✓ Stronger than default for privileged accounts
```

### Definition of Done
- [ ] Default Policy auslesen
- [ ] FGPP auslesen
- [ ] NIST Compliance Check
- [ ] CIS Compliance Check
- [ ] Klare Empfehlungen

---

## Issue #12: Firewall Policy Auditor

### Metadata
```
Title: [Feature] Windows Firewall Policy Auditor (firewall_auditor)
Labels: type:feature, priority:medium, status:backlog, component:tools
Milestone: v0.9.0 - Extended Audit Capabilities
Estimate: 2-3 days
```

### Beschreibung

**Was ist das Tool?**
Prüft Windows Firewall Konfiguration auf Zielsystemen. Vergleicht GPO-Konfiguration mit tatsächlichem Status.

### Requirements

#### Credentials
| Level | Funktionsumfang |
|-------|-----------------|
| **Local Admin** | Vollständig (Remote WMI/Registry) |

### Architektur

```python
# tools/audit/windows/firewall_auditor.py

@dataclass
class FirewallProfile:
    """Ein Firewall-Profil (Domain/Private/Public)"""
    name: str                    # Domain, Private, Public
    enabled: bool
    default_inbound: str         # Block, Allow
    default_outbound: str
    log_dropped: bool
    log_successful: bool

@dataclass
class FirewallAuditResult:
    """Firewall Audit Ergebnis"""
    target: str
    profiles: List[FirewallProfile]
    all_enabled: bool
    issues: List[str]
    gpo_matches_reality: bool

class FirewallAuditor:
    """
    Auditiert Windows Firewall Status.

    Requires: Local Admin on target
    """

    def audit_single(self, target: str,
                     username: str, password: str) -> FirewallAuditResult:
        """
        Prüft Firewall Status via Remote Registry/WMI.

        netsh advfirewall show allprofiles
        """
        pass
```

### Definition of Done
- [ ] Alle drei Profile prüfen
- [ ] Vergleich mit GPO-Konfiguration
- [ ] Rule Analysis (wichtige Ports)
- [ ] Logging Status

---

## Issue #13: BitLocker Status Auditor

### Metadata
```
Title: [Feature] BitLocker Status Auditor (bitlocker_auditor)
Labels: type:feature, priority:medium, status:backlog, component:tools
Milestone: v0.9.0 - Extended Audit Capabilities
Estimate: 2 days
```

### Beschreibung

**Was ist das Tool?**
Prüft ob BitLocker auf Zielsystemen aktiviert ist und ob Recovery Keys in AD gespeichert werden.

### Requirements

#### Credentials
| Level | Funktionsumfang |
|-------|-----------------|
| **Local Admin** | Status auf einzelnem System |
| **Domain Admin** | Recovery Keys aus AD lesen |

### Architektur

```python
# tools/audit/windows/bitlocker_auditor.py

@dataclass
class BitLockerStatus:
    """BitLocker Status eines Systems"""
    target: str
    volume: str                  # C:, D:, etc.
    protection_status: str       # On, Off, Suspended
    encryption_percentage: int
    encryption_method: str       # AES-128, AES-256, XTS-AES-128
    key_protectors: List[str]    # TPM, PIN, RecoveryKey, etc.
    recovery_key_in_ad: bool

class BitLockerAuditor:
    """
    Auditiert BitLocker Deployment.

    Requires: Local Admin (Status), Domain Admin (Recovery Keys)
    """

    def check_status(self, target: str,
                     username: str, password: str) -> BitLockerStatus:
        """
        Prüft BitLocker Status via WMI.

        manage-bde -status C:
        """
        pass

    def check_recovery_keys_in_ad(self) -> List[tuple]:
        """
        Prüft ob Recovery Keys in AD gespeichert sind.

        LDAP Query auf msFVE-RecoveryPassword Attribut
        """
        pass
```

### Definition of Done
- [ ] Status auf einzelnem System
- [ ] Bulk-Check über mehrere Systeme
- [ ] Recovery Key AD-Check
- [ ] Encryption Method Bewertung

---

# IMPLEMENTATION ORDER

## Empfohlene Reihenfolge

```
Phase 1: Foundation (2-3 Wochen)
├── Issue #1: gpo_enum (LDAP Basis)
├── Issue #3: smb_signing_check (Keine Creds nötig)
└── Issue #4: protocol_detector (LLMNR/NBT-NS)

Phase 2: Credential Checks (2 Wochen)
├── Issue #5: wdigest_check
├── Issue #6: credguard_check
└── Issue #7: laps_auditor

Phase 3: GPO Deep Dive (2 Wochen)
├── Issue #2: sysvol_parser (GPP Credentials!)
├── Issue #8: gpo_link_analyzer
├── Issue #9: gpo_scope_validator
└── Issue #10: gpo_filter_checker

Phase 4: Compliance (1-2 Wochen)
├── Issue #11: password_policy_auditor
├── Issue #12: firewall_auditor
└── Issue #13: bitlocker_auditor
```

## Dependencies Graph

```
gpo_enum (LDAP) ─────┬─→ gpo_link_analyzer
                     ├─→ gpo_scope_validator
                     ├─→ gpo_filter_checker
                     └─→ sysvol_parser

smb_signing_check ─────→ (standalone)

protocol_detector ─────→ (standalone)

wdigest_check ────────┬─→ (needs impacket)
credguard_check ──────┤
laps_auditor ─────────┘

password_policy_auditor → (uses gpo_enum LDAP)
```

---

# LABELS FÜR ISSUES

```
# Type Labels
type:feature
type:bug
type:docs
type:refactor

# Priority Labels
priority:critical    # SMB Signing, LLMNR (Sofort exploitierbar)
priority:high        # WDigest, LAPS (Credential Access)
priority:medium      # Compliance Checks
priority:low         # Nice-to-have

# Component Labels
component:tools
component:agent
component:cli

# Attack Phase Labels
attack-phase:reconnaissance
attack-phase:initial-access
attack-phase:credential-access
attack-phase:lateral-movement
attack-phase:privilege-escalation

# Status Labels
status:backlog
status:ready
status:in-progress
status:review
status:blocked
```
