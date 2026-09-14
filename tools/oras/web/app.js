/* Editor de oras: desenezi strazile (orice unghi), inaltimile la intersectii, zonele cvartalelor; vezi planul
   in 2D si 3D; Genereaza ruleaza tools/gen_oras.py in Blender. Vue 2 + canvas + three.js, fara build. */
(function () {
  'use strict';

  const ZONES = [
    { id: 'lc_caramida', nume: 'Blocuri LC caramida', culoare: '#b5523b', h: 17 },
    { id: 'centru', nume: 'Centru / turnuri', culoare: '#6b82b0', h: 48 },
    { id: 'proiecte', nume: 'Blocuri-turn pe gazon (Bohan)', culoare: '#8c5a44', h: 45 },
    { id: 'suburbie', nume: 'Case / suburbie', culoare: '#d9b25f', h: 6 },
    { id: 'industrial', nume: 'Industrial / port', culoare: '#8d8d8d', h: 9 },
    { id: 'parc', nume: 'Parc', culoare: '#4f9a4a', h: 0.6 },
    { id: 'piateta', nume: 'Piateta', culoare: '#c9c2b0', h: 0.3 },
    { id: 'parcare', nume: 'Parcare', culoare: '#5a606b', h: 0.3 },
    { id: 'gol', nume: 'Gol (doar curte)', culoare: '#777777', h: 0.3 },
  ];
  const ZMAP = {};
  ZONES.forEach(z => { ZMAP[z.id] = z; });
  ZMAP.apa = { id: 'apa', nume: 'Apa', culoare: '#2d6f9f', h: 0 };
  const ROAD_W = { strada: { r: 8, s: 3 }, artera: { r: 14, s: 3.5 }, alee: { r: 5, s: 1.5 } };
  // suprafete desenate cu unealta Suprafata (in cvartal; apa oriunde)
  const AREA_TYPES = [
    { id: 'parc', nume: 'Parc (iarba, alei, banci, copaci)', culoare: '#4f9a4a' },
    { id: 'piateta', nume: 'Piateta pavata (fantana, banci)', culoare: '#c9c2b0' },
    { id: 'parcare', nume: 'Parcare (cu locuri trasate)', culoare: '#5a606b' },
    { id: 'sport', nume: 'Teren de baschet', culoare: '#c96a3a' },
    { id: 'gazon', nume: 'Gazon cu copaci', culoare: '#6fae5a' },
    { id: 'apa', nume: 'Apa (lac, rau, port, mare) - oriunde', culoare: '#2d6f9f' },
    { id: 'plaja', nume: 'Plaja (nisip, palmieri) - oriunde', culoare: '#d9c38a' },
    { id: 'camp', nume: 'Camp (iarba, tufe, pietre) - oriunde', culoare: '#8fae5e' },
    { id: 'padure', nume: 'Padure - oriunde', culoare: '#2f6b34' },
    { id: 'lc_caramida', nume: 'Cladiri: blocuri de caramida', culoare: '#b5523b' },
    { id: 'centru', nume: 'Cladiri: centru / turnuri', culoare: '#6b82b0' },
    { id: 'proiecte', nume: 'Cladiri: blocuri-turn pe gazon', culoare: '#8c5a44' },
    { id: 'suburbie', nume: 'Cladiri: case', culoare: '#d9b25f' },
    { id: 'industrial', nume: 'Cladiri: hale', culoare: '#8d8d8d' },
  ];
  const AMAP = {};
  AREA_TYPES.forEach(a => { AMAP[a.id] = a; });
  // pensula: seturi de modele GTA (verificate in biblioteca); r = distanta minima intre doua (m)
  const PROP_SETS = [
    { id: 'copaci', nume: 'Copaci', culoare: '#3f9a3a', r: 5, m: ['prop_tree_eng_oak_01', 'prop_tree_maple_02', 'prop_tree_maple_03', 'prop_tree_birch_01', 'prop_tree_birch_02'] },
    { id: 'tufe', nume: 'Tufe', culoare: '#7cc46a', r: 1.8, m: ['prop_bush_lrg_01', 'prop_bush_lrg_02', 'prop_bush_med_01', 'prop_bush_med_03'] },
    { id: 'banci', nume: 'Banci', culoare: '#b98b5a', r: 2.6, m: ['prop_bench_01a', 'prop_bench_01b', 'prop_bench_01c', 'prop_bench_05'] },
    { id: 'gunoaie', nume: 'Gunoaie, saci, cutii', culoare: '#8a7a5a', r: 1.2, m: ['prop_rub_binbag_01', 'prop_rub_binbag_03', 'prop_rub_boxpile_01', 'prop_rub_cardpile_01', 'prop_rub_litter_01', 'prop_rub_pile_01'] },
    { id: 'tomberoane', nume: 'Tomberoane, containere de gunoi', culoare: '#4f7a52', r: 3, m: ['prop_dumpster_01a', 'prop_dumpster_02a', 'prop_dumpster_4a', 'prop_skip_01a'] },
    { id: 'epave', nume: 'Masini abandonate', culoare: '#9a5a4a', r: 5, m: ['prop_rub_carwreck_2', 'prop_rub_carwreck_3', 'prop_rub_carwreck_5', 'prop_rub_carwreck_7'] },
    { id: 'containere', nume: 'Containere de port', culoare: '#c0633a', r: 7, m: ['prop_container_01a', 'prop_container_01b', 'prop_container_03a', 'prop_container_05a'] },
    { id: 'stalpi', nume: 'Stalpi de iluminat', culoare: '#e0d27a', r: 14, m: ['prop_streetlight_01', 'prop_streetlight_03'] },
    { id: 'strada', nume: 'Mobilier stradal', culoare: '#d06a6a', r: 3, m: ['prop_fire_hydrant_1', 'prop_postbox_01a', 'prop_phonebox_01a', 'prop_news_disp_02a', 'prop_bin_01a', 'prop_parknmeter_01'] },
    { id: 'bariere', nume: 'Bariere, conuri', culoare: '#e89a3a', r: 1.6, m: ['prop_barrier_work01a', 'prop_mc_conc_barrier_01', 'prop_roadcone01a'] },
    { id: 'sport', nume: 'Sport, picnic', culoare: '#c96a3a', r: 6, m: ['prop_basketball_net', 'prop_table_tennis', 'prop_picnictable_01'] },
  ];
  const PROP_COLOR = {};
  PROP_SETS.forEach(s => s.m.forEach(m => { PROP_COLOR[m] = s.culoare; }));
  // cladiri puse de mana (generate); pentru locuri fixe de RP
  const BUILD_PRESETS = [
    { id: 'bloc', nume: 'Bloc de caramida', p: { tip: 'bloc', latime: 16, adancime: 16, etaje: 6, comercial: true, perete: 'perete_caramida' } },
    { id: 'casa', nume: 'Casa', p: { tip: 'casa', latime: 11, adancime: 10, etaje: 1 } },
    { id: 'vila', nume: 'Vila', p: { tip: 'vila', latime: 18, adancime: 13, etaje: 2 } },
    { id: 'magazin', nume: 'Magazin / benzinarie', p: { tip: 'magazin', latime: 16, adancime: 12, etaje: 1, comercial: true } },
    { id: 'hala', nume: 'Hala / depozit', p: { tip: 'hala', latime: 30, adancime: 36, etaje: 1 } },
    { id: 'politie', nume: 'Sectie de politie', p: { tip: 'bloc', latime: 34, adancime: 22, etaje: 3, comercial: false, perete: 'perete_beton' } },
    { id: 'spital', nume: 'Spital', p: { tip: 'bloc', latime: 44, adancime: 26, etaje: 7, comercial: false, perete: 'perete_beton' } },
    { id: 'birouri', nume: 'Turn de birouri (benzi de geam)', p: { tip: 'turn', stil: 'birouri', latime: 26, adancime: 24, etaje: 18, comercial: true } },
    { id: 'hotel', nume: 'Hotel de caramida (turn)', p: { tip: 'turn', stil: 'hotel', latime: 22, adancime: 20, etaje: 14, comercial: true } },
    { id: 'sticla', nume: 'Turn de sticla', p: { tip: 'turn', stil: 'sticla', latime: 28, adancime: 28, etaje: 24, comercial: true } },
  ];
  const TERRAIN_MODES = [
    { id: 'ridica', name: 'Ridica', key: '1', icon: 'M12 20V6M6 12l6-6 6 6', help: 'Tragi = dealul creste (Shift = coboara).' },
    { id: 'coboara', name: 'Coboara', key: '2', icon: 'M12 4v14M6 12l6 6 6-6', help: 'Tragi = terenul coboara (vale, mal).' },
    { id: 'netezeste', name: 'Netezeste', key: '3', icon: 'M3 14c4-6 6 4 9-2s5 2 9-2M3 19h18', help: 'Tragi = pantele devin line (Ctrl).' },
    { id: 'platou', name: 'Platou', key: '4', icon: 'M3 16h6l3-6h9M3 20h18', help: 'Aduce terenul la inaltimea de unde ai inceput sa tragi (Alt).' },
    { id: 'deal', name: 'Deal', key: '5', icon: 'M3 19c4 0 5-11 9-11s5 11 9 11', help: 'Un click = un deal lin cu inaltimea aleasa, cat pensula. Shift + click = vale.' },
    { id: 'nivel', name: 'Nivel', key: '6', icon: 'M3 12h18M3 18h18M12 3v6', help: 'Tragi = terenul ajunge exact la inaltimea aleasa (ex. 5 m), lin spre margine.' },
    { id: 'panta', name: 'Panta', key: '7', icon: 'M3 19L21 7M3 19h18', help: 'Tragi de la A la B = panta dreapta intre ele, lata cat pensula: B e mai sus cu inaltimea aleasa (Shift: mai jos).' },
  ];
  const TOOLS = [
    { id: 'select', key: 'V', name: 'Selecteaza / muta', help: 'Click pe nod, strada, zona, suprafata, cladire sau obiect ca sa-l selectezi; tragi ca sa-l muti.\nColturile suprafetelor se trag si ele.\nClick pe un cvartal gol = info. Delete sterge ce e selectat.' },
    { id: 'road', key: 'R', name: 'Strada', help: 'Moduri: 1 Drept, 2 Curb, 3 Liber, 4 Schimba tip.\nSe lipeste de noduri si de strazi; unde treci peste o strada apare singura intersectia (punctele verzi).\nStrada sta pe teren si urca singura pe dealuri. PageUp / PageDown = pod (+4 m) sau tunel (-4 m); punct albastru = trece pe sus / pe dedesubt.\nShift = fara lipire de unghi, Ctrl = grila de 5 m, Alt = fara nicio lipire.\nClick dreapta / Esc = un pas inapoi; Enter sau dublu-click = gata.' },
    { id: 'curve', key: 'C', name: 'Curbeaza', help: 'Tragi de o strada ca s-o indoi (se adauga un punct de curba).\nTragi de un punct de curba ca sa-l muti.' },
    { id: 'terrain', key: 'T', name: 'Teren (dealuri)', help: 'Pictezi dealurile: tragi = ridici, Shift = cobori, Ctrl = netezesti, Alt = platou.\nTii apasat pe loc = creste mai mult.\nStrazile puse pe teren urca si coboara singure cu el.\n[ si ] = marimea pensulei.' },
    { id: 'height', key: 'H', name: 'Inaltime nod', help: 'Pentru poduri si rampe: rotita peste un nod il ridica / coboara (Shift: 0,1 m); nodul nu mai sta pe teren.\nIn dreapta, "Pe teren" il pune inapoi pe teren.' },
    { id: 'zone', key: 'Z', name: 'Zona', help: 'Alegi zona, apoi click in cvartal.\nFiecare zona are stilul ei (fara amestec).' },
    { id: 'area', key: 'P', name: 'Suprafata', help: 'Alegi ce desenezi (parc, piateta, parcare, teren de sport, gazon, apa sau cladiri), apoi click pe fiecare colt.\nClick pe primul colt, Enter sau dublu-click = gata. Click dreapta / Esc = un colt inapoi.\nColturile puse langa trotuar se lipesc de marginea lui; doua la rand pe acelasi trotuar = conturul urmeaza trotuarul (si pe curbe). Alt = fara lipire.\nParcurile, parcarile si cladirile raman in cvartalul in care le desenezi; apa merge oriunde (in joc e marea).' },
    { id: 'brush', key: 'B', name: 'Pensula (copaci, props)', help: 'Alegi ce pictezi (copaci, tufe, gunoaie, masini abandonate, containere...) si tragi peste harta.\nShift + tras = sterge. "Cate unul" = pui un singur obiect si il rotesti tragand.' },
    { id: 'building', key: 'K', name: 'Cladire', help: 'Alegi o cladire (generata sau din GTA) si dai click: se intoarce singura cu fata spre strada si se lipeste de trotuar.\nRotita = roteste, Shift = o pui exact unde e mouse-ul.\nCvartalele o ocolesc la generare.' },
    { id: 'bg', key: 'F', name: 'Fundal (imagine)', help: 'Importi o harta sau o schita cu "Imagine de fundal" (sus), apoi o tragi cu mouse-ul la locul ei.\nRotita = mai mare / mai mica, Shift + rotita = roteste.\nApoi desenezi strazile peste ea cu unealta Strada.' },
    { id: 'delete', key: 'X', name: 'Sterge', help: 'Click pe ce vrei sa stergi (nod, strada, zona, suprafata, cladire, obiect, punct).' },
  ];

  // iconite (trasee SVG 24x24) si nume scurte pentru bara de unelte
  const TOOL_LOOK = {
    select: { short: 'Selecteaza', icon: 'M5 3l13 8-6 1.5L9.5 19z', color: '#e6e9ef' },
    road: { short: 'Strada', icon: 'M5 21L10 3M19 21L14 3M12 5v2.5M12 10.5v3M12 16.5v3', color: '#4c8dff' },
    curve: { short: 'Curbeaza', icon: 'M4 19C6 9 18 15 20 5M4 19h.01M20 5h.01', color: '#8db6ff' },
    terrain: { short: 'Teren', icon: 'M2 20l7-11 4 6 3-4 6 9zM7 6c1-2 3-2 4 0', color: '#d19a52' },
    height: { short: 'Inaltime', icon: 'M12 3v12M8 7l4-4 4 4M5 21h14M9 17h6', color: '#7fd0ff' },
    zone: { short: 'Zona', icon: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z', color: '#3cc47c' },
    area: { short: 'Suprafata', icon: 'M4 8l7-5 9 4-2 12-11 1zM4 8h.01M11 3h.01M20 7h.01', color: '#6fd08a' },
    brush: { short: 'Pensula', icon: 'M14 4l6 6-9 9H5v-6zM12 6l6 6', color: '#9ad35a' },
    building: { short: 'Cladire', icon: 'M4 21V9l8-6 8 6v12zM9 21v-6h6v6', color: '#e0b27a' },
    bg: { short: 'Fundal', icon: 'M4 5h16v14H4zM4 16l5-5 4 4 3-3 4 4', color: '#c58cff' },
    delete: { short: 'Sterge', icon: 'M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13', color: '#ef5a4c' },
  };
  TOOLS.forEach(t => Object.assign(t, TOOL_LOOK[t.id] || {}));

  // modurile uneltei Strada (ca in Cities: Skylines)
  const ROAD_MODES = [
    { id: 'drept', name: 'Drept', key: '1', icon: 'M4 20L20 4M4 20h.01M20 4h.01', help: 'Click la inceput, click la capat; continui din capat.' },
    { id: 'curb', name: 'Curb', key: '2', icon: 'M4 20Q4 4 20 4M4 4h.01', help: 'Click la inceput, click unde se indoaie, click la capat.' },
    { id: 'liber', name: 'Liber', key: '3', icon: 'M3 18c5 0 5-12 10-12s4 8 8 8', help: 'Fiecare bucata continua lin din cea dinainte.' },
    { id: 'upgrade', name: 'Schimba tip', key: '4', icon: 'M12 20V6M6 12l6-6 6 6M5 3h14', help: 'Click pe o strada existenta: devine tipul ales.' },
  ];

  function segHit(a, b, c, d) {
    const rx = b[0] - a[0], ry = b[1] - a[1], sx = d[0] - c[0], sy = d[1] - c[1];
    const den = rx * sy - ry * sx;
    if (Math.abs(den) < 1e-12) return null;
    const qx = c[0] - a[0], qy = c[1] - a[1];
    const t = (qx * sy - qy * sx) / den, u = (qx * ry - qy * rx) / den;
    return t > 1e-6 && t < 1 - 1e-6 && u > 1e-6 && u < 1 - 1e-6 ? { x: a[0] + rx * t, y: a[1] + ry * t } : null;
  }
  function arcAt(path, i, h) {
    let s = 0;
    for (let k = 1; k <= i; k++) s += Math.hypot(path[k][0] - path[k - 1][0], path[k][1] - path[k - 1][1]);
    return s + Math.hypot(h.x - path[i][0], h.y - path[i][1]);
  }

  const V = { cx: 0, cy: 0, scale: 1.2, W: 1, H: 1, drag: null, pan: null, chain: null, mouse: null, need: true };
  const T = { ready: false, renderer: null, scene: null, camera: null, group: null,
              o: { tx: 0, ty: 0, tz: 0, dist: 500, az: -0.7, el: 0.75 }, drag: null };

  function emptyPlan() {
    return { version: 1, seed: 1, texturi: 'gta', panta_max: 0.10, zona_implicita: 'lc_caramida',
             nodes: [], roads: [], zones: [], altitudini: [], suprafete: [], props: [], cladiri: [], cladiri_sterse: [] };
  }
  function smooth(t) { t = Math.max(0, Math.min(1, t)); return t * t * (3 - 2 * t); }
  function polyArea(pts) {
    let a = 0;
    for (let i = 0; i < pts.length; i++) { const p = pts[i], q = pts[(i + 1) % pts.length]; a += p[0] * q[1] - q[0] * p[1]; }
    return Math.abs(a) / 2;
  }
  function footprint(b) {
    // colturile cladirii: r = directia spre care priveste fata (grade), w de-a lungul fatadei, d in adancime
    const w = b.tip === 'gta' ? b.w : b.p.latime, d = b.tip === 'gta' ? b.d : b.p.adancime;
    const a = (b.r || 0) * Math.PI / 180, fx = Math.cos(a), fy = Math.sin(a), tx = -fy, ty = fx;
    return [[-1, 1], [1, 1], [1, -1], [-1, -1]].map(([st, sf]) => [b.x + tx * st * w / 2 + fx * sf * d / 2, b.y + ty * st * w / 2 + fy * sf * d / 2]);
  }
  function dist(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }
  function segDist(p, a, b) {
    const dx = b.x - a.x, dy = b.y - a.y;
    let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy || 1e-9);
    t = Math.max(0, Math.min(1, t));
    const q = { x: a.x + t * dx, y: a.y + t * dy };
    return { d: dist(p, q), t: t, q: q };
  }
  function inPoly(p, poly) {
    let hit = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const xi = poly[i][0], yi = poly[i][1], xj = poly[j][0], yj = poly[j][1];
      if ((yi > p.y) !== (yj > p.y) && p.x < xi + (p.y - yi) * (xj - xi) / (yj - yi)) hit = !hit;
    }
    return hit;
  }
  function gradeColor(g, max) {
    const k = Math.min(1, g / Math.max(max, 1e-6));
    return 'hsl(' + Math.round(120 * (1 - k)) + ',80%,55%)';
  }

  new Vue({
    el: '#app',
    data: {
      planName: 'oras', plans: [], plan: emptyPlan(), analysis: null, tool: 'select', roadType: 'strada',
      zoneType: 'lc_caramida', sel: null, view3d: false, status: '', log: [], logFrom: 0, generating: false, fullGen: false, profDrag: null, job: null,
      lastFile: null, mouseTxt: '', toastOn: false,
      roadMode: 'drept', roadModes: ROAD_MODES, snapAngle: true, snapGrid: false, zOff: 0, undo: [], redo: [], zones: ZONES, tools: TOOLS,
      roadTypes: { strada: 'Strada (2 benzi)', artera: 'Artera (4 benzi)', alee: 'Alee' },
      areaTypes: AREA_TYPES, areaType: 'parc', areaPts: 0,
      propSets: PROP_SETS, brushSet: 'copaci', brushModel: '', brushMode: 'pensula', brushRadius: 12, brushDensity: 1,
      buildPresets: BUILD_PRESETS, buildPick: BUILD_PRESETS[0], buildRot: 0, gtaQuery: '', catalog: [],
      terrainModes: TERRAIN_MODES, terrainMode: 'ridica', terrainRadius: 50, terrainStrength: 1, terrainHeight: 3, showRelief: true, showFoot: true, footVer: 0,
      profileEdit: null, info: {}, exportResult: null,
      // interfata: meniul deschis (fisier / vizualizare / oras / build), fila din dreapta, fila cardului de strada,
      // schimbari nesalvate, ajutorul uneltei, consola de generare
      menu: null, rightTab: 'sel', roadTab: 'strada', dirty: 0, showHelp: false, showLog: false,
    },
    computed: {
      selNode() { return this.sel && this.sel.kind === 'node' ? this.plan.nodes.find(n => n.id === this.sel.id) : null; },
      selRoad() { return this.sel && this.sel.kind === 'road' ? this.plan.roads.find(r => r.id === this.sel.id) : null; },
      selZone() { return this.sel && this.sel.kind === 'zone' ? this.plan.zones[this.sel.i] : null; },
      selAlt() { return this.sel && this.sel.kind === 'alt' ? this.plan.altitudini[this.sel.i] : null; },
      selBlock() { return this.sel && this.sel.kind === 'block' && this.analysis ? this.analysis.blocks[this.sel.i] : null; },
      roadInfo() { return this.selRoad && this.analysis ? this.analysis.roads[this.selRoad.id] : null; },
      warnings() { return this.analysis ? this.analysis.warnings : []; },
      toolHelp() { return this.currentTool.help || ''; },
      currentTool() { return TOOLS.find(t => t.id === this.tool) || TOOLS[0]; },
      toolColor() { return this.currentTool.color || '#4c8dff'; },
      roadModeName() { return (ROAD_MODES.find(m => m.id === this.roadMode) || ROAD_MODES[0]).name; },
      // bara de unelte: fara "Inaltime nod" (nodurile au +/- pe card; tasta H merge in continuare) si fara
      // "Fundal" cand nu e nicio imagine
      visibleTools() { return TOOLS.filter(t => t.id !== 'height' && (t.id !== 'bg' || this.plan.fundal)); },
      hasSel() {
        return !!(this.selNode || this.selRoad || this.selZone || this.selArea || this.selBuilding || this.selGen
          || this.selProp || this.selAlt || this.selBlock);
      },
      jobPct() { return this.job && this.job.progress ? Math.round(this.job.progress * 100) : 0; },
      selArea() { return this.sel && (this.sel.kind === 'area' || this.sel.kind === 'areapt') ? (this.plan.suprafete || []).find(a => a.id === this.sel.id) : null; },
      selBuilding() { return this.sel && this.sel.kind === 'building' ? (this.plan.cladiri || []).find(b => b.id === this.sel.id) : null; },
      // o cladire generata automat (din ultima generare), sau semnul uneia sterse
      selGen() {
        this.footVer;     // V nu e reactiv: footVer se schimba la fiecare analiza
        return this.sel && this.sel.kind === 'gen' ? (V.foot || []).find(f => f.x === this.sel.x && f.y === this.sel.y) || null : null;
      },
      selGenRemoved() { const f = this.selGen; return !!f && (f.sters || this.genRemovedAt(f) >= 0); },
      selProp() { return this.sel && this.sel.kind === 'prop' ? (this.plan.props || [])[this.sel.i] : null; },
      allRoadTypes() {
        const out = Object.assign({}, this.roadTypes);
        Object.entries(this.plan.profile || {}).forEach(([k, p]) => { out[k] = p.nume || k; });
        return out;
      },
      currentSet() { return PROP_SETS.find(s => s.id === this.brushSet) || PROP_SETS[0]; },
      gtaResults() {
        const q = this.gtaQuery.trim().toLowerCase();
        return (q ? this.catalog.filter(c => c.m.includes(q) || c.cat.includes(q)) : this.catalog).slice(0, 60);
      },
      joc() {
        return Object.assign({ x: 6000, y: -2600, z: 25 }, this.info.joc_implicit || {}, { resursa: this.info.resursa || '' }, this.plan.joc || {});
      },
      spawnText() {
        const b = this.analysis ? this.analysis.bounds : [0, 0, 0, 0], j = this.joc;
        return 'X ' + (j.x + (b[0] + b[2]) / 2).toFixed(0) + '  Y ' + (j.y + (b[1] + b[3]) / 2).toFixed(0) + '  Z ' + (j.z + 10).toFixed(0);
      },
      roadProfile() {
        // strada vazuta din lateral (grafic in dreapta): inaltimea ei si terenul de dedesubt
        const info = this.roadInfo;
        if (!info || !info.samples || info.samples.length < 2) return null;
        const smp = info.samples, n = smp.length;
        const zr = smp.map(p => p[2]), zg = smp.map(p => this.terrainZ(p[0], p[1]));
        const lo = Math.min(...zr, ...zg) - 1, hi = Math.max(...zr, ...zg) + 1, k = 80 / Math.max(hi - lo, 4);
        const X = i => (i / (n - 1) * 240).toFixed(1), Y = z => (86 - (z - lo) * k).toFixed(1);
        return { road: 'M' + zr.map((z, i) => X(i) + ' ' + Y(z)).join(' L'),
                 ground: 'M0 90 L' + zg.map((z, i) => X(i) + ' ' + Y(z)).join(' L') + ' L240 90 Z',
                 za: zr[0].toFixed(1), zb: zr[n - 1].toFixed(1), L: info.L.toFixed(0),
                 ya: Y(zr[0]), yb: Y(zr[n - 1]), k };     // capetele trase cu mouse-ul (profDown)
      },
    },
    watch: {
      sel(v) { V.need = true; if (v) this.rightTab = 'sel'; },
      generating(v) { if (v) this.showLog = true; },
      status(v) {
        if (!v) return;
        this.toastOn = true;
        clearTimeout(this._toastT); this._toastT = setTimeout(() => { this.toastOn = false; }, 3800);
      },
    },
    mounted() {
      window.addEventListener('resize', () => { this.resize(); });
      window.addEventListener('mousemove', e => this.profMove(e));      // capetele din profilul lateral
      window.addEventListener('mouseup', () => this.profUp());
      window.addEventListener('keydown', e => this.key(e));
      // mouse ridicat in afara hartii: pensula / tragerea se opresc oricum
      window.addEventListener('mouseup', () => { if (V.stroke || V.drag) this.up(); });
      window.editor = this;   // pentru depanare din consola browserului
      window.editorV = V;
      this.resize();
      // ?plan=nume deschide direct un plan, ?unealta=... alege unealta (linkuri si capturi de ecran)
      const args = new URLSearchParams(location.search);
      let last = null;
      try { last = localStorage.getItem('oras_plan'); } catch (e) { last = null; }
      this.loadPlans().then(() => this.loadPlan(args.get('plan') || last || (this.plans.includes('demo') ? 'demo' : 'oras')))
        .then(() => {
          if (args.get('unealta') && TOOLS.some(t => t.id === args.get('unealta'))) this.setTool(args.get('unealta'));
          if (location.hash === '#3d') this.setView(true);
        });
      const tick = () => {
        if (V.need && !this.view3d) { V.need = false; this.draw(); }
        requestAnimationFrame(tick);
      };
      tick();
    },
    methods: {
      // ---------------------------------------------------------------- server
      api(path, body) {
        const opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
        return fetch(path, opt).then(r => r.json().then(j => { if (!r.ok) throw new Error(j.eroare || r.status); return j; }));
      },
      loadPlans() { return this.api('/api/plans').then(j => { this.plans = j.plans; }); },
      // cladirile pe care le va pune generatorul: cerute cand te opresti din desenat (dureaza mai mult decat
      // analiza strazilor); ce vine dupa ce planul s-a schimbat din nou se arata oricum, apoi se cere iar
      previewSoon() {
        clearTimeout(this._prevT);
        this._prevT = setTimeout(() => {
          if (this._prevBusy) { this._prevAgain = true; return; }
          this._prevBusy = true; this._prevAgain = false;
          this.api('/api/analyze?cladiri=1&name=' + encodeURIComponent(this.planName), this.plan)
            .then(a => { V.foot = a.cladiri_auto || []; V.poteci = a.poteci || []; V.carari = a.carari || []; this.footVer++; V.need = true; if (this.view3d) this.build3d(); })
            .catch(() => {})
            .then(() => { this._prevBusy = false; if (this._prevAgain) this.previewSoon(); });
        }, 700);
      },
      // indexul semnului de stergere care cade in cladirea generata f (-1: nu e stearsa)
      genRemovedAt(f) {
        return (this.plan.cladiri_sterse || []).findIndex(q => inPoly({ x: q[0], y: q[1] }, f.R));
      },
      genRemove() {
        const f = this.selGen;
        if (!f) return;
        this.snapshot();
        if (!this.plan.cladiri_sterse) this.$set(this.plan, 'cladiri_sterse', []);
        if (this.genRemovedAt(f) < 0) this.plan.cladiri_sterse.push([f.x, f.y]);
        this.changed(); this.status = 'cladirea nu se mai genereaza (se vede dupa urmatoarea generare)';
      },
      genRestore() {
        const f = this.selGen, i = f ? this.genRemovedAt(f) : -1;
        if (i < 0) return;
        this.snapshot(); this.plan.cladiri_sterse.splice(i, 1); this.changed();
      },
      // cladirea generata devine una a ta (o poti muta, roti, schimba); generatorul o ocoleste pe cea automata
      genEditable() {
        const f = this.selGen;
        if (!f) return;
        this.snapshot();
        if (!this.plan.cladiri) this.$set(this.plan, 'cladiri', []);
        const b = { tip: 'gen', p: { tip: f.tip || 'bloc', latime: f.w, adancime: f.d, etaje: f.etaje || 1, comercial: !!f.comercial },
                    x: f.x, y: f.y, r: Math.round(f.r) };
        b.id = this.nextId('k', this.plan.cladiri);
        this.plan.cladiri.push(b);
        this.sel = { kind: 'building', id: b.id }; this.changed();
      },
      loadPlan(name) {
        return this.api('/api/plan?name=' + encodeURIComponent(name)).then(p => {
          this.planName = name;
          if (!this.plans.includes(name)) this.plans.push(name);
          localStorage.setItem('oras_plan', name);
          this.plan = Object.assign(emptyPlan(), p);
          this.undo = []; this.redo = []; this.sel = null; V.chain = null;
          this.loadBackground();
          this.analyze().then(() => this.fitView());
          this.exportResult = null; this.info = {}; this.refreshInfo();
          this.status = 'plan: ' + name;
        });
      },
      newPlan() {
        const name = prompt('Numele noului oras (litere, cifre, - si _):', 'oras');
        if (!name) return;
        this.planName = name;
        if (!this.plans.includes(name)) this.plans.push(name);
        this.plan = emptyPlan(); this.analysis = null; this.undo = []; this.redo = []; this.sel = null;
        localStorage.setItem('oras_plan', name);
        this.savePlan(true); V.need = true; this.build3d();
      },
      savePlan(loud) {
        clearTimeout(this._saveT);
        return this.api('/api/plan?name=' + encodeURIComponent(this.planName), this.plan)
          .then(() => { this.dirty = 0; if (loud) this.status = 'salvat: output/orase/' + this.planName + '.json'; })
          .catch(e => { this.status = 'nu s-a salvat: ' + e.message; });
      },
      analyze() {
        // o singura analiza pe drum; ce se schimba intre timp se analizeaza imediat dupa. Rezultatul se arata
        // mereu (chiar daca planul s-a mai schimbat), ca intersectiile sa apara si cand desenezi fara pauza.
        clearTimeout(this._anaT);
        if (this._anaBusy) { this._anaAgain = true; return this._anaBusy; }
        this._anaAgain = false;
        this._anaBusy = this.api('/api/analyze', this.plan).then(a => {
          // nodurile puse pe teren primesc inaltimea terenului (pentru eticheta, panta si strazile noi)
          this.plan.nodes.forEach(n => { if (n.auto && a.noduri && a.noduri[n.id] !== undefined) n.z = a.noduri[n.id]; });
          this.analysis = a; V.need = true; V.relief = null;
          this.previewSoon();
          if (this.view3d) this.build3d();
        }).catch(e => { this.status = 'analiza: ' + e.message; })
          .then(() => { this._anaBusy = null; if (this._anaAgain) return this.analyze(); });
        return this._anaBusy;
      },
      changed(commit) {
        // commit === false: schimbarea face parte dintr-un gest care continua (primul nod al unei strazi)
        if (commit !== false) this.commit();
        V.need = true;
        clearTimeout(this._anaT); this._anaT = setTimeout(() => this.analyze(), 120);
        clearTimeout(this._saveT); this._saveT = setTimeout(() => this.savePlan(false), 1500);
      },
      // Anulare: snapshot() tine minte starea de dinaintea gestului (o singura data), commit() o pune in istoric
      // doar daca planul chiar s-a schimbat. Deci un click fara efect nu mai lasa un pas gol in Ctrl+Z.
      snapshot() { if (this._pre == null) this._pre = JSON.stringify(this.plan); },
      // pete pe iarba / murdarie pe cladiri pe un cvartal: stau pe marcajul lui de zona (se pune unul daca n-are)
      blockOpt(key) { const b = this.selBlock; return (b && b.marcaj && b.marcaj[key]) || ''; },
      setOpt(z, key, val) {
        this.snapshot();
        if (val) this.$set(z, key, val); else this.$delete(z, key);
        this.changed();
      },
      setBlockOpt(key, val) {
        const b = this.selBlock;
        if (!b) return;
        let z = b.marcaj ? this.plan.zones.find(q => Math.abs(q.x - b.marcaj.x) < 1e-6 && Math.abs(q.y - b.marcaj.y) < 1e-6) : null;
        if (!z) {
          if (!val) return;
          this.snapshot();
          z = { x: +b.centru[0].toFixed(1), y: +b.centru[1].toFixed(1), tip: b.zona };
          this.plan.zones.push(z);
        }
        this.setOpt(z, key, val);
      },
      commit() {
        if (this._pre == null) return;
        const before = this._pre;
        this._pre = null;
        if (before === JSON.stringify(this.plan)) return;
        this.dirty += 1;
        this.undo.push(before);
        if (this.undo.length > 150) this.undo.shift();
        this.redo = [];
      },
      restore(state) {
        const bg = this.plan.fundal && this.plan.fundal.fisier;
        this.plan = Object.assign(emptyPlan(), JSON.parse(state));
        this.sel = null; V.drag = null; V.chain = null; V.ctrl = null; V.lastDir = null; V.stroke = null; V.area = null;
        if ((this.plan.fundal && this.plan.fundal.fisier) !== bg) this.loadBackground();
        this.changed(false);
        if (this.view3d) this.build3d();
      },
      undoAct() {
        this.commit();
        if (!this.undo.length) { this.status = 'nimic de anulat'; return; }
        this.redo.push(JSON.stringify(this.plan));
        this.restore(this.undo.pop());
        this.status = 'anulat (' + this.undo.length + ' pasi inapoi disponibili)';
      },
      redoAct() {
        this.commit();
        if (!this.redo.length) { this.status = 'nimic de refacut'; return; }
        this.undo.push(JSON.stringify(this.plan));
        this.restore(this.redo.pop());
        this.status = 'refacut';
      },
      nextId(prefix, list) {
        let n = 0;
        list.forEach(o => { const m = /^[a-z]+(\d+)$/.exec(o.id); if (m) n = Math.max(n, +m[1]); });
        let id = prefix + (n + 1);
        while (list.some(o => o.id === id)) id = prefix + (++n + 1);
        return id;
      },
      generate() {
        this.generating = true; this.log = ['Salvez planul si pornesc Blender...']; this.logFrom = 0; this.lastFile = null; this.job = null;
        this.savePlan(false)
          .then(() => this.api('/api/generate?name=' + encodeURIComponent(this.planName) + (this.fullGen ? '&full=1' : ''), {}))
          .then(() => this.pollLog())
          .catch(e => { this.generating = false; this.log.push('Eroare: ' + e.message); });
      },
      pollLog() {
        this.api('/api/log?from=' + this.logFrom).then(j => {
          this.log.push(...j.lines); this.logFrom = j.total; this.job = j;
          if (j.running) { setTimeout(() => this.pollLog(), 1000); return; }
          this.generating = false;
          if (j.stopped) {
            this.status = j.kind === 'export' ? 'exportul a fost oprit: resursa din FiveM e incompleta pana exporti din nou'
              : 'generarea a fost oprita (orasul generat inainte a ramas)';
          } else if (j.kind === 'export') {
            this.exportResult = j.result || { ok: false, error: 'exportul nu a scris niciun rezultat (vezi jurnalul)' };
            const r = this.exportResult;
            this.status = !r.ok ? 'exportul a esuat'
              : (r.incremental ? 'resursa FiveM e gata (' + r.changed_models + ' modele schimbate, ' + r.seconds + ' s)'
                : 'resursa FiveM e gata: ' + r.res_dir)
                + (j.chain ? '; harta se reporneste singura in joc (mapeditor)' : '');
          } else {
            this.lastFile = j.file;
            this.status = j.code === 0 ? 'orasul e gata: ' + j.file : 'generarea a esuat (cod ' + j.code + ')';
          }
          this.refreshInfo();
        });
      },
      openBlender() { this.api('/api/open?name=' + encodeURIComponent(this.planName), {}).catch(e => { this.status = e.message; }); },
      stopJob() {
        const exp = this.job && this.job.kind === 'export';
        if (!confirm(exp ? 'Opresti exportul?\nResursa din FiveM ramane incompleta pana exporti din nou.'
          : 'Opresti generarea?\nOrasul generat inainte ramane cum era.')) return;
        this.api('/api/stop', {}).then(j => { if (j.oprit) this.status = 'opresc Blender...'; }).catch(e => { this.status = e.message; });
      },
      fmtTime(s) {
        s = Math.max(0, Math.round(s || 0));
        return s < 60 ? s + ' s' : Math.floor(s / 60) + ' min ' + String(s % 60).padStart(2, '0') + ' s';
      },
      refreshInfo() {
        return this.api('/api/status?name=' + encodeURIComponent(this.planName)).then(j => {
          this.info = j;
          if (j.export && !this.exportResult) this.exportResult = j.export;
        }).catch(() => {});
      },
      exportFivem() {
        // butonul nu tace niciodata: spune ce lipseste (server vechi, oras negenerat)
        if (!('blend' in this.info)) {
          this.status = 'serverul editorului e vechi: inchide fereastra EDITOR_ORAS.bat si porneste-l din nou';
          this.refreshInfo();
          return;
        }
        if (!this.info.blend && !this.lastFile) { this.status = 'apasa intai "Genereaza orasul", apoi FiveM'; return; }
        this.generating = true; this.exportResult = null; this.job = null;
        this.log = ['Export FiveM: salvez planul si pornesc Blender (poate dura 1-3 minute)...']; this.logFrom = 0;
        this.savePlan(false)
          .then(() => this.api('/api/export?name=' + encodeURIComponent(this.planName) + (this.fullGen ? '&full=1' : ''), {}))
          .then(j => { this.log.push('Resursa: ' + j.resursa); this.pollLog(); })
          .catch(e => { this.generating = false; this.log.push('Eroare: ' + e.message); this.status = e.message; });
      },
      // Genereaza + FiveM intr-un pas, doar ce s-a schimbat; mapeditor reporneste harta cand exportul e gata
      sendToGame() {
        this.generating = true; this.exportResult = null; this.job = null; this.lastFile = null;
        this.log = ['Trimit in joc: generez ce ai schimbat, export modelele schimbate, apoi harta se reporneste in joc...'];
        this.logFrom = 0;
        this.savePlan(false)
          .then(() => this.api('/api/build?name=' + encodeURIComponent(this.planName) + (this.fullGen ? '&full=1' : ''), {}))
          .then(j => { this.log.push('Resursa: ' + j.resursa); this.pollLog(); })
          .catch(e => { this.generating = false; this.log.push('Eroare: ' + e.message); this.status = e.message; });
      },
      addToCfg() {
        this.api('/api/servercfg?res=' + encodeURIComponent(this.info.resursa), {})
          .then(j => { this.status = j.adaugat ? 'adaugat in ' + j.path : 'era deja in server.cfg'; this.refreshInfo(); })
          .catch(e => { this.status = e.message; });
      },
      setJoc(k, v) {
        this.snapshot();
        if (!this.plan.joc) this.$set(this.plan, 'joc', {});
        if (k === 'resursa') v = String(v).toLowerCase().replace(/[^a-z0-9_\-]/g, '_');
        this.$set(this.plan.joc, k, v);
        this.changed();
        clearTimeout(this._infoT); this._infoT = setTimeout(() => this.savePlan(false).then(() => this.refreshInfo()), 400);
      },
      roadDims(k) {
        const p = this.plan.profile && this.plan.profile[k];
        if (p) return { r: +p.carosabil || 8, s: +p.trotuar || 3 };
        return ROAD_W[k] || ROAD_W.strada;
      },
      roadSwatch(k) { return this.plan.profile && this.plan.profile[k] ? this.profilePreview(this.plan.profile[k]) : {}; },
      profileWidth(p) { return 2 * (+p.benzi || 1) * (+p.banda || 3.25) + (p.parcare ? 4.8 : 0) + (+p.mediana || 0); },
      profilePreview(p) {
        // sectiunea strazii ca dungi colorate: trotuar | (parcare) | benzi | (mediana) | benzi | (parcare) | trotuar
        const lanes = (+p.benzi || 1) * (+p.banda || 3.25), park = p.parcare ? 2.4 : 0, med = +p.mediana || 0, side = +p.trotuar || 3;
        const parts = [[side, '#8a929c'], [park, '#4a4f58'], [lanes, '#353a42'], [med, med ? (p.mediana_tip === 'beton' ? '#9aa1ab' : '#4f9a4a') : '#353a42'],
                       [lanes, '#353a42'], [park, '#4a4f58'], [side, '#8a929c']];
        const total = parts.reduce((a, q) => a + q[0], 0) || 1;
        let x = 0;
        const stops = [];
        parts.forEach(([w, c]) => { if (!w) return; stops.push(c + ' ' + (x / total * 100).toFixed(1) + '%', c + ' ' + ((x + w) / total * 100).toFixed(1) + '%'); x += w; });
        return { background: 'linear-gradient(90deg,' + stops.join(',') + ')' };
      },
      editProfile(k) {
        const p = k ? this.plan.profile[k] : null;
        this.profileEdit = p ? Object.assign({ id: k, banda: 3.25, benzi: 1, mediana: 0, mediana_tip: 'iarba', stalpi: 28, marcaj: true }, JSON.parse(JSON.stringify(p)))
          : { id: null, nume: 'Bulevard', benzi: 2, banda: 3.25, trotuar: 4, mediana: 0, mediana_tip: 'iarba', parcare: false, copaci: false, marcaj: true, stalpi: 26 };
      },
      saveProfile() {
        const p = this.profileEdit;
        this.snapshot();
        if (!this.plan.profile) this.$set(this.plan, 'profile', {});
        let id = p.id;
        if (!id) { let n = 1; while (this.plan.profile['tip' + n]) n++; id = 'tip' + n; }
        this.$set(this.plan.profile, id, { nume: p.nume || id, carosabil: +this.profileWidth(p).toFixed(2), trotuar: +p.trotuar, benzi: +p.benzi,
                                           banda: +p.banda, parcare: !!p.parcare, mediana: +p.mediana || 0, mediana_tip: p.mediana_tip,
                                           copaci: !!p.copaci, marcaj: !!p.marcaj, stalpi: +p.stalpi || 0 });
        this.roadType = id; this.profileEdit = null; this.changed();
        this.status = 'tipul "' + (p.nume || id) + '" e salvat; strazile noi il folosesc (strazile vechi: Schimba tip, tasta 4)';
      },
      deleteProfile(id) {
        this.snapshot();
        this.plan.roads.forEach(r => { if (r.tip === id) r.tip = 'strada'; });
        this.$delete(this.plan.profile, id);
        if (this.roadType === id) this.roadType = 'strada';
        this.profileEdit = null; this.changed();
      },
      // -------- marcajele strazii selectate (plan.roads[i].marcaje; lipsa = ce da tipul strazii)
      mk(path, def) {
        const m = this.selRoad && this.selRoad.marcaje;
        const v = path.split('.').reduce((o, k) => (o && o[k] !== undefined ? o[k] : undefined), m);
        return v === undefined ? def : v;
      },
      setMk(path, value) {
        const r = this.selRoad;
        if (!r) return;
        this.snapshot();
        if (!r.marcaje) this.$set(r, 'marcaje', {});
        const keys = path.split('.');
        let o = r.marcaje;
        keys.slice(0, -1).forEach(k => { if (!o[k] || typeof o[k] !== 'object') this.$set(o, k, {}); o = o[k]; });
        this.$set(o, keys[keys.length - 1], value);
        this.changed();
      },
      // marcaje puse singure dupa intersectii: pe strada mai mica (mai ingusta; la T cea care se termina; la 4 strazi
      // egale toate) linie de stop si STOP, pe strazile cu 2+ benzi sageti pe benzi. ids = doar strazile astea;
      // force = si peste ce ai ales tu (butonul de pe strada); altfel doar unde n-ai ales nimic
      autoMarks(ids, force) {
        const A = this.analysis;
        if (!A) return;
        const tipuri = A.tipuri || {};
        const rank = r => { const T = r.T || tipuri[r.tip] || {}; return (r.r || T.r || 0) + (T.mediana || 0); };
        this.snapshot();
        let count = 0;
        for (const road of this.plan.roads) {
          if (ids && !ids.includes(road.id)) continue;
          const r = A.roads[road.id], T = r ? r.T || tipuri[r.tip] || {} : {};    // r.T = profilul cu benzile strazii
          if (!r || r.nivel !== 'sol' || T.marcaj === false) continue;
          const M = JSON.parse(JSON.stringify(road.marcaje || {}));
          const set = (k, end, v) => {
            if (!M[k] || typeof M[k] !== 'object') M[k] = {};
            if (force || M[k][end] === undefined) M[k][end] = v;
          };
          for (const [end, key] of [['a', 'st'], ['b', 'dr']]) {
            const J = A.junctions[r[end]];
            const arms = J ? J.brate : [];
            const n = Math.max(1, Math.min(4, +((M.benzi || {})[key]) || T.benzi || 1));
            let minor = false;
            if (arms.length >= 3) {
              const others = arms.filter(a => a.road !== road.id).map(a => A.roads[a.road]).filter(Boolean);
              const major = Math.max(...others.map(rank));
              if (rank(r) < major - 0.01) minor = true;
              else if (arms.length >= 4) minor = rank(r) <= major + 0.01;
              else if (rank(r) <= major + 0.01) {
                // T cu strazi egale: merg inainte cele doua cele mai aliniate, cea ramasa se opreste
                let best = null, bestDot = 2;
                for (let i = 0; i < 3; i++) for (let j = i + 1; j < 3; j++) {
                  const dt = arms[i].e[0] * arms[j].e[0] + arms[i].e[1] * arms[j].e[1];
                  if (dt < bestDot) { bestDot = dt; best = [arms[i].road, arms[j].road]; }
                }
                minor = !!best && !best.includes(road.id);
              }
            }
            const junction = arms.length >= 3;
            set('stop', end, minor);
            set('scris', end, minor && n === 1 ? 'STOP' : '');
            set('viraj', end, junction && n >= 2 ? 'banda' : '');
          }
          if (JSON.stringify(M) !== JSON.stringify(road.marcaje || {})) { this.$set(road, 'marcaje', M); count++; }
        }
        this.status = count ? `Marcaje automate pe ${count} strazi: le vezi pe harta cand te apropii, le schimbi din Marcaje`
          : 'Marcajele automate erau deja puse';
        this.changed();
      },
      resetMarks() {
        if (!this.selRoad || !this.selRoad.marcaje) return;
        this.snapshot(); this.$delete(this.selRoad, 'marcaje'); this.changed();
      },
      typeLanes() {
        const t = this.analysis && this.analysis.tipuri && this.selRoad ? this.analysis.tipuri[this.selRoad.tip] : null;
        return t ? (t.benzi || 1) : 1;
      },
      // benzile pe sens ale strazii selectate: ale ei (Benzi pe sens) sau ale tipului
      roadLanes() {
        const r = this.selRoad;
        return r && +r.benzi ? Math.max(1, Math.min(4, +r.benzi)) : this.typeLanes();
      },
      // schimba latimea reala a strazii (plan_geom.Road): la numarul de benzi al tipului se scoate suprascrierea
      setLanes(n) {
        const r = this.selRoad;
        if (!r || n === this.roadLanes()) return;
        this.snapshot();
        if (n === this.typeLanes()) this.$delete(r, 'benzi'); else this.$set(r, 'benzi', n);
        this.changed();
      },
      // polilinia mutata cu x metri spre dreapta sensului ei (ca x din gen_oras.profile_for)
      offsetPts(pts, x) {
        return pts.map((p, i) => {
          const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)];
          const dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1;
          return [p[0] + dy / l * x, p[1] - dx / l * x];
        });
      },
      // bucata de polilinie dintre s0 si s1 metri de la inceput (strada fara intersectiile de la capete)
      subPath(pts, s0, s1) {
        const out = []; let acc = 0;
        for (let i = 0; i + 1 < pts.length; i++) {
          const a = pts[i], b = pts[i + 1], L = Math.hypot(b[0] - a[0], b[1] - a[1]);
          const at = t => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
          if (L > 1e-9 && acc + L >= s0 && acc <= s1) {
            if (!out.length) out.push(at(Math.max(0, (s0 - acc) / L)));
            if (acc + L <= s1) out.push(b); else { out.push(at((s1 - acc) / L)); break; }
          }
          acc += L;
        }
        return out.length >= 2 ? out : pts;
      },
      // marcajele pe harta, schematic: linia din mijloc, benzile, parcarea, bordurile vopsite, stop si sageti
      drawMarks(ctx, A, s) {
        const tipuri = A.tipuri || {};
        const world = (p, d, x, u) => [p[0] + d[0] * u + d[1] * x, p[1] + d[1] * u - d[0] * x];
        for (const r of Object.values(A.roads)) {
          const T = r.T || tipuri[r.tip] || {};
          if (r.nivel === 'tunel' || T.marcaj === false) continue;
          const M = r.marcaje || {}, h = r.r / 2, med = (T.mediana || 0) > 0.5 ? T.mediana : 0;
          const P = this.subPath(r.pts, r.s0, r.s1);
          const line = (x, color, w, dash) => {
            this.poly(ctx, this.offsetPts(P, x)); ctx.strokeStyle = color; ctx.lineWidth = Math.max(1, w * s);
            ctx.setLineDash(dash ? dash.map(d => d * s) : []); ctx.stroke();
          };
          const centre = M.centru || 'dubla';
          if (!med && centre === 'dubla') { line(-0.16, '#e0b030', 0.12); line(0.16, '#e0b030', 0.12); }
          else if (!med && centre !== 'niciuna') line(0, '#e0b030', 0.14, centre === 'intrerupta' ? [3, 3] : null);
          const side = M.parcare || (T.parcare ? 'ambele' : 'niciuna');
          const bus = M.bus || '';
          const lanes = {};
          for (const [sg, key] of [[-1, 'st'], [1, 'dr']]) {
            const n = Math.max(1, Math.min(4, +((M.benzi || {})[key]) || T.benzi || 1));
            // ca gen_oras.lane_layout: parcarea oblica ia 4.6 m doar daca benzile raman de macar 2.75 m
            let park = side === 'ambele' || side === key ? 2.4 : 0;
            if (park && M.parcare_stil === 'oblica' && (h - med / 2 - 4.6) / n >= 2.75) park = 4.6;
            const lw = (h - med / 2 - park) / n;
            lanes[sg] = { n, lw, park, bus: bus === 'ambele' || bus === key };
            for (let k = 1; k < n; k++) {
              if (k === n - 1 && lanes[sg].bus) line(sg * (med / 2 + k * lw), '#ffffff', 0.25);
              else line(sg * (med / 2 + k * lw), 'rgba(255,255,255,.8)', 0.12, [2.5, 2.5]);
            }
            if (park) line(sg * (h - park), 'rgba(255,255,255,.8)', 0.12);
            const curb = (M.bordura || {})[key];
            if (curb === 'rosie' || curb === 'galbena') line(sg * (h + 0.12), curb === 'rosie' ? '#d9453b' : '#e0b030', 0.25);
          }
          ctx.setLineDash([]);
          // punctul si directia (sensul a -> b) la dist metri de-a lungul strazii
          const segs = [];
          let total = 0;
          for (let i = 1; i < P.length; i++) {
            const L = Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]);
            segs.push([P[i - 1], P[i], L, total]); total += L;
          }
          const along = dist => {
            for (let i = 0; i < segs.length; i++) {
              const [a, b, L, acc] = segs[i];
              if (dist <= acc + L || i === segs.length - 1) {
                const t = L ? Math.max(0, Math.min(1, (dist - acc) / L)) : 0;
                return [[a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t], [(b[0] - a[0]) / (L || 1), (b[1] - a[1]) / (L || 1)]];
              }
            }
            return [P[0], [1, 0]];
          };
          // un cuvant pe banda, lungit ca in joc, citit de cine merge spre "toward"
          const word = (text, p, toward, lw) => {
            ctx.save();
            ctx.translate(this.sx(p[0]), this.sy(p[1]));
            ctx.rotate(Math.atan2(toward[0], toward[1]));
            ctx.scale(1, 2.2);
            ctx.font = `bold ${Math.max(6, lw * s * 0.3)}px Segoe UI`;
            ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = 'rgba(255,255,255,.9)';
            ctx.fillText(text, 0, 0);
            ctx.restore();
          };
          for (const sg of [-1, 1]) {
            const { n, lw, park } = lanes[sg];
            const dir = sg > 0 ? 1 : -1;
            if (park && total > 12) {
              // locurile de parcare: liniute la 5.5 m, sau oblice la 45 de grade din 3.5 in 3.5 m
              const x0 = sg * (h - park), x1 = sg * (h - 0.05), oblic = park > 3;
              ctx.strokeStyle = 'rgba(255,255,255,.7)'; ctx.lineWidth = Math.max(1, 0.1 * s);
              for (let dist = 3 + (oblic ? park : 0); dist < total - 3 - (oblic ? park : 0); dist += oblic ? 3.5 : 5.5) {
                const [p, d] = along(dist);
                this.poly(ctx, [world(p, d, x0, 0), world(p, d, x1, oblic ? dir * park : 0)]); ctx.stroke();
              }
            }
            if (lanes[sg].bus && total > 30) {
              const xc = sg * (med / 2 + (n - 0.5) * lw);
              for (let dist = 15; dist < total - 15; dist += 60) {
                const [p, d] = along(dist);
                word('BUS', world(p, d, xc, 0), dir > 0 ? d : [-d[0], -d[1]], lw);
              }
            }
          }
          for (const [end, sg] of [['a', -1], ['b', 1]]) {
            const p = end === 'a' ? P[0] : P[P.length - 1], q = end === 'a' ? P[1] : P[P.length - 2];
            const l = Math.hypot(p[0] - q[0], p[1] - q[1]) || 1;
            const fwd = [(p[0] - q[0]) / l, (p[1] - q[1]) / l];                 // spre capat
            const d = end === 'b' ? fwd : [-fwd[0], -fwd[1]];                  // sensul a -> b
            const { n, lw, park } = lanes[sg];
            if ((M.stop || {})[end]) {
              const u = end === 'b' ? -0.55 : 0.55;
              this.poly(ctx, [world(p, d, sg * 0.25, u), world(p, d, sg * (h - park - 0.1), u)]);
              ctx.strokeStyle = '#ffffff'; ctx.lineWidth = Math.max(1.5, 0.4 * s); ctx.stroke();
            }
            const txt = (M.scris || {})[end];
            if (txt) {
              for (let k = 0; k < n; k++) word(txt, world(p, d, sg * (med / 2 + (k + 0.5) * lw), end === 'b' ? -2.7 : 2.7), fwd, lw);
            }
            if ((M.viraj || {})[end]) {
              for (let k = 0; k < n; k++) {
                const x = sg * (med / 2 + (k + 0.5) * lw);
                const base = world(p, d, x, end === 'b' ? -7.2 : 7.2), tip = [base[0] + fwd[0] * 1.4, base[1] + fwd[1] * 1.4];
                const side2 = [-fwd[1] * 0.45, fwd[0] * 0.45];
                this.poly(ctx, [tip, [base[0] + side2[0], base[1] + side2[1]], [base[0] - side2[0], base[1] - side2[1]]], true);
                ctx.fillStyle = 'rgba(255,255,255,.9)'; ctx.fill();
              }
            }
          }
        }
        // capetele a / b ale strazii selectate (panoul Marcaje le foloseste)
        const sr = this.selRoad && A.roads[this.selRoad.id];
        if (sr) {
          ctx.font = 'bold 12px Segoe UI'; ctx.fillStyle = '#ffd24a';
          [['a', sr.pts[0]], ['b', sr.pts[sr.pts.length - 1]]].forEach(([t, p]) => ctx.fillText(t, this.sx(p[0]) + 6, this.sy(p[1]) - 6));
        }
      },
      // -------- profilul lateral al strazii: capetele se trag in sus / jos (nodul primeste inaltimea aleasa)
      profNode(end) {
        const r = this.selRoad;
        return r ? this.plan.nodes.find(n => n.id === (end === 'a' ? r.a : r.b)) : null;
      },
      profDown(end, ev) {
        const p = this.roadProfile, node = this.profNode(end);
        if (!p || !node) return;
        this.snapshot();
        const svg = ev.target.ownerSVGElement;
        this.profDrag = { node, y0: ev.clientY, z0: +(end === 'a' ? p.za : p.zb), k: p.k,
                          h: svg ? svg.getBoundingClientRect().height : 90, moved: false };
      },
      profMove(ev) {
        const d = this.profDrag;
        if (!d) return;
        const z = d.z0 + (d.y0 - ev.clientY) / d.h * 90 / d.k * (ev.shiftKey ? 0.2 : 1);
        this.$set(d.node, 'auto', false);
        this.$set(d.node, 'z', Math.round(z * 10) / 10);
        d.moved = true;
        this.status = 'capatul strazii la ' + d.node.z.toFixed(1) + ' m';
      },
      profUp() {
        const d = this.profDrag;
        this.profDrag = null;
        if (d && d.moved) this.changed();
      },
      // capetele strazii revin la inaltimile calculate: pe teren, iar la pod / tunel cat cere ce trece dedesubt
      autoHeights() {
        const r = this.selRoad;
        if (!r) return;
        this.snapshot();
        for (const id of [r.a, r.b]) {
          const n = this.plan.nodes.find(x => x.id === id);
          if (n) { this.$set(n, 'auto', true); this.$delete(n, 'z'); }
        }
        this.changed();
      },
      podZ(n) {
        const a = this.analysis;
        return a && a.noduri_pod && n && a.noduri_pod[n.id] !== undefined ? a.noduri_pod[n.id] : null;
      },
      setNodeAuto(v) {
        const n = this.selNode;
        if (!n) return;
        this.snapshot();
        this.$set(n, 'auto', v);
        if (!v && n.z === undefined) this.$set(n, 'z', +this.terrainZ(n.x, n.y).toFixed(1));
        this.changed();
      },
      setRoadLevel(v) {
        const r = this.selRoad;
        if (!r) return;
        if (v === 'sol') this.$delete(r, 'nivel'); else this.$set(r, 'nivel', v);
        this.changed();
        if (v !== 'sol') this.status = v === 'pod' ? 'pod: ridica nodurile de la capete cu unealta Inaltime (H) sau PageUp la desenat'
          : 'tunel: coboara nodurile de la capete cu unealta Inaltime (H) sau PageDown la desenat';
      },
      areaColor(t) { return (AMAP[t] || AMAP.parc).culoare; },
      propColor(m) { return PROP_COLOR[m] || '#cccccc'; },
      polyArea(pts) { return polyArea(pts || []); },
      redraw() { V.relief = null; V.need = true; },
      loadCatalog() {
        if (this.catalog.length) return;
        this.api('/api/catalog').then(j => { this.catalog = j.cladiri || []; }).catch(e => { this.status = 'catalog: ' + e.message; });
      },
      pickBuilding(b) { this.buildPick = b; this.buildRot = 0; },
      pickGta(c) { this.buildPick = { id: 'gta:' + c.m, nume: c.m, gta: c }; this.buildRot = 0; },
      zoneName(id) { return (ZMAP[id] || { nume: id }).nume; },
      zoneColor(id) { return (ZMAP[id] || ZMAP.gol).culoare; },
      zoomBy(k) {
        if (this.view3d) { T.o.dist = Math.max(20, Math.min(8000, T.o.dist / k)); this.render3d(); return; }
        V.scale = Math.max(0.05, Math.min(40, V.scale * k)); V.need = true;
      },

      // ---------------------------------------------------------------- import
      importPlan(ev) {
        const file = ev.target.files[0];
        ev.target.value = '';
        if (!file) return;
        file.text().then(text => {
          let data;
          try { data = JSON.parse(text); } catch (e) { alert('Fisierul nu e un plan valid (JSON): ' + e.message); return; }
          if (!Array.isArray(data.nodes) || !Array.isArray(data.roads)) { alert('Fisierul nu are noduri si strazi.'); return; }
          const name = prompt('Sub ce nume il salvez in output/orase?', file.name.replace(/\.json$/i, '').replace(/[^\w\-]/g, '_'));
          if (!name) return;
          this.planName = name;
          if (!this.plans.includes(name)) this.plans.push(name);
          this.plan = Object.assign(emptyPlan(), data);
          this.undo = []; this.redo = []; this.sel = null;
          localStorage.setItem('oras_plan', name);
          this.loadBackground();
          this.savePlan(true).then(() => this.analyze()).then(() => this.fitView());
        });
      },
      importImage(ev) {
        const file = ev.target.files[0];
        ev.target.value = '';
        if (!file) return;
        fetch('/api/fundal?name=' + encodeURIComponent(this.planName), { method: 'POST', headers: { 'Content-Type': file.type }, body: file })
          .then(r => r.json().then(j => { if (!r.ok) throw new Error(j.eroare); return j; }))
          .then(j => {
            this.snapshot();
            const old = this.plan.fundal;
            this.$set(this.plan, 'fundal', old ? Object.assign({}, old, { fisier: j.fisier }) : {
              fisier: j.fisier, x: +V.cx.toFixed(1), y: +V.cy.toFixed(1),
              latime: Math.round(V.W / V.scale * 0.8), rotatie: 0, opacitate: 0.55 });
            this.loadBackground(); this.bgChanged(); this.setTool('bg');
            this.status = 'imagine importata: trage-o la locul ei (unealta F), apoi desenezi peste ea';
          })
          .catch(e => { this.status = 'imaginea nu s-a importat: ' + e.message; });
      },
      loadBackground() {
        V.bg = null;
        const f = this.plan.fundal;
        if (!f || !f.fisier) { V.need = true; return; }
        const img = new Image();
        img.onload = () => { V.bg = img; V.need = true; };
        img.src = '/fundal/' + encodeURIComponent(f.fisier) + '?v=' + Date.now();
      },
      bgChanged() {
        this.commit();
        V.need = true;
        clearTimeout(this._saveT); this._saveT = setTimeout(() => this.savePlan(false), 1500);
      },
      removeBackground() { this.snapshot(); this.$delete(this.plan, 'fundal'); V.bg = null; this.bgChanged(); },

      // ---------------------------------------------------------------- vedere
      resize() {
        const c = this.$refs.c2d, box = this.$refs.main.getBoundingClientRect();
        V.W = c.width = Math.max(1, box.width); V.H = c.height = Math.max(1, box.height);
        if (T.ready) { T.renderer.setSize(V.W, V.H); T.camera.aspect = V.W / V.H; T.camera.updateProjectionMatrix(); this.render3d(); }
        V.need = true;
      },
      toWorld(ev) {
        const r = this.$refs.c2d.getBoundingClientRect();
        return { x: V.cx + (ev.clientX - r.left - V.W / 2) / V.scale, y: V.cy - (ev.clientY - r.top - V.H / 2) / V.scale };
      },
      sx(x) { return (x - V.cx) * V.scale + V.W / 2; },
      sy(y) { return V.H / 2 - (y - V.cy) * V.scale; },
      fitView() {
        const pts = this.plan.nodes.map(n => [n.x, n.y]).concat(this.plan.altitudini.map(a => [a.x, a.y]));
        const f = this.plan.fundal;
        if (!pts.length && f) pts.push([f.x - f.latime / 2, f.y - f.latime / 3], [f.x + f.latime / 2, f.y + f.latime / 3]);
        if (!pts.length) { V.cx = 0; V.cy = 0; V.scale = 1.2; V.need = true; return; }
        const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
        const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
        V.cx = (x0 + x1) / 2; V.cy = (y0 + y1) / 2;
        V.scale = Math.min(V.W / Math.max(x1 - x0 + 80, 50), V.H / Math.max(y1 - y0 + 80, 50));
        T.o.tx = V.cx; T.o.tz = -V.cy; T.o.dist = Math.max(x1 - x0, y1 - y0, 100) * 1.3;
        V.need = true; this.render3d();
      },
      goTo(x, y) { V.cx = x; V.cy = y; V.scale = Math.max(V.scale, 2.5); V.need = true; if (this.view3d) this.setView(false); },
      // cel mai apropiat alt nod sub mouse (raza de click, cel putin 2 m)
      nodeNear(p, skip) {
        const r = Math.max(9 / V.scale, 2.0);
        let best = null, bd = r;
        for (const n of this.plan.nodes) {
          if (n.id === skip) continue;
          const d = dist(p, n);
          if (d < bd) { bd = d; best = n; }
        }
        return best;
      },
      // nodul `from` tras peste `to`: strazile lui trec pe `to`, apoi dispare; strazile ramase cu ambele capete in
      // acelasi nod si dublurile drepte (aceleasi doua noduri, fara curba) se scot
      mergeNodes(from, to) {
        for (const r of this.plan.roads) { if (r.a === from) r.a = to; if (r.b === from) r.b = to; }
        const seen = new Set();
        this.plan.roads = this.plan.roads.filter(r => {
          if (r.a === r.b) return false;
          if ((r.puncte || []).length) return true;
          const key = [r.a, r.b].sort().join('|');
          if (seen.has(key)) return false;
          seen.add(key); return true;
        });
        this.plan.nodes = this.plan.nodes.filter(n => n.id !== from);
        this.sel = { kind: 'node', id: to };
        this.changed(); this.status = 'noduri unite: strazile lor pleaca acum din acelasi nod';
      },
      // Strazile care intra in acelasi nod sub mai putin de 25 de grade (colturi de trotuar ca niste tepi, fasii de
      // iarba intre ele): una din ele (cea curba, altfel cea mai lunga) primeste un punct de curba langa nod, ca sa
      // intre in nod la 35 de grade de vecina ei. Un nod pe apasare; nu strica unghiul cu strada de pe partea cealalta.
      fixAngles() {
        const MIN = 25 * Math.PI / 180, WANT = 35 * Math.PI / 180;
        const TWO = 2 * Math.PI;
        const wrap = a => ((a % TWO) + TWO) % TWO;
        this.snapshot();
        let fixed = 0;
        for (const node of this.plan.nodes) {
          const arms = [];
          for (const road of this.plan.roads) {
            if ((road.a !== node.id && road.b !== node.id) || road.a === road.b) continue;
            const line = this.roadLine(road);
            const pts = road.a === node.id ? line : line.slice().reverse();
            if (pts.length < 2) continue;
            let q = pts[pts.length - 1], len = 0, found = false;
            for (let i = 1; i < pts.length; i++) {
              len += dist(pts[i], pts[i - 1]);
              if (!found && len >= 8) { q = pts[i]; found = true; }
            }
            arms.push({ road, atA: road.a === node.id, ang: Math.atan2(q.y - node.y, q.x - node.x), len });
          }
          if (arms.length < 2) continue;
          arms.sort((u, v) => u.ang - v.ang);
          const n = arms.length;
          for (let i = 0; i < n; i++) {
            const u = arms[i], v = arms[(i + 1) % n];
            if (wrap(v.ang - u.ang) >= MIN) continue;
            const cu = (u.road.puncte || []).length, cv = (v.road.puncte || []).length;
            const bendV = cv > cu || (cv === cu && v.len >= u.len);
            const bend = bendV ? v : u;
            // v e in sens trigonometric fata de u: v se roteste mai departe inainte, u inapoi
            const target = bendV ? u.ang + WANT : v.ang - WANT;
            if (n > 2) {
              const next = bendV ? arms[(i + 2) % n] : arms[(i - 1 + n) % n];
              const room = bendV ? wrap(next.ang - target) : wrap(target - next.ang);
              if (room < MIN) continue;
            }
            const D = Math.min(18, Math.max(6, bend.len * 0.3));
            const P = [+(node.x + Math.cos(target) * D).toFixed(1), +(node.y + Math.sin(target) * D).toFixed(1)];
            const road = bend.road;
            if (!road.puncte) this.$set(road, 'puncte', []);
            const k = bend.atA ? 0 : road.puncte.length - 1;
            const near = road.puncte.length && dist(node, { x: road.puncte[k][0], y: road.puncte[k][1] }) < 25;
            if (near) this.$set(road.puncte, k, P);
            else if (bend.atA) road.puncte.unshift(P);
            else road.puncte.push(P);
            fixed++;
            break;
          }
        }
        // strazi care se taie fara intersectie: un nod nou exact in punctul lor, fiecare strada se imparte in doua
        let split = 0;
        for (const w of this.warnings) {
          const m = w.tip === 'incrucisare' && /strazile (\S+) si (\S+)/.exec(w.mesaj);
          if (!m) continue;
          const node = { id: this.nextId('n', this.plan.nodes), x: +w.x.toFixed(1), y: +w.y.toFixed(1), auto: true };
          this.plan.nodes.push(node);
          for (const id of [m[1], m[2]]) {
            const road = this.plan.roads.find(r => r.id === id);
            if (road) { this.splitRoad(road, node); split++; }
          }
        }
        if (fixed || split) {
          this.changed();
          this.status = `am curbat ${fixed} strazi langa unghiuri prea mici si am pus ${split / 2} noduri la incrucisari (Ctrl+Z anuleaza)`;
        } else {
          this._pre = null;
          this.status = 'nu am gasit ce sa repar automat (muta nodurile de mana)';
        }
      },
      // strada impartita la nodul `node` (pus pe ea): punctele de curba de dinainte raman pe prima parte, restul trec
      // pe a doua (dupa latura liniei de control cea mai apropiata de nod)
      splitRoad(road, node) {
        const line = this.ctrl(road);
        let best = 0, bd = Infinity;
        for (let i = 0; i + 1 < line.length; i++) {
          const s = segDist(node, line[i], line[i + 1]);
          if (s.d < bd) { bd = s.d; best = i; }
        }
        const pts = road.puncte || [];
        const second = JSON.parse(JSON.stringify(road));
        second.id = this.nextId('r', this.plan.roads);
        second.a = node.id; second.puncte = pts.slice(best);
        road.b = node.id; this.$set(road, 'puncte', pts.slice(0, best));
        this.plan.roads.push(second);
      },
      setView(on) {
        this.view3d = on;
        if (on) { this.$nextTick(() => { this.init3d(); this.build3d(); }); } else { V.need = true; }
      },
      setTool(id) { this.finishChain(true); this.tool = id; this.chainFromSelection(); V.need = true; },
      toggleMenu(id) { this.menu = this.menu === id ? null : id; },
      closeMenus() { this.menu = null; },
      // butonul mare de sus: ce face acum
      buildLabel() {
        if (!this.generating) return 'Trimite in joc';
        const j = this.job;
        if (!j) return 'Pornesc...';
        return this.jobPct + '% · ' + (j.stopped ? 'oprit' : (j.stage || 'lucrez'));
      },
      terrainZ(x, y) {
        const t = this.analysis && this.analysis.teren;
        if (!t) return 0;
        const fx = (x - t.x0) / t.step, fy = (y - t.y0) / t.step;
        const j = Math.max(0, Math.min(t.z.length - 2, Math.floor(fy))), i = Math.max(0, Math.min(t.z[0].length - 2, Math.floor(fx)));
        const tx = Math.max(0, Math.min(1, fx - i)), ty = Math.max(0, Math.min(1, fy - j));
        return t.z[j][i] * (1 - tx) * (1 - ty) + t.z[j][i + 1] * tx * (1 - ty) + t.z[j + 1][i] * (1 - tx) * ty + t.z[j + 1][i + 1] * tx * ty;
      },

      // ---------------------------------------------------------------- ce e sub mouse
      ctrl(road) {
        const a = this.plan.nodes.find(n => n.id === road.a), b = this.plan.nodes.find(n => n.id === road.b);
        if (!a || !b) return [];
        return [{ x: a.x, y: a.y }].concat((road.puncte || []).map(p => ({ x: p[0], y: p[1] })), [{ x: b.x, y: b.y }]);
      },
      roadLine(road) {
        const info = this.analysis && this.analysis.roads[road.id];
        return info ? info.pts.map(p => ({ x: p[0], y: p[1] })) : this.ctrl(road);
      },
      hit(p, kinds) {
        const r = 9 / V.scale;
        const want = k => !kinds || kinds.includes(k);
        if (want('point')) {
          for (const road of this.plan.roads) {
            const pts = road.puncte || [];
            for (let i = 0; i < pts.length; i++) if (dist(p, { x: pts[i][0], y: pts[i][1] }) < r) return { kind: 'point', id: road.id, i: i };
          }
        }
        if (want('node')) for (const n of this.plan.nodes) if (dist(p, n) < r) return { kind: 'node', id: n.id };
        if (want('zone')) for (let i = 0; i < this.plan.zones.length; i++) if (dist(p, this.plan.zones[i]) < r) return { kind: 'zone', i: i };
        if (want('alt')) for (let i = 0; i < this.plan.altitudini.length; i++) if (dist(p, this.plan.altitudini[i]) < r) return { kind: 'alt', i: i };
        if (want('areapt')) {
          for (const a of this.plan.suprafete || []) {
            for (let i = 0; i < a.puncte.length; i++) if (dist(p, { x: a.puncte[i][0], y: a.puncte[i][1] }) < r) return { kind: 'areapt', id: a.id, i: i };
          }
        }
        if (want('prop')) {
          const pr = this.plan.props || [];
          let best = -1, bd = Math.max(r * 0.8, 1.2);
          for (let i = 0; i < pr.length; i++) { const d = dist(p, pr[i]); if (d < bd) { bd = d; best = i; } }
          if (best >= 0) return { kind: 'prop', i: best };
        }
        if (want('building')) for (const b of this.plan.cladiri || []) if (inPoly(p, footprint(b))) return { kind: 'building', id: b.id };
        if (want('building') && this.showFoot) {
          // cladirile pe care le va pune generatorul (previzualizarea din analiza)
          for (const f of V.foot || []) if (inPoly(p, f.R)) return { kind: 'gen', x: f.x, y: f.y };
        }
        if (want('road')) {
          let best = null;
          for (const road of this.plan.roads) {
            const line = this.roadLine(road), half = this.roadDims(road.tip).r / 2;
            for (let i = 0; i + 1 < line.length; i++) {
              const s = segDist(p, line[i], line[i + 1]);
              if (s.d < Math.max(half, r) && (!best || s.d < best.d)) best = { kind: 'road', id: road.id, d: s.d, q: s.q };
            }
          }
          if (best) return best;
        }
        if (want('area')) {
          const list = this.plan.suprafete || [];
          for (let i = list.length - 1; i >= 0; i--) if (list[i].puncte.length > 2 && inPoly(p, list[i].puncte)) return { kind: 'area', id: list[i].id };
        }
        if (want('block') && this.analysis) {
          const b = this.analysis.blocks.findIndex(bl => bl.poligon.length > 2 && inPoly(p, bl.poligon));
          if (b >= 0) return { kind: 'block', i: b };
        }
        return null;
      },
      // ---------------------------------------------------------------- strazi ca in Cities: Skylines
      setRoadMode(m) {
        // schimbi modul in timp ce desenezi: strada continua din acelasi capat (doar "Schimba tip" o opreste)
        this.roadMode = m; V.ctrl = null;
        if (m === 'upgrade') this.finishChain(true); else { this.chainFromSelection(); V.need = true; }
      },
      chainFromSelection() {
        // ai un nod selectat si nu desenezi nimic: strada porneste din el (nu se pierde selectia)
        if (this.tool !== 'road' || V.chain || !this.selNode) return;
        const node = this.selNode, roads = this.plan.roads.filter(r => r.a === node.id || r.b === node.id);
        V.chain = node.id; V.ctrl = null;
        V.lastDir = roads.length === 1 ? this.outDir(roads[0], node.id) : null;
      },
      roadWidth(k) { const w = this.roadDims(k); return +(w.r + 2 * w.s).toFixed(1); },
      splineJS(pts, step) {
        // aceeasi curba ca plan_geom.spline (Catmull-Rom prin punctele de forma), ca previzualizarea sa fie exacta
        if (pts.length === 2) return pts.map(p => [p[0], p[1]]);
        const P = [pts[0]].concat(pts, [pts[pts.length - 1]]), out = [[pts[0][0], pts[0][1]]];
        for (let k = 1; k < P.length - 2; k++) {
          const p0 = P[k - 1], p1 = P[k], p2 = P[k + 1], p3 = P[k + 2];
          const n = Math.max(2, Math.ceil(Math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / step));
          for (let m = 1; m <= n; m++) {
            const t = m / n, t2 = t * t, t3 = t2 * t;
            out.push([0, 1].map(i => 0.5 * (2 * p1[i] + (p2[i] - p0[i]) * t + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t2
                                             + (3 * p1[i] - p0[i] - 3 * p2[i] + p3[i]) * t3)));
          }
        }
        return out;
      },
      roadPath(road) {
        // curba fiecarei strazi, tinuta minte cat timp nu i se misca punctele (la fiecare miscare de mouse se
        // cauta lipirea si intersectiile prin toate strazile; fara asta planurile mari merg greu)
        const c = this.ctrl(road).map(p => [p.x, p.y]), key = c.join(';');
        if (!V.paths) V.paths = new Map();
        let e = V.paths.get(road.id);
        if (!e || e.key !== key) { e = { key: key, path: this.splineJS(c, 1) }; V.paths.set(road.id, e); }
        return e.path;
      },
      pathLength(path) {
        let L = 0;
        for (let i = 1; i < path.length; i++) L += Math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]);
        return L;
      },
      nearestOnRoads(p, maxD) {
        let best = null;
        for (const road of this.plan.roads) {
          const path = this.roadPath(road);
          for (let i = 0; i + 1 < path.length; i++) {
            const s = segDist(p, { x: path[i][0], y: path[i][1] }, { x: path[i + 1][0], y: path[i + 1][1] });
            if (s.d < maxD && (!best || s.d < best.d)) best = { road: road.id, d: s.d, x: s.q.x, y: s.q.y };
          }
        }
        return best;
      },
      snapTo(p, mods, from, free) {
        // 1. noduri, 2. strazi existente (acolo apare o intersectie), 3. unghi fata de strada din care pleci, 4. grila
        if (!mods.altKey && !free) {
          const n = this.hit(p, ['node']);
          if (n) { const node = this.plan.nodes.find(o => o.id === n.id); return { x: node.x, y: node.y, node: node.id }; }
          const r = this.nearestOnRoads(p, Math.max(10 / V.scale, 2));
          if (r) return { x: r.x, y: r.y, road: r.road };
        }
        let q = { x: p.x, y: p.y }, guide = null;
        if (from && this.snapAngle && !mods.shiftKey && !mods.altKey) {
          const L = dist(from, q);
          if (L > 0.5) {
            const a = Math.atan2(q.y - from.y, q.x - from.x), base = V.lastDir ? Math.atan2(V.lastDir.y, V.lastDir.x) : 0;
            const k = Math.round((a - base) / (Math.PI / 12)), target = base + k * Math.PI / 12;
            if (Math.abs(Math.atan2(Math.sin(a - target), Math.cos(a - target))) < 5 * Math.PI / 180) {
              q = { x: from.x + Math.cos(target) * L, y: from.y + Math.sin(target) * L };
              guide = { deg: ((k * 15) % 360 + 360) % 360, a: target };
            }
          }
        }
        if (this.snapGrid || mods.ctrlKey) {
          if (from && guide) {
            const L = Math.max(5, Math.round(dist(from, q) / 5) * 5);
            q = { x: from.x + Math.cos(guide.a) * L, y: from.y + Math.sin(guide.a) * L };
          } else q = { x: Math.round(q.x / 5) * 5, y: Math.round(q.y / 5) * 5 };
        }
        return { x: +q.x.toFixed(2), y: +q.y.toFixed(2), guide: guide };
      },
      controlFor(A, E) {
        if (this.roadMode === 'curb' && V.ctrl) return V.ctrl;
        if (this.roadMode === 'liber' && V.lastDir) {
          const L = dist(A, E) / 2;
          return { x: A.x + V.lastDir.x * L, y: A.y + V.lastDir.y * L };
        }
        return null;
      },
      curvePoints(A, C, E) {
        if (!C) return [];
        return [0.25, 0.5, 0.75].map(t => {
          const u = 1 - t;
          return [+(u * u * A.x + 2 * u * t * C.x + t * t * E.x).toFixed(2), +(u * u * A.y + 2 * u * t * C.y + t * t * E.y).toFixed(2)];
        });
      },
      crossings(path, ends, zA, zB) {
        // unde taie traseul strazile existente (departe de capete): acolo se fac intersectii. Cu zA / zB (inaltimea
        // capetelor): la peste 4,5 m una de alta pe verticala e pasaj (una trece pe sus), fara intersectie
        const out = [], L = this.pathLength(path);
        for (const road of this.plan.roads) {
          const other = this.roadPath(road), all = ends.concat([other[0], other[other.length - 1]]);
          let Lo = null;
          for (let i = 0; i + 1 < path.length; i++) {
            for (let j = 0; j + 1 < other.length; j++) {
              const h = segHit(path[i], path[i + 1], other[j], other[j + 1]);
              if (h && !all.some(e => Math.hypot(e[0] - h.x, e[1] - h.y) < 3)) {
                // unghiul dintre cele doua strazi (0-90 de grade): sub 25 intersectia iese urata (avertisment)
                const a1 = Math.atan2(path[i + 1][1] - path[i][1], path[i + 1][0] - path[i][0]);
                const a2 = Math.atan2(other[j + 1][1] - other[j][1], other[j + 1][0] - other[j][0]);
                const ang = Math.abs(Math.atan2(Math.sin(a1 - a2), Math.cos(a1 - a2))) * 180 / Math.PI;
                const hit = { road: road.id, x: h.x, y: h.y, s: arcAt(path, i, h), ang: Math.min(ang, 180 - ang) };
                if (zA !== undefined) {
                  if (Lo === null) Lo = this.pathLength(other);
                  const na = this.plan.nodes.find(n => n.id === road.a), nb = this.plan.nodes.find(n => n.id === road.b);
                  const zo = (na.z || 0) + ((nb.z || 0) - (na.z || 0)) * smooth(arcAt(other, j, h) / Math.max(Lo, 1e-6));
                  const zn = zA + (zB - zA) * smooth(hit.s / Math.max(L, 1e-6));
                  hit.pasaj = Math.abs(zn - zo) >= 4.5;
                  hit.sus = zn > zo;
                }
                out.push(hit);
              }
            }
          }
        }
        out.sort((a, b) => a.s - b.s);
        return out.filter((h, i) => !i || h.s - out[i - 1].s > 3);
      },
      outDir(road, nodeId) {
        const path = this.roadPath(road), n = path.length;
        const [a, b] = road.a === nodeId ? [path[1], path[0]] : [path[n - 2], path[n - 1]];
        const d = { x: b[0] - a[0], y: b[1] - a[1] }, L = Math.hypot(d.x, d.y) || 1;
        return { x: d.x / L, y: d.y / L };
      },
      nodeAt(s) {
        if (s.node) return this.plan.nodes.find(n => n.id === s.node);
        if (s.road) return this.splitRoad(s.road, s);
        const node = this.addNode(s);
        if (this.zOff) { node.z = +(this.terrainZ(s.x, s.y) + this.zOff).toFixed(1); node.auto = false; }
        return node;
      },
      addRoadAuto(a, b, puncte) {
        if (a === b || this.plan.roads.some(r => (r.a === a && r.b === b) || (r.a === b && r.b === a))) return;
        const A = this.plan.nodes.find(n => n.id === a), B = this.plan.nodes.find(n => n.id === b);
        const path = this.splineJS([[A.x, A.y]].concat(puncte, [[B.x, B.y]]), 1);
        const allHits = this.crossings(path, [[A.x, A.y], [B.x, B.y]], A.z || 0, B.z || 0);
        const hits = allHits.filter(h => !h.pasaj), over = allHits.length - hits.length;
        // fiecare bucata: capat la peste 4 m deasupra terenului = pod; sub -4 m = tunel (terenul nu se mai ridica /
        // sapa dupa ea); bucatile ramase la sol raman strazi obisnuite
        const above = n => (n.z || 0) - this.terrainZ(n.x, n.y);
        const levelOf = (ia, ib) => {
          const na = this.plan.nodes.find(n => n.id === ia), nb = this.plan.nodes.find(n => n.id === ib);
          const hi = Math.max(above(na), above(nb)), lo = Math.min(above(na), above(nb));
          return hi >= 4 ? 'pod' : lo <= -4 ? 'tunel' : null;
        };
        let nivel = null;
        const stops = [{ id: a, s: 0 }];
        hits.forEach(h => {
          const r = this.nearestOnRoads(h, 1.5);
          const node = r ? this.splitRoad(r.road, { x: h.x, y: h.y }) : this.addNode(h);
          stops.push({ id: node.id, s: h.s });
        });
        const cum = [0];
        for (let i = 1; i < path.length; i++) cum.push(cum[i - 1] + Math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]));
        stops.push({ id: b, s: cum[cum.length - 1] });
        const at = s => {
          let i = 1;
          while (i < cum.length - 1 && cum[i] < s) i++;
          const t = (s - cum[i - 1]) / Math.max(cum[i] - cum[i - 1], 1e-9);
          return [+(path[i - 1][0] + (path[i][0] - path[i - 1][0]) * t).toFixed(2), +(path[i - 1][1] + (path[i][1] - path[i - 1][1]) * t).toFixed(2)];
        };
        for (let i = 0; i + 1 < stops.length; i++) {
          // o curba taiata de intersectii: fiecare bucata primeste puncte luate de pe curba, ca sa ramana rotunda
          const s0 = stops[i].s, s1 = stops[i + 1].s;
          const mine = stops.length === 2 ? puncte : (puncte.length && s1 - s0 > 12 ? [0.25, 0.5, 0.75].map(k => at(s0 + (s1 - s0) * k)) : []);
          const road = { id: this.nextId('r', this.plan.roads), a: stops[i].id, b: stops[i + 1].id, tip: this.roadType, puncte: mine };
          const lvl = levelOf(stops[i].id, stops[i + 1].id);
          if (lvl) { road.nivel = lvl; nivel = lvl; }
          this.plan.roads.push(road);
        }
        if (hits.length) this.status = hits.length === 1 ? 'intersectie noua, facuta automat' : hits.length + ' intersectii noi, facute automat';
        if (over) this.status = (nivel === 'tunel' ? 'tunel' : 'pod') + ': trece ' + (over === 1 ? 'peste o strada' : 'peste ' + over + ' strazi') + ' fara intersectie';
      },
      roadClick(p, ev) {
        const mods = { shiftKey: ev.shiftKey, ctrlKey: ev.ctrlKey, altKey: ev.altKey };
        if (this.roadMode === 'upgrade') {
          const h = this.hit(p, ['road']);
          if (h) {
            this.snapshot();
            const road = this.plan.roads.find(r => r.id === h.id);
            road.tip = this.roadType; this.sel = { kind: 'road', id: road.id }; this.changed();
          }
          return;
        }
        const from = V.chain ? this.plan.nodes.find(n => n.id === V.chain) : null;
        if (!from) {
          // primul nod face parte din aceeasi anulare cu prima bucata de strada (Ctrl+Z nu lasa un nod singur)
          this.snapshot();
          const node = this.nodeAt(this.snapTo(p, mods, null));
          const roads = this.plan.roads.filter(r => r.a === node.id || r.b === node.id);
          V.chain = node.id; V.ctrl = null;
          V.lastDir = roads.length === 1 ? this.outDir(roads[0], node.id) : null;
          this.sel = { kind: 'node', id: node.id }; this.changed(false);
          return;
        }
        if (this.roadMode === 'curb' && !V.ctrl) { V.ctrl = this.snapTo(p, mods, from, true); V.need = true; return; }
        const s = this.snapTo(p, mods, from);
        if (dist(from, s) < 4) return;
        this.snapshot();
        const C = this.controlFor(from, s);
        const end = this.nodeAt(s);
        this.addRoadAuto(from.id, end.id, this.curvePoints(from, C, end));
        const d = C ? { x: end.x - C.x, y: end.y - C.y } : { x: end.x - from.x, y: end.y - from.y }, L = Math.hypot(d.x, d.y) || 1;
        V.lastDir = { x: d.x / L, y: d.y / L }; V.ctrl = null; V.chain = end.id;
        this.sel = { kind: 'node', id: end.id }; this.changed();
      },
      tag(ctx, p, text, bad) {
        ctx.font = '600 12px Segoe UI';
        const w = ctx.measureText(text).width + 18;
        const x = Math.max(8, Math.min(this.sx(p.x) + 16, V.W - w - 8)), y = Math.max(8, this.sy(p.y) - 34);
        ctx.fillStyle = 'rgba(17,20,24,.9)'; ctx.fillRect(x, y, w, 24);
        ctx.strokeStyle = bad ? '#ef5a4c' : '#3a4454'; ctx.lineWidth = 1; ctx.strokeRect(x + 0.5, y + 0.5, w - 1, 23);
        ctx.fillStyle = bad ? '#ffb4ab' : '#e6e9ef'; ctx.fillText(text, x + 9, y + 16);
      },
      drawRoadGhost(ctx) {
        const m = V.mouse;
        if (!m) return;
        const mods = V.mods || { shiftKey: false, ctrlKey: false, altKey: false }, s = V.scale;
        if (this.roadMode === 'upgrade') {
          const h = this.hit(m, ['road']);
          if (h) {
            const road = this.plan.roads.find(r => r.id === h.id);
            this.poly(ctx, this.roadPath(road)); ctx.lineCap = 'round';
            ctx.strokeStyle = 'rgba(76,141,255,.55)'; ctx.lineWidth = Math.max(4, this.roadWidth(this.roadType) * s); ctx.stroke();
            this.tag(ctx, m, this.roadTypes[road.tip] + '  →  ' + this.roadTypes[this.roadType]);
          }
          return;
        }
        const from = V.chain ? this.plan.nodes.find(n => n.id === V.chain) : null;
        const waitingCtrl = this.roadMode === 'curb' && from && !V.ctrl;
        const snap = this.snapTo(m, mods, from, waitingCtrl);
        if (from) {
          const w = this.roadDims(this.roadType);
          const path = waitingCtrl ? [[from.x, from.y], [snap.x, snap.y]]
            : this.splineJS([[from.x, from.y]].concat(this.curvePoints(from, this.controlFor(from, snap), snap), [[snap.x, snap.y]]), 1);
          if (snap.guide) {
            const a = snap.guide.a, R = 5000;
            ctx.strokeStyle = 'rgba(255,210,74,.35)'; ctx.lineWidth = 1; ctx.setLineDash([2, 6]);
            ctx.beginPath(); ctx.moveTo(this.sx(from.x - Math.cos(a) * R), this.sy(from.y - Math.sin(a) * R));
            ctx.lineTo(this.sx(from.x + Math.cos(a) * R), this.sy(from.y + Math.sin(a) * R)); ctx.stroke(); ctx.setLineDash([]);
          }
          if (V.ctrl) {
            ctx.setLineDash([4, 4]); ctx.strokeStyle = 'rgba(200,215,255,.45)'; ctx.lineWidth = 1;
            this.poly(ctx, [[from.x, from.y], [V.ctrl.x, V.ctrl.y], [snap.x, snap.y]]); ctx.stroke(); ctx.setLineDash([]);
            ctx.fillStyle = '#c58cff'; ctx.fillRect(this.sx(V.ctrl.x) - 5, this.sy(V.ctrl.y) - 5, 10, 10);
          }
          if (!waitingCtrl) {
            ctx.lineCap = 'butt'; ctx.lineJoin = 'round';
            this.poly(ctx, path); ctx.strokeStyle = 'rgba(160,185,225,.35)'; ctx.lineWidth = Math.max(3, (w.r + 2 * w.s) * s); ctx.stroke();
            this.poly(ctx, path); ctx.strokeStyle = 'rgba(76,141,255,.6)'; ctx.lineWidth = Math.max(2, w.r * s); ctx.stroke();
          }
          this.poly(ctx, path); ctx.setLineDash([7, 6]); ctx.strokeStyle = '#e4ecff'; ctx.lineWidth = 1.3; ctx.stroke(); ctx.setLineDash([]);
          let sharp = false, over = 0;
          const L = this.pathLength(path);
          const endZ = snap.node ? (this.plan.nodes.find(n => n.id === snap.node).z || 0) : this.terrainZ(snap.x, snap.y) + this.zOff;
          if (!waitingCtrl) {
            this.crossings(path, [[from.x, from.y], [snap.x, snap.y]], from.z || 0, endZ).forEach(h => {
              if (h.pasaj) {
                // pasaj: strada trece pe sus (sau pe dedesubt), fara intersectie
                over++;
                ctx.fillStyle = '#5ab0ff'; ctx.fillRect(this.sx(h.x) - 6, this.sy(h.y) - 6, 12, 12);
                ctx.strokeStyle = '#0d1014'; ctx.lineWidth = 2; ctx.strokeRect(this.sx(h.x) - 6, this.sy(h.y) - 6, 12, 12);
                return;
              }
              const bad = h.ang < 25;
              sharp = sharp || bad;
              ctx.beginPath(); ctx.arc(this.sx(h.x), this.sy(h.y), bad ? 7 : 6, 0, 7); ctx.fillStyle = bad ? '#ef5a4c' : '#3cc47c'; ctx.fill();
              ctx.strokeStyle = '#0d1014'; ctx.lineWidth = 2; ctx.stroke();
            });
          }
          const grade = L > 1 ? 1.5 * Math.abs(endZ - (from.z || 0)) / Math.max(L - 20, L * 0.6) : 0;
          const parts = waitingCtrl ? ['click unde se indoaie strada'] : [L.toFixed(0) + ' m'];
          if (snap.guide) parts.push(snap.guide.deg + '°');
          if (!waitingCtrl) {
            const rel = endZ - this.terrainZ(snap.x, snap.y);
            parts.push(Math.abs(rel) < 0.3 ? 'pe teren' : (rel > 0 ? '+' : '') + rel.toFixed(1) + ' m ' + (rel >= 4 ? '(pod)' : rel <= -4 ? '(tunel)' : 'fata de teren'));
          }
          if (!waitingCtrl && grade > 0.005) parts.push('panta ' + (grade * 100).toFixed(0) + '%');
          if (over) parts.push(over === 1 ? 'pasaj peste o strada' : 'pasaj peste ' + over + ' strazi');
          if (sharp) parts.push('unghi prea ascutit la punctul rosu');
          this.tag(ctx, snap, parts.join('  ·  '), grade > this.plan.panta_max || sharp);
        }
        if (snap.node && !from) {
          const n = this.plan.nodes.find(o => o.id === snap.node);
          ctx.beginPath(); ctx.arc(this.sx(n.x), this.sy(n.y), 11, 0, 7); ctx.strokeStyle = '#4c8dff'; ctx.lineWidth = 2.5; ctx.stroke();
        } else if (snap.node) {
          const n = this.plan.nodes.find(o => o.id === snap.node);
          ctx.beginPath(); ctx.arc(this.sx(n.x), this.sy(n.y), 11, 0, 7); ctx.strokeStyle = '#4c8dff'; ctx.lineWidth = 2.5; ctx.stroke();
        } else if (snap.road) {
          const x = this.sx(snap.x), y = this.sy(snap.y);
          ctx.beginPath(); ctx.moveTo(x, y - 7); ctx.lineTo(x + 7, y); ctx.lineTo(x, y + 7); ctx.lineTo(x - 7, y); ctx.closePath();
          ctx.fillStyle = '#3cc47c'; ctx.fill();
        } else {
          ctx.beginPath(); ctx.arc(this.sx(snap.x), this.sy(snap.y), 4, 0, 7); ctx.fillStyle = '#e4ecff'; ctx.fill();
        }
      },

      // ---------------------------------------------------------------- editare
      addNode(p) {
        const node = { id: this.nextId('n', this.plan.nodes), x: +p.x.toFixed(2), y: +p.y.toFixed(2), z: +this.terrainZ(p.x, p.y).toFixed(1), auto: true };
        this.plan.nodes.push(node);
        return node;
      },
      splitRoad(roadId, p) {
        const road = this.plan.roads.find(r => r.id === roadId);
        const ctrl = this.ctrl(road);
        let best = { d: 1e9, k: 0 };
        for (let k = 0; k + 1 < ctrl.length; k++) { const s = segDist(p, ctrl[k], ctrl[k + 1]); if (s.d < best.d) best = { d: s.d, k: k }; }
        const node = this.addNode(p);
        const a = ctrl[0], b = ctrl[ctrl.length - 1];
        node.z = +(this.plan.nodes.find(n => n.id === road.a).z + (this.plan.nodes.find(n => n.id === road.b).z - this.plan.nodes.find(n => n.id === road.a).z) * (dist(a, p) / Math.max(dist(a, p) + dist(p, b), 1e-6))).toFixed(1);
        const na = this.plan.nodes.find(n => n.id === road.a), nb = this.plan.nodes.find(n => n.id === road.b);
        node.auto = !!(na && nb && na.auto && nb.auto);    // intre doua noduri pe teren, noul nod sta si el pe teren
        const pts = road.puncte || [];
        const second = { id: this.nextId('r', this.plan.roads), a: node.id, b: road.b, tip: road.tip, puncte: pts.slice(best.k) };
        if (road.nivel) second.nivel = road.nivel;
        road.b = node.id; road.puncte = pts.slice(0, best.k);
        this.plan.roads.push(second);
        return node;
      },
      deleteHit(h) {
        if (!h) return;
        if (h.kind === 'node') {
          this.plan.roads = this.plan.roads.filter(r => r.a !== h.id && r.b !== h.id);
          this.plan.nodes = this.plan.nodes.filter(n => n.id !== h.id);
        } else if (h.kind === 'road') {
          this.plan.roads = this.plan.roads.filter(r => r.id !== h.id);
          const used = new Set(); this.plan.roads.forEach(r => { used.add(r.a); used.add(r.b); });
          this.plan.nodes = this.plan.nodes.filter(n => used.has(n.id));
        } else if (h.kind === 'point') {
          const road = this.plan.roads.find(r => r.id === h.id); road.puncte.splice(h.i, 1);
        } else if (h.kind === 'zone') { this.plan.zones.splice(h.i, 1); } else if (h.kind === 'alt') { this.plan.altitudini.splice(h.i, 1);
        } else if (h.kind === 'area' || (h.kind === 'areapt' && h.i === undefined)) {
          this.plan.suprafete = this.plan.suprafete.filter(a => a.id !== h.id);
        } else if (h.kind === 'areapt') {
          const a = this.plan.suprafete.find(o => o.id === h.id);
          if (a.puncte.length > 3) a.puncte.splice(h.i, 1); else this.plan.suprafete = this.plan.suprafete.filter(o => o.id !== h.id);
        } else if (h.kind === 'building') {
          this.plan.cladiri = this.plan.cladiri.filter(b => b.id !== h.id);
        } else if (h.kind === 'gen') {
          // o cladire generata nu se sterge din plan: se tine minte sa nu se mai genereze
          const f = (V.foot || []).find(o => o.x === h.x && o.y === h.y);
          if (!f) return;
          if (!this.plan.cladiri_sterse) this.$set(this.plan, 'cladiri_sterse', []);
          if (this.genRemovedAt(f) < 0) this.plan.cladiri_sterse.push([f.x, f.y]);
          this.changed(); return;
        } else if (h.kind === 'prop') { this.plan.props.splice(h.i, 1); } else return;
        this.sel = null; this.changed();
      },
      deleteSel() {
        if (!this.sel) return;
        this.snapshot();
        // o suprafata selectata (chiar si prin colt) se sterge intreaga din buton / Delete
        this.deleteHit(this.sel.kind === 'areapt' ? { kind: 'area', id: this.sel.id } : this.sel);
      },
      straighten() { this.snapshot(); this.selRoad.puncte = []; this.changed(); },
      finishChain(all) {
        if (V.area) {
          // suprafata in lucru: Enter / dublu-click = gata, click dreapta / Esc = un colt inapoi
          if (all === true) this.finishArea();
          else { V.area.pts.pop(); this.areaPts = V.area.pts.length; if (!V.area.pts.length) V.area = null; }
          V.need = true; return;
        }
        // click dreapta / Esc: intai renunti la punctul de indoire, apoi la strada inceputa; Enter = gata de tot
        if (V.ctrl && all !== true) V.ctrl = null;
        else { V.chain = null; V.ctrl = null; V.lastDir = null; }
        V.need = true;
      },

      // ---------------------------------------------------------------- mouse si taste
      down(ev) {
        const p = this.toWorld(ev);
        if (ev.button === 1 || (ev.button === 2 && !(this.tool === 'road' || V.area)) || (ev.button === 0 && ev.getModifierState && ev.getModifierState(' '))) {
          V.pan = { x: ev.clientX, y: ev.clientY, cx: V.cx, cy: V.cy }; return;
        }
        if (ev.button === 2) { this.finishChain(); return; }
        if (this.tool === 'select') {
          const h = this.hit(p);
          this.sel = !h ? null : h.kind === 'point' ? { kind: 'road', id: h.id } : h;
          if (h && ['node', 'zone', 'alt', 'point', 'areapt', 'prop'].includes(h.kind)) { this.snapshot(); V.drag = h; }
          if (h && h.kind === 'building') {
            const b = this.plan.cladiri.find(o => o.id === h.id);
            this.snapshot(); V.drag = { kind: 'building', id: h.id, sx: p.x, sy: p.y, ox: b.x, oy: b.y };
          }
          if (h && h.kind === 'area') {
            const a = this.plan.suprafete.find(o => o.id === h.id);
            this.snapshot(); V.drag = { kind: 'area', id: h.id, sx: p.x, sy: p.y, orig: a.puncte.map(q => q.slice()) };
          }
          if (!h) V.pan = { x: ev.clientX, y: ev.clientY, cx: V.cx, cy: V.cy };
        } else if (this.tool === 'road') {
          this.roadClick(p, ev);
        } else if (this.tool === 'curve') {
          const h = this.hit(p, ['point', 'road']);
          if (!h) return;
          this.snapshot();
          if (h.kind === 'point') { V.drag = h; } else {
            const road = this.plan.roads.find(r => r.id === h.id), ctrl = this.ctrl(road);
            let best = { d: 1e9, k: 0 };
            for (let k = 0; k + 1 < ctrl.length; k++) { const s = segDist(p, ctrl[k], ctrl[k + 1]); if (s.d < best.d) best = { d: s.d, k: k }; }
            road.puncte = road.puncte || [];
            road.puncte.splice(best.k, 0, [+p.x.toFixed(2), +p.y.toFixed(2)]);
            V.drag = { kind: 'point', id: road.id, i: best.k };
          }
          this.sel = { kind: 'road', id: h.id };
        } else if (this.tool === 'height') {
          const h = this.hit(p, ['node']); this.sel = h;
        } else if (this.tool === 'zone') {
          this.snapshot();
          const b = this.analysis ? this.analysis.blocks.find(bl => bl.poligon.length > 2 && inPoly(p, bl.poligon)) : null;
          const old = b && b.marcaj ? this.plan.zones.findIndex(z => Math.abs(z.x - b.marcaj.x) < 1e-6 && Math.abs(z.y - b.marcaj.y) < 1e-6) : -1;
          if (old >= 0) { this.plan.zones[old].tip = this.zoneType; this.sel = { kind: 'zone', i: old }; } else {
            this.plan.zones.push({ x: +p.x.toFixed(1), y: +p.y.toFixed(1), tip: this.zoneType });
            this.sel = { kind: 'zone', i: this.plan.zones.length - 1 };
          }
          this.changed();
        } else if (this.tool === 'area') {
          this.areaClick(p, ev);
        } else if (this.tool === 'terrain') {
          this.startTerrain(p, ev);
        } else if (this.tool === 'brush') {
          this.startBrush(p, ev);
        } else if (this.tool === 'building') {
          this.placeBuilding(p, ev);
        } else if (this.tool === 'bg') {
          if (!this.plan.fundal) { this.$refs.imageFile.click(); return; }
          this.snapshot();
          V.drag = { kind: 'bg', sx: p.x, sy: p.y, ox: this.plan.fundal.x, oy: this.plan.fundal.y };
        } else if (this.tool === 'delete') {
          const h = this.hit(p, ['point', 'node', 'zone', 'alt', 'prop', 'building', 'areapt', 'road', 'area']);
          if (h) { this.snapshot(); this.deleteHit(h); }
        }
      },
      move(ev) {
        const p = this.toWorld(ev);
        V.mouse = p;
        V.mods = { shiftKey: ev.shiftKey, ctrlKey: ev.ctrlKey, altKey: ev.altKey };
        this.mouseTxt ='x ' + p.x.toFixed(1) + '  y ' + p.y.toFixed(1) + '  teren ' + this.terrainZ(p.x, p.y).toFixed(1) + ' m';
        if (V.pan) { V.cx = V.pan.cx - (ev.clientX - V.pan.x) / V.scale; V.cy = V.pan.cy + (ev.clientY - V.pan.y) / V.scale; V.need = true; return; }
        if (V.drag && V.drag.kind === 'bg') {
          const d = V.drag;
          this.plan.fundal.x = +(d.ox + p.x - d.sx).toFixed(1);
          this.plan.fundal.y = +(d.oy + p.y - d.sy).toFixed(1);
          this.bgChanged(); return;
        }
        if (V.stroke) { this.strokeMove(p, ev); return; }
        if (V.drag) {
          const d = V.drag, q = ev.altKey ? p : { x: Math.round(p.x * 2) / 2, y: Math.round(p.y * 2) / 2 };
          if (d.kind === 'node') {
            // tras peste alt nod: se lipeste de el (la ridicarea mouse-ului se unesc)
            const n = this.plan.nodes.find(o => o.id === d.id);
            const other = this.nodeNear(p, d.id);
            n.x = other ? other.x : q.x; n.y = other ? other.y : q.y;
            d.onto = other ? other.id : null;
          }
          if (d.kind === 'zone') { Object.assign(this.plan.zones[d.i], { x: q.x, y: q.y }); }
          if (d.kind === 'alt') { Object.assign(this.plan.altitudini[d.i], { x: q.x, y: q.y }); }
          if (d.kind === 'point') { this.$set(this.plan.roads.find(r => r.id === d.id).puncte, d.i, [q.x, q.y]); }
          if (d.kind === 'areapt') {     // si coltul tras se lipeste de marginea trotuarului (Alt = fara)
            const c = !ev.altKey && this.curbSnap(p);
            this.$set(this.plan.suprafete.find(o => o.id === d.id).puncte, d.i, c ? [c.x, c.y] : [q.x, q.y]);
          }
          if (d.kind === 'area') {
            const a = this.plan.suprafete.find(o => o.id === d.id), dx = q.x - Math.round(d.sx * 2) / 2, dy = q.y - Math.round(d.sy * 2) / 2;
            a.puncte = d.orig.map(v => [+(v[0] + dx).toFixed(2), +(v[1] + dy).toFixed(2)]);
          }
          if (d.kind === 'building') {
            const b = this.plan.cladiri.find(o => o.id === d.id);
            b.x = +(d.ox + p.x - d.sx).toFixed(1); b.y = +(d.oy + p.y - d.sy).toFixed(1);
          }
          if (d.kind === 'prop') { const o = this.plan.props[d.i]; o.x = +p.x.toFixed(2); o.y = +p.y.toFixed(2); }
          if (d.kind === 'proprot') {
            // "cate unul": tragi ca sa-l rotesti; se salveaza la ridicarea mouse-ului
            const o = this.plan.props[d.i];
            if (Math.hypot(p.x - o.x, p.y - o.y) > 0.5) o.r = Math.round(Math.atan2(p.y - o.y, p.x - o.x) * 180 / Math.PI);
            V.need = true; return;
          }
          this.changed(); return;
        }
        if (['road', 'area', 'brush', 'building', 'terrain'].includes(this.tool)) V.need = true;
      },
      up() {
        if (V.stroke) this.endStroke();
        if (V.drag && V.drag.kind === 'proprot') this.changed();
        if (V.drag && V.drag.kind === 'node' && V.drag.onto) this.mergeNodes(V.drag.id, V.drag.onto);
        V.drag = null; V.pan = null;
      },
      wheel(ev) {
        const p = this.toWorld(ev);
        if (this.tool === 'building' && !ev.ctrlKey) {
          this.buildRot = ((this.buildRot + (ev.deltaY < 0 ? 15 : -15)) % 360 + 360) % 360; V.need = true; return;
        }
        if (this.tool === 'bg' && this.plan.fundal) {
          const f = this.plan.fundal;
          if (ev.shiftKey) f.rotatie = +((f.rotatie || 0) + (ev.deltaY < 0 ? 0.5 : -0.5)).toFixed(1);
          else f.latime = Math.max(10, Math.round(f.latime * Math.pow(1.001, -ev.deltaY)));
          this.bgChanged(); return;
        }
        if (this.tool === 'height') {
          const h = this.hit(p, ['node']);
          if (h) {
            // mai multe clicuri de rotita pe acelasi nod = un singur pas de anulare
            const lw = this._lastWheel;
            if (!lw || lw.id !== h.id || Date.now() - lw.t > 900) { this.commit(); this.snapshot(); }
            this._lastWheel = { id: h.id, t: Date.now() };
            const n = this.plan.nodes.find(o => o.id === h.id), step = ev.shiftKey ? 0.1 : 0.5;
            n.auto = false;
            n.z = +((n.z || 0) + (ev.deltaY < 0 ? step : -step)).toFixed(1);
            this.sel = h; this.changed(false); return;
          }
        }
        const k = Math.pow(1.0015, -ev.deltaY);
        V.scale = Math.max(0.05, Math.min(40, V.scale * k));
        const q = this.toWorld(ev);
        V.cx += p.x - q.x; V.cy += p.y - q.y; V.need = true;
      },
      key(e) {
        // intr-o casuta de text Ctrl+Z anuleaza textul (ca oriunde); pe butoane, bife si liste anuleaza in plan
        const el = document.activeElement, tag = el ? el.tagName : '';
        const typing = tag === 'TEXTAREA' || (tag === 'INPUT' && /^(text|number|search)$/.test(el.type));
        if (typing) return;
        const k = e.key.toLowerCase();
        if (e.ctrlKey && (k === 'y' || (e.shiftKey && k === 'z'))) { e.preventDefault(); if (el && el.blur) el.blur(); this.redoAct(); return; }
        if (e.ctrlKey && k === 'z') { e.preventDefault(); if (el && el.blur) el.blur(); this.undoAct(); return; }
        if (tag === 'INPUT' || tag === 'SELECT') return;
        if (e.ctrlKey && k === 's') { e.preventDefault(); this.savePlan(true); return; }
        if (k === 'escape' && this.menu) { this.menu = null; return; }
        if (k === 'escape') { this.finishChain(); return; }
        if (k === 'delete' && this.sel) { this.deleteSel(); return; }
        if (k === 'enter') { this.finishChain(true); return; }
        if (this.tool === 'road') {
          if (e.key === 'PageUp' || e.key === ']') { e.preventDefault(); this.zOff += 1; V.need = true; return; }
          if (e.key === 'PageDown' || e.key === '[') { e.preventDefault(); this.zOff -= 1; V.need = true; return; }
          const mode = ROAD_MODES.find(o => o.key === e.key);
          if (mode) { this.setRoadMode(mode.id); return; }
        }
        if (this.tool === 'terrain') {
          const mode = TERRAIN_MODES.find(o => o.key === e.key);
          if (mode) { this.terrainMode = mode.id; return; }
        }
        if ((this.tool === 'terrain' || this.tool === 'brush') && (e.key === '[' || e.key === ']')) {
          const k2 = e.key === ']' ? 1.2 : 1 / 1.2;
          if (this.tool === 'terrain') this.terrainRadius = Math.round(Math.max(10, Math.min(200, this.terrainRadius * k2)));
          else this.brushRadius = Math.round(Math.max(3, Math.min(60, this.brushRadius * k2)));
          V.need = true; return;
        }
        if (k === 'delete' || k === 'backspace') { this.deleteSel(); return; }
        if (k === 'tab') { e.preventDefault(); this.setView(!this.view3d); return; }
        if (k === 'home') { this.fitView(); return; }
        const t = TOOLS.find(o => o.key.toLowerCase() === k);
        if (t && !e.ctrlKey) this.setTool(t.id);
      },

      // ---------------------------------------------------------------- suprafete
      // lipire de trotuar: un colt de suprafata langa marginea exterioara a trotuarului (linia strazii mutata cu W, ca
      // in plan_geom) se pune fix pe ea. u = segmentul liniei strazii + pozitia pe el, side = partea (+1 stanga)
      curbSnap(p) {
        const A = this.analysis;
        if (!A || !A.roads) return null;
        const tol = Math.max(10 / V.scale, 1.5);
        let best = null;
        for (const [id, r] of Object.entries(A.roads)) {
          const P = r.pts || [];
          for (let i = 0; i + 1 < P.length; i++) {
            const a = { x: P[i][0], y: P[i][1] }, b = { x: P[i + 1][0], y: P[i + 1][1] };
            const s = segDist(p, a, b), off = Math.abs(s.d - r.W);
            if (off >= tol || (best && off >= best.off)) continue;
            const len = dist(a, b) || 1;
            const side = (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x) >= 0 ? 1 : -1;
            const nx = -(b.y - a.y) / len * side, ny = (b.x - a.x) / len * side;
            best = { off: off, road: id, side: side, u: i + s.t, x: +(s.q.x + nx * r.W).toFixed(2), y: +(s.q.y + ny * r.W).toFixed(2) };
          }
        }
        return best;
      },
      // colturile marginii trotuarului dintre doua puncte lipite de aceeasi strada, pe aceeasi parte (si pe curbe)
      curbRun(c0, c1) {
        const r = this.analysis.roads[c0.road], P = r.pts;
        const at = k => {
          const i = Math.min(k, P.length - 2), t = k - i;
          const a = { x: P[i][0], y: P[i][1] }, b = { x: P[i + 1][0], y: P[i + 1][1] }, len = dist(a, b) || 1;
          const nx = -(b.y - a.y) / len * c0.side, ny = (b.x - a.x) / len * c0.side;
          return [+(a.x + (b.x - a.x) * t + nx * r.W).toFixed(2), +(a.y + (b.y - a.y) * t + ny * r.W).toFixed(2)];
        };
        const ks = [];
        for (let k = Math.floor(Math.min(c0.u, c1.u)) + 1; k < Math.max(c0.u, c1.u); k++) ks.push(k);
        if (c1.u < c0.u) ks.reverse();
        return ks.map(at);
      },
      areaClick(p, ev) {
        const c = !ev.altKey && this.curbSnap(p);
        const q = c ? { x: c.x, y: c.y } : ev.altKey ? p : { x: Math.round(p.x), y: Math.round(p.y) };
        if (!V.area) V.area = { pts: [] };
        const pts = V.area.pts;
        if (pts.length >= 3 && dist(q, { x: pts[0][0], y: pts[0][1] }) < 10 / V.scale) { this.finishArea(); return; }
        const last = pts[pts.length - 1];
        if (last && Math.hypot(last[0] - q.x, last[1] - q.y) < 0.5) return;
        // doua colturi la rand pe acelasi trotuar: conturul urmeaza marginea lui, nu o linie dreapta peste el
        const prev = V.area.curb;
        if (c && prev && prev.road === c.road && prev.side === c.side) this.curbRun(prev, c).forEach(v => pts.push(v));
        V.area.curb = c || null;
        pts.push([q.x, q.y]); this.areaPts = pts.length; V.need = true;
      },
      finishArea() {
        const a = V.area;
        V.area = null; this.areaPts = 0; V.need = true;
        if (!a) return;
        const pts = a.pts.filter((p, i) => !i || Math.hypot(p[0] - a.pts[i - 1][0], p[1] - a.pts[i - 1][1]) > 0.5);
        if (pts.length < 3) { if (pts.length) this.status = 'o suprafata are nevoie de cel putin 3 colturi'; return; }
        this.snapshot();
        if (!this.plan.suprafete) this.$set(this.plan, 'suprafete', []);
        const id = this.nextId('s', this.plan.suprafete);
        this.plan.suprafete.push({ id: id, tip: this.areaType, puncte: pts });
        this.sel = { kind: 'area', id: id }; this.changed();
        this.status = (AMAP[this.areaType] || {}).nume + ': ' + polyArea(pts).toFixed(0) + ' m²';
      },

      // ---------------------------------------------------------------- teren pictat (ca in Cities: Skylines)
      ensureTerrain(bx0, by0, bx1, by1) {
        // grila de 8 m a terenului pictat creste cat e nevoie (valorile vechi raman)
        const s = 8, t = this.plan.teren;
        const X0 = Math.floor(bx0 / s) * s, Y0 = Math.floor(by0 / s) * s, X1 = Math.ceil(bx1 / s) * s, Y1 = Math.ceil(by1 / s) * s;
        if (t && t.x0 <= X0 && t.y0 <= Y0 && t.x0 + (t.nx - 1) * s >= X1 && t.y0 + (t.ny - 1) * s >= Y1) return t;
        const nx0 = t ? Math.min(t.x0, X0) : X0, ny0 = t ? Math.min(t.y0, Y0) : Y0;
        const nx1 = t ? Math.max(t.x0 + (t.nx - 1) * s, X1) : X1, ny1 = t ? Math.max(t.y0 + (t.ny - 1) * s, Y1) : Y1;
        const nx = Math.round((nx1 - nx0) / s) + 1, ny = Math.round((ny1 - ny0) / s) + 1, h = new Array(nx * ny).fill(0);
        if (t) {
          const oi = Math.round((t.x0 - nx0) / s), oj = Math.round((t.y0 - ny0) / s);
          for (let j = 0; j < t.ny; j++) for (let i = 0; i < t.nx; i++) h[(j + oj) * nx + i + oi] = t.h[j * t.nx + i];
        }
        const out = { x0: nx0, y0: ny0, step: s, nx: nx, ny: ny, h: h };
        this.$set(this.plan, 'teren', out);
        return out;
      },
      // inaltimea de mana, cu butoanele +/- (cardul intersectiei si capetele din cardul strazii): nodul trece pe
      // "inaltime aleasa"; strazile lui si terenul din jur se potrivesc singure (analiza)
      nudgeNode(node, dz) {
        if (!node) return;
        this.snapshot();
        this.$set(node, 'z', +((+node.z || 0) + dz).toFixed(2));
        this.$set(node, 'auto', false);
        this.changed();
      },
      // strada dreapta: capatul b la inaltimea capatului a
      flattenRoad() {
        const a = this.profNode('a'), b = this.profNode('b');
        if (!a || !b) return;
        this.snapshot();
        this.$set(b, 'z', +(+a.z || 0).toFixed(2));
        this.$set(b, 'auto', false);
        this.changed();
      },
      roadGrade() {
        const r = this.selRoad && this.analysis && this.analysis.roads[this.selRoad.id];
        return r ? (r.panta * 100).toFixed(1) : '';
      },
      paintedAt(x, y) {
        const t = this.plan.teren;
        if (!t) return 0;
        const fx = (x - t.x0) / t.step, fy = (y - t.y0) / t.step;
        if (fx < 0 || fy < 0 || fx > t.nx - 1 || fy > t.ny - 1) return 0;
        const i = Math.min(Math.floor(fx), t.nx - 2), j = Math.min(Math.floor(fy), t.ny - 2), tx = fx - i, ty = fy - j, H = t.h, n = t.nx;
        return H[j * n + i] * (1 - tx) * (1 - ty) + H[j * n + i + 1] * tx * (1 - ty) + H[(j + 1) * n + i] * (1 - tx) * ty + H[(j + 1) * n + i + 1] * tx * ty;
      },
      // modul pensulei cu tastele tinute: la Ridica / Coboara / Netezeste / Platou, Shift / Ctrl / Alt schimba modul;
      // la Deal, Nivel si Panta modul ramane (Shift = in jos: vale, panta care coboara)
      strokeMode(mods) {
        if (['deal', 'nivel', 'panta'].includes(this.terrainMode)) return this.terrainMode;
        return mods.shiftKey ? 'coboara' : mods.ctrlKey ? 'netezeste' : mods.altKey ? 'platou' : this.terrainMode;
      },
      startTerrain(p, ev) {
        this.snapshot();
        const mode = this.strokeMode(ev);
        V.stroke = { kind: 'terrain', target: this.paintedAt(p.x, p.y), start: { x: p.x, y: p.y }, mode };
        if (mode === 'deal') { this.stampHill(p, ev.shiftKey ? -1 : 1); return; }
        if (mode === 'panta') return;       // se face cand dai drumul (endStroke), de la A pana unde ai tras
        this.applyTerrain(p, ev);
        clearInterval(this._strokeT);
        // cat tii apasat, pensula lucreaza si pe loc (ca in CS)
        this._strokeT = setInterval(() => { if (V.stroke && V.mouse) this.applyTerrain(V.mouse, V.mods || {}); }, 70);
      },
      applyTerrain(p, mods) {
        const R = this.terrainRadius, t = this.ensureTerrain(p.x - R, p.y - R, p.x + R, p.y + R), s = t.step, H = t.h, nx = t.nx;
        const mode = this.strokeMode(mods);
        if (mode === 'deal' || mode === 'panta') return;
        const k = this.terrainStrength * 0.25;
        const i0 = Math.max(0, Math.floor((p.x - R - t.x0) / s)), i1 = Math.min(nx - 1, Math.ceil((p.x + R - t.x0) / s));
        const j0 = Math.max(0, Math.floor((p.y - R - t.y0) / s)), j1 = Math.min(t.ny - 1, Math.ceil((p.y + R - t.y0) / s));
        const old = mode === 'netezeste' ? H.slice() : null;
        for (let j = j0; j <= j1; j++) {
          for (let i = i0; i <= i1; i++) {
            const d = Math.hypot(t.x0 + i * s - p.x, t.y0 + j * s - p.y);
            if (d >= R) continue;
            const f = Math.pow(1 - (d / R) * (d / R), 2), idx = j * nx + i;
            let v = H[idx];
            if (mode === 'ridica') v += k * f;
            else if (mode === 'coboara') v -= k * f;
            else if (mode === 'netezeste') {
              let sum = 0, c = 0;
              for (let dj = -1; dj <= 1; dj++) for (let di = -1; di <= 1; di++) {
                const ii = i + di, jj = j + dj;
                if (ii >= 0 && jj >= 0 && ii < nx && jj < t.ny) { sum += old[jj * nx + ii]; c++; }
              }
              v += (sum / c - v) * f * 0.5;
            } else if (mode === 'nivel') v += (this.terrainHeight - v) * f * 0.35;
            else v += (V.stroke.target - v) * f * 0.25;
            H[idx] = Math.round(v * 100) / 100;
          }
        }
        V.reliefVer = (V.reliefVer || 0) + 1; V.need = true;
      },
      // Deal: un deal (sau o vale, sign -1) cu inaltimea aleasa in mijloc, lin pana la marginea pensulei
      stampHill(p, sign) {
        const R = this.terrainRadius, t = this.ensureTerrain(p.x - R, p.y - R, p.x + R, p.y + R), s = t.step, H = t.h, nx = t.nx;
        const i0 = Math.max(0, Math.floor((p.x - R - t.x0) / s)), i1 = Math.min(nx - 1, Math.ceil((p.x + R - t.x0) / s));
        const j0 = Math.max(0, Math.floor((p.y - R - t.y0) / s)), j1 = Math.min(t.ny - 1, Math.ceil((p.y + R - t.y0) / s));
        for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
          const d = Math.hypot(t.x0 + i * s - p.x, t.y0 + j * s - p.y);
          if (d >= R) continue;
          const idx = j * nx + i;
          H[idx] = Math.round((H[idx] + sign * this.terrainHeight * 0.5 * (1 + Math.cos(Math.PI * d / R))) * 100) / 100;
        }
        V.reliefVer = (V.reliefVer || 0) + 1; V.need = true;
      },
      // Panta: drumul drept de la A la B, lat cat pensula, urca de la terenul din A la A + inaltimea aleasa (sign -1 =
      // coboara); pe margini si dupa capete se imbina lin cu terenul din jur. -> textul pentru bara de jos
      applyRamp(a, b, za, sign) {
        const L = Math.hypot(b.x - a.x, b.y - a.y);
        if (L < 4) return '';
        const half = this.terrainRadius * 0.5, blend = this.terrainRadius * 0.5, pad = half + blend;
        const t = this.ensureTerrain(Math.min(a.x, b.x) - pad, Math.min(a.y, b.y) - pad, Math.max(a.x, b.x) + pad, Math.max(a.y, b.y) + pad);
        const s = t.step, H = t.h, nx = t.nx, zb = za + sign * this.terrainHeight;
        const ux = (b.x - a.x) / L, uy = (b.y - a.y) / L;
        const i0 = Math.max(0, Math.floor((Math.min(a.x, b.x) - pad - t.x0) / s)), i1 = Math.min(nx - 1, Math.ceil((Math.max(a.x, b.x) + pad - t.x0) / s));
        const j0 = Math.max(0, Math.floor((Math.min(a.y, b.y) - pad - t.y0) / s)), j1 = Math.min(t.ny - 1, Math.ceil((Math.max(a.y, b.y) + pad - t.y0) / s));
        for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
          const dx = t.x0 + i * s - a.x, dy = t.y0 + j * s - a.y;
          const along = dx * ux + dy * uy, across = Math.abs(dy * ux - dx * uy);
          if (along < -blend || along > L + blend || across > pad) continue;
          const wa = across <= half ? 1 : 1 - (across - half) / blend;
          const wl = along < 0 ? 1 + along / blend : along > L ? 1 - (along - L) / blend : 1;
          let w = Math.max(0, Math.min(wa, wl));
          w = w * w * (3 - 2 * w);
          const idx = j * nx + i, want = za + (zb - za) * Math.max(0, Math.min(1, along / L));
          H[idx] = Math.round((H[idx] + (want - H[idx]) * w) * 100) / 100;
        }
        V.reliefVer = (V.reliefVer || 0) + 1; V.need = true;
        return `panta: de la ${za.toFixed(1)} m la ${zb.toFixed(1)} m pe ${L.toFixed(0)} m (${(Math.abs(zb - za) / L * 100).toFixed(1)}%); strazile de pe ea urca / coboara cu ea`;
      },

      // ---------------------------------------------------------------- pensula de props
      startBrush(p, ev) {
        if (!this.plan.props) this.$set(this.plan, 'props', []);
        this.snapshot();
        if (this.brushMode === 'unul' && !ev.shiftKey) {
          const set = this.currentSet;
          this.plan.props.push({ m: this.brushModel || set.m[Math.floor(Math.random() * set.m.length)], x: +p.x.toFixed(2), y: +p.y.toFixed(2), r: 0 });
          const i = this.plan.props.length - 1;
          this.sel = { kind: 'prop', i: i }; V.drag = { kind: 'proprot', i: i }; V.need = true;
          return;
        }
        V.stroke = { kind: 'brush', last: p };
        this.paintProps(p, ev.shiftKey);
      },
      paintProps(p, erase) {
        const R = this.brushRadius, list = this.plan.props;
        if (erase) {
          const keep = list.filter(o => Math.hypot(o.x - p.x, o.y - p.y) > R);
          if (keep.length !== list.length) { this.plan.props = keep; this.sel = null; }
          V.need = true; return;
        }
        const set = this.currentSet, min = set.r / this.brushDensity;
        const near = list.filter(o => Math.abs(o.x - p.x) < R + min && Math.abs(o.y - p.y) < R + min);
        const tries = Math.max(3, Math.round(R * R / (min * min) * 0.6));
        for (let k = 0; k < tries; k++) {
          const a = Math.random() * 2 * Math.PI, d = R * Math.sqrt(Math.random());
          const q = { x: p.x + Math.cos(a) * d, y: p.y + Math.sin(a) * d };
          if (near.some(o => (o.x - q.x) * (o.x - q.x) + (o.y - q.y) * (o.y - q.y) < min * min) || this.onRoad(q)) continue;
          const o = { m: this.brushModel || set.m[Math.floor(Math.random() * set.m.length)], x: +q.x.toFixed(2), y: +q.y.toFixed(2), r: Math.round(Math.random() * 360) };
          list.push(o); near.push(o);
        }
        V.need = true;
      },
      onRoad(q) {
        // pe carosabil nu se picteaza (pe trotuar da)
        const A = this.analysis;
        if (!A) return false;
        if (!A._bb) {
          A._bb = Object.values(A.roads).map(r => {
            const xs = r.pts.map(p => p[0]), ys = r.pts.map(p => p[1]);
            return [r, Math.min(...xs) - r.W, Math.min(...ys) - r.W, Math.max(...xs) + r.W, Math.max(...ys) + r.W];
          });
        }
        for (const [r, x0, y0, x1, y1] of A._bb) {
          if (q.x < x0 || q.x > x1 || q.y < y0 || q.y > y1) continue;
          for (let i = 0; i + 1 < r.pts.length; i++) {
            if (segDist(q, { x: r.pts[i][0], y: r.pts[i][1] }, { x: r.pts[i + 1][0], y: r.pts[i + 1][1] }).d < r.r / 2 + 0.3) return true;
          }
        }
        return false;
      },
      strokeMove(p, ev) {
        const st = V.stroke;
        if (st.kind === 'brush' && dist(p, st.last) > Math.max(1, this.brushRadius * 0.35)) { st.last = p; this.paintProps(p, ev.shiftKey); }
        V.need = true;
      },
      endStroke() {
        clearInterval(this._strokeT);
        const st = V.stroke, kind = st && st.kind;
        let msg = kind === 'terrain' ? 'teren schimbat: strazile de pe el urca / coboara odata cu el' : '';
        if (kind === 'terrain' && st.mode === 'panta' && V.mouse) {
          msg = this.applyRamp(st.start, V.mouse, st.target, (V.mods || {}).shiftKey ? -1 : 1) || 'panta: trage mai departe (minim 4 m)';
        }
        V.stroke = null;
        this.changed();
        if (msg) this.status = msg;
      },

      // ---------------------------------------------------------------- cladiri puse de mana
      buildingGhost(p, mods) {
        const pk = this.buildPick;
        if (!pk) return null;
        const b = pk.gta ? { tip: 'gta', m: pk.gta.m, w: pk.gta.w, d: pk.gta.d, h: pk.gta.h } : { tip: 'gen', p: Object.assign({}, pk.p) };
        const d = pk.gta ? pk.gta.d : pk.p.adancime;
        b.x = +p.x.toFixed(1); b.y = +p.y.toFixed(1); b.r = this.buildRot;
        if (!mods.shiftKey) {
          // ca in CS: fata spre strada cea mai apropiata, lipita de trotuar
          const n = this.nearestOnRoads(p, 60);
          if (n) {
            const road = this.plan.roads.find(r => r.id === n.road), dims = this.roadDims(road.tip);
            const dx = p.x - n.x, dy = p.y - n.y, L = Math.hypot(dx, dy) || 1, off = dims.r / 2 + dims.s + 0.4 + d / 2;
            b.x = +(n.x + dx / L * off).toFixed(1); b.y = +(n.y + dy / L * off).toFixed(1);
            b.r = Math.round(Math.atan2(-dy, -dx) * 180 / Math.PI) + this.buildRot;
          }
        }
        return b;
      },
      placeBuilding(p, ev) {
        const b = this.buildingGhost(p, ev);
        if (!b) return;
        this.snapshot();
        if (!this.plan.cladiri) this.$set(this.plan, 'cladiri', []);
        b.id = this.nextId('k', this.plan.cladiri);
        this.plan.cladiri.push(b);
        this.sel = { kind: 'building', id: b.id }; this.changed();
      },

      // ---------------------------------------------------------------- relief in 2D (culori + curbe de nivel)
      reliefGrid() {
        if (V.stroke && V.stroke.kind === 'terrain' && this.plan.teren) {
          const t = this.plan.teren;
          return { x0: t.x0, y0: t.y0, step: t.step, nx: t.nx, ny: t.ny, at: (i, j) => t.h[j * t.nx + i], key: 'p' + V.reliefVer };
        }
        const t = this.analysis && this.analysis.teren;
        if (!t) return null;
        return { x0: t.x0, y0: t.y0, step: t.step, nx: t.z[0].length, ny: t.z.length, at: (i, j) => t.z[j][i], key: t };
      },
      drawRelief(ctx) {
        const g = this.reliefGrid();
        if (!g) return;
        if (!V.relief || V.relief.key !== g.key) {
          let lo = Infinity, hi = -Infinity;
          for (let j = 0; j < g.ny; j++) for (let i = 0; i < g.nx; i++) { const v = g.at(i, j); if (v < lo) lo = v; if (v > hi) hi = v; }
          if (!(hi - lo > 0.4)) { V.relief = { key: g.key, empty: true }; } else {
            const cv = document.createElement('canvas'); cv.width = g.nx; cv.height = g.ny;
            const c2 = cv.getContext('2d'), img = c2.createImageData(g.nx, g.ny), s = g.step;
            const ramp = [[0, [46, 84, 52]], [0.35, [104, 118, 62]], [0.7, [128, 96, 62]], [1, [196, 186, 168]]];
            for (let j = 0; j < g.ny; j++) {
              for (let i = 0; i < g.nx; i++) {
                const z = g.at(i, j), t = (z - lo) / (hi - lo);
                let k = 1;
                while (k < ramp.length - 1 && ramp[k][0] < t) k++;
                const t0 = ramp[k - 1][0], c0 = ramp[k - 1][1], t1 = ramp[k][0], c1 = ramp[k][1], u = Math.max(0, Math.min(1, (t - t0) / (t1 - t0)));
                const dx = (g.at(Math.min(i + 1, g.nx - 1), j) - g.at(Math.max(i - 1, 0), j)) / (2 * s);
                const dy = (g.at(i, Math.min(j + 1, g.ny - 1)) - g.at(i, Math.max(j - 1, 0))) / (2 * s);
                const shade = Math.max(0.45, Math.min(1.35, 1 + (-dx + dy) * 1.8));
                const o = ((g.ny - 1 - j) * g.nx + i) * 4;
                for (let c = 0; c < 3; c++) img.data[o + c] = Math.min(255, (c0[c] + (c1[c] - c0[c]) * u) * shade);
                img.data[o + 3] = 255;
              }
            }
            c2.putImageData(img, 0, 0);
            const stepZ = hi - lo > 60 ? 5 : hi - lo > 20 ? 2 : 1, segs = [], major = [];
            for (let lv = Math.ceil(lo / stepZ) * stepZ; lv <= hi; lv += stepZ) {
              const out = Math.round(lv / stepZ) % 5 === 0 ? major : segs;
              for (let j = 0; j + 1 < g.ny; j++) {
                for (let i = 0; i + 1 < g.nx; i++) {
                  const a = g.at(i, j) - lv, b = g.at(i + 1, j) - lv, c = g.at(i + 1, j + 1) - lv, d = g.at(i, j + 1) - lv;
                  const x0 = g.x0 + i * s, y0 = g.y0 + j * s, pts = [];
                  if ((a < 0) !== (b < 0)) pts.push([x0 + s * a / (a - b), y0]);
                  if ((b < 0) !== (c < 0)) pts.push([x0 + s, y0 + s * b / (b - c)]);
                  if ((c < 0) !== (d < 0)) pts.push([x0 + s - s * c / (c - d), y0 + s]);
                  if ((d < 0) !== (a < 0)) pts.push([x0, y0 + s - s * d / (d - a)]);
                  if (pts.length >= 2) out.push(pts[0], pts[1]);
                  if (pts.length === 4) out.push(pts[2], pts[3]);
                }
              }
            }
            V.relief = { key: g.key, cv: cv, g: { x0: g.x0, y0: g.y0, step: g.step, nx: g.nx, ny: g.ny }, segs: segs, major: major };
          }
        }
        const R = V.relief;
        if (R.empty) return;
        const gg = R.g, s = V.scale;
        ctx.save();
        ctx.globalAlpha = 0.5; ctx.imageSmoothingEnabled = true;
        ctx.drawImage(R.cv, this.sx(gg.x0 - gg.step / 2), this.sy(gg.y0 + (gg.ny - 0.5) * gg.step), gg.nx * gg.step * s, gg.ny * gg.step * s);
        ctx.globalAlpha = 1;
        for (const [list, col, w] of [[R.segs, 'rgba(255,244,214,.16)', 1], [R.major, 'rgba(255,244,214,.4)', 1.3]]) {
          ctx.strokeStyle = col; ctx.lineWidth = w; ctx.beginPath();
          for (let k = 0; k + 1 < list.length; k += 2) { ctx.moveTo(this.sx(list[k][0]), this.sy(list[k][1])); ctx.lineTo(this.sx(list[k + 1][0]), this.sy(list[k + 1][1])); }
          ctx.stroke();
        }
        ctx.restore();
      },
      // un copac pictat sub o cladire (sau la 1.5 m de ea): generatorul nu-l pune, deci nici aici nu se arata
      underBuilding(x, y) {
        const grow = R => {
          const cx = R.reduce((t, p) => t + p[0], 0) / R.length, cy = R.reduce((t, p) => t + p[1], 0) / R.length;
          const big = R.map(p => { const dx = p[0] - cx, dy = p[1] - cy, L = Math.hypot(dx, dy) || 1; return [p[0] + dx / L * 2.1, p[1] + dy / L * 2.1]; });
          return { big, bb: [Math.min(...big.map(p => p[0])), Math.min(...big.map(p => p[1])), Math.max(...big.map(p => p[0])), Math.max(...big.map(p => p[1]))] };
        };
        const test = g => x >= g.bb[0] && x <= g.bb[2] && y >= g.bb[1] && y <= g.bb[3] && inPoly({ x, y }, g.big);
        if (this.showFoot) {
          for (const f of V.foot || []) {
            if (f.sters) continue;
            if (!f._g) f._g = grow(f.R);
            if (test(f._g)) return true;
          }
        }
        return (this.plan.cladiri || []).some(b => test(grow(footprint(b))));
      },
      drawPlaced(ctx) {
        // obiectele pictate si cladirile puse de mana
        const s = V.scale, x0 = V.cx - V.W / 2 / s - 10, x1 = V.cx + V.W / 2 / s + 10, y0 = V.cy - V.H / 2 / s - 10, y1 = V.cy + V.H / 2 / s + 10;
        (this.plan.props || []).forEach((o, i) => {
          if (o.x < x0 || o.x > x1 || o.y < y0 || o.y > y1) return;
          if (this.underBuilding(o.x, o.y)) return;         // casa are prioritate (revine daca o stergi)
          const tree = /tree/.test(o.m), r = Math.max(tree ? 2.5 : 1.5, (tree ? 2.4 : 0.7) * s), on = this.sel && this.sel.kind === 'prop' && this.sel.i === i;
          ctx.beginPath(); ctx.arc(this.sx(o.x), this.sy(o.y), r, 0, 7);
          ctx.fillStyle = (PROP_COLOR[o.m] || '#cccccc') + (tree ? 'aa' : 'ee'); ctx.fill();
          if (on || s > 3) {
            const a = (o.r || 0) * Math.PI / 180;
            ctx.strokeStyle = on ? '#ffd24a' : 'rgba(0,0,0,.5)'; ctx.lineWidth = on ? 2 : 1; ctx.stroke();
            ctx.beginPath(); ctx.moveTo(this.sx(o.x), this.sy(o.y)); ctx.lineTo(this.sx(o.x + Math.cos(a) * 2), this.sy(o.y + Math.sin(a) * 2)); ctx.stroke();
          }
        });
        (this.plan.cladiri || []).forEach(b => {
          const f = footprint(b), on = this.sel && this.sel.kind === 'building' && this.sel.id === b.id;
          this.poly(ctx, f, true); ctx.fillStyle = b.tip === 'gta' ? 'rgba(143,177,214,.85)' : 'rgba(214,168,120,.85)'; ctx.fill();
          ctx.strokeStyle = on ? '#ffd24a' : '#1b1f25'; ctx.lineWidth = on ? 2.5 : 1; ctx.stroke();
          ctx.beginPath(); ctx.moveTo(this.sx(f[0][0]), this.sy(f[0][1])); ctx.lineTo(this.sx(f[1][0]), this.sy(f[1][1]));
          ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 3; ctx.stroke();     // fata cladirii
          if (s > 0.9) {
            ctx.fillStyle = '#111'; ctx.font = '600 11px Segoe UI';
            const label = b.tip === 'gta' ? b.m : (b.p.etaje + ' et.');
            ctx.fillText(label, this.sx(b.x) - ctx.measureText(label).width / 2, this.sy(b.y) + 4);
          }
        });
      },
      drawGhosts(ctx) {
        const m = V.mouse, s = V.scale;
        if (V.area) {
          const pts = V.area.pts.concat(m ? [[m.x, m.y]] : []);
          this.poly(ctx, pts, pts.length > 2);
          if (pts.length > 2) { ctx.fillStyle = this.areaColor(this.areaType) + '55'; ctx.fill(); }
          ctx.strokeStyle = '#ffd24a'; ctx.lineWidth = 1.5; ctx.setLineDash([6, 4]); ctx.stroke(); ctx.setLineDash([]);
          V.area.pts.forEach((p, i) => { const w = i ? 6 : 11; ctx.fillStyle = i ? '#ffd24a' : '#ffffff'; ctx.fillRect(this.sx(p[0]) - w / 2, this.sy(p[1]) - w / 2, w, w); });
          if (m) this.tag(ctx, m, V.area.pts.length + ' colturi' + (pts.length >= 3 ? '  ·  ' + polyArea(pts).toFixed(0) + ' m²  ·  Enter = gata' : ''));
        }
        if (!m) return;
        if (this.tool === 'brush' && this.brushMode === 'pensula') {
          const erase = V.mods && V.mods.shiftKey;
          ctx.beginPath(); ctx.arc(this.sx(m.x), this.sy(m.y), this.brushRadius * s, 0, 7);
          ctx.strokeStyle = erase ? '#ef5a4c' : this.currentSet.culoare; ctx.lineWidth = 2; ctx.stroke();
          ctx.fillStyle = erase ? 'rgba(239,90,76,.12)' : 'rgba(255,255,255,.06)'; ctx.fill();
        }
        if (this.tool === 'terrain') {
          const mods = V.mods || {}, mode = this.strokeMode(mods), st = V.stroke;
          ctx.beginPath(); ctx.arc(this.sx(m.x), this.sy(m.y), this.terrainRadius * s, 0, 7);
          ctx.strokeStyle = '#f0c27a'; ctx.lineWidth = 2; ctx.stroke();
          ctx.beginPath(); ctx.arc(this.sx(m.x), this.sy(m.y), this.terrainRadius * s * 0.5, 0, 7);
          ctx.setLineDash([4, 4]); ctx.strokeStyle = 'rgba(240,194,122,.6)'; ctx.lineWidth = 1; ctx.stroke(); ctx.setLineDash([]);
          let label = (TERRAIN_MODES.find(o => o.id === mode) || {}).name + '  ·  ' + this.terrainZ(m.x, m.y).toFixed(1) + ' m';
          if (mode === 'deal') label += `  ·  ${mods.shiftKey ? 'vale -' : 'deal +'}${this.terrainHeight} m`;
          if (mode === 'nivel') label += `  ·  pana la ${this.terrainHeight} m`;
          if (mode === 'panta' && st && st.start) {
            // banda pantei cat tragi: capetele si panta, ca sa stii ce iese inainte sa dai drumul
            const za = st.target, zb = za + (mods.shiftKey ? -1 : 1) * this.terrainHeight;
            const L = Math.hypot(m.x - st.start.x, m.y - st.start.y);
            ctx.beginPath(); ctx.moveTo(this.sx(st.start.x), this.sy(st.start.y)); ctx.lineTo(this.sx(m.x), this.sy(m.y));
            ctx.lineCap = 'round'; ctx.strokeStyle = 'rgba(240,194,122,.3)'; ctx.lineWidth = Math.max(2, this.terrainRadius * s); ctx.stroke();
            ctx.strokeStyle = '#f0c27a'; ctx.lineWidth = 2; ctx.stroke(); ctx.lineCap = 'butt';
            label = `Panta  ·  ${za.toFixed(1)} -> ${zb.toFixed(1)} m  ·  ${L.toFixed(0)} m  ·  ${L > 1 ? (Math.abs(zb - za) / L * 100).toFixed(1) : '0'}%`;
          }
          this.tag(ctx, m, label);
        }
        if (this.tool === 'building') {
          const b = this.buildingGhost(m, V.mods || {});
          if (b) {
            const f = footprint(b);
            this.poly(ctx, f, true); ctx.fillStyle = 'rgba(224,178,122,.35)'; ctx.fill();
            ctx.setLineDash([5, 4]); ctx.strokeStyle = '#e0b27a'; ctx.lineWidth = 1.5; ctx.stroke(); ctx.setLineDash([]);
            ctx.beginPath(); ctx.moveTo(this.sx(f[0][0]), this.sy(f[0][1])); ctx.lineTo(this.sx(f[1][0]), this.sy(f[1][1]));
            ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 3; ctx.stroke();
            const w = b.tip === 'gta' ? b.w : b.p.latime, d = b.tip === 'gta' ? b.d : b.p.adancime;
            this.tag(ctx, m, (this.buildPick.nume || '') + '  ·  ' + w + '×' + d + ' m');
          }
        }
      },

      // ---------------------------------------------------------------- desen 2D
      poly(ctx, pts, close) {
        ctx.beginPath();
        pts.forEach((p, i) => { const x = this.sx(p[0] !== undefined ? p[0] : p.x), y = this.sy(p[1] !== undefined ? p[1] : p.y); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
        if (close) ctx.closePath();
      },
      draw() {
        const ctx = this.$refs.c2d.getContext('2d'), W = V.W, H = V.H, s = V.scale;
        ctx.fillStyle = '#171a20'; ctx.fillRect(0, 0, W, H);
        // grila: 10 m (50 m mai groasa), rara cand esti departe
        const step = s > 1.5 ? 10 : s > 0.3 ? 50 : 250;
        const x0 = V.cx - W / 2 / s, x1 = V.cx + W / 2 / s, y0 = V.cy - H / 2 / s, y1 = V.cy + H / 2 / s;
        ctx.lineWidth = 1;
        for (let x = Math.floor(x0 / step) * step; x <= x1; x += step) { ctx.strokeStyle = x % (step * 5) === 0 ? '#2a3039' : '#1f242b'; ctx.beginPath(); ctx.moveTo(this.sx(x), 0); ctx.lineTo(this.sx(x), H); ctx.stroke(); }
        for (let y = Math.floor(y0 / step) * step; y <= y1; y += step) { ctx.strokeStyle = y % (step * 5) === 0 ? '#2a3039' : '#1f242b'; ctx.beginPath(); ctx.moveTo(0, this.sy(y)); ctx.lineTo(W, this.sy(y)); ctx.stroke(); }
        const f = this.plan.fundal;
        if (V.bg && f) {
          const w = f.latime * s, h = w * V.bg.height / V.bg.width;
          ctx.save();
          ctx.globalAlpha = f.opacitate || 0.55;
          ctx.translate(this.sx(f.x), this.sy(f.y));
          ctx.rotate(-(f.rotatie || 0) * Math.PI / 180);
          ctx.drawImage(V.bg, -w / 2, -h / 2, w, h);
          ctx.restore();
          if (this.tool === 'bg') { ctx.strokeStyle = '#ffd24a'; ctx.setLineDash([6, 4]); ctx.strokeRect(this.sx(f.x) - w / 2, this.sy(f.y) - h / 2, w, h); ctx.setLineDash([]); }
        }
        if (this.showRelief || this.tool === 'terrain') this.drawRelief(ctx);
        const A = this.analysis;
        if (A) {
          A.blocks.forEach((b, i) => {
            if (b.poligon.length < 3) return;
            this.poly(ctx, b.poligon, true);
            const z = ZMAP[b.zona] || ZMAP.gol;
            ctx.fillStyle = b.valid ? z.culoare + '66' : '#55555566'; ctx.fill();
            if (this.sel && this.sel.kind === 'block' && this.sel.i === i) { ctx.strokeStyle = '#ffd24a'; ctx.lineWidth = 2; ctx.stroke(); }
          });
          // suprafetele desenate (sub strazi: podurile trec peste apa)
          (this.plan.suprafete || []).forEach(a => {
            if (a.puncte.length < 3) return;
            const c = this.areaColor(a.tip), on = this.sel && (this.sel.kind === 'area' || this.sel.kind === 'areapt') && this.sel.id === a.id;
            this.poly(ctx, a.puncte, true); ctx.fillStyle = c + (a.tip === 'apa' ? 'dd' : '99'); ctx.fill();
            ctx.strokeStyle = on ? '#ffd24a' : c; ctx.lineWidth = on ? 2 : 1.2;
            ctx.setLineDash(a.tip === 'apa' ? [] : [5, 4]); ctx.stroke(); ctx.setLineDash([]);
            if (on || this.tool === 'area') a.puncte.forEach(p => { ctx.fillStyle = on ? '#ffd24a' : c; ctx.fillRect(this.sx(p[0]) - 3.5, this.sy(p[1]) - 3.5, 7, 7); });
            if (s > 0.7) {
              const cx = a.puncte.reduce((t, p) => t + p[0], 0) / a.puncte.length, cy = a.puncte.reduce((t, p) => t + p[1], 0) / a.puncte.length;
              const label = (AMAP[a.tip] || { nume: a.tip }).nume.split(' (')[0];
              ctx.fillStyle = 'rgba(255,255,255,.85)'; ctx.font = '11px Segoe UI'; ctx.fillText(label, this.sx(cx) - ctx.measureText(label).width / 2, this.sy(cy) + 4);
            }
          });
          if (this.showFoot && V.foot && V.foot.length) {     // cladirile din ultima generare
            V.foot.forEach(f => {
              const gone = f.sters || this.genRemovedAt(f) >= 0;
              const on = this.sel && this.sel.kind === 'gen' && this.sel.x === f.x && this.sel.y === f.y;
              this.poly(ctx, f.R, true);
              if (!gone) { ctx.fillStyle = 'rgba(205,210,220,.6)'; ctx.fill(); }
              ctx.strokeStyle = on ? '#ffd24a' : gone ? '#ef5a4c' : 'rgba(15,17,21,.85)'; ctx.lineWidth = on ? 2.5 : 1;
              if (gone) ctx.setLineDash([4, 3]);
              ctx.stroke(); ctx.setLineDash([]);
            });
          }
          if (this.showFoot && V.poteci) {     // aleile parcurilor, ca la generare (server: park_plan.park_paths)
            ctx.lineCap = 'round'; ctx.lineJoin = 'round';
            ctx.strokeStyle = ctx.fillStyle = 'rgba(214,202,176,.85)';
            V.poteci.forEach(pk => {
              pk.paths.forEach(([pts, w]) => { this.poly(ctx, pts); ctx.lineWidth = Math.max(1.5, w * s); ctx.stroke(); });
              if (pk.plaza) { ctx.beginPath(); ctx.arc(this.sx(pk.plaza[0]), this.sy(pk.plaza[1]), pk.plaza[2] * s, 0, Math.PI * 2); ctx.fill(); }
            });
          }
          (V.carari || []).forEach(c => {     // cararile tale (unealta Carare din /mapeditor): linie portocalie
            this.poly(ctx, c.puncte); ctx.strokeStyle = '#ff9f43'; ctx.lineWidth = 2; ctx.setLineDash([6, 4]); ctx.stroke(); ctx.setLineDash([]);
          });
          ctx.lineCap = 'butt'; ctx.lineJoin = 'round';
          Object.values(A.roads).forEach(r => {    // umbra podurilor
            if (r.nivel !== 'pod') return;
            this.poly(ctx, r.pts); ctx.strokeStyle = 'rgba(0,0,0,.5)'; ctx.lineWidth = Math.max(3, (2 * r.W + 4) * s); ctx.stroke();
          });
          for (const pass of ['s', 'r']) {
            Object.values(A.roads).forEach(r => {
              ctx.globalAlpha = r.nivel === 'tunel' ? 0.35 : 1;     // tunelul se vede ca prin pamant
              this.poly(ctx, r.pts);
              ctx.strokeStyle = pass === 's' ? '#7d8591' : '#383d46';
              ctx.lineWidth = Math.max(1, (pass === 's' ? 2 * r.W : r.r) * s);
              ctx.stroke();
            });
          }
          ctx.globalAlpha = 1;
          Object.values(A.junctions).forEach(j => {
            j.trotuare.forEach(w => { this.poly(ctx, w.poligon, true); ctx.fillStyle = '#7d8591'; ctx.fill(); });
            this.poly(ctx, j.asfalt, true); ctx.fillStyle = '#383d46'; ctx.fill();
          });
          if (s >= 1.2) this.drawMarks(ctx, A, s);      // de aproape: marcajele (ce se va genera pe asfalt)
          // strazile desenate chiar acum, inainte sa vina analiza lor de la server: se vad imediat
          const fresh = this.plan.roads.filter(r => !A.roads[r.id]);
          for (const pass of ['s', 'r']) {
            fresh.forEach(r => {
              const w = this.roadDims(r.tip);
              this.poly(ctx, this.roadPath(r)); ctx.lineCap = 'round';
              ctx.strokeStyle = pass === 's' ? '#7d8591' : '#383d46';
              ctx.lineWidth = Math.max(1, (pass === 's' ? w.r + 2 * w.s : w.r) * s); ctx.stroke();
            });
          }
          ctx.lineCap = 'butt';
          Object.entries(A.roads).forEach(([id, r]) => {
            this.poly(ctx, r.pts);
            ctx.strokeStyle = gradeColor(r.panta, this.plan.panta_max);
            ctx.lineWidth = this.sel && this.sel.kind === 'road' && this.sel.id === id ? 4 : 1.5;
            ctx.setLineDash(r.panta > 0.001 ? [] : [6, 6]); ctx.stroke(); ctx.setLineDash([]);
          });
          (A.pasaje || []).forEach(q => {
            ctx.fillStyle = '#5ab0ff'; ctx.fillRect(this.sx(q.x) - 5, this.sy(q.y) - 5, 10, 10);
            ctx.strokeStyle = '#0d1014'; ctx.lineWidth = 1.5; ctx.strokeRect(this.sx(q.x) - 5, this.sy(q.y) - 5, 10, 10);
          });
        } else {
          this.plan.roads.forEach(r => { this.poly(ctx, this.ctrl(r)); ctx.strokeStyle = '#777'; ctx.lineWidth = 2; ctx.stroke(); });
        }
        // puncte de curba (la strada selectata sau cu unealta Curbeaza)
        this.plan.roads.forEach(r => {
          if (!(r.puncte || []).length || !(this.tool === 'curve' || (this.sel && this.sel.id === r.id))) return;
          this.poly(ctx, this.ctrl(r)); ctx.strokeStyle = '#8fb1ff55'; ctx.lineWidth = 1; ctx.stroke();
          r.puncte.forEach(p => { ctx.fillStyle = '#8fb1ff'; ctx.fillRect(this.sx(p[0]) - 4, this.sy(p[1]) - 4, 8, 8); });
        });
        this.plan.zones.forEach((z, i) => {
          const c = ZMAP[z.tip] || ZMAP.gol;
          ctx.beginPath(); ctx.arc(this.sx(z.x), this.sy(z.y), 8, 0, 7); ctx.fillStyle = c.culoare; ctx.fill();
          ctx.strokeStyle = this.sel && this.sel.kind === 'zone' && this.sel.i === i ? '#ffd24a' : '#111'; ctx.lineWidth = 2; ctx.stroke();
          if (s > 0.6) { ctx.fillStyle = '#fff'; ctx.font = '11px Segoe UI'; ctx.fillText(c.nume, this.sx(z.x) + 11, this.sy(z.y) + 4); }
        });
        this.plan.altitudini.forEach((a, i) => {
          const x = this.sx(a.x), y = this.sy(a.y);
          ctx.beginPath(); ctx.moveTo(x, y - 9); ctx.lineTo(x + 8, y + 6); ctx.lineTo(x - 8, y + 6); ctx.closePath();
          ctx.fillStyle = '#c28f4a'; ctx.fill();
          ctx.strokeStyle = this.sel && this.sel.kind === 'alt' && this.sel.i === i ? '#ffd24a' : '#111'; ctx.stroke();
          ctx.fillStyle = '#ffd9a8'; ctx.font = '11px Segoe UI'; ctx.fillText(a.z + ' m', x + 10, y + 4);
        });
        this.drawPlaced(ctx);
        this.plan.nodes.forEach(n => {
          const x = this.sx(n.x), y = this.sy(n.y), on =this.sel && this.sel.kind === 'node' && this.sel.id === n.id;
          ctx.beginPath(); ctx.arc(x, y, on ? 7 : 5, 0, 7); ctx.fillStyle = on ? '#ffd24a' : (n.id === V.chain ? '#8fb1ff' : '#f0f2f5'); ctx.fill();
          ctx.strokeStyle = '#111'; ctx.lineWidth = 1.5; ctx.stroke();
          if (n.z && !n.auto && s > 0.4) { ctx.fillStyle = '#bfe3ff'; ctx.font = '11px Segoe UI'; ctx.fillText((n.z > 0 ? '+' : '') + n.z + ' m', x + 8, y - 7); }
        });
        this.warnings.forEach(w => {
          const x = this.sx(w.x), y = this.sy(w.y);
          ctx.beginPath(); ctx.arc(x, y, 9, 0, 7); ctx.fillStyle = '#d9483b'; ctx.fill();
          ctx.fillStyle = '#fff'; ctx.font = 'bold 13px Segoe UI'; ctx.fillText('!', x - 2, y + 5);
        });
        if (this.tool === 'road') this.drawRoadGhost(ctx);
        this.drawGhosts(ctx);
        // scara
        const m = [10, 20, 50, 100, 200, 500, 1000].find(v => v * s > 80) || 1000;
        ctx.fillStyle = '#cfd5de'; ctx.fillRect(12, H - 30, m * s, 3); ctx.font = '11px Segoe UI'; ctx.fillText(m + ' m', 12, H - 36);
      },

      // ---------------------------------------------------------------- 3D
      init3d() {
        if (T.ready) { this.resize(); return; }
        T.renderer = new THREE.WebGLRenderer({ antialias: true });
        T.renderer.setPixelRatio(window.devicePixelRatio || 1);
        this.$refs.c3d.appendChild(T.renderer.domElement);
        T.scene = new THREE.Scene();
        T.scene.background = new THREE.Color(0x9db3c8);
        T.scene.fog = new THREE.Fog(0x9db3c8, 1500, 5000);
        T.camera = new THREE.PerspectiveCamera(50, 1, 1, 20000);
        T.scene.add(new THREE.HemisphereLight(0xffffff, 0x556644, 0.75));
        const sun = new THREE.DirectionalLight(0xffffff, 0.7); sun.position.set(300, 600, 200); T.scene.add(sun);
        const el = T.renderer.domElement;
        el.addEventListener('mousedown', e => { T.drag = { x: e.clientX, y: e.clientY, b: e.button, o: Object.assign({}, T.o) }; });
        window.addEventListener('mouseup', () => { T.drag = null; });
        window.addEventListener('mousemove', e => {
          if (!T.drag || !this.view3d) return;
          const dx = e.clientX - T.drag.x, dy = e.clientY - T.drag.y, o = T.drag.o;
          if (T.drag.b === 0) { T.o.az = o.az - dx * 0.006; T.o.el = Math.max(0.08, Math.min(1.5, o.el + dy * 0.006)); } else {
            const k = T.o.dist / 700, ca = Math.cos(T.o.az), sa = Math.sin(T.o.az);
            T.o.tx = o.tx - (dx * ca + dy * sa) * k; T.o.tz = o.tz - (-dx * sa + dy * ca) * k;
          }
          this.render3d();
        });
        el.addEventListener('wheel', e => { e.preventDefault(); T.o.dist = Math.max(20, Math.min(8000, T.o.dist * Math.pow(1.0015, e.deltaY))); this.render3d(); });
        T.ready = true;
        this.resize();
      },
      // Cladirile pe care le va pune generatorul, ca niste cutii cu geamuri (fara modele din Blender): o textura de
      // fatada desenata aici, repetata la 3 m (un geam pe travee si pe etaj), acoperis plin; culoarea dupa tip.
      buildings3d() {
        if (!T.winTex) {
          const cv = document.createElement('canvas'); cv.width = cv.height = 64;
          const g = cv.getContext('2d');
          g.fillStyle = '#ffffff'; g.fillRect(0, 0, 64, 64);
          g.fillStyle = '#4a5d75'; g.fillRect(18, 16, 28, 30);          // geamul
          g.fillStyle = '#d9d9d9'; g.fillRect(14, 46, 36, 4);           // pervazul
          T.winTex = new THREE.CanvasTexture(cv);
          T.winTex.wrapS = T.winTex.wrapT = THREE.RepeatWrapping;
          T.walls = {};
          T.roof = new THREE.MeshLambertMaterial({ color: 0x5c5f66 });
        }
        const FLOOR = { bloc: 3.1, casa: 3.0, vila: 3.6, magazin: 4.5, hala: 8.0, turn: 3.4 };
        const COLOR = { bloc: 0xb4694e, casa: 0xe2d2b0, vila: 0xefe6d2, magazin: 0xc9c2b4, hala: 0xa8adb3, turn: 0x8fa3bf };
        for (const f of V.foot) {
          if (f.sters) continue;
          const h = (f.etaje || 1) * (FLOOR[f.tip] || 3.1) + 0.6;
          if (!T.walls[f.tip]) T.walls[f.tip] = new THREE.MeshLambertMaterial({ color: COLOR[f.tip] || 0xc8b8a0, map: T.winTex });
          const g = new THREE.BoxGeometry(f.w, h, f.d);
          // UV-urile in metri / 3 pe fiecare fata (+x, -x, +y, -y, +z, -z), ca textura sa se repete, nu sa se intinda
          const uv = g.attributes.uv, dims = [[f.d, h], [f.d, h], [f.w, f.d], [f.w, f.d], [f.w, h], [f.w, h]];
          const fl = FLOOR[f.tip] || 3.1;
          for (let k = 0; k < 6; k++) for (let v = 0; v < 4; v++) {
            const i = k * 4 + v;
            uv.setXY(i, uv.getX(i) * Math.max(1, Math.round(dims[k][0] / 3)), uv.getY(i) * Math.max(1, Math.round(dims[k][1] / fl)));
          }
          const wall = T.walls[f.tip];
          const m = new THREE.Mesh(g, [wall, wall, T.roof, T.roof, wall, wall]);
          m.position.set(f.x, this.terrainZ(f.x, f.y) + 0.2 + h / 2, -f.y);
          m.rotation.y = (f.r + 90) * Math.PI / 180;       // latimea (x-ul cutiei) de-a lungul fatadei
          T.group.add(m);
        }
      },
      build3d() {
        if (!T.ready) return;
        if (T.group) { T.scene.remove(T.group); T.group.traverse(o => { if (o.geometry) o.geometry.dispose(); }); }
        T.group = new THREE.Group(); T.scene.add(T.group);
        const A = this.analysis;
        if (!A) { this.render3d(); return; }
        const V3 = (x, y, z) => new THREE.Vector3(x, z, -y);
        const mat = c => new THREE.MeshLambertMaterial({ color: c, side: THREE.DoubleSide });
        const addTris = (tris, color) => {
          const g = new THREE.BufferGeometry();
          g.setAttribute('position', new THREE.Float32BufferAttribute(tris, 3)); g.computeVertexNormals();
          T.group.add(new THREE.Mesh(g, mat(color)));
        };
        const flat = (poly, z, color) => {
          const pts = poly.map(p => new THREE.Vector2(p[0], p[1]));
          const tris = [];
          THREE.ShapeUtils.triangulateShape(pts, []).forEach(t => t.forEach(i => { tris.push(pts[i].x, z, -pts[i].y); }));
          addTris(tris, color);
        };
        if (A.teren) {
          const t = A.teren, ny = t.z.length, nx = t.z[0].length, tris = [];
          const P = (i, j) => [t.x0 + i * t.step, t.z[j][i] - 0.4, -(t.y0 + j * t.step)];
          for (let j = 0; j + 1 < ny; j++) for (let i = 0; i + 1 < nx; i++) {
            tris.push(...P(i, j), ...P(i + 1, j), ...P(i + 1, j + 1), ...P(i, j), ...P(i + 1, j + 1), ...P(i, j + 1));
          }
          addTris(tris, 0x5b7a4b);
        }
        Object.values(A.roads).forEach(r => {
          const smp = r.samples;
          for (const [w, dz, color] of [[r.W, 0.15, 0x9aa0a8], [r.r / 2, 0.2, 0x42464d]]) {
            const tris = [];
            for (let i = 0; i + 1 < smp.length; i++) {
              const a = smp[i], b = smp[i + 1];
              const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1, nx = -dy / L * w, ny = dx / L * w;
              const q = [[a[0] + nx, a[1] + ny, a[2]], [a[0] - nx, a[1] - ny, a[2]], [b[0] - nx, b[1] - ny, b[2]], [b[0] + nx, b[1] + ny, b[2]]];
              [0, 1, 2, 0, 2, 3].forEach(k => { tris.push(q[k][0], q[k][2] + dz, -q[k][1]); });
            }
            addTris(tris, color);
          }
        });
        Object.values(A.junctions).forEach(j => {
          j.trotuare.forEach(w => flat(w.poligon, j.z + 0.15, 0x9aa0a8));
          flat(j.asfalt, j.z + 0.2, 0x42464d);
        });
        // cu cladirile previzualizate, cvartalele raman plate (volumul zonei le-ar acoperi)
        const withBuildings = this.showFoot && (V.foot || []).length > 0;
        A.blocks.forEach(b => {
          if (b.poligon.length < 3) return;
          if (b.zona === 'apa') return;
          const z = ZMAP[b.zona] || ZMAP.gol;
          const shape = new THREE.Shape(b.poligon.map(p => new THREE.Vector2(p[0], p[1])));
          const g = new THREE.ExtrudeGeometry(shape, { depth: b.valid && !withBuildings ? z.h : 0.3, bevelEnabled: false });
          g.rotateX(-Math.PI / 2);
          const m = new THREE.Mesh(g, mat(new THREE.Color(b.valid ? z.culoare : '#666666')));
          m.position.y = this.terrainZ(b.centru[0], b.centru[1]) + 0.2;
          T.group.add(m);
        });
        // marea (orasul sta la joc.z m deasupra ei) si apa desenata
        const bb = A.bounds, cxm = (bb[0] + bb[2]) / 2, cym = (bb[1] + bb[3]) / 2;
        const seaMesh = new THREE.Mesh(new THREE.PlaneGeometry(8000, 8000), new THREE.MeshLambertMaterial({ color: 0x2d5d7b, transparent: true, opacity: 0.88 }));
        seaMesh.rotation.x = -Math.PI / 2; seaMesh.position.set(cxm, A.mare !== undefined ? A.mare : -3, -cym); T.group.add(seaMesh);
        (A.suprafete || []).forEach(a => {
          if (a.tip === 'apa' || a.poligon.length < 3) return;
          const c = a.poligon.reduce((acc, p) => [acc[0] + p[0] / a.poligon.length, acc[1] + p[1] / a.poligon.length], [0, 0]);
          flat(a.poligon, this.terrainZ(c[0], c[1]) + 0.35, new THREE.Color(this.areaColor(a.tip)));
        });
        (this.plan.cladiri || []).forEach(bd => {
          const f = footprint(bd), shape = new THREE.Shape(f.map(p => new THREE.Vector2(p[0], p[1])));
          const h = bd.tip === 'gta' ? (bd.h || 12) : (bd.p.etaje || 1) * 3.2 + 1.5;
          const g = new THREE.ExtrudeGeometry(shape, { depth: h, bevelEnabled: false }); g.rotateX(-Math.PI / 2);
          const mm = new THREE.Mesh(g, mat(bd.tip === 'gta' ? 0x8fb1d6 : 0xd6a878)); mm.position.y = this.terrainZ(bd.x, bd.y) + 0.2; T.group.add(mm);
        });
        if (withBuildings) this.buildings3d();
        const placed = (this.plan.props || []).filter(o => !this.underBuilding(o.x, o.y));
        if (placed.length) {
          const inst = (list, geo, color, y) => {
            if (!list.length) return;
            const im = new THREE.InstancedMesh(geo, mat(color), list.length), M = new THREE.Matrix4();
            list.forEach((o, i) => { M.makeTranslation(o.x, this.terrainZ(o.x, o.y) + y, -o.y); im.setMatrixAt(i, M); });
            T.group.add(im);
          };
          inst(placed.filter(o => /tree/.test(o.m)), new THREE.ConeGeometry(2.8, 9, 7), 0x3f7a3a, 5);
          inst(placed.filter(o => !/tree/.test(o.m)), new THREE.BoxGeometry(1.2, 1.2, 1.2), 0xb0a080, 0.8);
        }
        Object.values(A.roads).forEach(r => {     // pilonii podurilor
          if (r.nivel !== 'pod') return;
          for (let i = 3; i < r.samples.length - 3; i += 7) {
            const p = r.samples[i], zg = this.terrainZ(p[0], p[1]);
            if (p[2] - zg < 3) continue;
            const mm = new THREE.Mesh(new THREE.BoxGeometry(1.4, p[2] - zg, 1.4), mat(0x9a9a9a));
            mm.position.set(p[0], zg + (p[2] - zg) / 2, -p[1]); T.group.add(mm);
          }
        });
        this.plan.nodes.forEach(n => {
          const m = new THREE.Mesh(new THREE.SphereGeometry(1.6, 10, 8), mat(0xffffff));
          m.position.copy(V3(n.x, n.y, (n.z || 0) + 1.5)); T.group.add(m);
        });
        this.render3d();
      },
      render3d() {
        if (!T.ready || !this.view3d) return;
        const o = T.o, ce = Math.cos(o.el);
        T.camera.position.set(o.tx + Math.sin(o.az) * ce * o.dist, o.ty + Math.sin(o.el) * o.dist, o.tz + Math.cos(o.az) * ce * o.dist);
        T.camera.lookAt(o.tx, o.ty, o.tz);
        T.renderer.render(T.scene, T.camera);
      },
    },
  });
})();
