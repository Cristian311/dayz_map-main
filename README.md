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

Capcana (rezolvata): compozitul **si** copiii BVH trebuie sa stea la 0,0,0, iar pozitia mondiala sa fie
direct in vertecsi (regula din tutorialul Sollumz "Creating Static Collisions"). Daca BVH-ul e mutat prin
transform, exportul scrie AABB-urile copiilor in spatiul local (in jurul lui 0,0,0) si jocul nu gaseste
niciodata coliziunea la pozitia reala, desi bounding box-ul compozitului e corect si fisierul se incarca.

## Harta pe radar si pe harta mare (minimap)

Generatorul scrie si `minimap/<nume>_minimap.gfx` (un Scaleform/SWF care contine imaginea din
`harta_preview.png`, latura = `minimap_px` din `map.json`, implicit 1024 px) plus `client/minimap.js`.
Scriptul incarca overlay-ul cu `AddMinimapOverlay` si il aseaza in coordonate de joc cu
`SetMinimapOverlayDisplay(id, origin_x, -(origin_y + size), 100*size/px, ...)`, deci imaginea apare exact
peste harta, atat pe radar cat si pe harta mare din pauza. Ambele fisiere sunt declarate automat in
`fxmanifest.lua` (`files` + `client_script`). Daca vrei alta imagine, inlocuieste PNG-ul in
`dayzgen/preview.py` sau scrie `.gfx`-ul din orice imagine cu `dayzgen.minimap_swf.write_minimap_gfx`.

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

## Generator de orase: catalogul de arhetipuri vanilla (faza A)

Cladirile de oras nu se genereaza procedural la calitatea GTA V. Ce se poate face e sa
folosim modelele de cladire care exista deja in joc (au LOD-uri, coliziuni si texturi
facute de artisti) si sa le asezam corect pe loturi generate. Pentru asta generatorul
are nevoie de **amprenta exacta** a fiecarui model - si aia nu se poate ghici din nume.

`dayzgen/city/` este stratul urban (numpy + json, fara Blender). Primul modul,
`catalog.py`, tine fisa tehnica a fiecarui model: cutia (bbox), inaltimea, cat coboara
sub origine, categoria (`tower`, `midrise`, `lowrise`, `shop`, `house`, `warehouse`,
`garage`, `filler`, `prop`) si stilul (`downtown`, `vinewood`, `suburb`, `industrial`,
`beach`, `country`). Rezultatul: `dayzgen/data/catalog.json`.

### Varianta 0 (recomandata): direct din fisierele jocului

```
python tools\catalog_from_game.py              zonele de oras (_citye, _cityw)
python tools\catalog_from_game.py --all        toata harta
python tools\catalog_from_game.py --area _citye
```

Citeste arhivele `.rpf` ale GTA V cu `szio` (din `tools\pydeps`), gaseste toate `.ytyp`-urile
si ia din ele numele exact si cutia exacta a fiecarei cladiri. Nu are nevoie de CodeWalker si
nici de joc pornit. Calea jocului o ia din `CitizenFX.ini` al FiveM (sau `--gta "<cale>"`).
Arhivele criptate se pot citi doar cu Python-ul din Blender (modulul nativ `pymateria` e
compilat pentru Python 3.13); scriptul se re-lanseaza singur cu el.

Arhetipurile importate au `ok = false`: stim ca exista si ce cutie au, dar unele `.ytyp` de
harta se incarca doar cand esti in zona lor. Dupa import ruleaza `CATALOG.bat --candidates`
si `/catalogscan` in joc: numele importate sunt verificate primele si marcate `ok`.

Doua limite de stiut. Rockstar imparte fiecare cvartal in zeci de piese (sol, drum, overlay,
detalii, decaluri, balcoane); filtrul pe nume taie majoritatea, dar nu pe toate, asa ca
verifica vizual cu `/catalog <nume>` inainte sa te bazezi pe o categorie. Si cladirile de
harta **nu au coliziune proprie** (doar cele cu eticheta `phys`): coliziunea lor e in `.ybn`-ul
zonei originale, deci mutate pe alta harta se vad, dar nu sunt solide pana nu le coacem
coliziunea in `.ybn`-ul nostru (faza C).

### Varianta 1: masurat din joc (fara alte unelte)

```
CATALOG.bat --candidates        scrie dayzgen\data\candidates.json (~291.000 nume de incercat)
```

apoi in joc, ca admin nivel 5 (resursa `rrp_mapeditor`):

```
/catalogscan          faza 1: intreaba jocul ce nume exista (IsModelInCdimage), cateva secunde
                      faza 2: incarca fiecare model valid si ii citeste cutia, cateva minute
/catalogstop          opreste scanarea
/catalog <model>      pune un model in fata ta, cu cutia desenata si dimensiunile scrise
                      (Q/E roteste, DEL sterge; linia verde = fata modelului, adica strada)
/catalogstats         cate modele are catalogul
/catalogmerge         ruleaza make_catalog.py fara sa mai scanezi
```

Scanarea scrie `dayzgen\data\measurements.json` direct in folderul generatorului
(calea vine din convarul `rrp_map_generator_dir`) si la final porneste singura
`make_catalog.py`, care clasifica si scrie `catalog.json`.

Numele se obtin in trei feluri, combinate: prop-urile de mobilier urban sunt o lista fixa
in `dayzgen/city/seed_names.py`; cladirile se incearca combinatoric pe schema Rockstar
`<zona>_<NN>_<ceva>` (`dt1_11_bld1`, `bh1_08_house3`, `id1_04_warehouse1`...); si orice
lista de nume pusa ca `.txt`/`.ini` in `dayzgen/data/namelists/` (de exemplu
`ObjectList.ini` de la Menyoo) e citita automat. Numele inexistente sunt aruncate de joc
instant, deci ghicitul nu costa decat secunde de scanare.

### Varianta 2: import din CodeWalker (mai precis, mai rapid)

Daca ai CodeWalker: RPF Explorer -> search `.ytyp` -> selectezi fisierele -> Export XML.

```
python tools\import_ytyp_xml.py D:\ytyp_xml
```

Ia numele si cutiile direct din fisiere, fara scanare in joc. Cele doua variante se pot
amesteca - importul si scanarea scriu in acelasi `catalog.json`.

### Corectii manuale

Clasificarea automata greseste uneori (o hala turtita si un bloc scund au aceeasi cutie):

```
CATALOG.bat --stats                       ce are catalogul acum, pe categorii
CATALOG.bat --tag dt1_11_bld1 tower downtown
CATALOG.bat --block ss1_03_garage         scoate un model urat din plasare
CATALOG.bat --reclassify                  re-aplica regulile automate peste tot
```

Etichetele puse manual (categorie, stil, `yaw_offset`, `blocked`) **nu** se pierd la
re-scanare sau re-import.

## Oras generat, vazut in Blender cu modelele reale din GTA V

Generatorul face strazile, zonele si cladirile. Blender e locul in care vezi orasul cu modelele
si texturile originale din joc si il retusezi. Editorul din joc ramane pentru detalii.
Formatul de schimb intre ele e harta GTA (`.ymap`).

```
python generate_city.py                          orasul, din map.json (orasul pornit automat)
python generate_city.py --preset demo --radius 280 --seed 7
BIBLIOTECA_GTA.bat                               modelele din joc in Blender + scena orasului
BLENDER_EDITOR.bat                               deschide scena in Blender, cu Sollumz configurat
```

`generate_city.py` scrie in `output\<nume>_oras\`:

| Fisier | Ce e |
|--------|------|
| `<nume>_city.ymap` | cladirile, in coordonate de lume, pentru joc si pentru Blender |
| `plan.json` | loturile si cladirile |
| `terrain.npz` | relieful, strazile si zonele, pentru scena din Blender |
| `ytyps.txt` | fisierele `.ytyp` din joc de care au nevoie cladirile |
| `preview.png` | harta 2D, cu amprentele cladirilor colorate pe categorie |

Cum alege cladirile: fiecare zona are categoriile ei (turnuri si blocuri in centru, case in
suburbie, hale in zona industriala), retragerea de la trotuar si marimea lotului. Pe fiecare
lot se pune un model din catalog care incape, cu fata spre strada, asezat pe coltul cel mai de
jos al terenului. Modelele din port, aeroport si zonele industriale merg doar in zona industriala.
Cele cu LOD propriu (eticheta `haslod`) au o sansa mai mare, iar un model deja folosit pierde
repede din sansa, ca orasul sa nu se repete. Unghiul gridului se alege dintre 8
incercari, dupa cate cvartale incap pe relief.

Nici numele, nici LOD-ul propriu nu spun sigur ce e o cladire intreaga. De aceea
`python tools\measure_solidity.py --all` incarca geometria fiecarui model din joc si masoara cat
din amprenta lui e acoperit de acoperis, vazut de sus. Conteaza doar suprafetele de deasupra unui
sfert din inaltime, ca planurile de la sol (iarba, umbre, apa) sa nu para acoperisuri. Modelele peste prag primesc eticheta `solid`,
iar plasatorul le foloseste doar pe ele (eticheta `cov:NN` pastreaza procentul masurat).

`BIBLIOTECA_GTA.bat` foloseste functia Sollumz de biblioteca de modele: citeste direct arhivele
jocului (fara CodeWalker) si face cate un `.blend` pentru fiecare `.ytyp` din `ytyps.txt`, in
`output\gta_asset_library\`. Prima rulare indexeaza tot jocul si dureaza cateva minute; dupa aceea
construieste doar fisierele noi. La final face `<nume>_city.blend` si `render.png`.

Unele texturi nu sunt in dictionarul propriu al cladirii, ci in dictionare comune ale jocului,
iar Sollumz nu le gaseste: in Blender apar roz. Ultimul pas al bibliotecii le cauta dupa nume in
toate `.ytd`-urile jocului si le scrie ca `.dds` langa biblioteca, unde Blender le cauta singur
(`tools\gta_textures.py` face acelasi lucru separat).

In Blender (`BLENDER_EDITOR.bat`), fiecare entitate din `.ymap` e modelul real, cu texturi:
- muti, rotesti sau stergi cladiri direct in scena;
- adaugi cladiri noi din Asset Browser, biblioteca „GTA V (generator)”;
- adaugi obiecte proprii (mesh-uri modelate, sculptate sau generate);
- exporti totul in FiveM cu panoul de mai jos.

Strazile generate sunt deocamdata doar teren nivelat (fara asfalt si borduri).

## Harta facuta de mana in Blender (tab-ul Harta)

Pentru cine nu stie Blender: [GHID_BLENDER.md](GHID_BLENDER.md), o pagina cu tastele si pasii.

`BLENDER_EDITOR.bat` aranjeaza singur ecranul: viewport cu texturile vizibile, **Asset Browser** jos, pe
biblioteca „GTA V (generator)”, si tab-ul **Harta** in bara din dreapta (tasta N). Uneltele, in ordine:

| Unealta | Ce face |
|---|---|
| *Harta noua* | teren plat din placi de 100 m (fiecare placa e un model separat, vizibil de la 1,5 km), sageata de spawn, cutia cu limitele hartii |
| *Pune pe sol* (tasta **J**) | asaza obiectele selectate cu baza pe teren (la cladirile GTA originea e de obicei la mijlocul cutiei, nu jos) |
| *90 stanga / 90 dreapta* | rotire in pasi de 90 de grade |
| *Lipeste de vecin* | ia orientarea celui mai apropiat obiect si il lipeste de el, cu fatadele in linie |
| *Deseneaza linie* | click-uri pe teren, Enter la final, C inchide linia (zona) |
| *Multiplica* | copii ale obiectului de-a lungul liniei selectate (pas, departare, pe ambele parti) sau drept in fata lui |
| *Imprastie in zona* | copii la intamplare ale obiectelor selectate, in interiorul unei linii inchise |
| *Rigla* | masurat distante |

**Generatorul de cladiri** (`tools/blender_gen_buildings.py`, sectiunea 5 din tab): vila in stil Vinewood
(tencuiala, pietre de colt, acoperis in patru ape), casa (doua ape, veranda, garaj), bloc de caramida in stil
Liberty City (buiandrugi, cornisa, atic, scara de incendiu, rezervor de apa, magazine la parter), magazin
(vitrine, copertine, firma), hala (rulouri, tabla). Dimensiunile implicite sunt medianele cladirilor GTA
intregi din catalog. Texturi „GTA” = materialele originale din biblioteca (cautate o data si tinute minte in
`output/gta_asset_library/_materiale_cladiri.json`); „simple” = texturile generatorului. Ferestrele au rama si
montanti din geometrie si sticla generata (texturile de fereastra din joc sunt atlase). Interiorul „simplu”
(pereti cu grosime, podele, scara, camere cu goluri de usa) e un obiect-copil separat. Acelasi seed da
aceeasi cladire; cladirile se exporta ca modele noi, cu coliziune.

Copiile folosesc acelasi model (ca Alt+D), deci la export devin tot referinte GTA, nu modele noi.
Liniile desenate nu se exporta. Tasta **F** centreaza vederea pe selectie.

Biblioteca din Asset Browser e pe categorii: Case, Cladiri mici, Blocuri, Turnuri, Magazine si
benzinarii, Hale si depozite, Garaje si anexe, Props/Garduri si porti, Props/Vegetatie, Props/Stalpi si
semne, Props/Mobilier stradal etc. In categoriile principale intra doar cladirile masurate ca intregi
(`solid`); restul stau in `Bucati (avansat)`. Fiecare model are descrierea cu dimensiunile si etichete
(`mic/mediu/mare`, stilul zonei). `tools\blender_library_catalogs.py` face organizarea si ruleaza singur la
finalul fiecarui import; `IMPORTA_GTA.bat props` aduce props-urile utile (lista in `tools\props_ytyps.txt`).

## Export din Blender in FiveM

`BLENDER_EDITOR.bat` incarca si panoul de export: in viewport, bara laterala (tasta N), tab-ul
**FiveM**. *Exporta in FiveM* scrie resursa hartii in folderul de resurse al serverului (implicit
`fivem_resources_dir` din `map.json`); o singura data adaugi `ensure <nume>` in `server.cfg`.
Exportul ruleaza intr-un Blender separat, pe o copie a scenei, deci fisierul deschis nu se schimba.
*Verifica* numara ce se exporta si cum, fara sa scrie nimic.

| Obiect vizibil in scena | In resursa |
|-------------------------|------------|
| model tras din biblioteca „GTA V (generator)” | referinta la joc: nume, pozitie, rotatie, scala; fara geometrie si texturi |
| orice alt mesh (modelat, sculptat, generat, cu modificatori) | model nou `.ydr`, cu texturile incorporate |
| interior GTA (MLO) | nu se exporta inca |

- **Cladirile GTA din fisierele `.ytyp` cu `_strm`** se incarca in joc doar langa locul lor
  original. Exportul le copiaza definitia in `<nume>_types.ytyp`, sub numele `<nume>_<model>`,
  cu acelasi model si aceleasi texturi din joc, ca sa se vada oriunde pe harta. Locul fisierelor
  `.ytyp` in arhivele jocului se retine in `output\ytyp_index.json` (se face o data, in cateva secunde).
- **Scala**: GTA are o singura scala pentru X si Y si alta pentru Z; la modelele GTA se foloseste X.
  La modelele noi scala intra in geometrie, deci merge orice scala, inclusiv oglindirea.
- **Materialele** modelelor noi trec automat pe shader-e GTA (conversia Sollumz). Texturile PNG/JPG
  devin DDS, iar un material fara textura primeste o textura de culoarea lui.
- **Coliziunea** (`.ybn` static, cate unul la 200 m) se coace din geometria simplificata, pentru
  modelele noi si pentru cladirile GTA, care in afara locului lor original nu sunt solide. Modelele
  cu coliziune proprie (props) nu primesc alta.
- Obiectele care impart acelasi mesh (Alt+D), fara modificatori si cu aceeasi scala, devin un singur model.
- Coordonatele din Blender sunt chiar coordonatele din GTA; *Mutare* le deplaseaza pe toate.
- *Vizibile de la* e distanta minima de la care se vad cladirile (peste 10 m) si modelele noi.

Pe obiectul activ: *Model nou* exporta un model GTA ca model propriu (de exemplu dupa ce l-ai
sculptat), iar *Fara coliziune* il lasa fara coliziune (decor prin care se poate trece).

Fara interfata:

```
tools\_blender.bat -b oras.blend -P tools\blender_fivem_export.py -- --name oras_meu
    [--out <folder resurse>] [--offset x,y,z] [--lod 300] [--no-gta-col]
```

La fiecare export folderul `stream` al resursei se rescrie. Un folder existent care nu a fost scris
de export (fara fisierul `.export_blender`) nu se atinge.

## Limitari cunoscute (varianta 0.1)

- Casele nu au interior (sunt solide); DayZ-ul adevarat are cladiri enterabile - se pot adauga ulterior ca modele
  separate in `buildings.py`.
- Nu exista inca ierarhie LOD intre ymap-uri (teren "far" cu parinti LOD/SLOD): tile-urile se vad pana la
  `lod_dist_terrain` (700 m). Pentru harta `full` merita adaugat un strat SLOD.
- Apa este oceanul standard al jocului la Z=0 (nu se genereaza lacuri / rauri).
- Nu se genereaza navmesh (.ynv) - NPC-urile nu se pot plimba, dar jucatorii si vehiculele merg normal.
