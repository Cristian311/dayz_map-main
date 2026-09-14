/* GPS pe strazile orasului: cand pui un waypoint in oras, traseul cel mai scurt pe strazile lui apare pe minimap si
   pe harta mare (ruta GPS "custom" a jocului; orasul nu are noduri de trafic GTA, deci GPS-ul normal nu-l vede).
   Copiat la export din tools/oras/gps_client.js, cu reteaua de strazi pusa in locul lui NET - nu edita de mana. */
const NET = /*NET*/null;
const ROUTE_COLOR = 12;       // HUD_COLOUR_YELLOW
const MAX_POINTS = 90;        // ruta custom tine un numar limitat de puncte: pastram colturile
const OFF_ROUTE = 40.0;       // m de ruta: se recalculeaza
const ARRIVED = 15.0;         // m de waypoint: ruta si waypointul dispar
// harta orasului e un strat opac pe minimap si acopera linia rutei custom; blipurile se deseneaza deasupra lui,
// asa ca traseul se arata si ca sir de puncte galbene, sterse din urma pe masura ce le treci
const DOT_STEP = 8.0;         // m intre puncte
const MAX_DOTS = 500;
const DOT_COLOUR = 5;         // galben
const PASSED = 18.0;          // m: punctul e in urma ta

const P = [];                 // varfurile retelei: [x, y, z]
const E = [];                 // vecinii fiecarui varf: [[varf, lungime]]
let box = null;               // dreptunghiul orasului (+200 m): waypointurile din afara lui nu sunt ale noastre

function addPoint(p) {
    P.push(p);
    E.push([]);
    return P.length - 1;
}

function link(a, b) {
    const d = Math.hypot(P[a][0] - P[b][0], P[a][1] - P[b][1], P[a][2] - P[b][2]);
    E[a].push([b, d]);
    E[b].push([a, d]);
}

function build() {
    const J = {};
    for (const [id, p] of Object.entries(NET.j)) J[id] = addPoint(p);
    for (const [a, b, pts] of NET.r) {
        let prev = a !== null && J[a] !== undefined ? J[a] : -1;
        for (const p of pts) {
            const v = addPoint(p);
            if (prev >= 0) link(prev, v);
            prev = v;
        }
        if (b !== null && J[b] !== undefined && prev >= 0) link(prev, J[b]);
    }
    box = [Infinity, Infinity, -Infinity, -Infinity];
    for (const [x, y] of P) box = [Math.min(box[0], x), Math.min(box[1], y), Math.max(box[2], x), Math.max(box[3], y)];
    box = [box[0] - 200, box[1] - 200, box[2] + 200, box[3] + 200];
}

function nearest(x, y) {
    let best = -1;
    let bestD = Infinity;
    for (let i = 0; i < P.length; i += 1) {
        const d = (P[i][0] - x) ** 2 + (P[i][1] - y) ** 2;
        if (d < bestD) {
            bestD = d;
            best = i;
        }
    }
    return best;
}

// A* cu un heap binar: drumul cel mai scurt intre doua varfuri, ca lista de varfuri
function shortest(from, to) {
    const g = new Float64Array(P.length).fill(Infinity);
    const came = new Int32Array(P.length).fill(-1);
    const h = (i) => Math.hypot(P[i][0] - P[to][0], P[i][1] - P[to][1]);
    const heap = [[h(from), from]];
    g[from] = 0;
    const push = (item) => {
        heap.push(item);
        let i = heap.length - 1;
        while (i > 0) {
            const up = (i - 1) >> 1;
            if (heap[up][0] <= heap[i][0]) break;
            [heap[up], heap[i]] = [heap[i], heap[up]];
            i = up;
        }
    };
    const pop = () => {
        const top = heap[0];
        const last = heap.pop();
        if (heap.length) {
            heap[0] = last;
            let i = 0;
            for (;;) {
                const l = 2 * i + 1;
                const r = l + 1;
                let m = i;
                if (l < heap.length && heap[l][0] < heap[m][0]) m = l;
                if (r < heap.length && heap[r][0] < heap[m][0]) m = r;
                if (m === i) break;
                [heap[m], heap[i]] = [heap[i], heap[m]];
                i = m;
            }
        }
        return top;
    };
    while (heap.length) {
        const [f, v] = pop();
        if (v === to) break;
        if (f - h(v) > g[v] + 1e-6) continue;
        for (const [w, d] of E[v]) {
            const ng = g[v] + d;
            if (ng < g[w]) {
                g[w] = ng;
                came[w] = v;
                push([ng + h(w), w]);
            }
        }
    }
    if (from !== to && came[to] < 0) return null;
    const path = [to];
    while (path[path.length - 1] !== from) path.push(came[path[path.length - 1]]);
    return path.reverse();
}

// Punctele pentru ruta: capetele si colturile (unde strada coteste), cel mult MAX_POINTS.
function corners(path) {
    const keep = [path[0]];
    for (let k = 1; k + 1 < path.length; k += 1) {
        const [a, b, c] = [P[keep[keep.length - 1]], P[path[k]], P[path[k + 1]]];
        const turn = Math.abs(Math.atan2(c[1] - b[1], c[0] - b[0]) - Math.atan2(b[1] - a[1], b[0] - a[0]));
        const bend = Math.min(turn, 2 * Math.PI - turn);
        if (bend > 0.12 || Math.hypot(b[0] - a[0], b[1] - a[1]) > 120) keep.push(path[k]);
    }
    keep.push(path[path.length - 1]);
    if (keep.length <= MAX_POINTS) return keep;
    const step = (keep.length - 1) / (MAX_POINTS - 1);
    return Array.from({ length: MAX_POINTS }, (_, i) => keep[Math.round(i * step)]);
}

let target = null;
let route = null;
let dots = [];                // [blip, x, y], in ordinea traseului

function clearDots() {
    for (const [blip] of dots) RemoveBlip(blip);
    dots = [];
}

function addDot(x, y, z) {
    const blip = AddBlipForCoord(x, y, z);
    SetBlipSprite(blip, 1);
    SetBlipScale(blip, 0.4);
    SetBlipColour(blip, DOT_COLOUR);
    SetBlipDisplay(blip, 8);              // pe minimap si pe harta mare, fara sa poata fi selectat
    SetBlipAsShortRange(blip, true);      // nu se lipesc de marginea minimapului
    SetBlipHiddenOnLegend(blip, true);
    SetBlipPriority(blip, 1);
    dots.push([blip, x, y]);
}

function placeDots(path) {
    clearDots();
    let carry = DOT_STEP;
    for (let k = 1; k < path.length && dots.length < MAX_DOTS; k += 1) {
        const [a, b] = [P[path[k - 1]], P[path[k]]];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        let s = carry;
        for (; s < len && dots.length < MAX_DOTS; s += DOT_STEP) {
            const t = s / len;
            addDot(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t);
        }
        carry = s - len;
    }
}

function trimDots(x, y) {
    let cut = -1;
    for (let i = 0; i < Math.min(dots.length, 12); i += 1) {
        if (Math.hypot(dots[i][1] - x, dots[i][2] - y) < PASSED) cut = i;
    }
    for (let i = 0; i <= cut; i += 1) RemoveBlip(dots[i][0]);
    if (cut >= 0) dots.splice(0, cut + 1);
}

function clearRoute() {
    if (route) ClearGpsCustomRoute();
    clearDots();
    route = null;
    target = null;
}

function draw(px, py, wx, wy) {
    const path = shortest(nearest(px, py), nearest(wx, wy));
    if (!path) {
        console.log(`[${GetCurrentResourceName()}] GPS: nu am gasit drum pe strazi pana la waypoint`);
        return clearRoute();
    }
    ClearGpsCustomRoute();
    StartGpsCustomRoute(ROUTE_COLOR, true, true);
    for (const i of corners(path)) AddPointToGpsCustomRoute(P[i][0], P[i][1], P[i][2]);
    SetGpsCustomRouteRender(true, 16, 16);
    placeDots(path);
    route = path;
    target = [wx, wy];
    console.log(`[${GetCurrentResourceName()}] GPS: traseu cu ${dots.length} puncte`);
}

function offRoute(x, y) {
    let best = Infinity;
    for (const i of route) best = Math.min(best, Math.hypot(P[i][0] - x, P[i][1] - y));
    return best > OFF_ROUTE;
}

function update() {
    if (!IsWaypointActive()) return clearRoute();
    const [wx, wy] = GetBlipInfoIdCoord(GetFirstBlipInfoId(8));
    if (wx < box[0] || wy < box[1] || wx > box[2] || wy > box[3]) return clearRoute();
    const [px, py] = GetEntityCoords(PlayerPedId(), false);
    if (Math.hypot(px - wx, py - wy) < ARRIVED) {
        SetWaypointOff();
        return clearRoute();
    }
    const moved = !target || Math.hypot(wx - target[0], wy - target[1]) > 1.0;
    if (moved || offRoute(px, py)) draw(px, py, wx, wy);
    else trimDots(px, py);
}

if (NET && NET.r && NET.r.length) {
    build();
    setInterval(update, 1000);
}

on('onResourceStop', (res) => {
    if (res === GetCurrentResourceName()) clearRoute();
});
