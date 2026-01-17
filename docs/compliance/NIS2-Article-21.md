# NIS2 Richtlinie Artikel 21 - Vollständige Referenz

**Stand:** Januar 2026
**Quelle:** [NIS 2 Directive Article 21](https://www.nis-2-directive.com/NIS_2_Directive_Article_21.html), [GoodAccess NIS2 Guide](https://www.goodaccess.com/blog/nis2-10-minimum-cybersecurity-risk-management-measures)
**In Kraft seit:** 18. Oktober 2024

---

## Übersicht

Die NIS2-Richtlinie (Network and Information Security Directive 2) ist die EU-weite Rechtsvorschrift zur Cybersicherheit. Artikel 21 definiert die **10 Mindestmaßnahmen** für das Cybersicherheits-Risikomanagement.

### Geltungsbereich

| Kategorie | Sektoren |
|-----------|----------|
| **Wesentliche Einrichtungen** | Energie, Transport, Bankwesen, Gesundheit, Trinkwasser, Abwasser, Digitale Infrastruktur, ICT-Dienstleister, Öffentliche Verwaltung, Raumfahrt |
| **Wichtige Einrichtungen** | Post, Abfallwirtschaft, Chemie, Lebensmittel, Verarbeitendes Gewerbe, Digitale Dienste, Forschung |

### Sanktionen

| Einrichtungstyp | Maximale Geldbuße |
|-----------------|-------------------|
| Wesentliche Einrichtungen | 10 Mio. € oder 2% des weltweiten Jahresumsatzes |
| Wichtige Einrichtungen | 7 Mio. € oder 1,4% des weltweiten Jahresumsatzes |

---

## Artikel 21 - Volltext der 10 Maßnahmen

### Artikel 21 Absatz 1 (Grundsatz)

> Member States shall ensure that essential and important entities take appropriate and proportionate technical, operational and organisational measures to manage the risks posed to the security of network and information systems which those entities use for their operations or for the provision of their services, and to prevent or minimise the impact of incidents on recipients of their services and on other services.

**Übersetzung:** Mitgliedstaaten stellen sicher, dass wesentliche und wichtige Einrichtungen angemessene technische, operative und organisatorische Maßnahmen ergreifen, um Risiken für die Sicherheit von Netz- und Informationssystemen zu beherrschen.

---

### Artikel 21 Absatz 2 (Die 10 Maßnahmen)

> The measures referred to in paragraph 1 shall be based on an all-hazards approach that aims to protect network and information systems and the physical environment of those systems from incidents, and shall include at least the following:

**Übersetzung:** Die Maßnahmen basieren auf einem gefahrenübergreifenden Ansatz und umfassen mindestens folgende Bereiche:

---

## Die 10 Mindestmaßnahmen im Detail

### (a) Policies on Risk Analysis and Information System Security
**Deutsche Bezeichnung:** Konzepte für Risikoanalyse und Sicherheit von Informationssystemen

**Offizielle Formulierung:**
> "policies on risk analysis and information system security"

**Anforderungen:**
- Regelmäßige Risikobewertung der IT- und OT-Infrastruktur
- Identifikation von Schwachstellen und potenziellen Bedrohungen
- Bewertung der Wahrscheinlichkeit von Cyberangriffen
- Dokumentierte Sicherheitsrichtlinien

**Umsetzung:**
- Risk Assessment Framework etablieren
- Asset-Inventar pflegen
- Regelmäßige Risikoüberprüfungen (mindestens jährlich)
- Risikobehandlungsplan entwickeln

**ISO 27001 Mapping:** A.5.1, A.5.8, A.5.9

**Ransomware-Relevanz:**
- Identifikation von Ransomware-Risiken
- Priorisierung von Schutzmaßnahmen

---

### (b) Incident Handling ⭐ IM DOKUMENT
**Deutsche Bezeichnung:** Bewältigung von Sicherheitsvorfällen

**Offizielle Formulierung:**
> "incident handling"

**Anforderungen:**
- Definierter Incident Response Prozess
- Fähigkeit zur Erkennung, Reaktion und Wiederherstellung
- Schnelle und effektive Reaktion auf Cybervorfälle

**Umsetzung:**
- Incident Response Plan erstellen
- CSIRT/SOC etablieren oder beauftragen
- Eskalationsprozesse definieren
- Regelmäßige IR-Übungen durchführen
- Kommunikationsplan für Vorfälle

**ISO 27001 Mapping:** A.5.24, A.5.25, A.5.26, A.5.27, A.5.28

**Ransomware-Relevanz:**
- Conti: 9 Tage unerkannt im Netzwerk
- Schnelle Detection und Response begrenzen Schaden
- Klare Prozesse verhindern Panik

---

### (c) Business Continuity ⭐ IM DOKUMENT
**Deutsche Bezeichnung:** Aufrechterhaltung des Betriebs

**Offizielle Formulierung:**
> "business continuity, such as backup management and disaster recovery, and crisis management"

**Anforderungen:**
- Backup-Management
- Disaster Recovery
- Krisenmanagement
- Aufrechterhaltung des Geschäftsbetriebs

**Umsetzung:**
- Business Continuity Plan (BCP) erstellen
- Disaster Recovery Plan (DRP) erstellen
- 3-2-1-Backup-Strategie implementieren
- Offline/Air-Gapped Backups
- Regelmäßige Recovery-Tests
- Krisenmanagement-Team benennen

**ISO 27001 Mapping:** A.5.29, A.5.30, A.8.13, A.8.14

**Ransomware-Relevanz:**
- 94% der Ransomware-Angriffe zielen auf Backups (ENISA)
- Colonial Pipeline: 4,4 Mio. $ Lösegeld wegen fehlender Backups
- Offline-Backups sind letzte Verteidigungslinie

---

### (d) Supply Chain Security ⭐ IM DOKUMENT
**Deutsche Bezeichnung:** Sicherheit der Lieferkette

**Offizielle Formulierung:**
> "supply chain security, including security-related aspects concerning the relationships between each entity and its direct suppliers or service providers"

**Anforderungen:**
- Berücksichtigung von Lieferanten- und Dienstleister-Risiken
- Bewertung der Gesamtqualität von Produkten und Services
- Prüfung der Cybersicherheitspraktiken von Lieferanten

**Umsetzung:**
- Lieferanten-Risikobewertung
- Sicherheitsanforderungen in Verträgen
- Regelmäßige Audits von kritischen Lieferanten
- Software Bill of Materials (SBOM)
- Monitoring von Lieferanten-Sicherheitsvorfällen

**ISO 27001 Mapping:** A.5.19, A.5.20, A.5.21, A.5.22

**Ransomware-Relevanz:**
- Kaseya (2021): Supply-Chain-Angriff infizierte 1.500+ Unternehmen
- SolarWinds: Kompromittierung über Software-Update
- MSP-Angriffe als Multiplikator

---

### (e) Security in Network and Information Systems ⭐ IM DOKUMENT
**Deutsche Bezeichnung:** Sicherheit bei Erwerb, Entwicklung und Wartung von Netz- und Informationssystemen

**Offizielle Formulierung:**
> "security in network and information systems acquisition, development and maintenance, including vulnerability handling and disclosure"

**Anforderungen:**
- Sicherheit bei Beschaffung
- Sicherheit bei Entwicklung
- Sicherheit bei Wartung
- Schwachstellenmanagement
- Vulnerability Disclosure

**Umsetzung:**
- Secure Development Lifecycle (SDLC)
- Vulnerability Management Programm
- Patch Management
- Responsible Disclosure Policy
- Security Testing (SAST, DAST, Penetration Testing)

**ISO 27001 Mapping:** A.8.8, A.8.25, A.8.26, A.8.27, A.8.28, A.8.29

**Ransomware-Relevanz:**
- Ungepatchte Schwachstellen als Initial Access
- WannaCry: EternalBlue (MS17-010) Exploit
- Regelmäßiges Patching reduziert Angriffsfläche

---

### (f) Effectiveness Assessment ⭐ IM DOKUMENT
**Deutsche Bezeichnung:** Bewertung der Wirksamkeit von Risikomanagementmaßnahmen

**Offizielle Formulierung:**
> "policies and procedures to assess the effectiveness of cybersecurity risk-management measures"

**Anforderungen:**
- Regelmäßige Bewertung der Cybersicherheitsmaßnahmen
- Penetrationstests
- Red-Team-Übungen
- Attack Simulation
- Nachweis gegenüber Aufsichtsbehörden

**Umsetzung:**
- Regelmäßige Penetrationstests (mindestens jährlich)
- Red Team / Purple Team Übungen
- Vulnerability Assessments
- Security Audits
- KPIs für Cybersicherheit definieren
- Continuous Security Monitoring

**ISO 27001 Mapping:** A.5.35, A.5.36, A.8.29

**Ransomware-Relevanz:**
- Attack Simulation prüft Ransomware-Abwehr
- Penetrationstests identifizieren Lateral Movement Pfade
- Nachweis der Wirksamkeit für Versicherung und Behörden

---

### (g) Cyber Hygiene and Training
**Deutsche Bezeichnung:** Grundlegende Cyberhygiene und Schulungen

**Offizielle Formulierung:**
> "basic cyber hygiene practices and cybersecurity training"

**Anforderungen:**
- Security Awareness Training
- Grundlegende Cyberhygiene
- Regelmäßige Schulungen
- Aufbau einer Sicherheitskultur

**Umsetzung:**
- Onboarding-Schulungen für neue Mitarbeiter
- Regelmäßige Awareness-Trainings (mindestens jährlich)
- Phishing-Simulationen
- Rollenspezifische Schulungen
- Dokumentation der Teilnahme

**ISO 27001 Mapping:** A.6.3, A.6.8

**Ransomware-Relevanz:**
- Phishing ist häufigster Initial Access Vektor
- Geschulte Mitarbeiter erkennen Social Engineering
- Reduziert menschliche Fehler
- Meldekultur für verdächtige Aktivitäten

---

### (h) Cryptography and Encryption
**Deutsche Bezeichnung:** Konzepte und Verfahren für Kryptographie und Verschlüsselung

**Offizielle Formulierung:**
> "policies and procedures regarding the use of cryptography and, where appropriate, encryption"

**Anforderungen:**
- Kryptographie-Richtlinien
- Verschlüsselung wo angemessen
- Key Management

**Umsetzung:**
- Verschlüsselung at Rest und in Transit
- TLS 1.3 für Kommunikation
- Festplattenverschlüsselung
- Key Management System
- Regelmäßige Krypto-Reviews
- Ausmusterung unsicherer Algorithmen

**ISO 27001 Mapping:** A.8.24

**Ransomware-Relevanz:**
- SMB Signing verhindert Relay Attacks
- Verschlüsselte Backups schützen vor Manipulation
- Sichere Kommunikation verhindert MITM

---

### (i) Human Resources, Access Control, and Asset Management
**Deutsche Bezeichnung:** Sicherheit des Personals, Zugangskontrollen und Asset-Management

**Offizielle Formulierung:**
> "human resources security, access control policies and asset management"

**Anforderungen:**
- HR-Sicherheit
- Zugangskontrollrichtlinien
- Asset-Management
- Kontrolle für Mitarbeiter mit Zugang zu sensiblen Daten

**Umsetzung:**
- Background Checks für kritische Positionen
- Least Privilege Prinzip
- Access Control Policy
- Asset-Inventar und -Klassifizierung
- Offboarding-Prozesse
- Regelmäßige Access Reviews

**ISO 27001 Mapping:** A.5.9, A.5.10, A.5.11, A.5.15, A.5.18, A.6.1, A.6.2, A.6.5

**Ransomware-Relevanz:**
- Insider Threats
- Kompromittierte Mitarbeiter-Accounts
- Übermäßige Berechtigungen ermöglichen Lateral Movement

---

### (j) Multi-Factor Authentication and Secure Communications ⭐ IM DOKUMENT
**Deutsche Bezeichnung:** Multi-Faktor-Authentifizierung und sichere Kommunikation

**Offizielle Formulierung:**
> "the use of multi-factor authentication or continuous authentication solutions, secured voice, video and text communications and secured emergency communication systems within the entity, where appropriate"

**Anforderungen:**
- Multi-Faktor-Authentifizierung (MFA)
- Continuous Authentication (wo angemessen)
- Sichere Sprach-, Video- und Textkommunikation
- Sichere Notfallkommunikationssysteme

**Umsetzung:**
- MFA für alle Remote-Zugänge
- MFA für privilegierte Accounts
- MFA für Cloud-Dienste
- Phishing-resistente MFA (FIDO2, Hardware-Tokens)
- Ende-zu-Ende-verschlüsselte Kommunikation
- Out-of-Band Kommunikationskanäle für Krisen

**ISO 27001 Mapping:** A.5.17, A.8.5

**Ransomware-Relevanz:**
- Colonial Pipeline: Kein MFA auf VPN
- MFA verhindert 99% der Credential-basierten Angriffe
- Sichere Kommunikation während Incident Response

---

## Artikel 21 Absatz 3 (Verhältnismäßigkeit)

> Member States shall ensure that, when considering which measures referred to in paragraph 2, point (d), are appropriate, entities take into account the vulnerabilities specific to each direct supplier and service provider and the overall quality of products and cybersecurity practices of their suppliers and service providers, including their secure development procedures.

**Übersetzung:** Bei der Bewertung von Lieferkettenrisiken sind die spezifischen Schwachstellen jedes direkten Lieferanten und die Gesamtqualität der Produkte und Cybersicherheitspraktiken zu berücksichtigen.

---

## Artikel 21 Absatz 4 (Europäische Standards)

> Member States shall ensure that an entity that finds that it does not comply with the measures provided for in paragraph 2 takes, without undue delay, all necessary, appropriate and proportionate corrective measures.

**Übersetzung:** Einrichtungen, die feststellen, dass sie die Maßnahmen nicht erfüllen, müssen unverzüglich alle notwendigen Korrekturmaßnahmen ergreifen.

---

## Cross-Reference: NIS2 zu Ransomware-Angriffskette

| Angriffsphase | Relevante NIS2-Maßnahmen |
|---------------|-------------------------|
| **Initial Access** | (a), (g), (j) |
| **Credential Harvesting** | (h), (i), (j) |
| **Lateral Movement** | (i), (e) |
| **Privilege Escalation** | (i) |
| **Persistence** | (e), (f) |
| **Backup Targeting** | (c) |
| **Incident Response** | (b), (c) |
| **Recovery** | (b), (c) |

---

## Cross-Reference: NIS2 zu ISO 27001:2022

| NIS2 Artikel 21(2) | ISO 27001:2022 Annex A |
|--------------------|------------------------|
| (a) Risk Analysis | A.5.1, A.5.8, A.5.9 |
| (b) Incident Handling | A.5.24, A.5.25, A.5.26, A.5.27, A.5.28 |
| (c) Business Continuity | A.5.29, A.5.30, A.8.13, A.8.14 |
| (d) Supply Chain | A.5.19, A.5.20, A.5.21, A.5.22 |
| (e) Network Security | A.8.8, A.8.25, A.8.26, A.8.27, A.8.28, A.8.29 |
| (f) Effectiveness | A.5.35, A.5.36, A.8.29 |
| (g) Cyber Hygiene | A.6.3, A.6.8 |
| (h) Cryptography | A.8.24 |
| (i) HR & Access | A.5.9, A.5.15, A.5.18, A.6.1, A.6.2, A.6.5 |
| (j) MFA & Secure Comms | A.5.17, A.8.5 |

---

## Fristen und Umsetzung

| Datum | Ereignis |
|-------|----------|
| 16. Januar 2023 | NIS2 in Kraft getreten |
| 17. Oktober 2024 | Umsetzungsfrist für Mitgliedstaaten |
| 18. Oktober 2024 | NIS1 aufgehoben, NIS2 gilt |
| Ab 2025 | Erste Prüfungen und Sanktionen möglich |

---

## Quellen

- [NIS 2 Directive Article 21 - Official Text](https://www.nis-2-directive.com/NIS_2_Directive_Article_21.html)
- [GoodAccess - NIS2 10 Minimum Measures](https://www.goodaccess.com/blog/nis2-10-minimum-cybersecurity-risk-management-measures)
- [Advisera - NIS2 Article 21](https://advisera.com/nis2/cybersecurity-risk-management-measures/)
- [Eye Security - NIS2 Articles 21 and 23](https://www.eye.security/blog/nis2-directive-articles-21-23)
- [EU Digital Strategy - NIS2 Directive](https://digital-strategy.ec.europa.eu/en/policies/nis2-directive)
