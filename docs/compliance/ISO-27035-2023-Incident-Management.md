# ISO/IEC 27035:2023 - Information Security Incident Management

**Stand:** Januar 2026
**Quelle:** [ISO Official](https://www.iso.org/standard/78973.html), [ANSI Blog](https://blog.ansi.org/ansi/iso-iec-27035-1-2023-information-security-management/)
**Version:** 2023 (Parts 1-3)

---

## Übersicht

ISO/IEC 27035 ist die internationale Norm für Information Security Incident Management. Die Norm besteht aus drei Teilen und bietet einen strukturierten Ansatz für die Vorbereitung, Erkennung, Meldung, Bewertung und Reaktion auf Sicherheitsvorfälle.

### Die drei Teile

| Teil | Titel | Inhalt |
|------|-------|--------|
| **ISO/IEC 27035-1:2023** | Principles and Process | Grundkonzepte, Prinzipien und Prozess |
| **ISO/IEC 27035-2:2023** | Guidelines to Plan and Prepare | Planung und Vorbereitung |
| **ISO/IEC 27035-3:2020** | Guidelines for ICT Incident Response Operations | ICT Incident Response Operations |

---

## Die 5 Phasen des Incident Managements

### Phase 1: Preparation & Planning (Vorbereitung)
**Zweck:** Etablierung von Richtlinien, Zuweisung von Verantwortlichkeiten und Einrichtung notwendiger Tools.

**Aktivitäten:**
- Incident Response Policy erstellen
- Incident Response Team (IRT/CSIRT) aufbauen
- Rollen und Verantwortlichkeiten definieren
- Kommunikationswege festlegen
- Tools und Ressourcen bereitstellen
- Schulungen durchführen
- Playbooks erstellen

**Dokumentation:**
- Incident Response Plan
- Eskalationsmatrix
- Kontaktlisten
- Playbooks pro Incident-Typ

---

### Phase 2: Detection & Reporting (Erkennung und Meldung)
**Zweck:** Identifizierung und Dokumentation potenzieller Sicherheitsereignisse.

**Aktivitäten:**
- Monitoring von Sicherheitsereignissen
- Log-Analyse
- Anomalie-Erkennung
- Meldung durch Mitarbeiter
- Automatische Alerts (SIEM, EDR)
- Erste Dokumentation

**Quellen:**
- SIEM-Alerts
- IDS/IPS
- EDR/XDR
- User Reports
- External Intelligence
- Vulnerability Scans

---

### Phase 3: Assessment & Decision (Bewertung und Entscheidung)
**Zweck:** Evaluierung der Schwere des Vorfalls und Bestimmung angemessener Reaktionsmaßnahmen.

**Aktivitäten:**
- Verifizierung des Vorfalls (True Positive?)
- Klassifizierung nach Schweregrad
- Impact-Analyse
- Priorisierung
- Entscheidung über Eskalation
- Aktivierung des Response Teams

**Klassifizierung (Beispiel):**

| Schweregrad | Beschreibung | Reaktionszeit |
|-------------|--------------|---------------|
| **Critical** | Vollständige Systemkompromittierung, Ransomware aktiv | Sofort |
| **High** | Aktive Bedrohung, Datenleck möglich | < 4 Stunden |
| **Medium** | Verdächtige Aktivität, begrenzte Auswirkung | < 24 Stunden |
| **Low** | Geringfügiges Ereignis, keine unmittelbare Gefahr | < 72 Stunden |

---

### Phase 4: Response & Recovery (Reaktion und Wiederherstellung)
**Zweck:** Ausführung technischer und prozeduraler Maßnahmen zur Eindämmung und Behebung.

**Aktivitäten:**

**Containment (Eindämmung):**
- Isolation betroffener Systeme
- Netzwerksegmentierung
- Account-Sperrung
- Blockierung von IoCs

**Eradication (Beseitigung):**
- Malware-Entfernung
- Patching von Schwachstellen
- Credential-Reset
- System-Reimaging

**Recovery (Wiederherstellung):**
- System-Wiederherstellung
- Daten-Restore aus Backup
- Service-Wiederaufnahme
- Monitoring verstärken

---

### Phase 5: Lessons Learned (Erkenntnisse)
**Zweck:** Lernen aus dem Vorfall zur Verbesserung der zukünftigen Reaktionsfähigkeit.

**Aktivitäten:**
- Post-Incident Review
- Root Cause Analysis
- Timeline-Rekonstruktion
- Dokumentation der Lessons Learned
- Update von Playbooks
- Verbesserungsmaßnahmen implementieren
- Management-Bericht

**Dokumentation:**
- Incident Report
- Timeline
- Root Cause Analysis
- Improvement Actions
- Metrics (MTTD, MTTR)

---

## Incident Response Team (IRT/CSIRT)

### Rollen

| Rolle | Verantwortlichkeiten |
|-------|---------------------|
| **Incident Manager** | Gesamtkoordination, Entscheidungen, Kommunikation |
| **Technical Lead** | Technische Analyse und Reaktion |
| **Forensic Analyst** | Beweissicherung, Analyse |
| **Communications Lead** | Interne/externe Kommunikation |
| **Legal Counsel** | Rechtliche Beratung |
| **HR Representative** | Personalangelegenheiten (Insider) |

### RACI-Matrix

| Aktivität | Incident Mgr | Tech Lead | Forensics | Comms |
|-----------|--------------|-----------|-----------|-------|
| Triage | A | R | C | I |
| Containment | A | R | C | I |
| Forensics | A | C | R | I |
| Communication | R | I | I | A |
| Recovery | A | R | C | I |
| Reporting | R | C | C | A |

---

## Ransomware Incident Response

### Spezifisches Playbook

**Phase 1 - Detection:**
- Anomale Dateiverschlüsselung erkannt
- Ransom Note gefunden
- Ungewöhnliche Prozesse (vssadmin, bcdedit)

**Phase 2 - Assessment:**
- Scope bestimmen (Welche Systeme betroffen?)
- Ransomware-Variante identifizieren
- Backup-Status prüfen
- Exfiltration prüfen (Double Extortion?)

**Phase 3 - Containment:**
- Netzwerk-Isolation (SOFORT!)
- Betroffene Systeme vom Netz trennen
- Backup-Systeme schützen
- Credential-Reset (alle Domain Admins)

**Phase 4 - Eradication:**
- Ransomware-Artefakte identifizieren
- Persistence-Mechanismen entfernen
- Systems reimagen
- KEINE Zahlung ohne Abwägung

**Phase 5 - Recovery:**
- Systeme aus Clean Backups wiederherstellen
- Priorität: Kritische Geschäftsprozesse
- Monitoring verstärken
- Threat Hunting durchführen

**Phase 6 - Lessons Learned:**
- Wie kam der Initial Access?
- Warum wurde Lateral Movement nicht erkannt?
- Waren Backups geschützt?
- Was muss verbessert werden?

---

## Metriken

| Metrik | Beschreibung | Ziel |
|--------|--------------|------|
| **MTTD** | Mean Time to Detect | < 24h |
| **MTTR** | Mean Time to Respond | < 4h |
| **MTTC** | Mean Time to Contain | < 1h |
| **MTTE** | Mean Time to Eradicate | < 48h |
| **Incidents/Month** | Anzahl Vorfälle pro Monat | Tracking |
| **False Positive Rate** | Anteil Fehlalarme | < 20% |

---

## Integration mit anderen Standards

| Standard | Beziehung |
|----------|-----------|
| **ISO 27001** | A.5.24-A.5.28 (Incident Management Controls) |
| **ISO 27002** | Detaillierte Implementierungsguidance |
| **ISO 22301** | Business Continuity bei Major Incidents |
| **ISO 27037** | Digital Evidence (Forensics) |
| **NIS2 Art.21(b)** | Incident Handling Anforderung |

---

## Quellen

- [ISO Official - ISO/IEC 27035-1:2023](https://www.iso.org/standard/78973.html)
- [ISO Official - ISO/IEC 27035-2:2023](https://www.iso.org/standard/78974.html)
- [ANSI Blog - ISO 27035-1:2023](https://blog.ansi.org/ansi/iso-iec-27035-1-2023-information-security-management/)
- [ISO27001Security - ISO 27035](https://www.iso27001security.com/html/27035.html)
