# ISO 22301:2019 - Business Continuity Management Systems

**Stand:** Januar 2026
**Quelle:** [ISO Official](https://www.iso.org/standard/75106.html), [NQA Implementation Guide](https://www.nqa.com/medialibraries/NQA/NQA-Media-Library/PDFs/NQA-ISO-22301-Implementation-Guide.pdf)
**Version:** 2019 (ersetzt ISO 22301:2012)

---

## Übersicht

ISO 22301 ist der internationale Standard für Business Continuity Management Systems (BCMS). Er bietet einen Rahmen für Organisationen, um sich auf Störungen vorzubereiten, darauf zu reagieren und sich davon zu erholen.

### Vollständiger Titel
**ISO 22301:2019 - Security and resilience — Business continuity management systems — Requirements**

### Zweck

- Schutz vor Störungen
- Reduzierung der Wahrscheinlichkeit von Unterbrechungen
- Sicherstellung der Wiederherstellung nach disruptiven Ereignissen
- Aufrechterhaltung des Geschäftsbetriebs

---

## Struktur (High-Level Structure)

ISO 22301 folgt der Annex SL High-Level Structure, identisch mit ISO 27001, ISO 9001, etc.

| Klausel | Titel | Inhalt |
|---------|-------|--------|
| **4** | Context of the Organization | Organisationskontext, Stakeholder, Scope |
| **5** | Leadership | Management-Commitment, Rollen |
| **6** | Planning | Risiken, Ziele, Planung |
| **7** | Support | Ressourcen, Kompetenz, Kommunikation, Dokumentation |
| **8** | Operation | Business Impact Analysis, Strategie, Pläne |
| **9** | Performance Evaluation | Monitoring, Audit, Management Review |
| **10** | Improvement | Nonconformities, Continuous Improvement |

---

## Kernelemente

### Business Impact Analysis (BIA)

**Zweck:** Identifikation kritischer Geschäftsprozesse und deren Abhängigkeiten.

**Schritte:**
1. Identifikation aller Geschäftsprozesse
2. Bewertung der Kritikalität
3. Bestimmung der maximalen Ausfalltoleranz
4. Identifikation von Abhängigkeiten (IT, Personal, Lieferanten)
5. Festlegung von Recovery-Zielen

**Schlüsselmetriken:**

| Metrik | Beschreibung |
|--------|--------------|
| **RTO** | Recovery Time Objective - Maximale Zeit bis zur Wiederherstellung |
| **RPO** | Recovery Point Objective - Maximaler akzeptabler Datenverlust |
| **MTPD** | Maximum Tolerable Period of Disruption |
| **MBCO** | Minimum Business Continuity Objective |

---

### Business Continuity Strategie

**Strategieoptionen:**

| Option | Beschreibung | Kosten | RTO |
|--------|--------------|--------|-----|
| **Hot Site** | Sofort einsatzbereit, gespiegelt | Hoch | Minuten |
| **Warm Site** | Hardware bereit, Daten müssen geladen werden | Mittel | Stunden |
| **Cold Site** | Räumlichkeiten bereit, keine Hardware | Niedrig | Tage |
| **Cloud DR** | Cloud-basierte Disaster Recovery | Variabel | Minuten-Stunden |
| **Reciprocal** | Gegenseitige Unterstützung mit Partnerunternehmen | Niedrig | Variabel |

---

### Business Continuity Plan (BCP)

**Inhalt:**
- Aktivierungskriterien
- Eskalationsprozeduren
- Rollen und Verantwortlichkeiten
- Kommunikationspläne
- Recovery-Prozeduren
- Ressourcenanforderungen
- Kontaktlisten

**Plantypen:**

| Plan | Fokus |
|------|-------|
| **Incident Response Plan** | Erste Reaktion auf Störung |
| **Crisis Management Plan** | Übergeordnete Krisensteuerung |
| **Business Continuity Plan** | Aufrechterhaltung des Betriebs |
| **Disaster Recovery Plan** | IT-Wiederherstellung |
| **Communication Plan** | Interne/externe Kommunikation |

---

## Klausel 8: Operation (Kernkapitel)

### 8.1 Operational Planning and Control
- Planung der BC-Aktivitäten
- Festlegung von Kriterien für Prozesse
- Kontrolle geplanter Änderungen

### 8.2 Business Impact Analysis and Risk Assessment
- Durchführung der BIA
- Risikoanalyse für BC
- Dokumentation der Ergebnisse

### 8.3 Business Continuity Strategy
- Entwicklung von BC-Strategien
- Bestimmung von Recovery-Optionen
- Ressourcenplanung

### 8.4 Business Continuity Plans and Procedures
- Erstellung der BC-Pläne
- Dokumentation der Verfahren
- Kommunikationsstrukturen

### 8.5 Exercise Programme
- Planung von Übungen
- Durchführung von Tests
- Bewertung und Verbesserung

---

## Übungsprogramm

### Übungstypen

| Typ | Beschreibung | Häufigkeit |
|-----|--------------|------------|
| **Tabletop** | Theoretische Durchsprache | Quartalsweise |
| **Walkthrough** | Schritt-für-Schritt-Durchgang | Halbjährlich |
| **Simulation** | Realistische Simulation | Jährlich |
| **Full-Scale** | Vollständiger Test mit Failover | Alle 2 Jahre |

### Übungsszenarien für Ransomware

1. **Szenario:** Ransomware verschlüsselt File-Server
   - Entdeckung und Meldung
   - Aktivierung des IR-Teams
   - Isolation und Assessment
   - Wiederherstellung aus Backup

2. **Szenario:** Double Extortion mit Datenabfluss
   - Kommunikation mit Angreifern?
   - Behördenmeldung
   - PR-Krise managen
   - Rechtliche Schritte

3. **Szenario:** Backup-Systeme kompromittiert
   - Alternativen identifizieren
   - Offline-Backups lokalisieren
   - Wiederaufbau ohne Backups

---

## Ransomware-Relevanz

### Warum ISO 22301 bei Ransomware?

| Aspekt | Relevanz |
|--------|----------|
| **BIA** | Identifiziert kritische Systeme für Priorisierung |
| **RTO/RPO** | Definiert akzeptable Recovery-Zeiten |
| **Backup-Strategie** | Strukturierte Backup-Anforderungen |
| **Krisenmanagement** | Koordination während Ransomware-Angriff |
| **Kommunikation** | Interne/externe Krisenkommunikation |
| **Übungen** | Vorbereitung auf Ransomware-Szenario |

### Ransomware Recovery-Prioritäten

1. **Kritische Infrastruktur:** Active Directory, DNS, DHCP
2. **Geschäftskritische Systeme:** ERP, CRM, E-Mail
3. **Operative Systeme:** File-Server, Datenbanken
4. **Unterstützende Systeme:** Drucker, sekundäre Anwendungen

---

## Änderungen 2019 vs. 2012

| Bereich | 2012 | 2019 |
|---------|------|------|
| Fokus | Prescriptive | Mehr Flexibilität |
| Klausel 8 | Allgemein | Disziplin-spezifische Guidelines |
| Terminologie | BS 25999 basiert | Modernisiert |
| Integration | Standalone | Bessere Integration mit ISO 27001 |
| Fail Safety | Weniger Fokus | Stärkerer Fokus |

---

## Integration mit anderen Standards

| Standard | Integration mit ISO 22301 |
|----------|--------------------------|
| **ISO 27001** | ISMS + BCMS = Resilienz |
| **ISO 27035** | Incident Management als Input für BC |
| **ISO 31000** | Risikomanagement-Framework |
| **ISO 27005** | Sicherheitsrisiken als BC-Input |
| **NIS2 Art.21(c)** | Direkte Abbildung auf Business Continuity |

---

## Quellen

- [ISO Official - ISO 22301:2019](https://www.iso.org/standard/75106.html)
- [NQA - ISO 22301 Implementation Guide](https://www.nqa.com/medialibraries/NQA/NQA-Media-Library/PDFs/NQA-ISO-22301-Implementation-Guide.pdf)
- [Advisera - What is ISO 22301](https://advisera.com/27001academy/what-is-iso-22301/)
- [Wikipedia - ISO 22301](https://en.wikipedia.org/wiki/ISO_22301)
- [AWS - ISO 22301 Compliance](https://aws.amazon.com/compliance/iso-22301-faqs/)
