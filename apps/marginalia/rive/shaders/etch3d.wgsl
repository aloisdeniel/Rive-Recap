// Marginalia etched 3D: small lit objects (open books, closed volumes, a brass
// reading lamp, a paper theatre) built from parametric patches and printed
// like the engraved moon.
//
// Geometry: there are no vertex buffers. Every instance is one *patch* of the
// uniform array below; the vertex shader turns (vertex_index -> grid cell,
// corner -> u,v) into a point of that patch's surface (a quad, a frustum, a
// sphere, a page block, an arch, a curtain...), moves it by the patch's model
// matrix, takes its normal from the surface itself (central differences, so a
// bent page is smooth) and projects it through a pinhole camera that looks at
// the scene from slightly above. One instanced draw, a depth buffer, 4x MSAA.
//
// Shading: a soft key light, an optional spot light (the theatre's moon, the
// reading lamp) and a little specular, then *printed*: where the tone falls,
// engraved hatch lines follow the object (they are laid in its own space, so
// they turn with it) and swell with darkness - the moon's technique, so the 3D
// objects belong to the same book as the vector art. Materials add page type,
// page-edge lines, cloth, brass, a starry backdrop and stage boards.
//
// A second entry point (fs_beam) draws the reading lamp's light in the
// drawable's own 2D space: a soft cone, a pool and dust motes drifting in it.
// No `discard` anywhere; output is premultiplied.

struct G {
    cam: vec4<f32>,    // x cos pitch, y sin pitch, z camera distance, w depth half-range
    eye: vec4<f32>,    // xyz camera position (world), w px per unit (AA)
    box: vec4<f32>,    // drawable-space box the canvas covers: x, y, w, h
    key: vec4<f32>,    // xyz direction toward the key light, w key strength
    amb: vec4<f32>,    // rgb ambient, w etch strength
    spot: vec4<f32>,   // xyz spot position (world), w intensity
    sdir: vec4<f32>,   // xyz spot direction, w cos(outer angle)
    scol: vec4<f32>,   // rgb spot colour, w cos(inner angle)
    ink: vec4<f32>,    // rgb engraving ink, w spot range (falloff distance)
    beam0: vec4<f32>,  // fs_beam: apex xy, unit direction xy (drawable space)
    beam1: vec4<f32>,  // x mouth radius, y spread (tan), z length, w intensity
    beam2: vec4<f32>,  // pool: centre xy, radii xy
    beam3: vec4<f32>,  // x dim, y time, z motes amount, w pool strength
    misc: vec4<f32>,   // x yaw cos, y yaw sin, z height the camera looks at, w unused
};

struct Patch {
    g: vec4<f32>,    // x kind, yzw params
    h: vec4<f32>,    // params
    m0: vec4<f32>,   // model matrix rows (affine)
    m1: vec4<f32>,
    m2: vec4<f32>,
    col: vec4<f32>,  // rgb base colour, w material
    hat: vec4<f32>,  // xyz hatch direction (patch space), w lines per unit
    ex: vec4<f32>,   // x lit (spot response / ghost), y detail, z emissive, w hatch strength
};

const MAXP: u32 = 96u;

struct U {
    g: G,
    p: array<Patch, 96>,
};

@group(0) @binding(0) var<uniform> u: U;

const PI: f32 = 3.14159265;
const GU: u32 = 40u;   // grid cells per patch, along u
const GV: u32 = 10u;   // ... along v

// ------------------------------------------------------------ helpers
fn hash2(p: vec2<f32>) -> f32 {
    var q = fract(p * vec2<f32>(0.1031, 0.1030));
    q = q + dot(q, q.yx + 33.33);
    return fract((q.x + q.y) * q.x);
}

fn vnoise(p: vec2<f32>) -> f32 {
    let i = floor(p);
    let f = fract(p);
    let w = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash2(i), hash2(i + vec2<f32>(1.0, 0.0)), w.x),
               mix(hash2(i + vec2<f32>(0.0, 1.0)), hash2(i + vec2<f32>(1.0, 1.0)), w.x), w.y);
}

// open-book page block: height of the top of the pages across one half,
// s = 0 at the gutter .. 1 at the fore-edge
fn pageTop(s: f32, T: f32, C: f32) -> f32 {
    let rise = smoothstep(0.0, 0.22, s);
    let crown = C * sin(PI * clamp(s * 0.95, 0.0, 1.0)) * (1.0 - 0.35 * s);
    return T * (0.30 + 0.70 * rise) + crown * rise;
}

// arch outline: t 0..1 from the left foot, up and over, to the right foot
fn archPt(t: f32, w: f32, h: f32) -> vec2<f32> {
    let r = w * 0.5;
    let leg = max(h - r, 0.0);
    let L = 2.0 * leg + PI * r;
    let d = t * L;
    if (d < leg) {
        return vec2<f32>(-r, d);
    }
    if (d < leg + PI * r) {
        let a = PI - (d - leg) / r;
        return vec2<f32>(r * cos(a), leg + r * sin(a));
    }
    return vec2<f32>(r, leg - (d - leg - PI * r));
}

// the surface of a patch, in patch space
fn surf(p: Patch, uu: f32, vv: f32) -> vec3<f32> {
    let k = u32(p.g.x + 0.5);
    let u0 = clamp(uu, 0.0, 1.0);
    let v0 = clamp(vv, 0.0, 1.0);
    switch k {
        case 0u: {       // quad in the XZ plane (normal +Y), centred: size g.y x g.z
            return vec3<f32>((u0 - 0.5) * p.g.y, 0.0, (v0 - 0.5) * p.g.z);
        }
        case 1u: {       // frustum about +Y: angle g.y..g.z, radius g.w..h.x, height h.y
            let a = mix(p.g.y, p.g.z, u0);
            let r = mix(p.g.w, p.h.x, v0);
            return vec3<f32>(r * cos(a), v0 * p.h.y, -r * sin(a));
        }
        case 2u: {       // sphere: longitude g.y..g.z, polar g.w..h.x, radius h.y
            let a = mix(p.g.y, p.g.z, u0);
            let ph = mix(p.g.w, p.h.x, v0);
            let r = p.h.y;
            return vec3<f32>(r * sin(ph) * cos(a), r * cos(ph), -r * sin(ph) * sin(a));
        }
        case 3u: {       // open-book page block (one half, +X): width g.y, depth g.z,
                         // thickness g.w, crown h.x, face h.y (0 top, 1 fore-edge, 2 tail, 3 head)
            let W = p.g.y;
            let D = p.g.z;
            let T = p.g.w;
            let C = p.h.x;
            let f = u32(p.h.y + 0.5);
            if (f == 0u) {
                return vec3<f32>(u0 * W, pageTop(u0, T, C), (v0 - 0.5) * D);
            }
            if (f == 1u) {
                return vec3<f32>(W, v0 * pageTop(1.0, T, C), (0.5 - u0) * D);
            }
            let z = select(-0.5 * D, 0.5 * D, f == 2u);
            return vec3<f32>(u0 * W, v0 * pageTop(u0, T, C), z);
        }
        case 4u: {       // arch: outer w g.y, h g.z, frame g.w, depth h.x, face h.y
                         // (0 front ring, 1 outer wall, 2 inner reveal, 3 recessed door)
            let w = p.g.y;
            let h = p.g.z;
            let fr = p.g.w;
            let dz = p.h.x;
            let f = u32(p.h.y + 0.5);
            let o = archPt(u0, w, h);
            let i = archPt(u0, w - 2.0 * fr, h - fr);
            if (f == 0u) {
                let q = mix(i, o, v0);
                return vec3<f32>(q.x, q.y, 0.5 * dz);
            }
            if (f == 1u) {
                return vec3<f32>(o.x, o.y, mix(0.5 * dz, -0.5 * dz, v0));
            }
            if (f == 2u) {
                return vec3<f32>(i.x, i.y, mix(0.5 * dz, -0.1 * dz, v0));
            }
            let q = i * v0;
            return vec3<f32>(q.x, q.y, -0.1 * dz);
        }
        case 5u: {       // curtain, hung from its outer edge (x = 0) toward +X:
                         // width g.y, height g.z, fold depth g.w, folds h.x,
                         // tie-back h.y (fraction of width kept at the tie), open h.z
            let W = p.g.y * p.h.z;
            let H = p.g.z;
            let tie = 0.62;
            let pinch = mix(1.0, p.h.y, smoothstep(0.0, tie, v0)) ;
            let flare = mix(pinch, p.h.y * 1.45, smoothstep(tie, 1.0, v0));
            let wv = select(pinch, flare, v0 > tie);
            let x = u0 * W * wv;
            let amp = p.g.w * (0.55 + 0.45 * u0) * (1.0 - 0.45 * smoothstep(0.2, tie, v0));
            let z = amp * sin(u0 * p.h.x * 2.0 * PI + 0.6);
            return vec3<f32>(x, -v0 * H, z);
        }
        case 6u: {       // closed volume's page-edge face (front): width g.y, height g.z
            return vec3<f32>((u0 - 0.5) * p.g.y, (v0 - 0.5) * p.g.z, 0.0);
        }
        default: {
            return vec3<f32>(0.0);
        }
    }
}

fn model(p: Patch, q: vec3<f32>) -> vec3<f32> {
    let v = vec4<f32>(q, 1.0);
    return vec3<f32>(dot(p.m0, v), dot(p.m1, v), dot(p.m2, v));
}

fn modelDir(p: Patch, q: vec3<f32>) -> vec3<f32> {
    let v = vec4<f32>(q, 0.0);
    return vec3<f32>(dot(p.m0, v), dot(p.m1, v), dot(p.m2, v));
}

// world -> view (yaw about Y, then pitch about X toward the camera)
fn toView(w: vec3<f32>) -> vec3<f32> {
    let cy = u.g.misc.x;
    let sy = u.g.misc.y;
    let x1 = cy * w.x + sy * w.z;
    let z1 = -sy * w.x + cy * w.z;
    let y1 = w.y - u.g.misc.z;
    let cp = u.g.cam.x;
    let sp = u.g.cam.y;
    return vec3<f32>(x1, cp * y1 - sp * z1, sp * y1 + cp * z1);
}

fn project(w: vec3<f32>) -> vec4<f32> {
    let v = toView(w);
    let D = u.g.cam.z;
    let f = D / max(D - v.z, 1.0);
    let q = vec2<f32>(v.x * f, -v.y * f - u.g.misc.z);   // drawable space (y down)
    let b = u.g.box;
    let ndc = vec2<f32>((q.x - b.x) / b.z * 2.0 - 1.0, 1.0 - (q.y - b.y) / b.w * 2.0);
    let R = u.g.cam.w;
    let depth = clamp(0.5 - v.z / (2.0 * R), 0.0, 1.0);
    let ww = 1.0 / f;
    return vec4<f32>(ndc * ww, depth * ww, ww);
}

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) wp: vec3<f32>,
    @location(1) n: vec3<f32>,
    @location(2) lp: vec3<f32>,
    @location(3) uv: vec2<f32>,
    @location(4) @interpolate(flat) idx: u32,
};

@vertex
fn vs_main(@builtin(vertex_index) vi: u32, @location(0) pid: f32) -> VOut {
    // the patch index arrives as a per-instance attribute (instance_index is
    // not available on every backend)
    let ii = u32(pid + 0.5);
    let p = u.p[min(ii, MAXP - 1u)];
    let cell = vi / 6u;
    let c = vi % 6u;
    var du = 0.0;
    var dv = 0.0;
    if (c == 1u || c == 4u || c == 5u) { du = 1.0; }
    if (c == 2u || c == 3u || c == 5u) { dv = 1.0; }
    let uu = (f32(cell % GU) + du) / f32(GU);
    let vv = (f32(cell / GU) + dv) / f32(GV);
    let lp = surf(p, uu, vv);
    let e = 1.0 / 512.0;
    let pu = modelDir(p, surf(p, uu + e, vv) - surf(p, uu - e, vv));
    let pv = modelDir(p, surf(p, uu, vv + e) - surf(p, uu, vv - e));
    var n = cross(pu, pv);
    if (dot(n, n) < 1e-12) {
        n = modelDir(p, vec3<f32>(0.0, 1.0, 0.0));
    }
    let wp = model(p, lp);
    var o: VOut;
    o.clip = project(wp);
    o.wp = wp;
    o.n = n;
    o.lp = lp;
    o.uv = vec2<f32>(uu, vv);
    o.idx = min(ii, MAXP - 1u);
    return o;
}

// engraved hatching: lines along `h`, width swelling with darkness
fn hatch(h: f32, fw: f32, dark: f32) -> f32 {
    let f = fw * 1.1;
    let d = abs(fract(h) - 0.5) * 2.0;
    let w = clamp(dark, 0.0, 0.92);
    let line = (1.0 - smoothstep(w - f, w + f, d)) * smoothstep(0.0, 0.1, w);
    // lines finer than a pixel fade to their mean tone instead of shimmering
    return mix(line, w, smoothstep(0.35, 0.8, f));
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    // derivatives first: everything below branches on the patch (non-uniform)
    let dlp = fwidth(i.lp);
    let duv = fwidth(i.uv);
    let p = u.p[i.idx];
    let mat = u32(p.col.w + 0.5);
    var base = p.col.rgb;
    var N = normalize(i.n);
    let V = normalize(u.g.eye.xyz - i.wp);
    if (dot(N, V) < 0.0) {
        N = -N;
    }
    // ---- shadow catcher: soft rounded-rect falloff, premultiplied ink
    if (mat == 5u) {
        let q = abs(i.uv - 0.5) * 2.0;
        let soft = p.ex.y;
        let d = length(max(q - vec2<f32>(1.0 - soft), vec2<f32>(0.0))) / max(soft, 0.001);
        let a = p.ex.x * (1.0 - smoothstep(0.0, 1.0, d)) * (1.0 - smoothstep(0.0, 1.0, d));
        return vec4<f32>(base * a, a);
    }
    var detail = 0.0;   // extra ink (type, page lines, seams)
    var shin = 12.0;
    var ks = 0.10;
    var etch = 1.0;
    let lit = p.ex.x;
    switch mat {
        case 1u: {   // page top: margins and greeked type in two blocks
            let s = i.uv.x;
            let z = i.lp.z;
            let D = p.g.z;
            let row = (z + 0.5 * D) / max(p.ex.y, 1.0);
            let r = floor(row);
            let ragged = 0.70 + 0.28 * hash2(vec2<f32>(r, p.h.z));
            let inS = step(0.16, s) * step(s, 0.16 + 0.70 * ragged);
            let inZ = step(0.12 * D, z + 0.5 * D) * step(z + 0.5 * D, 0.86 * D);
            let lineW = 0.30;
            let fz = dlp.z / max(p.ex.y, 1.0) * 1.2;
            let band = 1.0 - smoothstep(lineW - fz, lineW + fz, abs(fract(row) - 0.5) * 2.0);
            let typ = band * inS * inZ * (1.0 - smoothstep(0.35, 0.9, fz));
            detail = typ * 0.20 * p.ex.z;
            // the gutter swallows the light
            base = base * (1.0 - 0.30 * (1.0 - smoothstep(0.0, 0.2, s)));
            ks = 0.05;
            etch = 0.6;
        }
        case 2u: {   // page edges: leaves as fine lines across the face
            let rows = i.uv.y * p.ex.y;
            let f = duv.y * p.ex.y * 2.0;
            let d = abs(fract(rows) - 0.5) * 2.0;
            let line = (1.0 - smoothstep(0.55 - f, 0.55 + f, d)) * (1.0 - smoothstep(0.3, 0.9, f));
            detail = line * 0.18;
            base = base * (0.96 + 0.04 * vnoise(i.uv * vec2<f32>(3.0, 90.0)));
            ks = 0.03;
            etch = 0.6;
        }
        case 3u: {   // brass / gilt
            shin = 46.0;
            ks = 0.75;
            etch = 0.8;
        }
        case 4u: {   // emissive: a lamp bulb, the inside of the shade
            let glow = mix(base, vec3<f32>(1.0, 0.985, 0.93), clamp(p.ex.z, 0.0, 1.0));
            return vec4<f32>(glow, 1.0);
        }
        case 6u: {   // book cloth: a faint weave, worn corners
            let wv = vnoise(i.lp.xz * 1.6) * 0.5 + vnoise(i.lp.xz * vec2<f32>(9.0, 1.2)) * 0.5;
            base = base * (0.92 + 0.10 * wv);
            shin = 18.0;
            ks = 0.12;
        }
        case 7u: {   // night backdrop: deep gradient, small engraved stars
            let y = i.uv.y;
            base = mix(u.g.ink.rgb * 0.9, base, smoothstep(0.0, 1.0, y));
            let cell = floor(i.lp.xz / 26.0);
            let h = hash2(cell + vec2<f32>(3.1, 7.7));
            let c = (cell + 0.2 + 0.6 * vec2<f32>(hash2(cell + 1.3), hash2(cell + 9.1))) * 26.0;
            let dd = abs(i.lp.xz - c);
            let star = (1.0 - smoothstep(0.0, 1.2, min(dd.x * 5.0 + dd.y, dd.y * 5.0 + dd.x) / max(0.6 + 2.2 * h, 0.1)));
            let on = step(0.62, h);
            return vec4<f32>(mix(base, vec3<f32>(0.87, 0.74, 0.52), star * on * 0.85) * (0.85 + 0.15 * lit), 1.0);
        }
        case 8u: {   // stage boards: planks running upstage, faint grain
            let x = i.lp.x / 22.0;
            let f = dlp.x / 22.0;
            let seam = 1.0 - smoothstep(0.0, 0.06 + f, abs(fract(x) - 0.02));
            let grain = vnoise(vec2<f32>(x * 4.0, i.lp.z * 0.08)) * 0.5 + vnoise(i.lp.xz * vec2<f32>(0.9, 0.05)) * 0.5;
            base = base * (0.90 + 0.12 * grain);
            detail = seam * 0.35;
            ks = 0.06;
        }
        case 9u: {   // velvet: dark in the folds, a sheen on the crests
            shin = 6.0;
            ks = 0.18;
        }
        default: {}
    }
    // ---- light
    let L = normalize(u.g.key.xyz);
    let wrap = 0.35;
    let kd = max((dot(N, L) + wrap) / (1.0 + wrap), 0.0) * u.g.key.w;
    var light = u.g.amb.rgb + vec3<f32>(kd);
    var spec = pow(max(dot(N, normalize(L + V)), 0.0), shin) * ks * u.g.key.w;
    if (u.g.spot.w > 0.0) {
        let toS = u.g.spot.xyz - i.wp;
        let dS = length(toS);
        let Ls = toS / max(dS, 0.001);
        let cone = smoothstep(u.g.sdir.w, u.g.scol.w, dot(-Ls, normalize(u.g.sdir.xyz)));
        let rr = dS / max(u.g.ink.w, 1.0);
        let att = 1.0 / (1.0 + rr * rr);
        let sd = max(dot(N, Ls), 0.0) * cone * att * u.g.spot.w * lit;
        light = light + u.g.scol.rgb * sd;
        spec = spec + pow(max(dot(N, normalize(Ls + V)), 0.0), shin) * ks * cone * att * u.g.spot.w * lit;
    }
    if (mat == 9u) {
        let rim = pow(1.0 - max(dot(N, V), 0.0), 2.0);
        light = light + vec3<f32>(rim * 0.35 * kd);
    }
    var col = base * light + vec3<f32>(spec) * select(vec3<f32>(1.0), base * 1.6 + 0.2, mat == 3u);
    // ---- print: engraved hatching where the tone falls
    let tone = clamp(dot(light, vec3<f32>(0.30, 0.50, 0.20)), 0.0, 1.4);
    let ghost = 1.0 - smoothstep(0.25, 0.6, lit);   // unexplored arches: an engraved outline only
    let dark = clamp((0.86 - tone) * 1.25, 0.0, 1.0) * u.g.amb.w * etch + ghost * 0.25;
    var ink = 0.0;
    if (p.hat.w > 0.0) {
        let d1 = p.hat.xyz;
        let d2 = vec3<f32>(d1.y, d1.z, d1.x);
        let h1 = dot(i.lp, d1) * p.hat.w;
        let f1 = dot(dlp, abs(d1)) * p.hat.w;
        ink = hatch(h1, f1, dark * 0.85);
        let h2 = (dot(i.lp, d2) + dot(i.lp, d1) * 0.6) * p.hat.w * 0.9;
        let f2 = (dot(dlp, abs(d2)) + dot(dlp, abs(d1)) * 0.6) * p.hat.w * 0.9;
        ink = max(ink, hatch(h2, f2, (dark - 0.45) * 1.3) * 0.85);
    }
    ink = clamp(max(ink * 0.55 * p.ex.w, detail), 0.0, 1.0);
    col = mix(col, u.g.ink.rgb, ink);
    if (ghost > 0.0) {
        let paper = vec3<f32>(0.945, 0.910, 0.835);
        col = mix(col, mix(paper, u.g.ink.rgb, ink * 0.8 + 0.12), ghost * 0.78);
    }
    return vec4<f32>(clamp(col, vec3<f32>(0.0), vec3<f32>(1.0)), 1.0);
}

// ------------------------------------------------------------ the lamp's light
struct QOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) q: vec2<f32>,
};

@vertex
fn vs_quad(@builtin(vertex_index) vi: u32) -> QOut {
    var corners = array<vec2<f32>, 6>(
        vec2<f32>(0.0, 0.0), vec2<f32>(1.0, 0.0), vec2<f32>(0.0, 1.0),
        vec2<f32>(0.0, 1.0), vec2<f32>(1.0, 0.0), vec2<f32>(1.0, 1.0));
    let c = corners[vi];
    var o: QOut;
    o.clip = vec4<f32>(c.x * 2.0 - 1.0, 1.0 - c.y * 2.0, 0.0, 1.0);
    let b = u.g.box;
    o.q = b.xy + c * b.zw;
    return o;
}

fn moteField(q: vec2<f32>, t: f32, cellSize: f32, seed: f32) -> f32 {
    var s = 0.0;
    let base = floor(q / cellSize);
    for (var j = -1; j <= 1; j = j + 1) {
        for (var k = -1; k <= 1; k = k + 1) {
            let c = base + vec2<f32>(f32(j), f32(k));
            let h1 = hash2(c + seed);
            let h2 = hash2(c + seed + 17.3);
            let h3 = hash2(c + seed + 41.9);
            // each mote drifts on a slow lissajous inside its cell neighbourhood
            let ph = h3 * 6.2831;
            let off = vec2<f32>(h1 + 0.35 * sin(t * (0.21 + 0.17 * h2) + ph),
                                h2 + 0.30 * sin(t * (0.15 + 0.13 * h1) + ph * 1.7) - 0.25 * sin(t * 0.07 + h3 * 3.0));
            let pos = (c + off) * cellSize;
            let r = cellSize * (0.045 + 0.06 * h3);
            let d = length(q - pos);
            let tw = 0.55 + 0.45 * sin(t * (0.9 + h1) + ph * 2.0);
            s = s + (1.0 - smoothstep(r * 0.25, r, d)) * step(0.55, h2) * tw;
        }
    }
    return s;
}

@fragment
fn fs_beam(i: QOut) -> @location(0) vec4<f32> {
    let q = i.q;
    let apex = u.g.beam0.xy;
    let dir = normalize(u.g.beam0.zw);
    let rel = q - apex;
    let t = dot(rel, dir);
    let s = abs(rel.x * dir.y - rel.y * dir.x);
    let len = u.g.beam1.z;
    let halfW = u.g.beam1.x + u.g.beam1.y * max(t, 0.0);
    let across = 1.0 - smoothstep(halfW * 0.35, halfW * 1.05, s);
    let along = smoothstep(-2.0, 14.0, t) * (1.0 - smoothstep(len * 0.62, len * 1.02, t));
    let fall = 1.0 / (1.0 + t / max(len * 0.55, 1.0));
    let inBeam = across * along;
    let beam = inBeam * fall * u.g.beam1.w;
    // pool of light where the cone meets the stack and the desk
    let pr = (q - u.g.beam2.xy) / max(u.g.beam2.zw, vec2<f32>(1.0));
    let pool = (1.0 - smoothstep(0.15, 1.0, length(pr))) * u.g.beam3.w;
    // dust motes, only where the beam reaches
    let t0 = u.g.beam3.y;
    let motes = (moteField(q, t0, 13.0, 0.0) + moteField(q + vec2<f32>(5.0, 3.0), t0 * 0.8, 21.0, 7.0) * 0.8)
        * inBeam * smoothstep(0.05, 0.4, across) * u.g.beam3.z;
    // the room dims a little around the lamp, outside its light (a soft disc
    // round the beam, fading to nothing well inside the canvas edge)
    let b = u.g.box;
    let e = min(min(q.x - b.x, b.x + b.z - q.x), min(q.y - b.y, b.y + b.w - q.y));
    let edge = smoothstep(0.0, min(b.z, b.w) * 0.25, e);
    let mid = apex + dir * len * 0.55;
    let room = 1.0 - smoothstep(len * 0.35, len * 1.25, length(q - mid));
    let ad = u.g.beam3.x * edge * room * (1.0 - clamp(inBeam * 1.6 + pool * 1.5, 0.0, 1.0));
    let warm = vec3<f32>(1.0, 0.84, 0.50);
    let al = clamp(beam * 0.50 + pool * 0.45 + motes * 0.85, 0.0, 0.95);
    let dark = u.g.ink.rgb;
    let rgb = warm * al + dark * ad * (1.0 - al);
    let a = al + ad * (1.0 - al);
    return vec4<f32>(rgb, a);
}
