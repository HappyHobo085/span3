# MOON Mobiele Toepassing — Tegniese Verwysing & Ontwikkelingsgids

> **NSWIW370 · Akademia · Span 3 — Finale Inhandiging (DA11)**
> **Flutter 3.x · Dart · Android & iOS · NFC · Mosquitto MQTT · OpenStreetMap**

Hierdie gids dien as die amptelike tegniese en ontwikkelingshandleiding vir die **MOON Mobiele Toepassing** (`studente_mobile_flutter_app`). Dit dokumenteer die toepassing se argitektuur, multi-rol koppelvlakke, NFC-hekskandering, interaktiewe OpenStreetMap-optelkaarte, intydse MQTT-noodgevalstelsel met native agtergronddienste, en instruksies vir konfigurasie en uitrol.

---

## Inhoudsopgawe
1. [Oorsig & Argitektuur](#oorsig--argitektuur)
2. [Rol-gebaseerde Roetering & Skerms](#rol-gebaseerde-roetering--skerms)
3. [Kernmodules & Spesialis-kenmerke](#kernmodules--spesialis-kenmerke)
4. [Kode-organisasie (`lib/`)](#kode-organisasie-lib)
5. [Inheemse Toestemmings & Konfigurasie](#inheemse-toestemmings--konfigurasie)
6. [Opstelling & Uitvoering (Quickstart)](#opstelling--uitvoering-quickstart)
7. [Toetsing & Gehaltebeheer](#toetsing--gehaltebeheer)

---

## Oorsig & Argitektuur

Die MOON-selfoontoepassing is 'n moderne kruisplatform Flutter-toepassing wat ontwerp is om die hele Akademia-gemeenskap op een enkele mobiele platform te verenig.

### Sleutelargitektoniese Eienskappe:
- **Eenvormige Kodebasis, Veelvuldige Rolle**: 'n Enkele app bedien vyf verskillende tipes gebruikers. Na aanmelding dekodeer die toepassing die JWT-token en laai outomaties die toepaslike koppelvlak volgens 'n gedefinieerde rol-prioriteit:
  $$\text{Administrateur} \succ \text{Kampus\_Opsigter} \succ \text{Sekuriteit\_Wag} \succ \text{Personeel} \succ \text{Student}$$
- **Kontaklose NFC-Tegnologie**: Integreer met `nfc_manager` om fisiese NFC-kaarte/tags by kampushekke en lesingsale te lees en te verifieer.
- **Interaktiewe Kartering**: OpenStreetMap-integrasie via `flutter_map` en `latlong2` vir die keuse van presiese Saamry-optelkoördinate sonder afhanklikheid van betaalde kaart-API's.
- **Intydse IoT-Boodskappe & Agtergrondwaarskuwings**: Volledige MQTT-kliënt (`mqtt_client`) gekoppel aan Eclipse Mosquitto, ondersteun deur 'n inheemse Android `MethodChannel` agtergronddiens (`moon/noodgeval_service`) wat verseker dat noodboodskappe selfs afgelewer word wanneer die toepassing nie oop is nie.
- **Material 3 Ontwerp & Tipografie**: Skoon gebruikerservaring met pasgemaakte temas en Google Fonts.

---

## Rol-gebaseerde Roetering & Skerms

Die app pas sy navigasie en beskikbare funksies outomaties aan op grond van die gebruiker se aangemelde rol:

### 1. 🎓 Student (`lib/student.dart`)
- **Kampusstatus**: Vertoon huidige status (`IN` of `UIT`), tydstempel van die laaste hekskandering, en die spesifieke lokaal.
- **Persoonlike Rooster**: Dinamiese dag- en weekrooster wat vakke, lesingtye en klaskamers vertoon.
- **Klasbywoning**: Visuele bywoningsaanwysers gebaseer op NFC-skanderings tydens geskeduleerde periodes.
- **Koshuisoorsig**: Vertoon inligting oor die student se toegewese koshuis en kamerstatus.
- **Saamry & Noodgevalle**: Direkte toegang tot ritte, kletse en die noodpaneel.

### 2. 👩‍🏫 Personeel (`lib/personeel.dart`)
- **Doseerrooster**: Volledige oorsig van klasse wat deur die dosent aangebied word.
- **Elektroniese Klasregister**: Lewendige klaslys met studentefoto's, ID-nommers, en aanduiding van wie fisies by die lokaal ingeskandeer het.
- **Departementele Inligting**: Toegang tot fakulteitsmodules en Saamry-reëlings.

### 3. 🛡️ Sekuriteitswag (`lib/sekuriteitswag.dart`)
- **Hekskandering**:
  - Lees studente- en personeelkaarte via NFC.
  - Wissel tussen `IN` en `UIT` hekmodusse.
  - Vinnige studenteverifikasie wat studentestatus en foto vertoon, maar sensitiewe privaatheidsinligting (e-pos, volle ID-nommer) verskans.
- **Besoeker-OTP Validering**:
  - Sleutel die gas se 6-syfer OTP in om toegang te verleen of vertrek aan te teken.
  - Beskerm teen ongeldige of vervalde kodes.
- **QR-Kaartjieskandering**:
  - Skandeer eksterne Funksie/Event QR-kodes by die hek vir kitsverifikasie.

### 4. 🏢 Kampus Opsigter (`lib/opsigter.dart`)
- **Kampusoorsig**: Lewendige opsomming van studente en personeel tans binne die grense van die toegewese kampus.
- **Lokaaltoesig**: Besigtig lokaalbenutting en hekbewegings.
- **Ontruimingskontrole**: Vinnige toegang tot die lewendige noodappèl-paneel.

### 5. ⚙️ Administrateur (`lib/admin.dart`)
- **Globale Toesig**: Moniteer stelselwye tellers, gebruikersrekeninge en statusveranderinge direk vanaf 'n mobiele toestel.

---

## Kernmodules & Spesialis-kenmerke

### 🚗 Saamry met OpenStreetMap (`lib/saamry_pickup_map.dart` & `lib/saamry_recommendations.dart`)
- **Interaktiewe Optelkaart**:
  - Gebruikers kan die kaart vrylik pan en zoem om hul daaglikse optelplek te kies.
  - Tik 'n adresbeskrywing in (bv. *"Hoek van Jan Cilliers- en Beyers Naudé-rylaan"*).
  - Stoor presiese GPS-koördinate (`latitude`, `longitude`) na die backend via `MoonApi`.
- **Slim Pasmaats**:
  - Vertoon kandidate wat deur die backend se 4-pilaar algoritme (Tyd 40%, Ligging 30%, Rol 15%, Betroubaarheid 15%) aanbeveel word.
  - Toon duidelike gehalte-etikette (`UITSTEKEND`, `GOED`, `MATIG`).
- **Groepe, Ritte & Kletse**:
  - Skep permanente groepe, genereer eenmalige ritte, en gesels intyds via privaat- of groepkletse.
  - **Hek-outomatisering**: Wanneer 'n bestuurder by die kampushek inskandeer, word alle bevestigde passasiers outomaties saam as `IN` aangeteken.

### 🚨 Noodgevalle & Agtergrondkennisgewings (`lib/noodgeval_dashboard.dart`, `lib/mqtt_noodgeval_service.dart`)
- **Intydse Uitsendings**: Koppel aan Mosquitto MQTT en luister na `moon/noodgeval/kampus/{kampus_id}`.
- **Android Native Agtergronddiens**:
  - 'n Toegewyde Java/Kotlin Android Foreground Service gekoppel via MethodChannel `moon/noodgeval_service`.
  - Verseker dat noodboodskappe ontvang en gelui word selfs as die app deur die gebruiker uit *Recent Apps* wegge-swipe is.
- **Plaaslike Kennisgewings**: Gebruik `flutter_local_notifications` met hoë-prioriteit klank en vibrasie.
- **Lewendige Ontruimingskontrole (Roll Call)**:
  - Sekuriteit en opsigters kan alle persone wat tans op kampus is besigtig.
  - Merk individue regstreeks as `DAAR` of `NIE_DAAR` tydens fisiese ontruimings.

### 👤 Profiel & Foto-bestuur (`lib/profile_page.dart`)
- Vertoon geregistreerde persoonlike inligting, ID-nommer, e-pos, selfoonnommer en roltoewysing.
- Ondersteun die neem van 'n nuwe profielfoto met die kamera of die keuse van 'n prent uit die galery via `image_picker`.
- Laai die foto op as 'n multi-deel HTTP-versoek na `/gebruikers/{id}/foto`.

---

## Kode-organisasie (`lib/`)

```text
studente_mobile_flutter_app/lib/
├── main.dart                          # Ingangspunt, tema, JWT-dekodering en rolroetering
├── moon_api.dart                      # Sentrale API-kliënt, HTTP-versoeke en DTO's
├── app_shared.dart                    # Gedeelde temas, konstantes, widgets en dialoë
├── student.dart                       # Studentpaneelbord, rooster en bywoning
├── personeel.dart                     # Personeelpaneelbord en klasregisters
├── sekuriteitswag.dart                # Sekuriteitswag skanderingskoppelvlak (NFC/OTP/QR)
├── opsigter.dart                      # Kampus-opsigter toesigpaneel
├── admin.dart                         # Mobiele administrasiepaneel
├── profile_page.dart                  # Gebruikersprofiel en foto-oplaai
├── saamry_pickup_map.dart             # Interaktiewe OpenStreetMap optelplekkaart
├── saamry_recommendations.dart        # Saamry pasmaats en versoenbaarheidsverslae
├── noodgeval_dashboard.dart           # Ontruimingskontrolepaneel (roll call)
├── mqtt_noodgeval_service.dart        # MQTT kliënt vir intydse noodboodskappe
└── noodgeval_notification_service.dart# Plaaslike stootkennisgewingsbestuurder
```

---

## Inheemse Toestemmings & Konfigurasie

### Android (`android/app/src/main/AndroidManifest.xml`)
Die toepassing vereis die volgende inheemse Android-toestemmings:
```xml
<!-- NFC Toegangsbeheer -->
<uses-permission android:name="android.permission.NFC" />
<uses-feature android:name="android.hardware.nfc" android:required="false" />

<!-- Netwerk & API Kommunikasie -->
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

<!-- Agtergrond Nooddiens & Kennisgewings -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<uses-permission android:name="android.permission.WAKE_LOCK" />
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />

<!-- Kamera & Galery vir Profielfoto's -->
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
```

### iOS (`ios/Runner/Info.plist`)
- `NFCReaderUsageDescription`: *"MOON benodig NFC om jou studentekaart by kampushekke en klaskamers te skandeer."*
- `NSCameraUsageDescription`: *"MOON benodig toegang tot jou kamera om 'n profielfoto te neem."*
- `NSPhotoLibraryUsageDescription`: *"MOON benodig toegang tot jou fotobiblioteek om 'n profielfoto te kies."*

---

## Opstelling & Uitvoering (Quickstart)

### 1. Voorvereistes
- [Flutter SDK](https://flutter.dev/) (weergawe 3.5.4 of nuwer)
- [Android Studio](https://developer.android.com/studio) (vir Android SDK en emulators) of [Xcode](https://developer.apple.com/xcode/) (vir iOS op macOS)
- 'n Lopende MOON Backend (plaaslik via Docker of op die wolk)

### 2. Installeer Afhanklikhede
Navigeer na die toepassinggids en installeer die Dart-pakkette:

```bash
cd studente_mobile_flutter_app
flutter pub get
```

### 3. Konfigureer & Begin die Toepassing
Die app gebruik `--dart-define` parameters om die API-basisadres en MQTT-bediener in te stel:

| Parameter | Verstekwaarde | Beskrywing |
|---|---|---|
| `API_BASE_URL` | Produksie Railway URL | Basis-URL van die FastAPI-backend |
| `MQTT_HOST` | `wss://...` | Hostnaam of WebSockets URL vir Mosquitto |
| `MQTT_PORT` | `443` (vir WSS) of `1883` | Poortnommer van die MQTT broker |
| `MQTT_USERNAME`| `moon_mobile` | MQTT kliënt gebruikersnaam |
| `MQTT_PASSWORD`| `""` | MQTT kliënt wagwoord |

#### A. Plaaslike Toetsing op 'n Webblaaier:
```bash
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

#### B. Toetsing op 'n Android Emulator (Koppel aan plaaslike Docker):
> **Let Wel:** Op 'n Android-emulator verwys `10.0.2.2` na die gasheerrekenaar se `localhost`:
```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000 --dart-define=MQTT_HOST=10.0.2.2 --dart-define=MQTT_PORT=1883
```

#### C. Toetsing teen die Produksie Wolkbediener:
```bash
flutter run --dart-define=API_BASE_URL=https://humorous-endurance-production-ee64.up.railway.app
```

### 4. Bou vir Produksie (Android APK)
Om 'n geoptimaliseerde vrystellings-APK te bou:

```bash
flutter build apk --release --dart-define=API_BASE_URL=https://humorous-endurance-production-ee64.up.railway.app
```
Die voltooide APK sal beskikbaar wees by `build/app/outputs/flutter-apk/app-release.apk`.

---

## Toetsing & Gehaltebeheer

Die toepassing sluit geoutomatiseerde widget- en eenheidstoetse in onder die `test/`-gids.

### Uitvoer van Toetse:
```bash
flutter test
```
