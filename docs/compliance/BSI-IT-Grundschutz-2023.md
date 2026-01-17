# BSI IT-Grundschutz Kompendium Edition 2023

**Stand:** Januar 2026
**Quelle:** [BSI Official](https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/IT-Grundschutz-Kompendium/it-grundschutz-kompendium_node.html)
**Version:** Edition 2023 (aktuell, keine 2024 Edition)

---

## Übersicht

Das BSI IT-Grundschutz-Kompendium ist die deutsche Umsetzung von ISO 27001 und enthält **113 Bausteine** in **10 Themengebieten**. Es ist vollständig kostenlos verfügbar.

### Vorteile gegenüber ISO 27001

| Aspekt | ISO 27001 | BSI IT-Grundschutz |
|--------|-----------|-------------------|
| **Kosten** | ~150-200 CHF | Kostenlos |
| **Sprache** | Englisch | Deutsch |
| **Detailgrad** | Abstrakt | Konkrete Maßnahmen |
| **Zertifizierung** | Weltweit anerkannt | In DE anerkannt, ISO-kompatibel |

---

## Die 10 Schichten (Themengebiete)

### Prozess-Bausteine

| Kürzel | Name | Beschreibung | Anzahl |
|--------|------|--------------|--------|
| **ISMS** | Sicherheitsmanagement | Informationssicherheitsmanagementsystem | 1 |
| **ORP** | Organisation und Personal | Organisatorische und personelle Sicherheit | 5 |
| **CON** | Konzeption und Vorgehensweisen | Sicherheitskonzepte, Kryptographie, Datenschutz | 10 |
| **OPS** | Betrieb | IT-Betrieb, Administration, Outsourcing | 15 |
| **DER** | Detektion und Reaktion | Monitoring, Incident Response, Forensik | 4 |

### System-Bausteine

| Kürzel | Name | Beschreibung | Anzahl |
|--------|------|--------------|--------|
| **APP** | Anwendungen | Office, Groupware, Datenbanken, Webserver | 25 |
| **SYS** | IT-Systeme | Server, Clients, Mobile Devices, VMs | 20 |
| **IND** | Industrielle IT | ICS, SCADA, IoT | 5 |
| **NET** | Netze und Kommunikation | Netzarchitektur, Firewalls, VPN, WLAN | 15 |
| **INF** | Infrastruktur | Gebäude, Rechenzentrum, Verkabelung | 13 |

---

## Ransomware-relevante Bausteine

### Kritische Bausteine für Ransomware-Schutz

| Baustein | Name | Ransomware-Relevanz |
|----------|------|---------------------|
| **ORP.4** | Identitäts- und Berechtigungsmanagement | Credential Protection, Least Privilege |
| **OPS.1.1.2** | Ordnungsgemäße IT-Administration | Privileged Access, Admin-Härtung |
| **OPS.1.1.3** | Patch- und Änderungsmanagement | Vulnerability Management |
| **OPS.1.1.4** | Schutz vor Schadprogrammen | AV, EDR, Application Control |
| **OPS.1.1.5** | Protokollierung | SIEM, Logging, Forensik |
| **OPS.1.1.6** | Software-Tests und -Freigaben | Secure Development |
| **OPS.1.2.5** | Fernwartung | RDP/VPN-Härtung |
| **OPS.2.2** | Cloud-Nutzung | Cloud Security |
| **DER.1** | Detektion von sicherheitsrelevanten Ereignissen | Anomalie-Erkennung |
| **DER.2.1** | Behandlung von Sicherheitsvorfällen | Incident Response |
| **DER.2.2** | Vorsorge für IT-Forensik | Evidence Collection |
| **DER.2.3** | Bereinigung weitreichender Sicherheitsvorfälle | Ransomware Recovery |
| **DER.4** | Notfallmanagement | Business Continuity |
| **CON.3** | Datensicherungskonzept | Backup-Strategie |
| **CON.6** | Löschen und Vernichten | Secure Deletion |
| **NET.1.1** | Netzarchitektur und -design | Segmentierung |
| **NET.3.1** | Router und Switches | Network Hardening |
| **NET.3.2** | Firewall | Perimeter Security |

---

## Mapping: BSI → ISO 27001:2022

| BSI Baustein | ISO 27001 Control | Thema |
|--------------|-------------------|-------|
| **ISMS.1** | 5.1-5.3, 6.1-6.2 | ISMS, Risikomanagement |
| **ORP.1** | A.5.1-A.5.4 | Policies |
| **ORP.2** | A.6.1-A.6.2 | Organisation |
| **ORP.3** | A.6.3 | Awareness |
| **ORP.4** | A.5.15-A.5.18, A.8.2-A.8.5 | Access Control |
| **ORP.5** | A.5.19-A.5.23 | Supplier Relations |
| **CON.1** | A.5.9-A.5.13 | Kryptographie |
| **CON.2** | A.5.31-A.5.36 | Datenschutz |
| **CON.3** | A.8.13 | Backup |
| **OPS.1.1.2** | A.8.2-A.8.5 | Privileged Access |
| **OPS.1.1.3** | A.8.8-A.8.9 | Patch Management |
| **OPS.1.1.4** | A.8.7 | Malware Protection |
| **OPS.1.1.5** | A.8.15-A.8.17 | Logging |
| **DER.1** | A.8.16 | Monitoring |
| **DER.2.1** | A.5.24-A.5.28 | Incident Management |
| **DER.4** | A.5.29-A.5.30 | Business Continuity |
| **NET.1.1** | A.8.20-A.8.22 | Network Security |
| **NET.3.2** | A.8.20-A.8.21 | Firewall |

---

## Mapping: BSI → NIS2 Art. 21(2)

| NIS2 Maßnahme | BSI Bausteine |
|---------------|---------------|
| **(a)** Risikoanalyse | ISMS.1, ORP.1 |
| **(b)** Incident Handling | DER.2.1, DER.2.2, DER.2.3 |
| **(c)** Business Continuity | DER.4, CON.3 |
| **(d)** Supply Chain | ORP.5, OPS.2.2 |
| **(e)** Sichere Beschaffung | OPS.1.1.6, CON.8 |
| **(f)** Wirksamkeitsmessung | DER.3.1 (Audits), DER.3.2 (Pentests) |
| **(g)** Cyber-Hygiene & Training | ORP.3 |
| **(h)** Kryptographie | CON.1 |
| **(i)** HR & Access Control | ORP.2, ORP.4 |
| **(j)** MFA | ORP.4 |

---

## Anforderungsklassen

Jeder Baustein enthält Anforderungen in drei Klassen:

| Klasse | Bezeichnung | Beschreibung |
|--------|-------------|--------------|
| **Basis** | MUSS | Grundlegende Anforderungen, immer umzusetzen |
| **Standard** | SOLLTE | Standard-Anforderungen für normalen Schutzbedarf |
| **Erhöht** | SOLLTE (bei erhöhtem Schutzbedarf) | Zusätzliche Anforderungen |

---

## Download

**Offizielle BSI-Downloads (kostenlos):**
- [IT-Grundschutz-Bausteine PDF (ZIP)](https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/IT-Grundschutz-Kompendium/IT-Grundschutz-Bausteine/Bausteine_Download_Edition_node.html)
- [Kreuzreferenztabellen ISO 27001 (Excel)](https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/IT-Grundschutz-Kompendium/it-grundschutz-kompendium_node.html)

---

## Quellen

- [BSI IT-Grundschutz-Kompendium](https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/IT-Grundschutz-Kompendium/it-grundschutz-kompendium_node.html)
- [BSI IT-Grundschutz-Bausteine Download](https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/IT-Grundschutz-Kompendium/IT-Grundschutz-Bausteine/Bausteine_Download_Edition_node.html)
- [Tenfold Security - BSI IT-Grundschutz Übersicht](https://www.tenfold-security.com/bsi-it-grundschutz/)
