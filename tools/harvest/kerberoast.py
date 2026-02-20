"""Kerberoasting Checker Tool.

Identifies Kerberoastable service accounts in Active Directory by
requesting Kerberos service tickets (TGS) for accounts with SPNs
and extracting offline-crackable hashes.

Uses impacket's GetUserSPNs logic.

Authorization: active (requests real Kerberos tickets from DC).
"""

import logging
from tools.base import BaseTool
from tools.validation import resolve_and_validate

logger = logging.getLogger(__name__)

try:
    from impacket.krb5.kerberosv5 import getKerberosTGT, getKerberosTGS
    from impacket.krb5 import constants
    from impacket.krb5.types import Principal, KerberosTime
    from impacket.ldap import ldap as impacket_ldap
    from impacket.ldap import ldapasn1 as ldapasn1_impacket

    HAS_IMPACKET = True
except ImportError:
    HAS_IMPACKET = False


class KerberoastTool(BaseTool):
    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "kerberoast"

    @property
    def description(self) -> str:
        return (
            "Identifies Kerberoastable service accounts in Active Directory. "
            "Requests TGS tickets for accounts with SPNs and extracts "
            "offline-crackable hashes. Requires valid domain credentials."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Domain Controller IP or hostname",
                },
                "domain": {
                    "type": "string",
                    "description": "Active Directory domain name (e.g., corp.local)",
                },
                "username": {
                    "type": "string",
                    "description": "Domain username for authentication",
                },
                "password": {
                    "type": "string",
                    "description": "Domain user password",
                },
            },
            "required": ["target", "domain", "username", "password"],
        }

    @property
    def authorization_level(self) -> str:
        return "active"

    @property
    def category(self) -> str:
        return "harvest"

    @property
    def target_fields(self) -> list:
        return ["target", "domain"]

    def execute(self, target: str, domain: str, username: str, password: str) -> str:
        # Type guards
        if not isinstance(target, str):
            return (
                f"Validation error: target must be string, got {type(target).__name__}"
            )
        if not isinstance(domain, str):
            return (
                f"Validation error: domain must be string, got {type(domain).__name__}"
            )
        if not isinstance(username, str):
            return f"Validation error: username must be string, got {type(username).__name__}"
        if not isinstance(password, str):
            return f"Validation error: password must be string, got {type(password).__name__}"

        if not domain.strip():
            return "Validation error: domain must not be empty"
        if not username.strip():
            return "Validation error: username must not be empty"
        if not password.strip():
            return "Validation error: password must not be empty"

        # Dependency check
        if not HAS_IMPACKET:
            return "Error: impacket not installed. Install with: pip install impacket"

        # Target validation
        valid, error, ips = resolve_and_validate(target, allow_public=False)
        if not valid:
            return error

        target_ip = ips[0]

        try:
            return self._enumerate_spns(
                target_ip,
                domain,
                username,
                password,
                getKerberosTGT,
                getKerberosTGS,
                constants,
                Principal,
                KerberosTime,
                impacket_ldap,
                ldapasn1_impacket,
            )
        except Exception as e:
            error_str = str(e)
            if "KDC_ERR_PREAUTH_FAILED" in error_str:
                return f"Error: Authentication failed - invalid credentials for {domain}\\{username}"
            if "KDC_ERR_C_PRINCIPAL_UNKNOWN" in error_str:
                return f"Error: User not found in domain: {domain}\\{username}"
            if "Connection refused" in error_str or "timed out" in error_str:
                return f"Error: Could not connect to Domain Controller {target_ip}"
            return f"Error: Kerberoasting failed: {e}"

    def _enumerate_spns(
        self,
        target_ip,
        domain,
        username,
        password,
        getKerberosTGT,
        getKerberosTGS,
        constants,
        Principal,
        KerberosTime,
        impacket_ldap,
        ldapasn1_impacket,
    ) -> str:
        """Enumerate SPNs via LDAP and request TGS tickets."""

        # Step 1: Get TGT for authentication
        client_principal = Principal(
            username, type=constants.PrincipalNameType.NT_PRINCIPAL.value
        )

        tgt, cipher, old_session_key, session_key = getKerberosTGT(
            client_principal,
            password,
            domain,
            lmhash="",
            nthash="",
            kdcHost=target_ip,
        )

        # Step 2: Query LDAP for accounts with SPNs
        ldap_connection = impacket_ldap.LDAPConnection(
            f"ldap://{target_ip}", f"dc={domain.replace('.', ',dc=')}"
        )
        ldap_connection.login(username, password, domain)

        # Search for user accounts with servicePrincipalName set
        search_filter = (
            "(&(objectCategory=person)(objectClass=user)"
            "(servicePrincipalName=*)"
            "(!(userAccountControl:1.2.840.113556.1.4.803:=2))"  # Not disabled
            "(!(objectCategory=computer)))"  # Exclude machine accounts
        )

        try:
            resp = ldap_connection.search(
                searchFilter=search_filter,
                attributes=[
                    "sAMAccountName",
                    "servicePrincipalName",
                    "memberOf",
                    "pwdLastSet",
                    "lastLogon",
                ],
            )
        except Exception as e:
            return f"Error: LDAP search failed: {e}"

        # Step 3: Parse results and request TGS for each SPN
        spn_accounts = []

        for item in resp:
            if not isinstance(item, ldapasn1_impacket.SearchResultEntry):
                continue

            sam_name = ""
            spns = []
            member_of = []
            pwd_last_set = ""

            for attr in item["attributes"]:
                attr_type = str(attr["type"])
                if attr_type == "sAMAccountName":
                    sam_name = str(attr["vals"][0])
                elif attr_type == "servicePrincipalName":
                    spns = [str(v) for v in attr["vals"]]
                elif attr_type == "memberOf":
                    member_of = [str(v) for v in attr["vals"]]
                elif attr_type == "pwdLastSet":
                    try:
                        pwd_last_set = str(
                            KerberosTime.to_datetime(int(str(attr["vals"][0])))
                        )
                    except Exception:
                        pwd_last_set = str(attr["vals"][0])

            if sam_name and spns:
                # Check if member of privileged groups
                is_admin = any("admin" in group.lower() for group in member_of)

                spn_accounts.append(
                    {
                        "username": sam_name,
                        "spns": spns,
                        "member_of": member_of,
                        "pwd_last_set": pwd_last_set,
                        "is_admin": is_admin,
                    }
                )

        # Build output
        lines = [
            f"[Kerberoasting: {target_ip}]",
            f"[Domain: {domain}]",
            f"[Authenticated as: {domain}\\{username}]",
            "",
        ]

        if not spn_accounts:
            lines.append("No Kerberoastable service accounts found.")
            return "\n".join(lines)

        lines.append(f"Found {len(spn_accounts)} Kerberoastable account(s):")
        lines.append("")

        for account in spn_accounts:
            severity = "critical" if account["is_admin"] else "high"
            admin_flag = " [ADMIN]" if account["is_admin"] else ""

            lines.append(f"  Account: {account['username']}{admin_flag}")
            lines.append(f"  Password Last Set: {account['pwd_last_set']}")
            for spn in account["spns"]:
                lines.append(f"    SPN: {spn}")

            # Try to get TGS hash for first SPN
            try:
                spn_principal = Principal(
                    account["spns"][0],
                    type=constants.PrincipalNameType.NT_SRV_INST.value,
                )
                tgs, cipher_tgs, old_key, new_key = getKerberosTGS(
                    spn_principal,
                    domain,
                    kdcHost=target_ip,
                    tgt=tgt,
                    cipher=cipher,
                    sessionKey=session_key,
                )
                lines.append(f"    TGS Hash: [extracted - {len(tgs)} bytes]")
            except Exception as e:
                lines.append(f"    TGS Hash: [failed: {e}]")

            lines.append("")

            self.report_finding(
                severity=severity,
                title=f"Kerberoastable SPN found: {account['username']}",
                host=target_ip,
                port=88,
                protocol="tcp",
                description=(
                    f"Service account '{account['username']}' has SPNs set and is "
                    f"Kerberoastable. SPNs: {', '.join(account['spns'])}. "
                    f"Password last set: {account['pwd_last_set']}."
                    + (" Account has admin privileges!" if account["is_admin"] else "")
                ),
                remediation=(
                    "Use Managed Service Accounts (gMSA) for service accounts. "
                    "If not possible, use long (25+ char) randomly generated passwords "
                    "and rotate regularly."
                ),
            )

        lines.append(f"Total: {len(spn_accounts)} Kerberoastable account(s) found")

        return "\n".join(lines)
