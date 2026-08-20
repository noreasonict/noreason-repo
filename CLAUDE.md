# NoReason Kodi Repository — pokyny pro Claude Code a další agenty

## Účel

- Toto je produkční statický Kodi repository feed publikovaný přes GitHub Pages.
- GitHub: `noreasonict/noreason-repo`, větev `main`.
- Feed: `https://noreasonict.github.io/noreason-repo/addons.xml`.
- Tento repozitář není zdrojový strom addonů. Zdroj je v `Pigman91/Raklamni-smycky/Doplnky/`.
- Publikace změny může automaticky aktualizovat více než 150 Kodi zařízení; každý push je produkční deploy a vyžaduje explicitní souhlas uživatele.

## Struktura

```text
repository.noreason/          Kodi addon repozitáře
service.dohled/               verzované ZIP balíčky hlavního addonu
service.smycky/               verzované ZIP balíčky kompatibilního/proxy addonu
addons.xml                    metadata aktuálně publikovaných addonů
addons.xml.md5                MD5 přes přesné bajty Git blobu addons.xml
.nojekyll                     GitHub Pages bez Jekyll transformace
```

## Release workflow

1. Ověř, že zdrojová verze addonu je commitnutá a otestovaná v `Raklamni-smycky`.
2. Zkontroluj `addon.xml`: ID, verzi, závislosti, provider, changelog a Kodi Python kompatibilitu.
3. Vytvoř ZIP s jediným top-level adresářem ve formátu `service.dohled-X.Y.Z/` nebo `service.smycky-X.Y.Z/`.
4. Vlož ZIP do odpovídajícího adresáře tohoto repozitáře; staré verze nemaž bez explicitního rozhodnutí o rollback politice.
5. Aktualizuj `addons.xml` z metadata právě publikované verze. Nepřidávej starý proxy addon do feedu, pokud to není výslovně zamýšlené.
6. Stage-ni `addons.xml` a vypočti MD5 z Git indexu, ne z CRLF pracovní kopie na Windows:

```bash
git add addons.xml
git show :addons.xml | md5sum
```

7. Zapiš pouze 32znakový hash do `addons.xml.md5` bez dodatečného textu.
8. Ověř ZIP pomocí Python `zipfile`: nepoškozený archiv, správný top-level adresář a shodná verze v `addon.xml`.
9. Zkontroluj `git diff --cached`, že release obsahuje jen zamýšlený ZIP, `addons.xml` a MD5.
10. Commit/push prováděj pouze po explicitním schválení uživatele.

## Aktuální stav při vytvoření pravidel

- Publikovaný `service.dohled` je 3.5.0.
- Zdrojový repozitář obsahuje 3.5.1, která ještě není publikovaná.
- `service.smycky` 3.0.0 je proxy addon závislý na `service.dohled`.

Před každým releasem živě ověř verze; tento odstavec může zestárnout.

## Validace po publikaci

- Ověř dostupnost `addons.xml`, `addons.xml.md5` a nového ZIPu přes GitHub Pages.
- Spočítej MD5 staženého `addons.xml` a porovnej s publikovaným checksumem.
- Ověř instalaci/aktualizaci nejdřív na testovacím Kodi zařízení.
- Rollout na ostatní zařízení považuj za dokončený až po skutečném testu restartu a aktualizace.

## Bezpečnost

- ZIP nesmí obsahovat `.env`, privátní klíče, credentials, logy, cache, testovací data nebo osobní údaje.
- Nikdy nekopíruj credentials ze zdrojového `CLAUDE.md`, historie chatu ani serveru.
- Neprováděj release automaticky jen proto, že existuje vyšší zdrojová verze.
- Do stejného release stromu nesmí současně zapisovat více agentů.
