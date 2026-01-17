# ISO/IEC 27005:2022 - Information Security Risk Management

**Stand:** Januar 2026
**Quelle:** [ISO Official](https://www.iso.org/standard/80585.html), [Secureframe](https://secureframe.com/blog/iso-27005), [ISMS.online](https://www.isms.online/iso-27005/)
**Version:** 4. Edition (Oktober 2022)

---

## Übersicht

ISO/IEC 27005 ist der internationale Standard für das Management von Informationssicherheitsrisiken. Er ist ein Kernbestandteil der ISO/IEC 27000-Familie und unterstützt die Implementierung eines ISMS nach ISO/IEC 27001.

### Zweck

- Strukturierter Ansatz zur Identifikation, Bewertung und Behandlung von Informationssicherheitsrisiken
- Anpassung der allgemeinen Prinzipien von ISO 31000 auf den Kontext der Informationssicherheit
- Abdeckung des vollständigen Risikomanagement-Zyklus

---

## Struktur (10 Klauseln + 1 Annex)

ISO 27005:2022 konsolidiert die 12 Klauseln und 6 Annexe der Version 2018 in 10 Klauseln und einen Annex.

| Klausel | Inhalt |
|---------|--------|
| 1 | Scope |
| 2 | Normative References |
| 3 | Terms and Definitions |
| 4 | Structure of This Document |
| 5 | Information Security Risk Management |
| 6 | Context Establishment |
| 7 | Information Security Risk Assessment |
| 8 | Information Security Risk Treatment |
| 9 | Information Security Risk Communication |
| 10 | Information Security Risk Monitoring and Review |
| Annex A | Examples of Techniques in Support of the Risk Assessment Process |

---

## Der 5-Schritte Risikomanagement-Prozess

### 1. Context Establishment (Kontextfestlegung)
- Definition des Geltungsbereichs
- Festlegung von Risikokriterien
- Identifikation von Stakeholdern

### 2. Risk Identification (Risikoidentifikation)
- Identifikation von Assets und deren Werten
- Identifikation von Bedrohungen
- Identifikation von Schwachstellen
- Identifikation von bestehenden Kontrollen

**Zwei Ansätze:**
| Ansatz | Beschreibung | Fokus |
|--------|--------------|-------|
| **Event-based** | Was sind die Hauptereignisse/Szenarien, die Risiken einführen? | Gesamte Bedrohungslandschaft |
| **Asset-based** | Was sind die Hauptrisiken für jedes Informations-Asset? | Spezifische Assets und Architektur |

### 3. Risk Analysis (Risikoanalyse)
- Bewertung der Wahrscheinlichkeit
- Bewertung der Auswirkungen
- Bestimmung des Risikoniveaus

**Analysetypen:**
- Qualitative Analyse
- Quantitative Analyse
- **Semiquantitative Analyse** (NEU in 2022)

### 4. Risk Evaluation (Risikobewertung)
- Vergleich mit Risikoakzeptanzkriterien
- Priorisierung der Risiken
- Entscheidung über Behandlung

### 5. Risk Treatment (Risikobehandlung)
- **Modify (Mitigate):** Kontrollen implementieren
- **Retain (Accept):** Risiko akzeptieren
- **Avoid:** Aktivität beenden
- **Share (Transfer):** Risiko teilen (z.B. Versicherung)

---

## Änderungen gegenüber ISO 27005:2018

| Bereich | 2018 | 2022 |
|---------|------|------|
| Struktur | 12 Klauseln, 6 Annexe | 10 Klauseln, 1 Annex |
| Terminologie | Eigene Terminologie | Alignment mit ISO 31000:2018 |
| Risikoanalyse | Qualitativ/Quantitativ | + Semiquantitativ |
| Risikoidentifikation | Nur Asset-basiert | Event-basiert + Asset-basiert |
| Risikoszenarien | Nicht vorhanden | NEU: Risikoszenarien-Konzept |
| Alignment | ISO 27001:2013 | ISO 27001:2022 |

---

## Risikokriterien

### Impact-Kriterien
- Finanzielle Auswirkungen
- Reputationsschäden
- Rechtliche Konsequenzen
- Betriebsunterbrechung
- Datenschutzverletzungen

### Likelihood-Kriterien
- Historische Daten
- Bedrohungslandschaft
- Schwachstellenexposition
- Bestehende Kontrollen

### Risikoakzeptanzkriterien
- Risikoappetit der Organisation
- Regulatorische Anforderungen
- Vertragliche Verpflichtungen

---

## Ransomware-Relevanz

### Risikoszenarien für Ransomware

| Szenario | Likelihood | Impact | Risiko |
|----------|------------|--------|--------|
| Initial Access via Phishing | Hoch | Kritisch | Sehr Hoch |
| Lateral Movement via SMB | Hoch | Kritisch | Sehr Hoch |
| Backup-Verschlüsselung | Mittel | Kritisch | Hoch |
| Datenexfiltration (Double Extortion) | Mittel | Kritisch | Hoch |
| Credential Harvesting | Hoch | Hoch | Hoch |

### Risikobewertung Attack Chain

```
Initial Access → Credential Harvesting → Lateral Movement → Escalation → Encryption
    ↓                  ↓                      ↓                ↓            ↓
 [RISK A]          [RISK B]              [RISK C]         [RISK D]     [RISK E]
```

### Behandlungsoptionen

| Risiko | Behandlung | Kontrollen (ISO 27001) |
|--------|------------|------------------------|
| Initial Access | Mitigate | A.6.3 (Training), A.8.7 (Malware) |
| Credential Harvesting | Mitigate | A.5.17 (Auth), A.8.5 (Secure Auth) |
| Lateral Movement | Mitigate | A.8.22 (Segmentation), A.5.15 (Access) |
| Backup-Verschlüsselung | Mitigate | A.8.13 (Backup), A.5.30 (BCM) |
| Restrisiko | Transfer | Cyber-Versicherung |

---

## Integration mit anderen Standards

| Standard | Beziehung zu ISO 27005 |
|----------|------------------------|
| **ISO 27001** | ISO 27005 unterstützt die Risikobewertungsanforderungen von 27001 |
| **ISO 31000** | ISO 27005 passt die allgemeinen Risikomanagement-Prinzipien an |
| **ISO 27002** | Kontrollen zur Risikobehandlung |
| **NIS2 Art.21(a)** | Direkte Abbildung auf Risikoanalyse-Anforderung |

---

## Quellen

- [ISO Official - ISO/IEC 27005:2022](https://www.iso.org/standard/80585.html)
- [Secureframe - ISO 27005 Approach](https://secureframe.com/blog/iso-27005)
- [ISMS.online - ISO 27005](https://www.isms.online/iso-27005/)
- [C-Risk - ISO 27005 Guide](https://www.c-risk.com/blog/iso-27005)
- [Wikipedia - ISO/IEC 27005](https://en.wikipedia.org/wiki/ISO/IEC_27005)
