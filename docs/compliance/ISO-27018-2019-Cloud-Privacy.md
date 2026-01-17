# ISO/IEC 27018:2019 - Protection of PII in Public Clouds

**Stand:** Januar 2026
**Quelle:** [ISO Official](https://www.iso.org/standard/76559.html), [ISMS.online](https://www.isms.online/iso-27018/), [AWS](https://aws.amazon.com/compliance/iso-27018-faqs/)
**Version:** 2019

---

## Übersicht

ISO/IEC 27018 ist der erste internationale Standard zum Schutz personenbezogener Daten (PII) in öffentlichen Cloud-Umgebungen. Er bietet Guidelines für Cloud-Service-Provider, die als PII-Prozessoren agieren.

### Vollständiger Titel
**ISO/IEC 27018:2019 - Information technology — Security techniques — Code of practice for protection of personally identifiable information (PII) in public clouds acting as PII processors**

### Zweck

- Schutz personenbezogener Daten in der Cloud
- Transparenz bei der Datenverarbeitung
- Verantwortlichkeit für PII-Verarbeitung
- Einhaltung von Datenschutzvorschriften (GDPR, etc.)

---

## Schlüsselprinzipien

### 1. Consent and Choice (Einwilligung und Auswahl)
- Verarbeitung nur mit Zustimmung des PII-Principals
- Transparenz über Verarbeitungszwecke
- Opt-out Möglichkeiten

### 2. Purpose Legitimacy and Specification (Zweckbindung)
- Datenverarbeitung nur für definierte Zwecke
- Keine Zweckänderung ohne Zustimmung
- Dokumentierte Verarbeitungszwecke

### 3. Collection Limitation (Datenminimierung)
- Nur notwendige Daten sammeln
- Keine übermäßige Datenerfassung
- Begründung für jede Datensammlung

### 4. Data Minimization (Datensparsamkeit)
- Minimale Datenmenge speichern
- Regelmäßige Überprüfung
- Löschung nach Zweckerfüllung

### 5. Use, Retention, and Disclosure Limitation (Nutzungsbeschränkung)
- Beschränkte Nutzung auf definierten Zweck
- Aufbewahrungsfristen definieren
- Kontrollierte Weitergabe

### 6. Accuracy and Quality (Richtigkeit)
- Datenqualität sicherstellen
- Aktualisierungsmöglichkeiten
- Korrekturmechanismen

### 7. Openness, Transparency, and Notice (Transparenz)
- Offene Kommunikation über Datenverarbeitung
- Datenschutzerklärungen
- Benachrichtigung bei Änderungen

### 8. Individual Participation and Access (Betroffenenrechte)
- Auskunftsrecht
- Berichtigungsrecht
- Löschungsrecht
- Datenportabilität

### 9. Accountability (Rechenschaftspflicht)
- Nachweisbare Compliance
- Dokumentation aller Verarbeitungen
- Regelmäßige Audits

### 10. Information Security (Informationssicherheit)
- Technische Schutzmaßnahmen
- Organisatorische Maßnahmen
- Incident Response für Datenpannen

### 11. Privacy Compliance (Datenschutz-Compliance)
- Einhaltung anwendbarer Gesetze
- Regulatorische Updates überwachen
- Compliance-Nachweise

---

## Privacy-Spezifische Kontrollen

ISO 27018 ergänzt ISO 27002 um ca. 25-30 privacy-spezifische Kontrollen.

### Ausgewählte Kontrollen

| Bereich | Kontrolle |
|---------|-----------|
| **Consent** | PII nur mit dokumentierter Einwilligung verarbeiten |
| **Deletion** | Sichere und vollständige Löschung auf Anfrage |
| **Transparency** | Offenlegung aller Subprozessoren |
| **Breach Notification** | Unverzügliche Benachrichtigung bei Datenpannen |
| **Data Location** | Transparenz über Speicherorte |
| **Subprocessors** | Kontrolle über Unterauftragsverarbeiter |
| **Government Access** | Benachrichtigung bei behördlichen Anfragen |

---

## Anforderungen an Cloud Service Provider

### Vertragliche Anforderungen

| Anforderung | Beschreibung |
|-------------|--------------|
| **Processing Agreement** | Dokumentierte Verarbeitungsvereinbarung |
| **Purpose Limitation** | Verarbeitung nur gemäß Auftrag |
| **Subcontractor Control** | Kontrolle über Subunternehmer |
| **Audit Rights** | Auditmöglichkeiten für Kunden |
| **Data Return** | Rückgabe/Löschung bei Vertragsende |

### Technische Anforderungen

| Anforderung | Beschreibung |
|-------------|--------------|
| **Encryption** | Verschlüsselung at Rest und in Transit |
| **Access Control** | Strenge Zugriffskontrollen |
| **Logging** | Protokollierung aller PII-Zugriffe |
| **Isolation** | Mandantentrennung |
| **Backup** | Sichere Backup-Verfahren |

### Organisatorische Anforderungen

| Anforderung | Beschreibung |
|-------------|--------------|
| **Staff Training** | Datenschutzschulungen |
| **Confidentiality** | Vertraulichkeitsverpflichtungen |
| **Incident Response** | Verfahren für Datenpannen |
| **Documentation** | Vollständige Dokumentation |

---

## GDPR-Alignment

ISO 27018 unterstützt die Einhaltung der DSGVO.

| GDPR-Artikel | ISO 27018 Abdeckung |
|--------------|---------------------|
| **Art. 5** - Grundsätze | Prinzipien 1-11 |
| **Art. 6** - Rechtmäßigkeit | Consent-Kontrollen |
| **Art. 17** - Löschung | Deletion-Kontrollen |
| **Art. 28** - Auftragsverarbeiter | Provider-Anforderungen |
| **Art. 32** - Sicherheit | Security Controls |
| **Art. 33/34** - Datenpannen | Breach Notification |

---

## Ransomware-Relevanz

### PII-Risiken bei Ransomware

| Risiko | Beschreibung | Kontrolle |
|--------|--------------|-----------|
| **Data Exfiltration** | PII wird vor Verschlüsselung gestohlen | DLP, Monitoring |
| **Double Extortion** | Drohung der Veröffentlichung | Encryption, Access Control |
| **Breach Notification** | Meldepflicht bei PII-Kompromittierung | Incident Response |
| **Data Loss** | PII-Verlust ohne Backup | Backup, Recovery |
| **Compliance Failure** | GDPR-Strafen zusätzlich zu Ransomware-Schaden | Compliance-Programm |

### PII Protection Best Practices

1. **Data Classification**: PII identifizieren und klassifizieren
2. **Encryption**: PII immer verschlüsseln
3. **Access Logging**: Alle PII-Zugriffe protokollieren
4. **DLP**: Data Loss Prevention implementieren
5. **Backup**: PII-Backups verschlüsselt und offline
6. **Incident Plan**: Spezifischer Plan für PII-Breaches
7. **Testing**: Regelmäßige Breach-Response-Übungen

---

## Zertifizierung

### Wichtig zu wissen

> ISO 27018 ist **keine eigenständige Zertifizierung**. Sie wird als Erweiterung zu ISO 27001 geprüft.

### Zertifizierungspfad

```
ISO 27001 (Basis) + ISO 27018 (PII Extension) = Combined Certification
```

### Major Cloud Provider Zertifizierungen

| Provider | ISO 27018 |
|----------|-----------|
| AWS | ✓ |
| Microsoft Azure | ✓ |
| Google Cloud | ✓ |
| IBM Cloud | ✓ |
| Oracle Cloud | ✓ |

---

## Integration mit anderen Standards

| Standard | Beziehung |
|----------|-----------|
| **ISO 27001** | Basis-ISMS |
| **ISO 27002** | 27018 erweitert 27002 für PII |
| **ISO 27017** | Cloud Security (komplementär) |
| **ISO 27701** | Privacy Information Management System |
| **ISO 29100** | Privacy Framework (referenziert) |
| **GDPR** | Unterstützt Compliance |
| **NIS2** | Security Baseline für PII-Verarbeitung |

---

## Quellen

- [ISO Official - ISO/IEC 27018:2019](https://www.iso.org/standard/76559.html)
- [ISMS.online - ISO 27018](https://www.isms.online/iso-27018/)
- [AWS - ISO 27018 Compliance](https://aws.amazon.com/compliance/iso-27018-faqs/)
- [Microsoft - ISO 27018 Compliance](https://learn.microsoft.com/en-us/compliance/regulatory/offering-iso-27018)
- [Google Cloud - ISO 27018](https://cloud.google.com/security/compliance/iso-27018)
- [Linford & Company - ISO 27018 Guide](https://linfordco.com/blog/iso-iec-27018-cloud-privacy-guide/)
