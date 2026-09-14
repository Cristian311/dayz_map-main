# Ghid Blender pentru harti (o pagina)

Pornesti **`BLENDER_EDITOR.bat`**. Ecranul are trei parti:

- **viewport** (sus, mare): harta ta;
- **Asset Browser** (jos): modelele din GTA V, pe categorii (Case, Blocuri, Turnuri, Magazine, Hale,
  Garaje, Props/Garduri, Props/Vegetatie...). `Bucati (avansat)` are bucati de cladiri, de obicei nu-ti trebuie;
- **tab-ul Harta** (dreapta): toate uneltele si exportul. Daca bara din dreapta lipseste: tasta **N**.

Daca jos nu vezi Asset Browser-ul, apesi **Deschide biblioteca GTA** in tab-ul Harta. Manual: iconita din
stanga barei de jos -> Asset Browser, apoi sus-stanga in el alegi biblioteca **GTA V (generator)**.

## Tastele de care ai nevoie

| Ce vrei | Cum |
|---|---|
| Rotesti vederea | tii apasata rotita mouse-ului si misti mouse-ul |
| Muti vederea | Shift + rotita apasata |
| Zoom | rotita |
| Vezi obiectul selectat de aproape | **F** |
| Vezi toata harta | **Home** |
| Selectezi | click stanga (Shift + click adauga la selectie, **Alt+A** deselecteaza tot) |
| Muti obiectul | **G**, misti mouse-ul, click stanga (dupa G: **X** sau **Y** = doar pe axa aia) |
| Rotesti | **R**, misti mouse-ul, click (**R Z 45 Enter** = exact 45 de grade) |
| Copiezi | **Shift+D**, misti, click |
| Stergi | **X** sau **Delete** |
| Pui pe sol | **J** |
| Anulezi / refaci | **Ctrl+Z** / **Ctrl+Shift+Z** |
| Salvezi harta | **Ctrl+S** (fisierul `.blend` e harta ta) |
| Vezi texturile ca in joc | **Z**, apoi Material Preview |

Orice miscare inceputa cu G, R sau S se anuleaza cu click dreapta sau Esc.

## Cum faci o harta

1. **Harta noua** (tab-ul Harta, sectiunea 1): alegi centrul, latura si cota; apare terenul (placi de
   100 m), sageata de spawn si cutia cu limitele hartii. Centrul implicit e in ocean, langa harta dzdemo.
2. **Cladiri**: tragi o miniatura din Asset Browser in viewport. Apesi **J** ca sa stea pe sol.
   **Lipeste de vecin** o roteste la fel ca cea de langa ea si o lipeste de ea, pentru siruri de cladiri.
   **90 stanga / 90 dreapta** o intorc.
3. **Garduri, stalpi, copaci**: **Deseneaza linie**, click pe teren pentru fiecare punct, Enter la final
   (C inchide linia, ca o zona). Apoi selectezi linia, Shift + click pe obiect (un gard, un stalp) si
   **Multiplica**: copii de-a lungul liniei (Pas 0 = lipite; Departare = cat stau in lateral; pe ambele parti
   pentru o strada). Pentru o linie inchisa: selectezi zona si cateva obiecte (copaci, tufe), apoi
   **Imprastie in zona**.
4. **Rigla** (sectiunea 4) masoara distante; **Selectie** te intoarce la selectat.
5. **Cladiri generate** (sectiunea 5): alegi tipul (vila, casa, bloc de caramida, magazin, hala), marimea,
   etajele, acoperisul, texturile (GTA sau simple) si daca are interior. **Shift + click dreapta** pe teren
   pune cursorul 3D acolo unde vrei cladirea, apoi **Genereaza**. **Seed nou** (sageata de langa seed) da
   alta varianta; cu o cladire generata selectata, o reface pe loc. **Refa cu setarile de sus** schimba
   cladirea selectata dupa panou, **Ia setarile ei** pune in panou setarile ei.
5. **Export FiveM** (jos in acelasi tab): numele resursei, apoi **Exporta in FiveM**. Prima data pui
   `ensure <nume>` in `server.cfg`; dupa fiecare export repornesti jocul (FiveM incarca modelele noi doar
   la pornire).

## Editorul de oras (desenezi tu, generatorul umple)

**`EDITOR_ORAS.bat`** (sau butonul din `GENERATOR.bat`) deschide editorul in browser. Uneltele (litera = tasta):
**R Strada**, ca in Cities: Skylines, cu modurile **1 Drept**, **2 Curb** (click inceput, click unde se
indoaie, click capat), **3 Liber** (fiecare bucata continua lin din cea dinainte) si **4 Schimba tip** (click pe
o strada: devine tipul ales). Vezi strada inainte sa o pui (latimea reala, lungimea, unghiul, inaltimea, panta);
se lipeste de noduri si de strazi, iar unghiul se prinde la 15 / 90 de grade fata de strada din care pleci
(linie galbena). Unde treci peste o strada apare singura o intersectie (punct verde; rosu = unghi prea
ascutit). PageUp / PageDown = inaltimea nodului urmator; Shift = fara lipire de unghi, Ctrl = grila de 5 m,
Alt = fara nicio lipire; click dreapta / Esc = un pas inapoi, Enter sau dublu-click = gata.
**C Curbeaza** (tragi de strada), **Z Zona** (click in cvartal: blocuri LC caramida, centru/turnuri, suburbie,
industrial, parc, piateta, parcare), **X Sterge**, **V Selecteaza/muta** (noduri, colturi de suprafete, cladiri,
obiecte). Tab = 2D/3D (3D: tragi cu stanga = roteste, cu dreapta = muta, rotita = zoom). Ctrl+Z / Ctrl+Y (un
pas = o actiune: o bucata de strada, o tragere de pensula), salvare automata in `output\orase\<nume>.json`.

- **T Teren**: pictezi dealurile ca in Cities: Skylines. Tragi = ridici, Shift = cobori, Ctrl = netezesti,
  Alt = platou (1-4 aleg modul, [ si ] = marimea). Strazile stau pe teren si urca singure cu el; in 2D relieful
  se vede colorat, cu curbe de nivel, iar strada selectata are un grafic cu profilul ei (in dreapta).
- **Poduri si tuneluri**: la desenat, PageUp / PageDown ridica strada urmatoare fata de teren; peste +4 m iese
  pod, sub -4 m tunel. Unde trece peste o strada apare un patrat albastru (pasaj, fara intersectie). In dreapta,
  la strada selectata, **Nivel** = la sol / pod / tunel. Podul are parapet si piloni, tunelul pereti, tavan si
  portaluri. **H Inaltime nod** (rotita peste nod) e pentru rampe; "Pe teren" pune nodul inapoi pe teren.
- **Tipuri de strada**: in cardul Strada, **+ Tip nou**: benzi pe sens, latimea benzii, trotuar, mediana (iarba
  sau beton), parcare pe margini, copaci pe trotuar, distanta intre stalpi. Tasta 4 (Schimba tip) il pune pe
  strazile existente.
- **P Suprafata**: click pe fiecare colt, Enter = gata. Parc, piateta, parcare cu locuri trasate, teren de
  baschet, gazon cu copaci, o zona de cladiri (de ex. blocuri doar pe o latura a unui cvartal de case) sau
  **apa** (lac, rau, port; poate fi oriunde, cu chei de beton; in joc e marea GTA). Colturile se trag cu V.
- **B Pensula**: copaci, tufe, banci, gunoaie, tomberoane, masini abandonate, containere, stalpi, mobilier
  stradal, bariere. Tragi = pictezi, Shift = stergi, "Cate unul" = pui unul si il rotesti tragand.
- **K Cladire**: o cladire aleasa de tine (bloc, casa, vila, magazin, hala, sectie de politie, spital, turn) sau
  una din GTA (cautare in catalog); se intoarce singura spre strada. Cvartalele o ocolesc la generare.
- **Mobilier stradal automat** (in Setarile orasului): stalpi de iluminat, semafoare la intersectii, hidranti,
  cosuri, automate de ziare, statii de autobuz pe artere.

Avertismentele (unghiuri prea ascutite, pante prea mari, strazi care se taie fara nod) apar in dreapta; click
pe unul te duce acolo. **Genereaza orasul** il construieste in Blender (`output\orase\<nume>.glb` + `.blend`),
apoi **Blender** il deschide. Planurile `demo`, `bohan` (Bronx-ul din GTA IV) si `exemple\complet` (pod, lac,
parc, parcare, bulevard cu mediana, deal) sunt exemple.

**In joc (FiveM):** dupa Genereaza, butonul **FiveM** (sus) face resursa direct in `resources\[gta_bucuresti]`, cu
orasul mutat in ocean (in dreapta, cardul **In joc**: numele resursei, X / Y si cati metri sta deasupra marii;
implicit X 6000, Y -2600, 25 m peste mare, ca valurile din larg sa nu treaca prin strazi; nu pune orasul la sud de
Y -4000 langa X 4400..5200, acolo e insula Cayo Perico, incarcata mereu din build 2189, departe de Los Santos si de harta dzdemo). Apoi **Adauga ensure in server.cfg**
(o singura data), repornesti serverul si jocul si mergi la coordonatele scrise acolo.

**Import:** *Imagine de fundal* pune o harta sau o schita (PNG/JPG) sub plan; cu unealta **F** o tragi la loc,
rotita o mareste, Shift + rotita o roteste, in dreapta ii dai latimea reala in metri si opacitatea; apoi
desenezi strazile peste ea. *Importa plan* deschide un plan `.json` (de ex. primit de la altcineva).
Zona **Blocuri-turn pe gazon** = blocurile de caramida inalte si izolate din Bohan, cu copaci intre ele.

## Generatorul (toate uneltele intr-o fereastra)

**`GENERATOR.bat`** deschide o fereastra cu tab-urile **Cladire**, **Rand de cladiri**, **Strazi**, **Cartier**.
Alegi o setare prestabilita sau scrii tu valorile, apesi **Genereaza**, apoi **Deschide in Blender** (sau
tragi `.glb`-ul in Blender). **Salveaza ca...** tine setarile tale (apar cu "(al meu)"). La cartier: alei
intre cladiri, cvartale cu alee pe mijloc, turnuri in piateta, parcari, parcuri si **relief** (dealuri line;
"lungimea dealurilor" mai mare = mai lin). Cu relief, cartierul vine cu teren in jur.
Fisierele `.bat` de mai jos fac acelasi lucru, doar cu intrebari in consola.

## O cladire intr-un fisier, fara tab-ul Harta

**`GENEREAZA_CLADIRE.bat`**: raspunzi la cateva intrebari (Enter = implicit) si apare
`output\cladiri\<tip>_<seed>.glb` (+ `.blend`). Tragi `.glb`-ul in fereastra Blender. Pentru export in FiveM
e mai bun `.blend`-ul: File > Append > fisierul > Object > cladirea (pastreaza materialele Sollumz).
Variantele 13-15 fac un **rand de blocuri lipite** (60-100 m, fiecare alta); din `.blend` il aduci cu
File > Append > Collection.

**`GENEREAZA_STRADA.bat`**: piese de strada (strada 2 benzi, artera 4 benzi, alee): drept 20/10 m, trecere de
pietoni, intersectie in cruce si in T, curba, capat; "tot kitul" le pune pe toate intr-un fisier
(`output\strazi`). Le copiezi cu **Shift+D** si le lipesti prin colturi: in bara de sus pornesti magnetul
si alegi **Snap To: Vertex**, apoi **G** si duci coltul piesei langa coltul celeilalte (se prinde singur).
**R Z 90 Enter** o roteste. Toate stau cu baza la Z = 0: asfaltul e la 5 cm, trotuarul la 20 cm.

**`GENEREAZA_CARTIER.bat`**: un cartier intreg in grila, ca Liberty City: bulevarde (4 benzi) pe o directie,
strazi pe cealalta, intersectii cu treceri de pietoni, blocuri lipite pe toate laturile fiecarui cvartal (mai
inalte spre centru), curti la mijloc si cate un parc. Alegi marimea (2 x 2 ... 5 x 4 cvartale), inaltimea,
marimea unui cvartal si seed-ul; iese in `output\cartiere`. Bratele intersectiilor de pe margine raman
deschise: acolo continui cu piese din kitul de strada (bulevard = artera, strada = strada). In `.blend`
fiecare rand de cladiri e un obiect gol parinte: il stergi sau il muti cu tot randul. Parcurile au alei curbe,
o piateta cu fantana, banci, cosuri, tufe si copaci din GTA (colectia "Vegetatie si mobilier"); in `.blend`
sunt referinte GTA, deci la export raman modelele jocului, cu coliziunea lor.

## Bine de stiut

- Modelele GTA raman referinte la joc: in resursa nu intra geometria lor, doar pozitia. Un model GTA
  trebuie scalat la fel pe X si Y (Z poate fi diferit).
- Poti adauga si obiecte proprii (Shift+A in viewport, de ex. Mesh > Cube): se exporta ca modele noi, cu
  coliziune. Un model GTA pe care l-ai modificat il marchezi cu **Model nou** in panoul de export.
- Liniile desenate nu ajung in joc; sunt doar ghidaje.
- Daca ceva nu merge, detaliile exportului sunt in `output\fivem_export\<nume>\export.log`.
