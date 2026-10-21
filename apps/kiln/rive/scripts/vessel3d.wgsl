// Kiln 3D vessel: a thrown pot lathed on the GPU.
//
// The mesh is only a (u, s) grid. The vertex shader turns it into a real
// surface of revolution from a six-row profile held in uniforms (radius and
// axis lean per row, plus height), so the state machine can morph between
// any two forms just by keying numbers: lump -> vessel -> slab -> plinth.
//
//   s in [0, 1]     outer wall, base to lip
//   s in [1, 1.1]   rounded lip (or a flat lid when `cap` = 1, for slabs)
//   s in [1.1, 2.1] inner wall, lip down to the floor
//   s in [2.1, 2.2] inner floor, to the axis
//
// The fragment shader is the material: speckled stoneware with throwing
// rings, and a cobalt glaze (dipped rim, flowing band with drip fingers,
// glazed interior) that breaks lighter over edges, pools darker at the drips
// and carries a studio softbox reflection. `heat` makes the whole piece glow
// like it is still in the kiln.

struct U {
    rA: vec4<f32>,    // radius rows 0..3
    rB: vec4<f32>,    // radius rows 4..5, height, cap (0 open .. 1 lidded)
    cA: vec4<f32>,    // axis lean rows 0..3
    cB: vec4<f32>,    // axis lean rows 4..5, spin angle, camera tilt
    body: vec4<f32>,  // clay rgb, speckle amount
    glaze: vec4<f32>, // glaze rgb, gloss
    gl: vec4<f32>,    // dip depth, band flow, band half-width (rad), drip
    misc: vec4<f32>,  // interior glaze, throwing rings, heat, wall thickness
    frame: vec4<f32>, // canvas half width, canvas top (local y), canvas bottom, opacity
    extra: vec4<f32>, // band centre (rad), band sway, sphere (0..1, blends the profile into a true sphere), seed
    more: vec4<f32>,  // roll of the hosting node (rad), clay sheen, coil ridges, thumbprints
};

@group(0) @binding(0) var<uniform> u: U;

const PI: f32 = 3.14159265;
const TAU: f32 = 6.2831853;

struct VIn {
    @location(0) uv: vec2<f32>,
};

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) n: vec3<f32>,   // view space normal
    @location(1) lp: vec3<f32>,  // object space position (unspun), for speckle
    @location(2) tv: vec3<f32>,  // theta (unspun), height fraction, segment
};

fn rowsR() -> array<f32, 6> {
    return array<f32, 6>(u.rA.x, u.rA.y, u.rA.z, u.rA.w, u.rB.x, u.rB.y);
}

fn rowsC() -> array<f32, 6> {
    return array<f32, 6>(u.cA.x, u.cA.y, u.cA.z, u.cA.w, u.cB.x, u.cB.y);
}

// Cubic Hermite through the six rows at the profile's fixed heights.
fn interp(vIn: f32, a: array<f32, 6>) -> f32 {
    var T = array<f32, 6>(0.0, 0.2, 0.44, 0.68, 0.88, 1.0);
    var A = a;
    let v = clamp(vIn, 0.0, 1.0);
    var i = 0;
    for (var k = 0; k < 5; k++) {
        if (v >= T[k]) {
            i = k;
        }
    }
    let t0 = T[i];
    let t1 = T[i + 1];
    let dt = t1 - t0;
    let t = (v - t0) / dt;
    let im = max(i - 1, 0);
    let ip = min(i + 2, 5);
    let m0 = (A[i + 1] - A[im]) / (T[i + 1] - T[im]) * dt * 0.85;
    let m1 = (A[ip] - A[i]) / (T[ip] - T[i]) * dt * 0.85;
    let t2 = t * t;
    let t3 = t2 * t;
    return (2.0 * t3 - 3.0 * t2 + 1.0) * A[i] + (t3 - 2.0 * t2 + t) * m0
        + (-2.0 * t3 + 3.0 * t2) * A[i + 1] + (t3 - t2) * m1;
}

// profile sample: x = radius, y = height, z = height fraction, w = segment
fn coil(y: f32) -> f32 {
    // hand-built coils: soft ridges every 26 units, so a growing pot gains them one by one
    return u.more.z * (abs(sin(y * PI / 26.0)) - 0.62) * 7.0;
}

fn profile(sIn: f32) -> vec4<f32> {
    let R = rowsR();
    let h = max(u.rB.z, 1.0);
    let cap = clamp(u.rB.w, 0.0, 1.0);
    let wall = u.misc.w;
    let s = clamp(sIn, 0.0, 2.2);
    let vf = clamp(wall * 1.6 / h, 0.03, 0.45);
    if (s <= 1.0) {
        let sph = 0.5 * h * sqrt(max(0.0, 1.0 - (2.0 * s - 1.0) * (2.0 * s - 1.0)));
        return vec4<f32>(max(mix(interp(s, R), sph, u.extra.z) + coil(h * s), 0.0), h * s, s, 0.0);
    }
    if (s <= 1.1) {
        let k = (s - 1.0) / 0.1;
        let rTop = max(mix(interp(1.0, R), 0.0, u.extra.z), 0.0);
        let rIn = mix(max(rTop - wall, 0.0), 0.0, cap);
        let lift = wall * 0.5 * sin(PI * k) * (1.0 - cap) + cap * min(h * 0.06, 4.0) * sin(PI * 0.5 * k);
        return vec4<f32>(mix(rTop, rIn, k), h + lift, 1.0, 1.0);
    }
    if (s <= 2.1) {
        let k = s - 1.1;
        let v = 1.0 - k * (1.0 - vf);
        return vec4<f32>(max(interp(v, R) + coil(h * v) - wall, 0.0) * (1.0 - cap), h * v, v, 2.0);
    }
    let k = (s - 2.1) / 0.1;
    let rb = max(interp(vf, R) - wall, 0.0) * (1.0 - cap);
    return vec4<f32>(mix(rb, 0.0, k), h * vf, vf, 3.0);
}

fn surface(s: f32, th: f32) -> vec3<f32> {
    let p = profile(s);
    let c = interp(p.z, rowsC());
    return vec3<f32>(c + p.x * cos(th), p.y, p.x * sin(th));
}

// object space -> view space (spin about the axis, then the camera tilt)
fn toView(p: vec3<f32>) -> vec3<f32> {
    let a = u.cB.z;
    let e = u.cB.w;
    let x = p.x * cos(a) + p.z * sin(a);
    let z = p.z * cos(a) - p.x * sin(a);
    let y = p.y * cos(e) - z * sin(e);
    let zz = z * cos(e) + p.y * sin(e);
    return vec3<f32>(x, y, zz);
}

@vertex
fn vs_main(v: VIn) -> VOut {
    var o: VOut;
    let th = v.uv.x * TAU;
    let s = v.uv.y;
    let p = surface(s, th);
    let e = 0.004;
    let pa = surface(max(s - e, 0.0), th);
    let pb = surface(min(s + e, 2.2), th);
    var ts = pb - pa;
    if (dot(ts, ts) < 1e-8) {
        ts = vec3<f32>(0.0, 1.0, 0.0);
    }
    let tt = vec3<f32>(-sin(th), 0.0, cos(th));
    var n = normalize(cross(ts, tt));
    let vp = toView(p);
    let vn = toView(n);
    let hw = u.frame.x;
    let top = u.frame.y;
    let bot = u.frame.z;
    let yd = -vp.y;
    o.clip = vec4<f32>(vp.x / hw, 1.0 - 2.0 * (yd - top) / (bot - top), 0.5 - vp.z / 1200.0, 1.0);
    o.n = vn;
    o.lp = p;
    let prof = profile(s);
    o.tv = vec3<f32>(th, prof.z, prof.w);
    return o;
}

fn hash2(p: vec2<f32>) -> f32 {
    var q = fract(p * vec2<f32>(123.34, 456.21));
    q = q + dot(q, q + 45.32);
    return fract(q.x * q.y);
}

fn hash3(p: vec3<f32>) -> f32 {
    var q = fract(p * 0.1031);
    q = q + dot(q, q.zyx + 31.32);
    return fract((q.x + q.y) * q.z);
}

// smooth value noise, for mineral mottling that never shows a grid
fn vnoise(p: vec3<f32>) -> f32 {
    let i = floor(p);
    let f = fract(p);
    let w = f * f * (3.0 - 2.0 * f);
    let a = mix(hash3(i), hash3(i + vec3<f32>(1.0, 0.0, 0.0)), w.x);
    let b = mix(hash3(i + vec3<f32>(0.0, 1.0, 0.0)), hash3(i + vec3<f32>(1.0, 1.0, 0.0)), w.x);
    let c = mix(hash3(i + vec3<f32>(0.0, 0.0, 1.0)), hash3(i + vec3<f32>(1.0, 0.0, 1.0)), w.x);
    let d = mix(hash3(i + vec3<f32>(0.0, 1.0, 1.0)), hash3(i + vec3<f32>(1.0, 1.0, 1.0)), w.x);
    return mix(mix(a, b, w.y), mix(c, d, w.y), w.z);
}

fn wrapPi(a: f32) -> f32 {
    return a - TAU * floor((a + PI) / TAU);
}

// sharp drip fingers around the circumference (0..1)
fn fingers(th: f32, seed: f32) -> f32 {
    let a = pow(0.5 + 0.5 * sin(th * 7.0 + seed), 10.0);
    let b = pow(0.5 + 0.5 * sin(th * 11.0 + seed * 2.3 + 1.7), 14.0);
    let c = pow(0.5 + 0.5 * sin(th * 4.0 - seed * 0.7 + 0.4), 6.0);
    return clamp(a * 0.9 + b * 0.7 + c * 0.5, 0.0, 1.0);
}

// incandescence: dull red -> cherry -> orange -> yellow-white, as a kiln sees it
fn blackbody(t: f32) -> vec3<f32> {
    let k = clamp(t, 0.0, 1.0);
    let c0 = vec3<f32>(0.30, 0.03, 0.01);
    let c1 = vec3<f32>(0.85, 0.18, 0.04);
    let c2 = vec3<f32>(1.00, 0.48, 0.12);
    let c3 = vec3<f32>(1.00, 0.80, 0.52);
    var c = mix(c0, c1, smoothstep(0.0, 0.35, k));
    c = mix(c, c2, smoothstep(0.3, 0.7, k));
    c = mix(c, c3, smoothstep(0.7, 1.0, k));
    return c;
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let seg = i.tv.z;
    let th = i.tv.x;
    let v = i.tv.y;
    let outer = seg < 0.5;
    let inner = seg > 1.5;
    var n = normalize(i.n);
    // screen-space derivatives, taken in uniform control flow for edge anti-aliasing
    let dv = fwidth(v);
    let dth = min(fwidth(th), 0.2);

    // throwing rings: a gentle horizontal ripple in the normal (outer and inner walls)
    var ringN = vec3<f32>(0.0);
    if (seg < 0.5 || (seg > 1.5 && seg < 2.5)) {
        let y = i.lp.y;
        let ring = sin(y * 0.42 + 1.6 * sin(y * 0.045 + th * 0.35 + u.extra.w))
            * (0.55 + 0.45 * sin(y * 0.11 + 2.0));
        ringN = vec3<f32>(0.0, ring * 0.05 * u.misc.y, 0.0);
    }

    // --- glaze coverage (in unspun object space, so it turns with the pot)
    let seed = u.extra.w;
    let dip = u.gl.x;
    let flow = u.gl.y;
    let bw = u.gl.z;
    let drip = u.gl.w;
    var g = 0.0;
    var edge = 0.0;   // 1 where the glaze is thin (breaking over the edge)
    var pool = 0.0;   // 1 where it pools at a drip tip
    if (!inner) {
        if (dip > 0.001) {
            let f = fingers(th, seed);
            let wob = 0.025 * sin(th * 3.0 + seed);
            let lim = 1.0 - dip - drip * dip * f * 0.55 + wob;
            let av = max(dv * 1.2, 0.002);
            let gd = smoothstep(lim - av, lim + av, v);
            g = max(g, gd);
            edge = max(edge, (1.0 - smoothstep(lim, lim + 0.06, v)) * gd);
            pool = max(pool, (1.0 - smoothstep(lim, lim + 0.03, v)) * gd * f);
        }
        if (flow > 0.001 && bw > 0.001) {
            let tc = u.extra.x + u.extra.y * sin(v * 4.2 + 0.6) + 0.12 * sin(v * 9.0 + seed);
            let w = bw * (0.78 + 0.22 * sin(v * 6.3 + 1.3 + seed));
            let d = abs(wrapPi(th - tc));
            let aa = max((dth + dv * abs(u.extra.y) * 4.0) * 1.2, 0.01);
            let inBand = 1.0 - smoothstep(w - aa, w + aa, d);
            let tip = 1.0 - flow * (1.02 + 0.1 * fingers(th * 1.7, seed + 2.0));
            let at = max(dv * 1.2, 0.002);
            let gb = inBand * smoothstep(tip - at, tip + at, v);
            g = max(g, gb);
            edge = max(edge, smoothstep(w * 0.55, w, d) * gb * 0.8);
            pool = max(pool, (1.0 - smoothstep(tip, tip + 0.05, v)) * gb);
        }
        if (seg > 0.5) {
            g = max(g, clamp((dip + flow * 0.6) * 4.0, 0.0, 1.0) * max(u.misc.x, step(0.001, dip)));
        }
    } else {
        g = u.misc.x;
    }

    // --- clay body with iron speckle and grog
    let sp = i.lp * 0.16;
    let cell = floor(sp);
    let fr = fract(sp) - 0.5;
    let hh = hash3(cell + seed);
    let jit = (vec3<f32>(hash3(cell + 7.0), hash3(cell + 13.0), hash3(cell + 3.0)) - 0.5) * 0.6;
    let spot = 1.0 - smoothstep(0.07, 0.15, length(fr - jit));
    var clay = u.body.rgb;
    let grain = hash3(floor(i.lp * 1.3)) - 0.5;
    let mott = (vnoise(i.lp * 0.045 + seed) - 0.5) * 1.6 + (vnoise(i.lp * 0.16) - 0.5) * 0.6;
    clay = clay * (1.0 + grain * 0.05 + mott * 0.035);
    let iron = step(1.0 - 0.34 * u.body.w, hh) * spot;
    clay = mix(clay, clay * vec3<f32>(0.42, 0.36, 0.33), iron * 0.85);
    let grog = step(0.93, hash3(cell + 41.0)) * spot * u.body.w;
    clay = mix(clay, clay * 1.12 + 0.05, grog * 0.6);

    n = normalize(n + ringN * (1.0 - 0.75 * g));

    // thumbprints pressed into hand-built walls: a shallow dent with fine whorl ridges
    var printShade = 0.0;
    if (u.more.w > 0.001 && outer) {
        let rr = length(i.lp.xz);
        for (var k = 0; k < 5; k++) {
            let fk = f32(k);
            let pth = 1.15 + fk * 0.62 + 0.25 * sin(fk * 2.3);
            let pv = 0.18 + fk * 0.15 + 0.06 * sin(fk * 4.1);
            let dx = wrapPi(th - pth) * max(rr, 10.0);
            let dy = (v - pv) * max(u.rB.z, 1.0);
            let q = vec2<f32>(dx / 1.15, dy);
            let d = length(q);
            let dent = 1.0 - smoothstep(4.0, 9.5, d);
            if (dent > 0.0) {
                let gdir = q / max(d, 0.001);
                let tang = vec3<f32>(-sin(th), 0.0, cos(th));
                let push = tang * gdir.x + vec3<f32>(0.0, 1.0, 0.0) * gdir.y;
                n = normalize(n + toView(push) * dent * 0.35 * u.more.w);
                printShade = max(printShade, dent * (0.5 + 0.5 * sin(d * 2.6)) * u.more.w);
            }
        }
    }

    // --- lighting (view space: x right, y up, z toward the viewer)
    let ro = u.more.x;
    let l0 = vec2<f32>(-0.55, 0.62);
    let lr = vec2<f32>(l0.x * cos(ro) - l0.y * sin(ro), l0.x * sin(ro) + l0.y * cos(ro));
    let L = normalize(vec3<f32>(lr.x, lr.y, 0.56));
    let V = vec3<f32>(0.0, 0.0, 1.0);
    let ndl = dot(n, L);
    let wrap = clamp((ndl + 0.42) / 1.42, 0.0, 1.0);
    let sky = vec3<f32>(1.0, 0.975, 0.94);
    let ground = vec3<f32>(0.55, 0.45, 0.40);
    let upv = vec2<f32>(-sin(ro), cos(ro));
    let hemi = mix(ground, sky, dot(n.xy, upv) * 0.5 + 0.5);
    let fres = pow(1.0 - clamp(n.z, 0.0, 1.0), 3.0);
    var occl = 1.0;
    if (inner) {
        // open forms (bowls) are lit to the floor; narrow necks stay dark inside
        let open = clamp(u.rB.y / max(u.rB.z, 1.0), 0.0, 1.5) / 1.5;
        occl = mix(mix(0.36, 0.62, open), 0.95, smoothstep(0.0, 0.85, v));
    }
    if (seg > 0.5 && seg < 1.5) {
        occl = 1.06;
    }
    // ambient occlusion where the foot meets the plinth
    occl = occl * mix(0.72, 1.0, smoothstep(0.0, 0.12, v));

    let clayLit = clay * (1.0 - printShade * 0.12) * (0.42 * hemi + 0.72 * wrap) * occl + fres * 0.10 * sky
        + pow(max(dot(n, normalize(L + V)), 0.0), 16.0) * (0.05 + u.more.y * 0.35)
        + pow(max(dot(n, normalize(L + V)), 0.0), 60.0) * u.more.y * 0.5;

    // glaze: deep where pooled, broken lighter and warmer over thin edges
    var gc = u.glaze.rgb;
    let glum = dot(u.glaze.rgb, vec3<f32>(0.3, 0.55, 0.15));
    let mottle = vnoise(i.lp * 0.07 + seed * 3.0) - 0.5;
    gc = gc * (0.94 + mottle * 0.22 * (1.0 - glum * 0.8));
    // lapis flecks: a few pale crystals floating in the glaze
    let fl = step(0.985, hash3(floor(i.lp * 0.55) + 17.0)) * (1.0 - smoothstep(0.12, 0.3, length(fract(i.lp * 0.55) - 0.5)));
    gc = mix(gc, vec3<f32>(0.72, 0.76, 0.92), fl * 0.55);
    gc = mix(gc, gc * 0.62, pool * 0.75);
    gc = mix(gc, mix(gc, clay * 0.9, 0.5) + 0.04, edge * 0.55);
    let gloss = u.glaze.w;
    let hv = normalize(L + V);
    let spec = pow(max(dot(n, hv), 0.0), 140.0) * 1.3 + pow(max(dot(n, hv), 0.0), 22.0) * 0.12;
    let r0 = reflect(-V, n);
    let r = vec3<f32>(r0.x * cos(ro) + r0.y * sin(ro), -r0.x * sin(ro) + r0.y * cos(ro), r0.z);
    let box = smoothstep(-0.82, -0.58, r.x) * (1.0 - smoothstep(-0.28, -0.1, r.x))
        * smoothstep(0.1, 0.28, r.y) * (1.0 - smoothstep(0.7, 0.86, r.y));
    let box2 = smoothstep(0.45, 0.62, r.x) * (1.0 - smoothstep(0.78, 0.92, r.x))
        * smoothstep(-0.1, 0.1, r.y) * (1.0 - smoothstep(0.45, 0.6, r.y));
    // pale glazes get the exposure white porcelain needs (they would read as grey metal otherwise)
    let expo = mix(1.0, 1.28, smoothstep(0.4, 0.9, glum));
    var glazeLit = gc * (0.30 * hemi + 0.82 * wrap) * mix(occl, 1.0, 0.35 * smoothstep(0.4, 0.9, glum)) * expo;
    // pale glazes read as porcelain, not chrome: their mirror reflections are kept soft
    let lum = dot(gc, vec3<f32>(0.3, 0.55, 0.15));
    let mirror = mix(1.0, 0.35, smoothstep(0.35, 0.85, lum));
    glazeLit = glazeLit + (spec + (box * 0.42 + box2 * 0.12) * mirror) * gloss * vec3<f32>(1.0, 0.99, 0.97)
        * mix(0.55, 1.0, occl);
    glazeLit = mix(glazeLit, vec3<f32>(0.85, 0.86, 0.92), fres * 0.22 * gloss);

    var col = mix(clayLit, glazeLit, g);

    // kiln heat: the body incandesces from inside, strongest on the turned-away edges
    let heat = u.misc.z;
    if (heat > 0.001) {
        // the piece glows from within: hotter where the wall is thin (lip, silhouette)
        let thin = 0.82 + 0.3 * fres + select(0.0, 0.15, seg > 0.5 && seg < 1.5);
        let bb = blackbody(heat * thin * 0.86);
        // keep a breath of form: glowing ware still shows its turning under the light
        let glow = bb * (0.62 + 0.5 * wrap + 0.2 * fres);
        col = mix(col, glow, smoothstep(0.0, 0.45, heat)) + bb * 0.18 * heat * fres;
    }

    return vec4<f32>(col, 1.0);
}
