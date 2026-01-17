# ISO/IEC 27017:2015 - Cloud Security Controls

**Stand:** Januar 2026
**Quelle:** [ISO Official](https://www.iso.org/standard/43757.html), [ISMS.online](https://www.isms.online/iso-27017/), [Sprinto](https://sprinto.com/blog/iso-27017/)
**Version:** 2015

---

## Übersicht

ISO/IEC 27017 ist ein Sicherheitsstandard speziell für Cloud-Service-Provider und Cloud-Kunden. Er bietet Cloud-spezifische Implementierungsrichtlinien basierend auf ISO/IEC 27002.

### Vollständiger Titel
**ISO/IEC 27017:2015 - Information technology — Security techniques — Code of practice for information security controls based on ISO/IEC 27002 for cloud services**

### Zweck

- Sicherere Cloud-Umgebungen schaffen
- Cloud-spezifische Risiken adressieren
- Klare Verantwortlichkeiten zwischen Provider und Kunde
- Ergänzung zu ISO 27001/27002

---

## Struktur

ISO/IEC 27017:2015 hat 18 Abschnitte plus einen umfangreichen Annex.

| Abschnitt | Inhalt |
|-----------|--------|
| 1-4 | Einleitung, Scope, Referenzen, Begriffe |
| 5-18 | Cloud-spezifische Guidance zu ISO 27002 Kontrollen |
| Annex A | Zusätzliche Cloud-spezifische Kontrollen |

---

## 7 Neue Cloud-Spezifische Kontrollen

Diese Kontrollen sind **zusätzlich** zu den 114 Kontrollen aus ISO 27002:2013.

### CLD.6.3.1 - Shared Roles and Responsibilities
**Verantwortlichkeiten zwischen Cloud Service Provider (CSP) und Cloud Service Customer (CSC)**

- Klare Dokumentation wer für was verantwortlich ist
- SLA-Definitionen
- Incident Response Verantwortlichkeiten
- Compliance-Zuständigkeiten

### CLD.8.1.5 - Removal/Return of Cloud Service Customer Assets
**Entfernung oder Rückgabe von Assets bei Vertragsende**

- Prozesse für Datenlöschung
- Datenexport-Mechanismen
- Verifizierung der vollständigen Löschung
- Zeitrahmen für Asset-Rückgabe

### CLD.9.5.1 - Segregation in Virtual Computing Environments
**Trennung in virtuellen Umgebungen**

- Isolation zwischen Mandanten (Multi-Tenancy)
- Netzwerksegmentierung in der Cloud
- Ressourcen-Isolation
- Schutz vor Cross-Tenant Attacks

### CLD.9.5.2 - Virtual Machine Hardening
**Härtung virtueller Maschinen**

- Sichere VM-Konfiguration
- Template-Härtung
- Deaktivierung unnötiger Dienste
- Patch-Management für VMs

### CLD.12.1.5 - Administrator's Operational Security
**Betriebssicherheit für Administratoren**

- Privilegierte Zugriffskontrollen
- Admin-Aktivitäten logging
- Separation of Duties
- Just-in-Time Access

### CLD.12.4.5 - Monitoring of Cloud Services
**Überwachung von Cloud-Diensten durch den Kunden**

- Kundenmonitoring-Capabilities
- Zugriff auf Logs
- Alerting und Reporting
- Performance Monitoring

### CLD.13.1.4 - Alignment of Security Management for Virtual and Physical Networks
**Abstimmung der Sicherheit für virtuelle und physische Netzwerke**

- Konsistente Sicherheitsrichtlinien
- Network Security Groups
- Virtual Firewalls
- Verschlüsselung des Netzwerkverkehrs

---

## Cloud-Spezifische Guidance zu ISO 27002 Kontrollen

ISO 27017 erweitert 37 der ISO 27002 Kontrollen mit Cloud-spezifischer Guidance.

### Ausgewählte Cloud-Erweiterungen

| ISO 27002 Control | Cloud-Erweiterung |
|-------------------|-------------------|
| **5.1** Information Security Policies | Cloud-spezifische Richtlinien definieren |
| **6.1** Internal Organization | Cloud-Governance etablieren |
| **8.1** Asset Management | Cloud-Assets inventarisieren |
| **9.1** Access Control | Cloud IAM implementieren |
| **10.1** Cryptography | Cloud Key Management |
| **12.1** Operations Security | Cloud Operations Management |
| **12.3** Backup | Cloud Backup Strategien |
| **13.1** Network Security | Virtual Network Security |
| **14.1** Secure Development | Cloud-native Security |
| **15.1** Supplier Relations | CSP Management |
| **18.1** Compliance | Cloud Compliance Mapping |

---

## Verantwortlichkeitsmodell (Shared Responsibility)

### IaaS (Infrastructure as a Service)

| Bereich | CSP | CSC |
|---------|-----|-----|
| Physical Security | ✓ | |
| Network Infrastructure | ✓ | |
| Hypervisor | ✓ | |
| Virtual Machines | | ✓ |
| Operating Systems | | ✓ |
| Applications | | ✓ |
| Data | | ✓ |

### PaaS (Platform as a Service)

| Bereich | CSP | CSC |
|---------|-----|-----|
| Physical to Runtime | ✓ | |
| Application Configuration | Shared | Shared |
| Data | | ✓ |

### SaaS (Software as a Service)

| Bereich | CSP | CSC |
|---------|-----|-----|
| Physical to Application | ✓ | |
| Configuration | Shared | Shared |
| User Access | | ✓ |
| Data | | ✓ |

---

## Ransomware-Relevanz in der Cloud

### Cloud-Spezifische Ransomware-Risiken

| Risiko | Beschreibung | Kontrolle |
|--------|--------------|-----------|
| **Kompromittierte Cloud Credentials** | Zugang über gestohlene API-Keys | CLD.12.1.5 |
| **Cross-Tenant Attack** | Laterale Bewegung zwischen Mandanten | CLD.9.5.1 |
| **Backup-Verschlüsselung** | Cloud-Backups werden mitverschlüsselt | ISO 27002 12.3 |
| **Shadow IT** | Unbekannte Cloud-Ressourcen | CLD.8.1.5 |
| **Misconfiguration** | Offene Storage Buckets | CLD.9.5.2 |

### Cloud Security Best Practices gegen Ransomware

1. **MFA für alle Cloud-Accounts**
2. **Immutable Backups** (WORM Storage)
3. **Network Segmentation** (VPCs, Security Groups)
4. **Cloud-Native Logging** (CloudTrail, Azure Monitor)
5. **CSPM** (Cloud Security Posture Management)
6. **Just-in-Time Access** für Admin-Rechte
7. **Key Management** (HSM, Key Vault)

---

## Zertifizierung

### Wichtig zu wissen

> ISO 27017 und ISO 27018 sind **keine eigenständigen Zertifizierungsstandards**. Sie werden im Rahmen einer ISO 27001-Zertifizierung als zusätzliche Kontrollen geprüft.

### Audit-Prozess

1. ISO 27001 ISMS muss bestehen
2. Cloud-spezifische Kontrollen aus ISO 27017 implementieren
3. Auditor prüft ISO 27017-Kontrollen während ISO 27001-Audit
4. Zertifikat listet ISO 27017-Konformität

---

## Integration mit anderen Standards

| Standard | Beziehung |
|----------|-----------|
| **ISO 27001** | Basis-ISMS, 27017 als Erweiterung |
| **ISO 27002** | 27017 erweitert 27002 Kontrollen für Cloud |
| **ISO 27018** | Cloud Privacy (komplementär) |
| **CSA STAR** | Cloud Security Alliance Framework |
| **NIS2 Art.21** | Cloud-Nutzung erfordert Security Controls |

---

## Quellen

- [ISO Official - ISO/IEC 27017:2015](https://www.iso.org/standard/43757.html)
- [ISMS.online - ISO 27017](https://www.isms.online/iso-27017/)
- [Sprinto - ISO 27017 Explained](https://sprinto.com/blog/iso-27017/)
- [Microsoft - ISO 27017 Compliance](https://learn.microsoft.com/en-us/compliance/regulatory/offering-iso-27017)
- [AWS - ISO 27017 Compliance](https://aws.amazon.com/compliance/iso-27017-faqs/)
- [Google Cloud - ISO 27017](https://cloud.google.com/security/compliance/iso-27017)
