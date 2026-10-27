# TV Remote voor de KPN TV+ box (Android TV)

Een kleine server die op je Windows-pc draait en je TV-box aanstuurt via het
Android TV Remote-protocol (hetzelfde protocol als de officiële Google TV-app).
Je bedient de TV via een webpagina op je iPhone.

Kan: pijltjes, OK, terug, home, aan/uit, volume, mute, zender op/af,
zendernummers, media-knoppen (play/pauze, spoelen, opnemen), gids/info/menu,
de vier kleurenknoppen, tekst typen (bijv. zoeken in YouTube) en apps starten.

## Vereisten

- Windows-pc die altijd aanstaat, in hetzelfde (wifi-)netwerk als de TV-box.
- Python 3.11 of nieuwer: https://www.python.org/downloads/windows/
  Vink bij het installeren **"Add python.exe to PATH"** aan.
- Het IP-adres van de TV-box. Op de box: Instellingen → Netwerk en internet
  (of Instellingen → Over → Status). Geef de box bij voorkeur een vast IP in je
  KPN-modem (Experia Box / Box 12), anders kan het adres na een tijd wisselen.

## Installeren en starten

1. Kopieer de map `tv-remote` naar je pc, bijvoorbeeld naar `C:\tv-remote`.
2. Dubbelklik op `start.bat`. De eerste keer worden de pakketten geïnstalleerd.
3. Je ziet: `TV Remote draait op http://0.0.0.0:8080`. Laat dit venster open.
4. Zoek het IP-adres van je pc: open een opdrachtprompt en typ `ipconfig`,
   kijk bij "IPv4-adres" (bijv. `192.168.1.20`).
5. Windows vraagt waarschijnlijk of Python netwerkverkeer mag ontvangen.
   Kies **Toestaan** voor privénetwerken. Gebeurt dat niet en kom je er vanaf je
   telefoon niet bij, voeg dan handmatig een regel toe:
   Windows Beveiliging → Firewall → Geavanceerde instellingen →
   Regels voor binnenkomende verbindingen → Nieuwe regel → Poort → TCP 8080.

## Koppelen met de TV (eenmalig)

1. Open op je iPhone in Safari: `http://<ip-van-je-pc>:8080`
2. Tik op het tandwiel, vul het IP-adres van de TV-box in en tik op **Verbind**.
3. Op de TV verschijnt een code van zes tekens. Typ die in het veld
   "Code op TV-scherm" en tik op **Koppel**.
4. De status wordt "Verbonden". De koppeling wordt bewaard in `cert.pem` en
   `key.pem`, dus dit hoef je maar één keer te doen.

Tip: tik in Safari op het deel-icoon → **Zet op beginscherm**. Dan opent de
afstandsbediening schermvullend als een app.

## Dagelijks gebruik

De server verbindt bij het starten automatisch met het opgeslagen IP en
herstelt de verbinding zelf als de TV uit en weer aan gaat.

- **Ingedrukt houden** op de pijltjes, volume en zender herhaalt de toets.
- **Aan/uit** stuurt de power-toets; de box gaat in stand-by of weer aan.
- **Tekst typen** werkt zodra er op de TV een tekstveld actief is.
- **Apps** start de app via zijn Android package-id. Pas de lijst aan in
  `config.json` (naam → package-id). Package-id's vind je op de Play Store-
  pagina van een app in de URL na `id=`.

## Automatisch starten met Windows

1. Druk op Win+R, typ `shell:startup`, Enter.
2. Maak daar een snelkoppeling naar `start.bat`.

Wil je geen zwart venster zien, maak dan een snelkoppeling naar
`.venv\Scripts\pythonw.exe server.py` met als werkmap de `tv-remote`-map.

## Problemen

| Melding | Oplossing |
|---|---|
| Kan geen verbinding maken met … | Controleer het IP van de box en of pc en box in hetzelfde netwerk zitten. Sommige modems hebben "client isolatie" of een gastnetwerk; zet dat uit voor beide apparaten. |
| Er verschijnt geen code op de TV | De box ondersteunt mogelijk de Android TV Remote Service niet. Controleer of de officiële Google TV-app op je iPhone de box wél kan vinden; zo niet, dan werkt dit protocol niet op deze box. |
| Onjuiste code | Let op hoofdletters en verwissel 0/O niet. Verbind opnieuw voor een nieuwe code. |
| De TV kent deze PC niet meer | De box is gereset of de koppeling is verwijderd. Verwijder `cert.pem` en `key.pem` en koppel opnieuw. |
| Server onbereikbaar op de iPhone | Firewall (zie boven), of de pc slaapt. Zet "Slaapstand" uit in Energiebeheer. |

## Bestanden

- `server.py` – de server (Python, aiohttp + androidtvremote2)
- `static/index.html` – de afstandsbediening-pagina
- `config.json` – IP van de box en de app-lijst (wordt automatisch aangemaakt)
- `cert.pem`, `key.pem` – de koppeling met de TV (niet delen)
- `start.bat` – installeert pakketten en start de server
