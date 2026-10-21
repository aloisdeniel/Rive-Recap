// Sprig folded-paper leaf, lit on the GPU.
//
// One (u, v) grid (u: base -> tip along the midrib, v: -1 -> 1 across the blade) is
// shaped entirely in the vertex shader from the uniforms below: a leaf (pointed) or a
// seed half-shell (round, deeply cupped) outline, folded along the midrib, cupped,
// curled toward the viewer, twisted and rippled at the edge. Up to two mirrored
// copies (the grid is stored twice, with the mirror sign as its third component) (a pair of leaves / the two halves of a seed) share one pass and one depth
// buffer. The fragment shader is the material: two paper stocks (outer / inner face),
// pressed veins, paper fibre, a cut-paper rim, a crease shadow and light coming
// *through* the blade when it is lit from behind (the veins then read dark).

struct U {
    a: vec4<f32>, // L, W, fold, cup
    b: vec4<f32>, // curl, twist, flip, pitch
    c: vec4<f32>, // spin, yaw, spread, gap
    d: vec4<f32>, // shape (0 leaf .. 1 shell), wave, persp, pair
    e: vec4<f32>, // halfW, top, bottom, seed
    f: vec4<f32>, // front rgb, glow
    g: vec4<f32>, // back rgb, veins
    h: vec4<f32>, // glow rgb, fibre
    k: vec4<f32>, // rim rgb, tipCurl
    m: vec4<f32>, // light angle, ambient, cy (pivot shift along the blade), unused
};

@group(0) @binding(0) var<uniform> u: U;

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) uv: vec2<f32>,
    @location(1) n: vec3<f32>,
    @location(2) z: f32,
    @location(3) side: f32,
};

const PI: f32 = 3.14159265;

fn halfWidth(t: f32) -> f32 {
    let W = u.a.y;
    // pointed leaf: broadest at ~38%, fine tip, narrow petiole
    let lf = pow(max(sin(PI * pow(clamp(t, 0.0, 1.0), 0.72)), 0.0), 0.95);
    // seed half-shell: an almond (ellipse, slightly pointed at the top)
    let s = clamp(t, 0.0, 1.0);
    let sh = sqrt(max(1.0 - pow(2.0 * s - 1.0, 2.0), 0.0)) * (1.0 - 0.18 * s);
    return W * mix(lf, sh, u.d.x);
}

fn rotX(p: vec3<f32>, a: f32) -> vec3<f32> {
    let c = cos(a); let s = sin(a);
    return vec3<f32>(p.x, p.y * c - p.z * s, p.y * s + p.z * c);
}
fn rotY(p: vec3<f32>, a: f32) -> vec3<f32> {
    let c = cos(a); let s = sin(a);
    return vec3<f32>(p.x * c + p.z * s, p.y, -p.x * s + p.z * c);
}
fn rotZ(p: vec3<f32>, a: f32) -> vec3<f32> {
    let c = cos(a); let s = sin(a);
    return vec3<f32>(p.x * c - p.y * s, p.x * s + p.y * c, p.z);
}

// Leaf-space position (y down the screen, +z toward the viewer), before mirroring.
fn shapeAt(t: f32, v: f32) -> vec3<f32> {
    let L = u.a.x;
    let W = u.a.y;
    let w = halfWidth(t);
    let d = v * w;
    let ad = abs(d);
    // fold: each half hinges on the midrib; cup: parabolic cross-section; edge ripple
    let fold = u.a.z;
    let cupZ = u.a.w * w * v * v;
    let ripple = u.d.y * W * 0.07 * sin(t * 15.0 + u.e.w * 3.7 + sign(v) * 1.3) * v * v;
    var X = d * cos(fold);
    var Z = ad * sin(fold) + cupZ + ripple;
    // twist the cross-section about the midrib, growing toward the tip
    let tw = u.b.y * t;
    let X2 = X * cos(tw) - Z * sin(tw);
    let Z2 = X * sin(tw) + Z * cos(tw);
    // midrib curls toward the viewer (uniform bend + an extra roll near the tip)
    let th = u.b.x * t + u.k.w * t * t * t;
    // integrate the bent midrib from the base to t (midpoint rule, smooth in t)
    let h = t / 16.0;
    var m = vec3<f32>(0.0, 0.0, 0.0);
    for (var i = 0; i < 16; i = i + 1) {
        let s0 = (f32(i) + 0.5) * h;
        let a = u.b.x * s0 + u.k.w * s0 * s0 * s0;
        m = m + vec3<f32>(0.0, -cos(a), sin(a)) * (L * h);
    }
    let N = vec3<f32>(0.0, sin(th), cos(th));
    return m + vec3<f32>(X2, 0.0, 0.0) + N * Z2;
}

fn place(p0: vec3<f32>, mir: f32) -> vec3<f32> {
    // per-leaf: roll about the own midrib, then splay in the picture plane, then offset
    // (the twin is the same leaf reflected in x, so nothing else needs the sign)
    var p = rotY(p0, u.b.z);
    p = rotZ(p, u.c.z);
    p.x = (p.x + u.c.w) * mir;
    // the twin sits a hair behind, so overlapping flat blades never z-fight
    p.z = p.z - (1.0 - mir) * 0.6;
    // pivot: the assembly turns about a point cy along the blade (cy = L/2 spins about the middle)
    p.y = p.y + u.m.z;
    // the whole assembly: yaw, pitch, in-plane spin (kept here so the light stays put)
    p = rotY(p, u.c.y);
    p = rotX(p, u.b.w);
    p = rotZ(p, u.c.x);
    return p;
}

fn project(p: vec3<f32>) -> vec4<f32> {
    let D = u.d.z;
    let f = D / max(D - p.z, D * 0.2);
    let sx = p.x * f;
    let sy = p.y * f;
    let halfW = u.e.x;
    let top = u.e.y;
    let bottom = u.e.z;
    let x = sx / halfW;
    let y = 1.0 - 2.0 * (sy - top) / (bottom - top);
    let zr = u.a.x * 2.5;
    let z = clamp(0.5 - p.z / zr, 0.0, 1.0);
    return vec4<f32>(x, y, z, 1.0);
}

@vertex
fn vs_main(@location(0) g: vec3<f32>) -> VOut {
    var o: VOut;
    let t = g.x;
    let v = g.y;
    let mir = g.z;
    let e = 0.01;
    let p = place(shapeAt(t, v), mir);
    let pu = place(shapeAt(min(t + e, 1.0), v), mir) - place(shapeAt(max(t - e, 0.0), v), mir);
    let pv = place(shapeAt(t, min(v + e, 1.0)), mir) - place(shapeAt(t, max(v - e, -1.0)), mir);
    var n = cross(pu, pv);
    let ln = length(n);
    n = select(vec3<f32>(0.0, 0.0, 1.0), n / max(ln, 1e-6), ln > 1e-7) * mir;
    o.clip = project(p);
    o.uv = vec2<f32>(t, v);
    o.n = n;
    o.z = p.z;
    o.side = mir;
    return o;
}

fn hash2(p: vec2<f32>) -> f32 {
    var q = fract(p * vec2<f32>(123.34, 456.21));
    q = q + dot(q, q + 45.32);
    return fract(q.x * q.y);
}

fn vnoise(p: vec2<f32>) -> f32 {
    let i = floor(p);
    let f = fract(p);
    let w = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash2(i), hash2(i + vec2<f32>(1.0, 0.0)), w.x),
               mix(hash2(i + vec2<f32>(0.0, 1.0)), hash2(i + vec2<f32>(1.0, 1.0)), w.x), w.y);
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let t = i.uv.x;
    let v = i.uv.y;
    let av = abs(v);
    let L = u.a.x;
    let W = u.a.y;
    var n = normalize(i.n);
    // which face of the paper is toward us (perspective-safe enough for paper)
    let facing = n.z >= 0.0;
    if (!facing) { n = -n; }
    let la = u.m.x;
    let ld = normalize(vec3<f32>(-0.55 * cos(la) + 0.2 * sin(la), -0.75, 0.62));
    let ndl = dot(n, ld);
    // the light reaches this face directly, or only through the paper
    let lit = max(ndl, 0.0);
    let through = max(-ndl, 0.0);

    // veins: midrib + lateral veins sweeping toward the tip (leaf only)
    let leafness = 1.0 - u.d.x;
    let mid = 1.0 - smoothstep(0.012, 0.035, av);
    let s = t * 9.0 - av * 2.6 + 0.35;
    let lat = (1.0 - smoothstep(0.0, 0.07, abs(fract(s) - 0.5) * 2.0 - 0.86)) * smoothstep(0.05, 0.2, av)
              * (1.0 - smoothstep(0.82, 0.98, av)) * smoothstep(0.04, 0.16, t) * (1.0 - smoothstep(0.86, 0.98, t));
    let vein = clamp(mid + lat * 0.7, 0.0, 1.0) * u.g.w * leafness;

    // paper fibre: long soft fibres along the blade + fine tooth
    let fp = vec2<f32>(t * L * 0.06 + v * 1.7, v * W * 0.45 + t * 3.0);
    let fib = vnoise(fp * vec2<f32>(0.6, 3.2)) - 0.5;
    let tooth = hash2(floor(vec2<f32>(t * L, v * W) * 1.1) + u.e.w) - 0.5;
    let mott = vnoise(vec2<f32>(t, v) * vec2<f32>(5.0, 3.0) + u.e.w) - 0.5;
    let paper = 1.0 + (fib * 0.08 + tooth * 0.05 + mott * 0.035) * u.h.w;

    var base: vec3<f32>;
    if (facing) { base = u.f.xyz; } else { base = u.g.xyz; }
    // a soft two-tone across the fold, like the folded-paper halves
    base = base * (1.0 - 0.06 * smoothstep(-0.2, 1.0, v * i.side));

    // crease and cup occlusion; the shell interior is darker toward its floor
    let crease = 1.0 - 0.28 * (1.0 - smoothstep(0.0, 0.35, av)) * clamp(u.a.z * 1.2 + u.a.w * 0.6, 0.0, 1.0);
    let amb = u.m.y;
    var col = base * (amb + (1.0 - amb) * (0.28 + 0.72 * lit)) * crease;
    // pressed veins: a raised highlight on the lit face
    col = mix(col, col * 1.18 + vec3<f32>(0.03), vein * 0.55 * select(0.6, 1.0, facing));
    // light through the paper: the blade glows, veins and fibres read darker
    let tr = through * u.f.w;
    let glowCol = u.h.xyz * (0.75 + 0.5 * (fib + 0.5)) * (1.0 - vein * 0.55);
    col = mix(col, glowCol, clamp(tr * 1.1, 0.0, 0.85));
    // cut-paper rim catching the light
    let rim = smoothstep(0.9, 0.995, av) * (0.35 + 0.65 * lit);
    col = mix(col, u.k.xyz, rim * 0.55);
    // a faint sheen along the crease ridge
    col = col + vec3<f32>(0.05) * pow(lit, 6.0) * (1.0 - smoothstep(0.0, 0.25, av));
    col = col * paper;
    return vec4<f32>(clamp(col, vec3<f32>(0.0), vec3<f32>(1.0)), 1.0);
}
