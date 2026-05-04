# MOON Admin API Dokumentasie

Hierdie API hanteer die administratiewe funksies vir die MOON projek.

## Toegang en Verifikasie
Alle roetes (behalwe `/token` en `/`) vereis 'n Bearer JWT Token.
Verkry 'n token deur te POST na `/token` met `username` (e-pos) en `password`.

## Response Formaat
Alle antwoorde volg hierdie standaard struktuur:
```json
{
  "sukses": true,
  "data": { ... },
  "fout": null
}
```

## Roetes

### 1. Gebruikerbestuur (F2)
*   **GET /gebruikers**: Lys alle gebruikers. 
    *   *Admins* sien almal. 
    *   *Kampus Opsigters* sien slegs gebruikers in hul kampus skoop.
*   **GET /gebruikers/{id}**: Kry volledige profiel van 'n spesifieke gebruiker.
*   **POST /gebruikers**: Skep 'n nuwe gebruiker (Slegs Admin).
    *   Verpligte velde: `GEB_Naam`, `GEB_Van`, `GEB_ID_Nommer`, `GEB_Epos`, `GEB_Wagwoord`, `Rol_ID`.
*   **PUT /gebruikers/{id}**: Dateer gebruiker inligting op (Slegs Admin).
*   **DELETE /gebruikers/{id}**: Deaktiveer 'n gebruiker (Sagte verwydering).

### 2. Status en NFC (F1)
*   **PATCH /gebruikers/{id}/status?is_aktief=false**: 
    *   Merk gebruiker as onaktief.
    *   Deaktiveer outomaties alle gekoppelde NFC tags.
    *   Skep 'n `Waarskuwing` rekord vir die ouditspoor.

### 3. Kampus Skoop (F20)
*   Middleware verifieer outomaties dat `Kampus_Opsigters` slegs toegang het tot data binne hul toegewese kampusse.

---
*Geskep deur Louis (Admin API Ontwikkelaar)*
