// Simmer cookbook (scene 3): a lit 3D book, printed like a risograph.
//
// World space is in points: x across the page, y down the table (toward the
// reader), z up off the table. The book's spine runs along y at x = 0. The
// camera looks down at the table, tilted toward the reader so the covers'
// and the page block's front edges show their thickness.
//
// Geometry (built once in scripts/book.luau):
//   static mesh   back cover board, page block, the front cover (a rigid
//                 board that swings open about the spine), the spine cloth
//                 (a strip that follows the cover), and the ribbon bookmark
//   leaves        one grid per leaf in one buffer (leaf index per vertex). Each leaf
//                 bends about the spine: every row is a circular arc whose
//                 base angle, curvature and corner lead come from the
//                 script, so a turning page curls, passes over the pile it
//                 leaves and lands flat on the other one
//   ground        a quad on the table that only prints shadow
//
// Depth testing decides what covers what, per pixel, every frame: a leaf
// lands above the leaves that turned before it because it lands higher, never
// because of a draw order.
//
// Shadows: a light-space depth map (vs_*_shadow, a depth-only pass), sampled
// with a comparison sampler and five taps. Shading is the collage's
// risograph: flat inks, light posterised to a soft step, shadow printed as an
// aubergine 45-degree halftone in stage points.
//
// No discard anywhere. Leaves are single surfaces shaded on both sides
// (never two coplanar faces); the ground never writes depth.

struct U {
    eye: vec4<f32>,     // camera position xyz, focal length (pt)
    camR: vec4<f32>,    // camera right xyz, screen x of the look-at point (region pt)
    camU: vec4<f32>,    // camera up xyz, screen y of the look-at point
    camF: vec4<f32>,    // camera forward xyz, near
    view: vec4<f32>,    // region w, h (pt), far, device px per point
    model: vec4<f32>,   // cos yaw, sin yaw, lift z, shift x (the book's entrance)
    lightD: vec4<f32>,  // toward the light xyz, ambient
    lightA: vec4<f32>,  // light basis a xyz, half extent of the map (pt)
    lightB: vec4<f32>,  // light basis b xyz, depth half range (pt)
    cover: vec4<f32>,   // cover angle psi (0 closed .. pi open), cover hinge z, ribbon length shown, ribbon sway
    misc: vec4<f32>,    // shadow strength, shadow map texel (uv), page width, page height
    atlas: vec4<f32>,   // face w, face h, cell pitch u, cell pitch v (uv)
    atlas2: vec4<f32>,  // face inset u, v (uv), columns, 0
    leafA: array<vec4<f32>, 5>,  // base angle, curvature (1/pt), corner lead (rad), hinge z
    leafB: array<vec4<f32>, 5>,  // front cell, back cell, 0, 0
};

@group(0) @binding(0) var<uniform> u: U;
@group(0) @binding(1) var atlasTex: texture_2d<f32>;
@group(0) @binding(2) var atlasSmp: sampler;
@group(1) @binding(0) var shadowTex: texture_depth_2d;
@group(1) @binding(1) var shadowSmp: sampler_comparison;

const PI: f32 = 3.14159265;
const COVER_T: f32 = 4.0;
const COVER_S0: f32 = 3.0;
const COVER_W: f32 = 152.0;
const COVER_H: f32 = 204.0;

// palette (the collage's inks)
const CREAM = vec3<f32>(0.992, 0.961, 0.882);
const PAPER = vec3<f32>(0.984, 0.941, 0.839);
const TOMATO = vec3<f32>(0.894, 0.286, 0.196);
const TOMATO_DK = vec3<f32>(0.722, 0.200, 0.122);
const BASIL = vec3<f32>(0.302, 0.463, 0.333);
const BASIL_DK = vec3<f32>(0.212, 0.353, 0.243);
const AUB = vec3<f32>(0.282, 0.161, 0.239);

// ------------------------------------------------------------------ space
fn toWorld(p: vec3<f32>) -> vec3<f32> {
    let c = u.model.x;
    let s = u.model.y;
    return vec3<f32>(c * p.x - s * p.y + u.model.w, s * p.x + c * p.y, p.z + u.model.z);
}

fn toWorldDir(n: vec3<f32>) -> vec3<f32> {
    let c = u.model.x;
    let s = u.model.y;
    return vec3<f32>(c * n.x - s * n.y, s * n.x + c * n.y, n.z);
}

// pinhole camera onto the region canvas, depth affine in screen space
fn project(w: vec3<f32>) -> vec4<f32> {
    let d = w - u.eye.xyz;
    let xc = dot(d, u.camR.xyz);
    let yc = dot(d, u.camU.xyz);
    let zc = max(dot(d, u.camF.xyz), 1.0);
    let f = u.eye.w / zc;
    let sx = u.camR.w + xc * f;
    let sy = u.camU.w - yc * f;
    let ndc = vec2<f32>(sx / u.view.x * 2.0 - 1.0, 1.0 - sy / u.view.y * 2.0);
    let near = u.camF.w;
    let far = u.view.z;
    let z = far * (zc - near) / (far - near);
    return vec4<f32>(ndc * zc, z, zc);
}

// orthographic light view: xy across the map, depth along the light
fn lightClip(w: vec3<f32>) -> vec4<f32> {
    let lx = dot(w, u.lightA.xyz) / u.lightA.w;
    let ly = dot(w, u.lightB.xyz) / u.lightA.w;
    let ld = 0.5 - dot(w, u.lightD.xyz) / (2.0 * u.lightB.w);
    return vec4<f32>(lx, ly, ld, 1.0);
}

// ------------------------------------------------------------------ the parts
struct Surf {
    pos: vec3<f32>,   // book-local
    nrm: vec3<f32>,   // book-local
};

// a point of leaf i at distance s from the spine, y along it (page coordinates)
fn leafPoint(i: u32, s: f32, y: f32) -> vec3<f32> {
    let a = u.leafA[i];
    let H = u.misc.w;
    let yn = clamp(y / H + 0.5, 0.0, 1.0);
    // the lower corner leads: rows nearer the reader bend further
    let k = a.y + a.z * yn / u.misc.z;
    let th = a.x;
    var x: f32;
    var z: f32;
    if (abs(k) < 1e-5) {
        x = s * cos(th);
        z = s * sin(th);
    } else {
        let ph = th + k * s;
        x = (sin(ph) - sin(th)) / k;
        z = (cos(th) - cos(ph)) / k;
    }
    return vec3<f32>(x, y, a.w + z);
}

fn leafSurf(i: u32, uv: vec2<f32>) -> Surf {
    let W = u.misc.z;
    let H = u.misc.w;
    let s = uv.x * W;
    let y = (uv.y - 0.5) * H;
    var o: Surf;
    o.pos = leafPoint(i, s, y);
    let e = 0.75;
    let ts = leafPoint(i, s + e, y) - leafPoint(i, max(s - e, 0.0), y);
    let ty = leafPoint(i, s, y + e) - leafPoint(i, s, y - e);
    o.nrm = normalize(cross(ts, ty));
    return o;
}

// the front cover: a rigid board in its own frame (s from the spine, y, t through the board)
fn coverSurf(p: vec3<f32>, n: vec3<f32>) -> Surf {
    let c = cos(u.cover.x);
    let s = sin(u.cover.x);
    var o: Surf;
    o.pos = vec3<f32>(p.x * c - p.z * s, p.y, u.cover.y + p.x * s + p.z * c);
    o.nrm = vec3<f32>(n.x * c - n.z * s, n.y, n.x * s + n.z * c);
    return o;
}

// the front cover's spine-side outer corner (where the spine cloth meets it)
fn coverHingeEdge() -> vec2<f32> {
    let c = cos(u.cover.x);
    let s = sin(u.cover.x);
    return vec2<f32>(COVER_S0 * c - COVER_T * s, u.cover.y + COVER_S0 * s + COVER_T * c);
}

// spine cloth: a quadratic arc in xz from the back board's edge to the front board's,
// bulging out past the spine; a in [0, 1] along it
fn spineXZ(a: f32) -> vec2<f32> {
    let A = vec2<f32>(COVER_S0, 0.35);
    let B = coverHingeEdge();
    let bulge = 0.42 * abs(B.y - A.y) + 1.5;
    let C = vec2<f32>(min(A.x, B.x) - bulge, 0.5 * (A.y + B.y));
    let q = 1.0 - a;
    let P = q * q * A + 2.0 * q * a * C + a * a * B;
    return vec2<f32>(P.x, max(P.y, 0.35));
}

fn spineSurf(a: f32, y: f32) -> Surf {
    let P = spineXZ(a);
    let d = spineXZ(min(a + 0.02, 1.0)) - spineXZ(max(a - 0.02, 0.0));
    var o: Surf;
    o.pos = vec3<f32>(P.x, y, P.y);
    // outward: the tangent turned away from the book
    o.nrm = normalize(vec3<f32>(-d.y, 0.0, d.x));
    return o;
}

// the ribbon's path in (y, z) as it leaves the page block, drapes over the
// block and the board, and lies along the table
fn ribbonYZ(d: f32) -> vec2<f32> {
    var pts = array<vec2<f32>, 7>(
        vec2<f32>(96.6, 14.45), vec2<f32>(97.4, 12.5), vec2<f32>(97.4, 5.2), vec2<f32>(98.6, 4.35),
        vec2<f32>(102.5, 4.35), vec2<f32>(102.9, 0.5), vec2<f32>(107.0, 0.3));
    var acc = 0.0;
    for (var k = 0; k < 6; k = k + 1) {
        let a = pts[k];
        let b = pts[k + 1];
        let l = length(b - a);
        if (d <= acc + l) {
            return mix(a, b, (d - acc) / l);
        }
        acc = acc + l;
    }
    return vec2<f32>(pts[6].x + (d - acc), 0.3);
}

const RIBBON_DRAPE: f32 = 21.9; // path length before the table (sum of the segments above, approx.)

struct VIn {
    @location(0) pos: vec3<f32>,
    @location(1) nrm: vec3<f32>,
    @location(2) uv: vec2<f32>,
    @location(3) tag: vec2<f32>,   // material, part
};

fn staticSurf(v: VIn) -> Surf {
    let part = u32(v.tag.y + 0.5);
    var o: Surf;
    o.pos = v.pos;
    o.nrm = v.nrm;
    if (part == 1u) {
        o = coverSurf(v.pos, v.nrm);
    } else if (part == 2u) {
        // ribbon: uv.x = distance along it, uv.y = side (-1..1), pos.x = notch depth
        // the centre column carries the notch, so the swallowtail survives any length
        let d = max(min(v.uv.x, u.cover.z - v.pos.x), 0.0);
        let p = ribbonYZ(d);
        let onTable = max(d - RIBBON_DRAPE, 0.0);
        let x = 40.0 + v.uv.y * 6.0 + u.cover.w * onTable;
        o.pos = vec3<f32>(x, p.x, p.y);
        let p2 = ribbonYZ(d + 0.5) - ribbonYZ(max(d - 0.5, 0.0));
        o.nrm = normalize(vec3<f32>(0.0, -p2.y, p2.x));
    } else if (part == 3u) {
        o = spineSurf(v.uv.x, v.pos.y);
    }
    return o;
}

// ------------------------------------------------------------------ vertex stages
struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) wpos: vec3<f32>,
    @location(1) wnrm: vec3<f32>,
    @location(2) uv: vec2<f32>,
    @location(3) @interpolate(flat) tag: vec2<f32>,
};

@vertex
fn vs_static(v: VIn) -> VOut {
    let s = staticSurf(v);
    var o: VOut;
    o.wpos = toWorld(s.pos);
    o.wnrm = toWorldDir(s.nrm);
    o.clip = project(o.wpos);
    o.uv = v.uv;
    o.tag = v.tag;
    return o;
}

@vertex
fn vs_static_shadow(v: VIn) -> @builtin(position) vec4<f32> {
    return lightClip(toWorld(staticSurf(v).pos));
}

@vertex
fn vs_leaf(@location(0) uv: vec2<f32>, @location(1) leaf: f32) -> VOut {
    let ii = u32(leaf + 0.5);
    let s = leafSurf(ii, uv);
    var o: VOut;
    o.wpos = toWorld(s.pos);
    o.wnrm = toWorldDir(s.nrm);
    o.clip = project(o.wpos);
    o.uv = uv;
    o.tag = vec2<f32>(f32(ii), 0.0);
    return o;
}

@vertex
fn vs_leaf_shadow(@location(0) uv: vec2<f32>, @location(1) leaf: f32) -> @builtin(position) vec4<f32> {
    return lightClip(toWorld(leafSurf(u32(leaf + 0.5), uv).pos));
}

// ------------------------------------------------------------------ shading
fn hash(p: vec2<f32>) -> f32 {
    var q = fract(p * vec2<f32>(0.1031, 0.1030));
    q = q + dot(q, q.yx + 33.33);
    return fract((q.x + q.y) * q.x);
}

// 1 = lit, 0 = in shadow; five comparison taps (each one bilinear-filtered)
fn visibility(w: vec3<f32>, n: vec3<f32>) -> f32 {
    let p = w + n * 0.9;
    let c = lightClip(p);
    let uv = vec2<f32>(c.x * 0.5 + 0.5, 0.5 - c.y * 0.5);
    let dref = c.z - 0.35 / (2.0 * u.lightB.w);
    let t = u.misc.y * 1.6;
    var v = textureSampleCompareLevel(shadowTex, shadowSmp, uv, dref) * 2.0;
    v = v + textureSampleCompareLevel(shadowTex, shadowSmp, uv + vec2<f32>(t, t), dref);
    v = v + textureSampleCompareLevel(shadowTex, shadowSmp, uv + vec2<f32>(-t, t), dref);
    v = v + textureSampleCompareLevel(shadowTex, shadowSmp, uv + vec2<f32>(t, -t), dref);
    v = v + textureSampleCompareLevel(shadowTex, shadowSmp, uv + vec2<f32>(-t, -t), dref);
    let inMap = step(abs(c.x), 0.999) * step(abs(c.y), 0.999);
    return mix(1.0, v / 6.0, inMap);
}

// a 45-degree dot screen in stage points (amount 0..1 -> dot coverage)
fn halftone(fragPx: vec2<f32>, amount: f32) -> f32 {
    let pt = fragPx / u.view.w;
    let r = vec2<f32>(pt.x + pt.y, pt.y - pt.x) * 0.70710678;
    let period = 3.4;
    let cell = fract(r / period) - 0.5;
    let dist = length(cell) * period;
    let rad = sqrt(clamp(amount, 0.0, 1.0)) * period * 0.64;
    let aa = 0.6 / max(u.view.w, 1.0) + 0.25;
    // no ink at all where there is no shade (the anti-aliasing band would print a faint screen)
    return (1.0 - smoothstep(rad - aa, rad + aa, dist)) * smoothstep(0.0, 0.06, amount);
}

// risograph light: the flat, unshadowed print keeps its exact colour; turning
// from the light and cast shadow darken it a little and print aubergine dots
fn riso(base: vec3<f32>, N: vec3<f32>, vis: f32, ao: f32, fragPx: vec2<f32>) -> vec3<f32> {
    let L = normalize(u.lightD.xyz);
    let amb = u.lightD.w;
    let flatLit = amb + (1.0 - amb) * max(L.z, 0.0);
    let lam = max(dot(N, L), 0.0);
    let lit = (amb + (1.0 - amb) * lam * mix(0.35, 1.0, vis)) * ao;
    let k = clamp(lit / flatLit, 0.5, 1.12);
    // posterise softly: two tones and a highlight, like two passes of ink
    let tone = mix(0.86, 1.0, smoothstep(0.80, 0.90, k)) * mix(0.9, 1.0, smoothstep(0.55, 0.65, k));
    var col = base * tone;
    col = mix(col, vec3<f32>(1.0, 0.99, 0.95), smoothstep(1.04, 1.1, k) * 0.35);
    let shade = clamp((0.97 - k) * 1.5, 0.0, 1.0);
    let dots = halftone(fragPx, shade * 0.65);
    col = mix(col, mix(col, AUB, 0.6), dots);
    return col;
}

fn atlasUV(cell: f32, uv: vec2<f32>) -> vec2<f32> {
    let cols = u.atlas2.z;
    let cx = cell - floor(cell / cols) * cols;
    let cy = floor(cell / cols);
    let q = clamp(uv, vec2<f32>(0.002), vec2<f32>(0.998));
    return vec2<f32>(cx * u.atlas.z + u.atlas2.x + q.x * u.atlas.x, cy * u.atlas.w + u.atlas2.y + q.y * u.atlas.y);
}

fn linen(p: vec2<f32>) -> f32 {
    let a = sin(p.x * 2.1) * sin(p.y * 2.3);
    return 0.5 + 0.5 * a + (hash(floor(p * 1.3)) - 0.5) * 0.6;
}

@fragment
fn fs_static(i: VOut) -> @location(0) vec4<f32> {
    let mat = u32(i.tag.x + 0.5);
    let V = normalize(u.eye.xyz - i.wpos);
    var N = normalize(i.wnrm);
    N = select(-N, N, dot(N, V) >= 0.0);
    // printed covers come from the atlas (cells 9 endpaper, 10 cover)
    let cell = select(9.0, 10.0, mat == 0u);
    let tex = textureSampleLevel(atlasTex, atlasSmp, atlasUV(cell, i.uv), 0.0).rgb;
    var base = TOMATO;
    var ao = 1.0;
    let lp = vec2<f32>(i.wpos.x, i.wpos.y);
    // page-edge lines (derivatives taken in uniform control flow)
    let z = i.uv.y;
    let zw = fwidth(z) * 0.8 + 0.02;
    let line = smoothstep(0.5 - zw, 0.5 + zw, abs(fract(z * 1.25) - 0.5) * 2.0);
    if (mat == 0u) {
        base = tex * (0.95 + 0.07 * linen(lp));
    } else if (mat == 1u) {
        base = tex;
        // the gutter: the endpaper dips into shade by the spine
        ao = 1.0 - 0.24 * exp(-(1.0 - i.uv.x) * COVER_W / 8.0);
    } else if (mat == 2u) {
        base = mix(TOMATO, TOMATO_DK, 0.35) * (0.93 + 0.1 * linen(lp * 1.2));
    } else if (mat == 3u) {
        // page edges: fine stacked lines of paper
        base = mix(CREAM, PAPER * 0.93, 0.55 * line);
    } else if (mat == 4u) {
        let weave = 0.5 + 0.5 * sin(i.uv.x * 3.2);
        base = mix(BASIL, BASIL_DK, 0.25 * weave);
    } else {
        base = TOMATO_DK;
        ao = 0.8;
    }
    let vis = visibility(i.wpos, N);
    return vec4<f32>(riso(base, N, vis, ao, i.clip.xy), 1.0);
}

@fragment
fn fs_leaf(i: VOut) -> @location(0) vec4<f32> {
    let li = u32(i.tag.x + 0.5);
    let V = normalize(u.eye.xyz - i.wpos);
    let n = normalize(i.wnrm);
    let front = dot(n, V) >= 0.0;
    let N = select(-n, n, front);
    // the back face is read with the spine on its right
    let fuv = select(vec2<f32>(1.0 - i.uv.x, i.uv.y), i.uv, front);
    let cell = select(u.leafB[li].y, u.leafB[li].x, front);
    var col = textureSampleLevel(atlasTex, atlasSmp, atlasUV(cell, fuv), 0.0).rgb;
    let W = u.misc.z;
    let H = u.misc.w;
    // a hairline aubergine edge, as every cutout has, and the gutter's shade
    let ex = min(i.uv.x, 1.0 - i.uv.x) * W;
    let ey = min(i.uv.y, 1.0 - i.uv.y) * H;
    let e = min(ex, ey);
    let px = 1.0 / max(u.view.w, 1.0);
    col = mix(col, AUB, (1.0 - smoothstep(0.35, 0.35 + 0.9 * px + 0.4, e)) * 0.55);
    let gutter = 1.0 - 0.26 * exp(-i.uv.x * W / 9.0);
    let vis = visibility(i.wpos, N);
    return vec4<f32>(riso(col, N, vis, gutter, i.clip.xy), 1.0);
}

// ------------------------------------------------------------------ the table: shadow only
struct GOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) wpos: vec3<f32>,
};

@vertex
fn vs_ground(@builtin(vertex_index) vi: u32) -> GOut {
    var corners = array<vec2<f32>, 6>(
        vec2<f32>(0.0, 0.0), vec2<f32>(1.0, 0.0), vec2<f32>(0.0, 1.0),
        vec2<f32>(0.0, 1.0), vec2<f32>(1.0, 0.0), vec2<f32>(1.0, 1.0));
    let c = corners[vi];
    // the table under the whole region, generously
    let w = vec3<f32>(mix(-320.0, 320.0, c.x), mix(-300.0, 340.0, c.y), 0.0);
    var o: GOut;
    o.wpos = w;
    o.clip = project(w);
    return o;
}

@fragment
fn fs_ground(i: GOut) -> @location(0) vec4<f32> {
    let vis = visibility(i.wpos, vec3<f32>(0.0, 0.0, 1.0));
    let sh = (1.0 - vis) * u.misc.x;
    // flat ink plus a dot screen that thickens toward the contact
    let dots = halftone(i.clip.xy, sh * 0.9);
    let a = clamp(sh * 0.22 + dots * sh * 0.55, 0.0, 1.0);
    return vec4<f32>(AUB * a, a);
}
