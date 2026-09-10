# DayZ Map Generator pentru GTA V (Blender + Sollumz)

Generator procedural de harta in stil DayZ (Chernarus): teren cu dealuri, coasta, paduri de conifere,
sate cu case, hambare, sopruri, drumuri de tara, campuri cu baloti, stanci, epave. Totul este optimizat
pentru GTA V:

- terenul e taiat in tile-uri de 256 m, fiecare cu 3 LOD-uri (4 m / 8 m / 16 m intre vertecsi);
- coliziunile sunt **fisiere `.ybn` separate** (bounds statice), cate unul per tile de teren, in coordonate
  mondiale, cu materiale corecte (iarba, pamant, stanca, nisip, tencuiala, lemn, tabla...);
- texturile de teren se amesteca prin shader-ul oficial `terrain_cb_w_4lyr` (4 straturi + normal maps) pe baza
  culorilor de vertex, nu prin texturi uriase;
- copacii, tufisurile, stancile, balotii, epavele sunt **props vanilla GTA V** (au deja LOD-uri, coliziuni si vant),
  deci nu costa memorie in plus;
- entitatile sunt impartite in .ymap-uri pe chunk-uri de 256 m, cu extents de streaming calculate corect;
- texturile custom (DXT1/DXT5 cu mipmap-uri) stau in doua .ytd partajate, nu sunt duplicate in fiecare model.

Rezultatul este direct **binar** (.ydr/.ybn/.ytd/.ytyp/.ymap, gen8 = GTA V Legacy) - nu ai nevoie de CodeWalker.
Iese gata impachetat ca **resursa FiveM** (fxmanifest + stream/).

## De ce e important .ybn (coliziunile)

GTA V nu porneste fizica statica pentru o zona doar pentru ca acolo exista modele. Fizica se activeaza
din **static bounds** - fisiere `.ybn` care se incarca singure, dupa bounding box-ul lor. Daca zona nu e
acoperita de niciun `.ybn`, **nimic** nu e solid acolo: nici terenul, nici casele, nici macar props-urile
vanilla (copaci, stanci) - cazi prin harta. De aceea generatorul scrie cate un `.ybn` per tile de teren
(`<nume>_t_XX_YY_col.ybn`), care contine mesh-ul de coliziune al terenului plus coliziunile cladirilor
care cad in acel tile, toate in coordonate mondiale. Coliziunea NU mai e pusa in `.ydr` (ar fi dubla).

## Cerinte

- Windows, Blender 4.2+ (testat pe 5.2).
- Sollumz 2.9 + dependintele lui Python (szio, pymateria). Le pune `INSTALEAZA_TOOLS.bat` in folderul `tools\`,
  izolat de Blender-ul tau (nu iti modifica nimic in Blender).

## Pasi rapizi (demo 1 km x 1 km)

1. `INSTALEAZA_TOOLS.bat` (o singura data; are nevoie de internet daca `tools\` e gol).
2. `GENEREAZA_DEMO.bat` -> dureaza 1-3 minute. Rezultatul e in `output\dzdemo\`:
   - `REZUMAT.txt` - coordonatele de spawn si instructiuni;
   - `fivem\dzdemo\` - resursa FiveM (fxmanifest + stream) - asta copiezi in server;
   - `harta_preview.png` - harta 2D (relief, paduri, drumuri, case);
   - `assets\` - fisierele binare individuale;
   - `dzdemo.blend` - scena Blender (poti edita/retusa cu Sollumz si re-exporta);
   - `textures\` - DDS + PNG de previzualizare.
3. Instaleaza in serverul FiveM: copiaza `output\dzdemo\fivem\dzdemo` in `resources\` (de ex.
   `resources\[rrp]\dzdemo`) si adauga `ensure dzdemo` in `server.cfg`. **Restart complet de server**
   (nu ajunge `refresh` / `restart dzdemo`: fisierele de streaming si coliziunile `.ybn` se inregistreaza
   doar la pornire; si clientul trebuie sa reintre pe server). Resursa este o harta clasica de streaming
   (`this_is_a_map` + `DLC_ITYP_REQUEST` pentru arhetipurile custom), fara scripturi.
4. Teleporteaza-te la coordonatele din `REZUMAT.txt` (harta e pusa implicit la X 7000+, Y -8000+, in ocean,
   departe de Los Santos, ca sa nu se suprapuna cu nimic). In FiveM: `/tp X Y Z` daca ai o comanda de teleport,
   sau din consola F8: `SetEntityCoords(PlayerPedId(), X, Y, Z, false, false, false, false)` intr-un script client.

## DayZ Map Studio (interfata grafica)

`MAP_STUDIO.bat` deschide **DayZ Map Studio** - o fereastra in care ai:

- stanga: toate setarile din `map.json`, grupate (Harta, Sate/drumuri, Vegetatie, Distante LOD, Texturi, Cai,
  Avansat), cu buton „Seed aleator” si selector de folder pentru resursele FiveM;
- dreapta: previzualizarea hartii (relief, paduri, drumuri, sate). Un click pe harta iti scrie coordonatele
  lumii GTA V, gata de copiat pentru `/gotoxyz`;
- jos: log-ul si butoanele:
  - **Salveaza map.json** - scrie setarile in `map.json`;
  - **Previzualizare** - ruleaza doar partea de numpy (fara Blender), in cateva secunde; afiseaza numarul de
    sate/cladiri/props si punctul de spawn;
  - **Genereaza** - porneste `tools\_run.bat <preset> --config map.json` (Blender headless) si iti arata
    log-ul in direct;
  - **Instaleaza in server** - copiaza `output\<nume>\fivem\<nume>` peste `<fivem_resources_dir>\<nume>`,
    cu confirmare, pastrand `editor\objects.json` care exista deja acolo;
  - **Exporta obiectele** - ruleaza `export_custom_ymap.py` (vezi mai jos);
  - **Deschide REZUMAT.txt**.

Studio-ul are nevoie doar de Python 3.10+ cu `numpy` si `tkinter` (Blender e necesar doar pentru „Genereaza”).

## Fisierul de setari `map.json`

`map.json` (langa `.bat`-uri) contine toate campurile din `MapConfig`. Cheia `"preset"` spune de la ce preset
se porneste, restul cheilor suprascriu preset-ul. O cheie necunoscuta da eroare clara. `map.example.json` e o
copie de referinta.

```json
{ "preset": "demo", "name": "dzdemo", "seed": 1337, "size": 1024.0,
  "origin_x": 7000.0, "origin_y": -8000.0,
  "fivem_resources_dir": "C:\\FXServer\\server-data\\resources\\[rrp]",
  "custom_objects_file": "editor/objects.json" }
```

- `fivem_resources_dir` - unde se instaleaza resursa (implicit `C:\FXServer\server-data\resources\[rrp]`);
- `custom_objects_file` - unde scrie editorul din joc, **relativ la folderul resursei instalate**.

`.bat`-urile de generare adauga automat `--config map.json` daca fisierul exista. Din linia de comanda:

```
blender -b -P run_dayz_map.py -- --config map.json
blender -b -P run_dayz_map.py -- --config map.json --seed 42     (argumentele CLI bat map.json)
```

## Obiecte puse manual din joc (editorul)

Editorul in joc (resursa separata) scrie `<resursa>\editor\objects.json`:

```json
{ "version": 1,
  "objects": [ { "id": "o_1694000000_1", "model": "prop_container_01a",
                 "x": 7530.2, "y": -7250.1, "z": 14.6, "rx": 0, "ry": 0, "rz": 90.0, "lod": 150 } ],
  "removed": [ 123456789 ],
  "exportedAt": 1694000123456 }
```

- coordonatele sunt mondiale, rotatiile in grade, in ordinea GTA (rx, ry, rz);
- `removed` = GUID-urile entitatilor **generate** care trebuie sterse din harta;
- `exportedAt` = momentul ultimului export (epoch in **milisecunde**); il scrie exportul, nu editorul.
  Editorul spawneaza la runtime doar obiectele mai noi decat aceasta valoare (restul sunt deja in `.ymap`).

La fiecare generare, in resursa se scriu si:

- `editor\entities.json` - `[{ "guid", "model", "x", "y", "z", "rz", "kind" }]` pentru **toate** entitatile
  generate (fara tile-urile de teren), ca editorul sa poata identifica dupa model+pozitie obiectul pe care ai
  dat click si sa-i puna GUID-ul in `removed`. `kind` este `tree|bush|rock|landmark|small|wreck|building`;
- `editor\chunks.json` - continutul complet al fiecarui `.ymap` generat (arhetip, pozitie, rotatie, scara,
  LOD, extents, flags, GUID), ca sa se poata reconstrui ymap-urile **fara Blender**.

`EXPORT_OBIECTE.bat` (sau butonul „Exporta obiectele” din studio) ruleaza `export_custom_ymap.py`:

- citeste `map.json` -> folderul resursei -> `editor\objects.json`;
- scrie `stream\<nume>_custom.ymap` cu obiectele puse manual;
- daca `removed` nu e gol, rescrie din `editor\chunks.json` doar ymap-urile afectate, fara entitatile sterse;
- scrie `exportedAt` inapoi in `objects.json` (pastrand `objects`, `removed` si orice alte chei).

Nu are nevoie de Blender. Scrierea binara se face cu `szio` + `pymateria` din `tools\pydeps`; modulul nativ
`pymateria` e compilat pentru Python 3.13 (acelasi cu al Blender-ului), asa ca daca Python-ul tau de sistem
nu il poate incarca, scriptul se re-lanseaza automat cu `python.exe` din instalarea de Blender.

Dupa export: **restart complet de server** (si reintra pe server cu clientul).

## Presets

| Preset | Latura | Sate | Timp aprox. | Comanda |
|--------|--------|------|-------------|---------|
| tiny   | 512 m  | 1    | 30 s        | `GENEREAZA_TINY.bat` |
| demo   | 1024 m | 2    | 1-3 min     | `GENEREAZA_DEMO.bat` |
| full   | 4096 m | 10   | 10-25 min   | `GENEREAZA_FULL.bat` |

Argumente suplimentare (se pot pune dupa numele .bat-ului sau in linia de comanda):

```
GENEREAZA_DEMO.bat --seed 42                  alt relief / alta asezare a satelor
GENEREAZA_FULL.bat --size 2048 --name dzmare  alta marime (multiplu de 256) si alt prefix de fisiere
GENEREAZA_DEMO.bat --origin 9000 -9000        alta pozitie in lumea GTA V (coltul SV al hartii)
GENEREAZA_DEMO.bat --gen9                     exporta si varianta GTA V Enhanced (gen9)
GENEREAZA_DEMO.bat --ragemp                   construieste si un dlc.rpf (RAGE:MP), daca ai nevoie vreodata
```

Linie de comanda directa (orice Blender cu Sollumz instalat):

```
blender -b -P run_dayz_map.py -- --preset demo --seed 42
```

Toti parametrii (densitatea padurii, numarul de case per sat, distantele de LOD, marimea texturilor etc.)
sunt in `dayzgen/config.py` (clasa `MapConfig` si dictionarul `PRESETS`).

## Ce genereaza, pe scurt

`dayzgen/` este un pachet Python:

| Modul | Rol |
|-------|-----|
| `noise.py` | Perlin / fBm / ridged / Worley vectorizat (numpy), tileable |
| `textures.py` | texturi procedurale (iarba, pamant, stanca, nisip, tencuiala, lemn, caramida, tigla, tabla, fereastra, usa) + normal maps |
| `dds_writer.py` | encoder DXT1/DXT5 cu mipmap-uri (fara dependinte) |
| `terrain.py` | relief (domain-warped fBm + ridged), insula, sate, drumuri prin A* pe panta, nivelare, campuri, straturi de textura, vegetatie, props |
| `buildings.py` | case/hambar/sopron low-poly cu UV-uri, ferestre, usi, cos de fum, mesh de coliziune |
| `blender_build.py` | mesh-uri Blender, materiale Sollumz, LOD-uri, compozite de coliziune, export .ydr + .ybn |
| `gta_export.py` | .ytd, .ytyp, .ymap (chunk-uri, extents), `editor/*.json`, resursa FiveM (si optional `dlc.rpf`) |
| `main.py` | orchestrare + `REZUMAT.txt` |

In radacina proiectului:

| Fisier | Rol |
|--------|-----|
| `map_studio.py` / `MAP_STUDIO.bat` | interfata grafica (setari, previzualizare, generare, instalare) |
| `export_custom_ymap.py` / `EXPORT_OBIECTE.bat` | export obiecte manuale -> `.ymap`, fara Blender |
| `map.json` / `map.example.json` | setarile hartii |

## Cum modifici harta manual

Deschide `output\<nume>\<nume>.blend` intr-un Blender cu Sollumz instalat (poti folosi zip-ul din `tools\`).
Tile-urile de teren sunt drawable-uri `dz..._t_XX_YY`, cladirile `dz..._house_a` etc. Dupa modificari,
selecteaza obiectele si exporta din Sollumz (File > Export > Sollumz / Export Assets) in folderul `assets\`,
apoi ruleaza din nou impachetarea (sau pune fisierele manual in rpf / stream).

Pentru pozitiile copacilor/props-urilor: sunt doar entitati in .ymap (nu obiecte Blender), ca sa nu incarce
scena. Le poti edita in CodeWalker sau poti schimba densitatile in `config.py` si regenera.

## Limitari cunoscute (varianta 0.1)

- Casele nu au interior (sunt solide); DayZ-ul adevarat are cladiri enterabile - se pot adauga ulterior ca modele
  separate in `buildings.py`.
- Nu exista inca ierarhie LOD intre ymap-uri (teren "far" cu parinti LOD/SLOD): tile-urile se vad pana la
  `lod_dist_terrain` (700 m). Pentru harta `full` merita adaugat un strat SLOD.
- Apa este oceanul standard al jocului la Z=0 (nu se genereaza lacuri / rauri).
- Nu se genereaza navmesh (.ynv) - NPC-urile nu se pot plimba, dar jucatorii si vehiculele merg normal.
