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

## Toegangsbeheer en Rolle
Die API implementeer streng rol-gebaseerde toegang (RBAC):
*   **Administrateur**: Volle toegang tot alle CRUD operasies en data.
*   **Kampus_Opsigter**: Kan slegs gebruikers en data binne hul toegewese kampusse sien (F20).
*   **Sekuriteit_Wag**: Mag gebruikers skandeer en lys, maar sien slegs 'n beperkte profiel (geen e-pos of sensitiewe data) (F21).

## Roetes

### 1. Gebruikerbestuur (F2)
*   **GET /gebruikers**: Lys gebruikers. Data word gefilter gebaseer op die versoeker se rol.
*   **GET /gebruikers/{id}**: Kry profiel. Sekuriteitswagte sien slegs `UserSecurityRead` velde.
*   **POST /gebruikers**: Skep 'n nuwe gebruiker (Slegs Admin).
*   **PUT /gebruikers/{id}**: Dateer gebruiker inligting op (Slegs Admin).
*   **DELETE /gebruikers/{id}**: Sagte verwydering (deaktiveer).

### 2. Status en NFC (F1 & F13)
*   **PATCH /gebruikers/{id}/status?is_aktief=false**: 
    *   Merk gebruiker as onaktief.
    *   Roep outomaties Steven se NFC deaktivering eindpunt aan.
    *   Skep 'n `Waarskuwing` rekord.
*   **PATCH /nfc-tags/{user_id}/deaktiveer**: 
    *   Steven se eindpunt (F13) om alle aktiewe tags vir 'n gebruiker te deaktiveer.

## Databasis Migrasies
Sien die `Backend/migrations/` gids vir die amptelike SQL skema-lêers. Nuwe veranderinge moet as genommerde SQL lêers bygevoeg word.

---
*Geskep deur Louis (Admin API Ontwikkelaar)*
