# Ontwerp: Personeel-dropdowns & lokaal-tag-koppeling

**Datum:** 2026-09-16
**Status:** Goedgekeur deur Connor

## Doel

1. Die personeel-bladsy se enkele "Kies Klas"-dropdown word gesplits in twee
   dropdowns: module en dag/sessie.
2. Die admin-bladsy kry 'n manier om 'n fisiese NFC-tag (bv. "L4") aan 'n
   klas-lokaal (bv. "Bitterbessie") te koppel.
3. Die personeel-klasregister wys per student sy laaste werklike
   inskandering van vandag (lokaal + tyd), sodat personeel kan sien in
   watter klas-lokaal die student ingeskandeer het.

## Huidige stand (verken 2026-09-16)

- `Webwerf/personeel.js` bou een `klas-select` met opsies soos
  "EBREK370 — Maandag 8:00–9:00 · GH117 A (50)"; die gekose item is 'n
  klas-sessie-objek `{klasId, kode, moduleNaam, dag, dagIndeks, begin, ...}`.
  Die kalender, KPI's en klasregister hang van daardie objek af.
- Elke `Lokasie` het presies een aktiewe `NFC_Tags`-ry met
  `NFC_Tipe="Lokasie"`; `GET /lokasies` skep dit outomaties indien dit
  ontbreek en gee reeds `NFC_UID` per lokaal terug.
- `POST /lokasies/klasse` (skep lokaal) genereer altyd self 'n UID en
  ignoreer die `NFC_UID` in die versoek.
- `toegangs_logs` stoor reeds `Lokasie_ID`, `TOE_Rigting` ("IN"/"UIT") en
  `TOE_Tydstempel` (UTC) per skandering.
- Die klasregister kom van `GET /rooster/klasse/{klas_id}/studente`
  (`resolver_klas_studente` in `Backend/routers/klasse.py`).

## Deel 1: Personeel-bladsy — module- en dag-dropdowns

**Net frontend** (`Webwerf/personeel.html`, `Webwerf/personeel.js`).

- Vervang die enkele `klas-select` met twee keuselyste:
  - `module-select` ("Kies Module"): unieke modules uit die dosent se
    rooster, etiket "KODE — Naam" (naam weggelaat as dit ontbreek).
  - `dag-select` ("Kies Dag"): die gekose module se sessies, etiket
    "Dag Begin–Eind · Lokaal".
- Gedrag: by verandering van `module-select` word `dag-select` herbou en
  die eerste sessie outomaties gekies. Die twee keuses saam resolveer na
  dieselfde klas-sessie-objek as voorheen; alle bestaande logika
  (kalender, KPI's, klasregister) bly onveranderd.
- Sessies binne 'n module word gesorteer op weekdag-indeks en begintyd.

## Deel 2: Admin-bladsy — tag ↔ lokaal

**Backend** (`Backend/routers/lokasie.py`, `Backend/schemas.py`):

- Nuwe endpoint `PUT /lokasies/{lokasie_id}/nfc-tag` (admin-slegs), body
  `{"NFC_UID": "L4"}`:
  - Vind die lokaal se aktiewe `Lokasie`-tag (skep een as dit ontbreek,
    soos `GET /lokasies` reeds doen) en hernoem sy `NFC_UID`.
  - Validasie: UID leeg → 400; UID behoort reeds aan 'n ander tag
    (lokaal- of gebruikerstag) → 409 met duidelike boodskap. Ons
    hergebruik doelbewus nié die generiese `POST /nfc-tags`-upsert nie,
    omdat dié stilweg 'n ander lokaal se tag sou kon skuif.
  - UID word getrim; vergelyking hooflettersensitief soos die res van
    die stelsel (`NFC_UID` is 'n unieke kolom).
- `POST /lokasies/klasse` (skep lokaal): gebruik die verskafte `NFC_UID`
  as dit nie leeg of "TEMP" is nie (met dieselfde uniekheidsvalidasie),
  anders genereer soos tans.

**Frontend** (`Webwerf/admin.html`, `Webwerf/admin.js`,
`Webwerf/website_api_calls.js`):

- Voeg 'n "NFC-tag UID"-teksveld by die bestaande Skep/Wysig-lokaal-venster.
- Lokaal-rye (klaskamers én hekke) wys die gekoppelde UID as 'n klein
  etiket; `addVenueRow`/`updateVenueRow` dra die UID saam in `dataset`.
- Wysig-modus: as die UID verander het, roep `MoonApi.updateLokasieTag()`
  (nuwe funksie → `PUT /lokasies/{id}/nfc-tag`) ná die naam/kampus-opdatering;
  wys die bediener se foutboodskap as die UID reeds in gebruik is.
- Skep-modus: stuur die getikte UID in die bestaande `createKlas()`-payload.

## Deel 3: Klasregister — laaste skandering per student

**Backend** (`Backend/routers/klasse.py`):

- `GET /rooster/klasse/{klas_id}/studente` kry per student 'n ekstra veld:

  ```json
  "Laaste_Skandering": {"lokaal": "Bitterbessie", "tyd": "2026-09-16T07:14:03Z"}
  ```

  of `null` as die student vandag nog nie "IN" geskandeer het nie.
  `tyd` is die ISO-8601 UTC-tydstempel; die blaaier formateer dit na
  plaaslike tyd (bv. "09:14") sodat personeel nie UTC sien nie.
- Berekening: een groepsquery oor `toegangs_logs` (jongste ry per
  gebruiker met `TOE_Rigting="IN"` en `TOE_Tydstempel` binne vandag se
  UTC-dag), gejoin met `lokasie` vir die naam. Geen N+1 nie.
- Tydnota: tydstempels is UTC; "vandag" is die UTC-dag. Vir SA-klastye
  (UTC+2) is dit prakties dieselfde; skanderings tussen 00:00 en 02:00
  SAST val op die vorige UTC-dag — aanvaarde beperking.

**Frontend** (`Webwerf/personeel.js`):

- Elke ry in die klasregister wys onder die student se naam:
  "Bitterbessie · 09:14" (plaaslike tyd, uit die ISO-tydstempel) of
  "Geen skandering vandag".

## Toetse

- `Backend/tests/test_klasse.py`: `Laaste_Skandering` word teruggegee met
  die regte lokaalnaam/tyd; `null` sonder logs; net vandag se logs tel.
- Nuwe toetse vir `PUT /lokasies/{id}/nfc-tag`: suksesvolle hernoem, 409
  by UID-botsing, 400 by leë UID, 403 vir nie-admin.
- Bestaande toetse loop met `DISABLE_AUTH=0` (wortel-`.env` skakel
  outentisering plaaslik af).

## Buite bestek

- Die gesimuleerde bywoningsyfers op die personeel-bladsy bly soos hulle
  is; net die laaste-skandering-lyn is werklike data.
- Geen veranderinge aan die mobiele app of die skandeer-vloei self nie.
