# Saamry Versoenbaarheidsalgoritme - Tegniese Dokumentasie

Hierdie dokument beskryf die volledige logika en stappe agter Akademia se Saamry-versoenbaarheidsalgoritme. Die algoritme is ontwerp om studente en personeel op grond van hul pendelgewoontes, ligging, roetines en voorkeure by mekaar te pas.

## Oorsig van die Stelsel

Die algoritme neem twee gebruikers (die *soeker* en die *kandidaat*) en bereken 'n finale verenigbaarheidstelling uit 100. Dit maak gebruik van 'n saamgestelde geweegde indeks wat uit vier hoofpilare bestaan:

1. **Tyd (40%)**: Die oorvleueling in daaglikse aankoms- en vertrektye.
2. **Ligging (30%)**: Geografiese roete-sinergie.
3. **Rol (15%)**: Bestuurder, passasier, of albei.
4. **Betroubaarheid (15%)**: Hoeveel historiese, ware data die skatting steun.

Voordat die geweegde telling bereken word, ondergaan die paar eers harde veiligheids- en uitsluitingsreëls.

---

## 1. Harde Uitsluitings (Filters)

Indien 'n paar aan enige van die volgende voorwaardes voldoen, word hulle onmiddellik uitgesluit (telling 0.0) sonder dat verdere wiskunde uitgevoer word:
- **Dieselfde Gebruiker**: 'n Gebruiker kan nie met hom/haarself pas nie.
- **Kampusverskil**: Studente moet na dieselfde spesifieke kampus pendel.
- **Geslagsvoorkeure**: As enige een van die twee "dieselfde geslag" kies, moet hul geslag ooreenstem.
- **Onversoenbare Rolle**: Twee studente wat beide as "Slegs Passasier" (sonder 'n eie voertuig) geregistreer is, kry 'n 0.0.

---

## 2. Ligging en Roeteberekening (30%)

Ligging word op voorstad-klustervlak vergelyk om by te dra tot die ooreenstemming:

1. **Normalisering**: Die gebruiker se gekose voorstad word geskrop van leestekens en onnodige spasies. 
2. **Kartering**: Die voorstad word dan gepas by 'n kluster (*Centurion, Oos, Noord, Moot, Sentraal, Midrand*). As daar nie 'n eksakte passing is nie, val dit terug na gedeeltelike passing vir agteruitversoenbaarheid. As dit selfs dan onbekend is: voorstad onbekend, teks bevat "pretoria" &rarr; 50%; andersins onbekend &rarr; 30%.
3. **Roeteberekening**: Die algoritme ken punte toe volgens roete logik:
   - *Dieselfde voorstad* kry 100%.
   - *Dieselfde kluster* kry 90%.
   - *Aangrensende of roete-logiese klusters* kry afskalings op grond van hoofweë. Bv. *Sentraal* en *Oos* kry 85%, *Centurion* en *Oos* kry 75%.
   - *Onlogiese roetes* kry swaar strawwe. Bv. *Centurion* na *Noord* kry 20%.

---

## 3. Aankomstyd-skatting (Die Koue-Begin Probleem)

Om die **Tyd** te bereken, moet die algoritme 'n skatting maak van wanneer elke student by die kampus aankom of vertrek.
* **Empiriese Hek-logs**: Die algoritme ontleed slegs logs van die afgelope 60 dae. Sodra 'n student ten minste 3 logs vir 'n spesifieke weeksdag het, word die ware gemiddelde aankomstyd en die standaardafwyking direk uit die hek-logs bereken.
* **Koue-Begin (Geen hek-logs)**: Aan die begin van die semester is daar geen hek-logs nie. 'n Gradient Boosting ML-Model is vroeër op 100 selfgerapporteerde opname-antwoorde geëvalueer. Uit hierdie kruisvalidasie het geblyk dat ingewikkelde ML modelle nie 'n aantoonbare voordeel bo 'n eenvoudige globale mediaan inhou nie.
* Die stelsel maak daarom 'n voorlopige skatting deur wiskundig terug te val op die mediaan-reël: **Daar word 'n skatting gemaak dat die student 30 minute voor hul eerste klas aankom, met 'n ingeboude onsekerheid (standaardafwyking $\sigma = 22.2$ minute).** 
* Vir *vertrektye* by koue-begin studente, word die laaste klas van die dag geïdentifiseer en as skatting word die student 15 minute na daardie klas ontslaan. Hierdie aanname is nie deur die opname getoets nie (aangesien slegs aankomstye gemeet is), maar dit gebruik dieselfde onsekerheid ($\sigma = 22.2$) as die aankoms.

---

## 4. Tydtelling-Wiskunde (40%)

Tydversoenbaarheid word *per gemeenskaplike dag* bereken:
1. **Effektiewe Tydsverskil**: Die tydtelling inkorporeer die daaglikse onsekerheid (variansie) van studente via 'n Pythagoraanse vergelyking:
   ```text
   gesamentlike_afwyking = (sigma_A + sigma_B) / 2
   effektiewe_verskil = sqrt((minuut_verskil)^2 + (gesamentlike_afwyking)^2)
   ```
   *Voorbeeld:* As twee nuwe koue-begin studente (albei met $\sigma = 22.2$) op presies dieselfde tyd klas het (0 minuut verskil), is hul gesamentlike afwyking steeds $22.2$. Die effektiewe verskil is $\sqrt{0^2 + 22.2^2} = 22.2$ minute. Weens hierdie ingeboude onsekerheid kry hulle $\sim 75.6\%$ vir daardie dag se aankomspunt en nie 100% nie. Gevolg: pare sonder hek-logs kan nie die hoogste punte behaal nie, wat slegs log-data later kan verbeter.
2. **Telling-verval**:
   - $0 - 10 \text{ min}$: 100% verenigbaar
   - $10 - 30 \text{ min}$: Daal lineêr van 100% af na 60%
   - $30 - 60 \text{ min}$: Daal lineêr van 60% af na 10%
   - meer as $60 \text{ min}$: 0%
3. Die aankomstyd tel 55% en vertrektyd tel 45% van 'n enkele dag se punt.
4. **Dae-faktor**: Die gemiddeld oor alle *gemeenskaplike dae* word vermenigvuldig met 'n dekking-faktor (tot $1.05 \times$) indien die kandidaat 100% van die soeker se kampus-dae kan dek. Die finale tydtelling word dan afgekap by 'n maksimum van 100%.

---

## 5. Betroubaarheid (15%) en Roltelling (15%)

- **Rol**: 
  - Bestuurder & Passasier = 100%
  - Albei & Enige Rol = 100%
  - Bestuurder & Bestuurder = 85%
  
- **Betroubaarheid**: Om kandidate met gevestigde gedrag voorrang te gee, loop die Betroubaarheidsfaktor op die volgende skaal:
  - As enige een van die twee gebruikers se tyd geskat is, is die betroubaarheid **40%**.
  - Indien daar 1 – 4 hek-logs per dag is, styg dit vanaf **50% tot 85%**.
  - Met 5 – 9 logs styg dit verder lineêr vanaf **85% tot 100%**.
  - Met 10 of meer logs verdien die student **100%** betroubaarheid.

*Die hoogste moontlike koue-begin-telling met die 40% betroubaarheid is ongeveer 83%. Dit is as studente dieselfde voorstad het (30 + 15), Bestuurder+Passasier rol (15), en dieselfde rooster wat met die $1.05$ dekking sowat 31.8 vir die tyd byvoeg. Dit is GOED, en beteken dat koue-begin gebruikers nie UITSTEKEND ($\ge 85\%$) kan bereik sonder dat hulle fisiese logs opbou nie.*

---

## 6. Finale Klassifikasie en Vertoonreël
Sodra al vier gewigte bymekaargetel word na die `totale_telling`, word die uitkoms in 'n gehalte-kategorie verdeel vir die stelsel:
- **UITSTEKEND**: $\ge 85\%$
- **GOED**: $\ge 70\%$
- **MATIG**: $\ge 50\%$
- **SWAK**: $> 0\%$
- **ONVERSOENBAAR**: $0\%$

Die algemene vertoonreël by kandidate op die webplatform vereis dat 'n voorstel slegs gegee en bekyk sal word indien die Totale Telling $\ge 50\%$ is **én** die Finale Tydtelling $\ge 30\%$ is.

## 7. Toekomstige Uitbreidbaarheid
Daar is opleidingskripte teenwoordig wat met latere data uitgevoer kan word, en die `SaamryVoorstelLog`-tabel teken voortaan aan watter voorstelle GESIEN en GESTUUR is om so masjienleerterugvalle vir die toekoms in te lig.
