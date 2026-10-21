// Patchwork signature fold: a real quilt rolled over a moving cylinder.
//
// The sheet is a fine grid (uv 0..1) the size of the scene patch. Each vertex
// is curled in the vertex shader in a *local* frame (mirrored for the leftward
// moves): points behind the roll axis lie flat on the scene, points past it wrap
// a cylinder of radius R, and points past half a turn lie flipped on top,
// rippling like loose cloth. A pinhole camera above the canvas centre makes the
// roll swell toward the viewer.
//
// The front is a pieced quilt (a diamond-in-square block of half-square
// triangles, a few appliqued hearts and sewn-on buttons, a bound edge), lit
// with a normal derived from its quilted puff, woven thread texture and running
// stitches along every seam. The back is the gingham lining with the quilting
// stitches showing through. A second pass casts the roll's shadow onto the
// scene underneath.

struct U {
    page: vec4<f32>,   // x W, y H (sheet px), zw sheet origin inside the canvas (px)
    view: vec4<f32>,   // xy canvas size (px), z camera distance (px), w mirror (0/1)
    axis: vec4<f32>,   // xy a point on the roll axis (local px), zw unit normal toward the free edge (local)
    curl: vec4<f32>,   // x radius (px), y shadow strength, z px per sheet point, w ripple amplitude (px)
    light: vec4<f32>,  // xyz toward the light, w ambient
    look: vec4<f32>,   // x theme (0 forward/terracotta, 1 back/rose), y seed, z,w sheet size in points
};

@group(0) @binding(0) var<uniform> u: U;

const PI: f32 = 3.14159265;
const CELL: f32 = 65.0;

// ------------------------------------------------------------------ palette
const IND = vec3<f32>(0.188, 0.294, 0.459);
const IND_D = vec3<f32>(0.137, 0.227, 0.369);
const IND_L = vec3<f32>(0.357, 0.451, 0.612);
const TER = vec3<f32>(0.800, 0.439, 0.318);
const TER_D = vec3<f32>(0.663, 0.353, 0.251);
const TER_L = vec3<f32>(0.878, 0.604, 0.494);
const ROSE = vec3<f32>(0.914, 0.675, 0.698);
const ROSE_D = vec3<f32>(0.831, 0.549, 0.584);
const ROSE_L = vec3<f32>(0.957, 0.827, 0.839);
const OAT = vec3<f32>(0.961, 0.922, 0.867);
const CREAM = vec3<f32>(0.984, 0.965, 0.933);
const TEAL = vec3<f32>(0.302, 0.561, 0.514);
const TEAL_D = vec3<f32>(0.227, 0.431, 0.396);
const TEAL_L = vec3<f32>(0.553, 0.733, 0.694);
const MUST = vec3<f32>(0.851, 0.647, 0.290);

fn hash(p: vec2<f32>) -> f32 {
    var q = fract(p * vec2<f32>(0.1031, 0.1030));
    q = q + dot(q, q.yx + 33.33);
    return fract((q.x + q.y) * q.x);
}

fn vnoise(p: vec2<f32>) -> f32 {
    let i = floor(p);
    let f = fract(p);
    let w = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2<f32>(1.0, 0.0)), w.x),
               mix(hash(i + vec2<f32>(0.0, 1.0)), hash(i + vec2<f32>(1.0, 1.0)), w.x), w.y);
}

fn darkOf(h: f32) -> vec3<f32> {
    if (u.look.x < 0.5) {
        if (h < 0.28) { return TER; }
        if (h < 0.50) { return IND; }
        if (h < 0.68) { return TEAL; }
        if (h < 0.80) { return ROSE_D; }
        if (h < 0.90) { return TER_D; }
        return MUST;
    }
    if (h < 0.30) { return ROSE_D; }
    if (h < 0.52) { return TEAL; }
    if (h < 0.70) { return IND_L; }
    if (h < 0.86) { return TER_L; }
    return TEAL_D;
}

fn lightOf(h: f32) -> vec3<f32> {
    if (h < 0.45) { return OAT; }
    if (h < 0.75) { return select(ROSE_L, TEAL_L * 0.35 + OAT * 0.65, u.look.x > 0.5); }
    return CREAM;
}

fn bindingCol() -> vec3<f32> {
    return select(IND, TEAL_D, u.look.x > 0.5);
}

fn dot2(v: vec2<f32>) -> f32 {
    return dot(v, v);
}

// Inigo Quilez's heart, point at the origin, ~1 unit tall (y up).
fn sdHeart(pin: vec2<f32>) -> f32 {
    let p = vec2<f32>(abs(pin.x), pin.y);
    if (p.y + p.x > 1.0) {
        return sqrt(dot2(p - vec2<f32>(0.25, 0.75))) - sqrt(2.0) / 4.0;
    }
    return sqrt(min(dot2(p - vec2<f32>(0.0, 1.0)), dot2(p - 0.5 * max(p.x + p.y, 0.0)))) * sign(p.x - p.y);
}

// Distance (points) to the nearest seam: cell edges and the HST diagonal.
struct Seam {
    edge: f32,
    diag: f32,
    dark: bool,
    along: f32,  // coordinate along the diagonal (for stitch dashes)
};

fn seams(q: vec2<f32>) -> Seam {
    let c = q / CELL;
    let cell = floor(c);
    let f = fract(c);
    let ix = i32(cell.x) & 1;
    let iy = i32(cell.y) & 1;
    var s: Seam;
    s.edge = min(min(f.x, 1.0 - f.x), min(f.y, 1.0 - f.y)) * CELL;
    // the dark triangle of each half-square triangle points at its block centre,
    // so every 2x2 block shows a dark diamond on a light ground
    var dd: f32;
    if (ix == iy) {
        dd = (f.x + f.y - 1.0) * 0.7071;
        s.along = (f.x - f.y) * 0.7071 * CELL;
        s.dark = select(dd > 0.0, dd < 0.0, ix == 1);
    } else {
        dd = (f.y - f.x) * 0.7071;
        s.along = (f.x + f.y) * 0.7071 * CELL;
        s.dark = select(dd > 0.0, dd < 0.0, ix == 0);
    }
    s.diag = abs(dd) * CELL;
    return s;
}

fn edgeDist(q: vec2<f32>) -> f32 {
    return min(min(q.x, u.look.z - q.x), min(q.y, u.look.w - q.y));
}

// Quilted loft: pillowy between seams, sunk at every seam, a rounded binding.
fn loft(q: vec2<f32>) -> f32 {
    let s = seams(q);
    let d = min(s.edge, s.diag);
    var h = sqrt(clamp(d / 13.0, 0.0, 1.0));
    let e = edgeDist(q);
    if (e < 8.0) {
        h = 0.55 + 0.45 * sin(PI * clamp(e / 8.0, 0.0, 1.0));
    } else if (e < 11.0) {
        h = h * smoothstep(8.0, 11.0, e);
    }
    return h;
}

fn weave(q: vec2<f32>) -> f32 {
    let a = q / 2.6;
    let cx = i32(floor(a.x));
    let cy = i32(floor(a.y));
    let over = ((cx + cy) & 1) == 1;
    let fx = fract(a.x);
    let fy = fract(a.y);
    let warp = sin(PI * fx);
    let weft = sin(PI * fy);
    let slub = vnoise(vec2<f32>(q.x * 0.35, q.y * 0.03)) * 0.5 + vnoise(vec2<f32>(q.x * 0.03, q.y * 0.35)) * 0.5;
    return select(weft, warp, over) * 0.75 + slub * 0.25;
}

// Albedo of the pieced front at sheet point q.
fn front(q: vec2<f32>) -> vec3<f32> {
    let seed = vec2<f32>(u.look.y * 7.13, u.look.y * 3.71);
    let s = seams(q);
    let block = floor(q / (2.0 * CELL));
    let corner = floor((q + vec2<f32>(CELL)) / (2.0 * CELL));
    var col: vec3<f32>;
    if (s.dark) {
        col = darkOf(hash(block + seed));
    } else {
        col = lightOf(hash(corner + seed + vec2<f32>(5.1, 1.7)));
    }
    // applique on some dark diamonds: a heart or a sewn-on button
    let bc = (block + vec2<f32>(1.0)) * 2.0 * CELL - vec2<f32>(CELL);
    let hb = hash(block + seed + vec2<f32>(11.0, 3.0));
    let m = (q - bc) / 22.0;
    if (hb > 0.55) {
        let dh = sdHeart(vec2<f32>(m.x, -m.y + 0.55));
        let ink = select(CREAM, ROSE_L, hb > 0.8);
        col = mix(col, ink, 1.0 - smoothstep(-0.02, 0.03, dh));
        // blanket stitch round the heart
        let ring = abs(dh + 0.09);
        let dash = step(0.5, fract(atan2(m.y, m.x) * 4.0));
        col = mix(col, TER_D, (1.0 - smoothstep(0.012, 0.03, ring)) * dash * 0.8);
    } else if (hb < 0.18) {
        let r = length(q - bc);
        col = mix(col, MUST, 1.0 - smoothstep(8.0, 8.8, r));
        let holes = vec2<f32>(abs(q.x - bc.x) - 2.4, abs(q.y - bc.y) - 2.4);
        col = mix(col, TER_D, (1.0 - smoothstep(0.8, 1.4, length(holes))) * step(r, 8.0));
    }
    // running stitches 4 pt inside every seam
    let thread = select(TER_D, CREAM, s.dark);
    let onEdge = (1.0 - smoothstep(0.45, 0.95, abs(s.edge - 4.2))) * step(0.45, fract((q.x + q.y) / 7.0));
    let onDiag = (1.0 - smoothstep(0.45, 0.95, abs(s.diag - 4.2))) * step(0.45, fract(s.along / 7.0));
    col = mix(col, thread, max(onEdge, onDiag) * 0.85);
    // the binding round the edge, with its stitch line
    let e = edgeDist(q);
    let bnd = 1.0 - smoothstep(7.5, 8.3, e);
    col = mix(col, bindingCol(), bnd);
    let bs = (1.0 - smoothstep(0.4, 0.9, abs(e - 10.5))) * step(0.5, fract((q.x + q.y) / 6.0));
    col = mix(col, CREAM, bs * 0.7 * (1.0 - bnd));
    return col;
}

// The lining: gingham, with the quilting stitched through it.
fn back(q: vec2<f32>) -> vec3<f32> {
    let lining = select(ROSE, TEAL_L, u.look.x > 0.5);
    let sx = smoothstep(0.46, 0.54, fract(q.x / 12.0)) * (1.0 - smoothstep(0.96, 1.0, fract(q.x / 12.0)));
    let sy = smoothstep(0.46, 0.54, fract(q.y / 12.0)) * (1.0 - smoothstep(0.96, 1.0, fract(q.y / 12.0)));
    var col = mix(CREAM, lining, 0.32 * sx + 0.32 * sy);
    let s = seams(q);
    let line = min(s.edge, s.diag);
    let dash = step(0.45, fract((q.x + q.y + s.along) / 7.0));
    col = mix(col, TER_D, (1.0 - smoothstep(0.5, 1.1, line)) * dash * 0.8);
    let e = edgeDist(q);
    col = mix(col, bindingCol(), 1.0 - smoothstep(7.5, 8.3, e));
    return col;
}

// ------------------------------------------------------------------ geometry
struct Curl {
    pos: vec3<f32>,
    a: f32,
};

fn curlPoint(P: vec2<f32>) -> Curl {
    let A = u.axis.xy;
    let n = u.axis.zw;
    let R = max(u.curl.x, 1.0);
    let d = dot(P - A, n);
    var c: Curl;
    if (d <= 0.0) {
        c.pos = vec3<f32>(P, 0.0);
        c.a = 0.0;
        return c;
    }
    let foot = P - d * n;
    if (d < PI * R) {
        let a = d / R;
        c.pos = vec3<f32>(foot + R * sin(a) * n, R * (1.0 - cos(a)));
        c.a = a;
    } else {
        let s = d - PI * R;
        let k = 2.0 * PI / (28.0 * u.curl.z);
        let rip = u.curl.w * sin(s * k) * smoothstep(0.0, 22.0 * u.curl.z, s);
        c.pos = vec3<f32>(foot - s * n, 2.0 * R + rip);
        c.a = PI;
    }
    return c;
}

// local frame (where the roll always travels toward -x) <-> sheet frame
fn toLocal(P: vec2<f32>) -> vec2<f32> {
    return select(P, vec2<f32>(u.page.x - P.x, P.y), u.view.w > 0.5);
}

fn project(pl: vec3<f32>) -> vec4<f32> {
    let p = vec3<f32>(toLocal(pl.xy) + u.page.zw, pl.z);
    let cam = u.view.xy * 0.5;
    let D = u.view.z;
    let f = D / max(D - p.z, 1.0);
    let q = cam + (p.xy - cam) * f;
    let ndc = vec2<f32>(q.x / u.view.x * 2.0 - 1.0, 1.0 - q.y / u.view.y * 2.0);
    let w = 1.0 / f;
    let depth = clamp(0.5 - p.z / (10.0 * max(u.curl.x, 1.0)), 0.01, 0.99);
    return vec4<f32>(ndc * w, depth * w, w);
}

fn pageSdf(p: vec2<f32>) -> f32 {
    let h = u.page.xy * 0.5;
    let q = abs(p - h) - h;
    return length(max(q, vec2<f32>(0.0))) + min(max(q.x, q.y), 0.0);
}

// ------------------------------------------------------------------ sheet
struct SheetOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) lp: vec2<f32>,   // local px (unmirrored sheet frame)
    @location(1) q: vec2<f32>,    // sheet points (pattern space)
};

@vertex
fn vs_sheet(@location(0) uv: vec2<f32>) -> SheetOut {
    let P = uv * u.page.xy;
    let L = toLocal(P);
    let c = curlPoint(L);
    var o: SheetOut;
    o.clip = project(c.pos);
    o.lp = L;
    o.q = uv * u.look.zw;
    return o;
}

fn flatShadow(S: vec2<f32>) -> f32 {
    let A = u.axis.xy;
    let n = u.axis.zw;
    let R = max(u.curl.x, 1.0);
    let L = normalize(u.light.xyz);
    let off = -L.xy / max(L.z, 0.25) * (2.0 * R) * 0.55;
    let Q = S - off;
    let s = dot(Q - A, n);
    let P = Q + (PI * R - 2.0 * s) * n;
    let flip = (1.0 - smoothstep(-R * 0.8, R * 0.5, pageSdf(P))) * (1.0 - smoothstep(-R * 0.2, R * 0.3, s));
    return clamp(u.curl.y * 0.34 * flip, 0.0, 0.55);
}

@fragment
fn fs_sheet(i: SheetOut) -> @location(0) vec4<f32> {
    let n = u.axis.zw;
    let t = vec2<f32>(-n.y, n.x);
    let R = max(u.curl.x, 1.0);
    let d = dot(i.lp - u.axis.xy, n);
    let a = clamp(d / R, 0.0, PI);
    // surface frame of the curled sheet (local)
    let Tn = vec3<f32>(cos(a) * n, sin(a));
    let Tt = vec3<f32>(t, 0.0);
    var Nf = vec3<f32>(-sin(a) * n, cos(a));
    // ripple of the flipped cloth tilts its normal along n
    if (d > PI * R) {
        let s = d - PI * R;
        let k = 2.0 * PI / (28.0 * u.curl.z);
        let slope = u.curl.w * k * cos(s * k) * smoothstep(0.0, 22.0 * u.curl.z, s);
        Nf = normalize(Nf + vec3<f32>(n * slope, 0.0));
    }
    // quilted loft as a bump: gradient along the sheet, in points
    let e = 0.9;
    let h0 = loft(i.q);
    let gx = (loft(i.q + vec2<f32>(e, 0.0)) - h0) / e;
    let gy = (loft(i.q + vec2<f32>(0.0, e)) - h0) / e;
    // the pattern's x runs mirrored in the local frame when mirrored
    let mx = select(1.0, -1.0, u.view.w > 0.5);
    let g = vec2<f32>(gx * mx, gy) * 5.5;
    let gn = dot(g, n);
    let gt = dot(g, t);
    let front_ = cos(a) >= 0.0;
    var col: vec3<f32>;
    var N: vec3<f32>;
    if (front_) {
        col = front(i.q);
        N = normalize(Nf - gn * Tn - gt * Tt);
    } else {
        col = back(i.q);
        N = normalize(-Nf - gn * Tn - gt * Tt);
    }
    // woven thread and felted mottling
    let wv = weave(i.q);
    col = col * (0.93 + 0.10 * wv) * (0.97 + 0.06 * vnoise(i.q * 0.12));
    // seams sit in shadow (occlusion from the loft)
    col = col * (0.72 + 0.28 * h0);
    // light: in the mirrored frame flip the light's x so shading stays world-consistent
    let Lw = normalize(u.light.xyz);
    let L = vec3<f32>(Lw.x * mx, Lw.y, Lw.z);
    let amb = u.light.w;
    let flatLit = amb + (1.0 - amb) * max(L.z, 0.0);
    let lit = amb + (1.0 - amb) * max(dot(N, L), 0.0);
    let k = clamp(lit / flatLit, 0.42, 1.18);
    col = col * k * mix(vec3<f32>(1.02, 0.97, 0.93), vec3<f32>(1.0), smoothstep(0.6, 1.0, k));
    // soft cloth sheen on the crest of the roll and on raised loft
    let H = normalize(L + vec3<f32>(0.0, 0.0, 1.0));
    let sheen = max(pow(max(dot(N, H), 0.0), 10.0) - pow(max(H.z, 0.0), 10.0), 0.0);
    col = col + vec3<f32>(1.0, 0.97, 0.92) * sheen * 0.22;
    let rim = pow(1.0 - clamp(abs(N.z), 0.0, 1.0), 3.0);
    col = col + vec3<f32>(1.0, 0.95, 0.9) * rim * 0.06;
    // occlusion deep in the roll where it nearly meets itself
    let inner = smoothstep(PI * 0.55, PI * 0.95, a) * (1.0 - smoothstep(PI * 0.95, PI, a));
    col = col * (1.0 - 0.22 * inner);
    if (a <= 0.0) {
        col = col * (1.0 - flatShadow(i.lp));
    }
    return vec4<f32>(clamp(col, vec3<f32>(0.0), vec3<f32>(1.0)), 1.0);
}

// ------------------------------------------------------------------ cast shadow on the scene beneath
struct ShadowOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) pp: vec2<f32>,
};

@vertex
fn vs_shadow(@builtin(vertex_index) vi: u32) -> ShadowOut {
    var corners = array<vec2<f32>, 6>(
        vec2<f32>(0.0, 0.0), vec2<f32>(1.0, 0.0), vec2<f32>(0.0, 1.0),
        vec2<f32>(0.0, 1.0), vec2<f32>(1.0, 0.0), vec2<f32>(1.0, 1.0));
    let c = corners[vi];
    var o: ShadowOut;
    o.clip = vec4<f32>(c.x * 2.0 - 1.0, 1.0 - c.y * 2.0, 0.995, 1.0);
    o.pp = c * u.view.xy - u.page.zw;
    return o;
}

@fragment
fn fs_shadow(i: ShadowOut) -> @location(0) vec4<f32> {
    let S = toLocal(i.pp);
    let A = u.axis.xy;
    let n = u.axis.zw;
    let R = max(u.curl.x, 1.0);
    let s = dot(S - A, n);
    let foot = S - s * n;
    let along = 1.0 - smoothstep(-R * 0.5, R * 0.9, pageSdf(foot));
    let inPage = 1.0 - smoothstep(-2.0, 6.0, pageSdf(S));
    let band = (1.0 - smoothstep(R * 0.4, R * 3.6, s)) * step(0.0, s);
    let broad = (1.0 - smoothstep(0.0, u.page.x * 1.2, s)) * step(0.0, s);
    let k = u.curl.y * along * inPage * (0.46 * band + 0.12 * broad);
    let tint = vec3<f32>(0.075, 0.10, 0.16);
    return vec4<f32>(tint * k, k);
}
