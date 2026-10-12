# MOON Projekdokumentasie & Vergaderingsrekords

> **NSWIW370 · Akademia · Span 3 — Finale Inhandiging (DA11)**

Hierdie gids dien as die amptelike register en inhoudsopgawe vir alle projekbeplanningsdokumente, tegniese algoritme-spesifikasies, produkdemonstrasies, en formele vergaderingsrekords vir die MOON-stelsel.

---

## Inhoudsopgawe
1. [Tegniese Spesifikasies & Algoritmes](#tegniese-spesifikasies--algoritmes)
2. [Produkdemonstrasies](#produkdemonstrasies)
3. [Projekbeplanning & Skedulering](#projekbeplanning--skedulering)
4. [Formele Vergaderingsnotules & Agendas](#formele-vergaderingsnotules--agendas)

---

## Tegniese Spesifikasies & Algoritmes

Die stelsel beskik oor twee omvattende, wiskundig-gefundeerde tegniese dokumente wat die kern-masjienleer en analitiese dienste van MOON spesifiseer:

| Dokument | Beskrywing | Kerninhoud |
|---|---|---|
| 🚗 **[`Saamry-Algoritme.md`](./Saamry-Algoritme.md)** | Saamry Versoenbaarheidsalgoritme Tegniese Spesifikasie | 4-pilaar geweegde formule (Tyd 40%, Ligging 30%, Rol 15%, Betroubaarheid 15%), aankomstyd-skatting met Pythagoras-onsekerheid ($\sigma = 22.2$ min), voorstad-klustermodellering, en koue-begin terugvalle. |
| 🏫 **[`Lokaalgebruik-Model.md`](./Lokaalgebruik-Model.md)** | Lokaalgebruik-Voorspellingsmodel Tegniese Spesifikasie | Skanderingskoers-modellering met `HistGradientBoostingRegressor` ($L_1$ absolute error verlies), data-lekkasie voorkoming, groeiende venster (walk-forward), gepaarde bootstrap-modelkeuse ($\ge 1 \text{ SE}$), en 80% residue-kwantielintervalle. |

---

## Produkdemonstrasies

Die volgende aanbiedings is tydens formele module-mylpale aan die paneel en dosente voorgelê:

| Lêer | Mylpaal | Formaat | Beskrywing |
|---|---|---|---|
| **`Alpha-Weergawe Produkdemonstrasie.pptx`** | DA7 (MVP / Alfa) | PowerPoint | Demonstrasie van die vroeë MVP-argitektuur, basiese NFC-skandering en aanmeldvloei. |
| **`MOON_Beta_Demonstrasie.pptx`** | DA9 (Beta) | PowerPoint | Omvattende stelseldemonstrasie van die voltooide Saamry-stelsel, Noodgevalle MQTT-diens, en multi-rol integrasie. |

---

## Projekbeplanning & Skedulering

| Lêer | Beskrywing |
|---|---|
| **`Werklike_Gantt_PreAlpha.xlsx`** | Gedetailleerde werklike Gantt-kaart en taaktoewysings vir die vroeë beplannings- en implementeringsfases van die projek. |

---

## Formele Vergaderingsnotules & Agendas

Die span het gereelde formele spanvergaderings gehou om vordering te monitor, argitektuurbesluite te neem en take toe te ken. Alle agendas en getekende notules is hieronder gelys:

### Vroeë Projekfase (DA1 – DA6)
- **Vergadering 1**: [`Vergadering 1(MOON)_Agenda.pdf`](./Vergadering%201%28MOON%29_Agenda.pdf) · [`Vergadering 1(MOON)_Notule.pdf`](./Vergadering%201%28MOON%29_Notule.pdf)
- **Vergadering 2**: [`Vergadering 2(MOON)_Agenda.pdf`](./Vergadering%202%28MOON%29_Agenda.pdf) · [`Vergadering 2(MOON)_Notule.pdf`](./Vergadering%202%28MOON%29_Notule.pdf)
- **Vergadering 3**: [`Vergadering 3(MOON)_Agenda.pdf`](./Vergadering%203%28MOON%29_Agenda.pdf) · [`Vergadering 3(MOON)_Notule.pdf`](./Vergadering%203%28MOON%29_Notule.pdf)
- **Vergadering 4**: [`Vergadering 4(MOON)_Agenda.pdf`](./Vergadering%204%28MOON%29_Agenda.pdf) · [`Vergadering 4(MOON)_Notule.pdf`](./Vergadering%204%28MOON%29_Notule.pdf)
- **Vergadering 5**: [`Vergadering 5(MOON)_Agenda.pdf`](./Vergadering%205%28MOON%29_Agenda.pdf) · [`Vergadering 5(MOON)_Notule.pdf`](./Vergadering%205%28MOON%29_Notule.pdf)
- **Vergadering 6**: [`Vergadering 6(MOON)_Agenda.pdf`](./Vergadering%206%28MOON%29_Agenda.pdf) · [`Vergadering 6(MOON)_Notule.pdf`](./Vergadering%206%28MOON%29_Notule.pdf)
- **Vergadering 7**: [`Vergadering 7(MOON)_Agenda.pdf`](./Vergadering%207%28MOON%29_Agenda.pdf) · [`Vergadering 7(MOON)_Notule.pdf`](./Vergadering%207%28MOON%29_Notule.pdf)

### Middel- en Slotfase (DA7 – DA11)
- **Vergadering 8**: [`MOON_Vergadering_8_Agenda.pdf`](./MOON_Vergadering_8_Agenda.pdf) · [`MOON_Vergadering_8_Notule.pdf`](./MOON_Vergadering_8_Notule.pdf)
- **Vergadering 9**: [`MOON_Vergadering_9_Agenda.pdf`](./MOON_Vergadering_9_Agenda.pdf) · [`MOON_Vergadering_9_Notule.pdf`](./MOON_Vergadering_9_Notule.pdf)
- **Vergadering 10**: [`MOON_Vergadering_10_Agenda.pdf`](./MOON_Vergadering_10_Agenda.pdf) · [`MOON_Vergadering_10_Notule.pdf`](./MOON_Vergadering_10_Notule.pdf)
- **Vergadering 11**: [`MOON_Vergadering_11_Agenda.pdf`](./MOON_Vergadering_11_Agenda.pdf) · [`MOON_Vergadering_11_Notule.pdf`](./MOON_Vergadering_11_Notule.pdf)
- **Vergadering 12**: [`MOON_Vergadering_12_Agenda.pdf`](./MOON_Vergadering_12_Agenda.pdf) · [`MOON_Vergadering_12_Notule.pdf`](./MOON_Vergadering_12_Notule.pdf)
- **Vergadering 13**: [`MOON_Vergadering_13_Agenda.pdf`](./MOON_Vergadering_13_Agenda.pdf) · [`MOON_Vergadering_13_Notule.pdf`](./MOON_Vergadering_13_Notule.pdf)
