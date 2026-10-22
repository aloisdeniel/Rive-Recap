// Kiln 3D effects: small ray-marched scenes drawn into a GPU canvas, one fragment
// shader with three modes (scripts/fx3d.luau picks the mode and fills the uniforms).
//
//   mode 1  liquid glaze drip (scene 4): a bead swells at the jug's lip, necks and
//           falls as a stretched teardrop, then splashes into the glaze of a tile:
//           a spreading sheet, a rebound jet, a crown of droplets and ripple rings.
//   mode 2  orbit rings (scene 9): tilted tori with droplets travelling on them.
//   mode 3  gift box (scene 8): a kraft box whose four walls fold up around the cup,
//           tissue paper blooming out of it, a ribbon wrapping round and a bow.
//
// Everything is in the hosting node's local units (y down on screen). The scene is
// orthographic and seen from the front, optionally tilted down by `tilt` (the same
// camera as scripts/vessel3d.wgsl, so a box and a lathed cup share one space).
//
// `side` splits a scene around a piece drawn by another drawable (the orb, the cup):
// side 1 draws only what lies in front of the view-space plane z = split, side -1 only
// what lies behind it. The two halves are drawn on either side of the piece, so its
// geometry passes in front of and behind it without any shared depth buffer.
// Output is premultiplied alpha, edges anti-aliased from the ray's closest approach.

struct U {
    fr: vec4<f32>,  // canvas frame (local units): x0, y0, w, h
    md: vec4<f32>,  // mode, side (-1 back, 0 all, 1 front), split (view z), local units per pixel
    cam: vec4<f32>, // camera tilt (rad), overall opacity, unused, unused
    p0: vec4<f32>,
    p1: vec4<f32>,
    p2: vec4<f32>,
    c0: vec4<f32>,
    c1: vec4<f32>,
    c2: vec4<f32>,
    c3: vec4<f32>,
};

@group(0) @binding(0) var<uniform> u: U;

const PI: f32 = 3.14159265;
const TAU: f32 = 6.2831853;
const FAR: f32 = 600.0;

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) uv: vec2<f32>,
};

@vertex
fn vs_main(@builtin(vertex_index) vi: u32) -> VOut {
    var o: VOut;
    let x = f32((vi << 1u) & 2u);
    let y = f32(vi & 2u);
    o.clip = vec4<f32>(x * 2.0 - 1.0, 1.0 - y * 2.0, 0.0, 1.0);
    o.uv = vec2<f32>(x, y);
    return o;
}

// ------------------------------------------------------------------ helpers

fn hash1(n: f32) -> f32 {
    return fract(sin(n * 127.1) * 43758.5453);
}

fn hash3(p: vec3<f32>) -> f32 {
    var q = fract(p * vec3<f32>(0.1031, 0.1030, 0.0973));
    q = q + dot(q, q.yxz + 33.33);
    return fract((q.x + q.y) * q.z);
}

fn vnoise(p: vec3<f32>) -> f32 {
    let i = floor(p);
    let f = fract(p);
    let w = f * f * (3.0 - 2.0 * f);
    let a = mix(mix(hash3(i), hash3(i + vec3<f32>(1.0, 0.0, 0.0)), w.x),
                mix(hash3(i + vec3<f32>(0.0, 1.0, 0.0)), hash3(i + vec3<f32>(1.0, 1.0, 0.0)), w.x), w.y);
    let b = mix(mix(hash3(i + vec3<f32>(0.0, 0.0, 1.0)), hash3(i + vec3<f32>(1.0, 0.0, 1.0)), w.x),
                mix(hash3(i + vec3<f32>(0.0, 1.0, 1.0)), hash3(i + vec3<f32>(1.0, 1.0, 1.0)), w.x), w.y);
    return mix(a, b, w.z);
}

fn smin(a: f32, b: f32, k: f32) -> f32 {
    let h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
    return mix(b, a, h) - k * h * (1.0 - h);
}

fn sdSphere(p: vec3<f32>, r: f32) -> f32 {
    return length(p) - r;
}

fn sdEllipsoid(p: vec3<f32>, r: vec3<f32>) -> f32 {
    let k0 = length(p / r);
    let k1 = length(p / (r * r));
    return k0 * (k0 - 1.0) / max(k1, 1e-5);
}

fn sdBox(p: vec3<f32>, b: vec3<f32>, rr: f32) -> f32 {
    let q = abs(p) - b + rr;
    return length(max(q, vec3<f32>(0.0))) + min(max(q.x, max(q.y, q.z)), 0.0) - rr;
}

fn sdTorus(p: vec3<f32>, R: f32, r: f32) -> f32 {
    return length(vec2<f32>(length(p.xz) - R, p.y)) - r;
}

fn sdRoundCone(p: vec3<f32>, a: vec3<f32>, b: vec3<f32>, r1: f32, r2: f32) -> f32 {
    let ba = b - a;
    let l2 = max(dot(ba, ba), 1e-4);
    let rr = r1 - r2;
    let a2 = l2 - rr * rr;
    let il2 = 1.0 / l2;
    let pa = p - a;
    let y = dot(pa, ba);
    let z = y - l2;
    let xv = pa * l2 - ba * y;
    let x2 = dot(xv, xv);
    let y2 = y * y * l2;
    let z2 = z * z * l2;
    let k = sign(rr) * rr * rr * x2;
    if (sign(z) * a2 * z2 > k) {
        return sqrt(x2 + z2) * il2 - r2;
    }
    if (sign(y) * a2 * y2 < k) {
        return sqrt(x2 + y2) * il2 - r1;
    }
    return (sqrt(x2 * a2 * il2) + y * rr) * il2 - r1;
}

fn rotX(p: vec3<f32>, a: f32) -> vec3<f32> {
    let c = cos(a);
    let s = sin(a);
    return vec3<f32>(p.x, p.y * c - p.z * s, p.y * s + p.z * c);
}

fn rotY(p: vec3<f32>, a: f32) -> vec3<f32> {
    let c = cos(a);
    let s = sin(a);
    return vec3<f32>(p.x * c + p.z * s, p.y, p.z * c - p.x * s);
}

fn rotZ(p: vec3<f32>, a: f32) -> vec3<f32> {
    let c = cos(a);
    let s = sin(a);
    return vec3<f32>(p.x * c - p.y * s, p.x * s + p.y * c, p.z);
}

fn easeOutBack(x: f32) -> f32 {
    let t = clamp(x, 0.0, 1.0) - 1.0;
    return 1.0 + 2.3 * t * t * t + 1.3 * t * t;
}

fn ease(x: f32) -> f32 {
    let t = clamp(x, 0.0, 1.0);
    return t * t * (3.0 - 2.0 * t);
}

// camera: view space is x right, y up, z toward the viewer; object space is tilted
// down by `tilt` about the x axis (the same convention as vessel3d's toView)
fn toObj(v: vec3<f32>) -> vec3<f32> {
    let e = u.cam.x;
    return vec3<f32>(v.x, v.y * cos(e) + v.z * sin(e), v.z * cos(e) - v.y * sin(e));
}

fn toView(p: vec3<f32>) -> vec3<f32> {
    let e = u.cam.x;
    return vec3<f32>(p.x, p.y * cos(e) - p.z * sin(e), p.z * cos(e) + p.y * sin(e));
}

// ------------------------------------------------------------------ mode 1: the drip

// surface frame of the tile glaze: a horizontal plane at the impact point seen from
// above at `st` rad, so ripples read as ellipses and the crown rises off the glaze
fn toSurf(q: vec3<f32>) -> vec3<f32> {
    let st = u.p2.x;
    return vec3<f32>(q.x, q.y * cos(st) + q.z * sin(st), q.z * cos(st) - q.y * sin(st));
}

fn mapDrop(p: vec3<f32>) -> f32 {
    let amt = u.p1.y;
    if (amt < 0.001) {
        return 1e3;
    }
    let lip = vec3<f32>(u.p0.x, -u.p0.y, 0.0);
    let hit = vec3<f32>(u.p0.z, -u.p0.w, 0.0);
    let ph = u.p1.x;
    let R = u.p1.z * (0.35 + 0.65 * amt);
    var d = 1e3;
    if (ph < 0.56) {
        // the bead swells under the lip, gets heavy and necks
        let g = smoothstep(0.0, 0.5, ph);
        let s = smoothstep(0.34, 0.56, ph);
        let rb = R * (0.36 + 0.64 * g);
        let c = lip + vec3<f32>(0.0, -(rb * 0.92 + R * 0.12 + s * R * 0.95), 0.0);
        let bead = sdEllipsoid(p - c, vec3<f32>(rb * (1.0 - 0.08 * s), rb * (1.0 + 0.16 * s), rb * (1.0 - 0.08 * s)));
        let neck = sdRoundCone(p, lip, c, R * 0.34 * (1.0 - 0.72 * s), rb * 0.55);
        d = smin(bead, neck, R * 0.32);
        d = smin(d, sdSphere(p - lip, R * 0.3), R * 0.3);
    } else {
        // what stays on the lip starts to gather again
        let g2 = smoothstep(0.56, 1.0, ph);
        d = sdSphere(p - (lip + vec3<f32>(0.0, -R * 0.12, 0.0)), R * (0.3 + 0.08 * g2));
        let startC = lip + vec3<f32>(0.0, -(R * 1.04 + R * 0.12 + R * 0.95), 0.0);
        let endC = hit + vec3<f32>(0.0, R * 0.7, 0.0);
        if (ph < 0.68) {
            // the fall: accelerating, stretched along the motion, a tail and a satellite
            let f = (ph - 0.56) / 0.12;
            let c = mix(startC, endC, f * f);
            let st = 1.0 + 0.55 * f;
            let body = sdEllipsoid(p - c, vec3<f32>(R * 0.96 / sqrt(st), R * 1.02 * st * 0.92, R * 0.96 / sqrt(st)));
            let tail = sdRoundCone(p, c + vec3<f32>(0.0, R * 0.2, 0.0), c + vec3<f32>(0.0, R * (1.15 + 0.9 * f), 0.0),
                                   R * 0.62 / sqrt(st), R * 0.06);
            d = min(d, smin(body, tail, R * 0.3));
            let sc = mix(lip + vec3<f32>(0.0, -R * 0.75, 0.0), endC, (f * 0.86) * (f * 0.86));
            d = min(d, sdSphere(p - sc, R * 0.17 * (1.0 - 0.3 * f)));
        } else {
            // the splash, in the frame of the glaze surface
            let v = (ph - 0.68) / 0.32;
            let q = toSurf(p - hit);
            // the drop slumps into a glossy puddle that spreads, then soaks into the bisque
            let soak = smoothstep(0.55, 1.0, v);
            let rp = R * (1.0 + 1.3 * ease(v * 2.4)) * (1.0 - soak);
            let tp = max(R * 0.2 + R * 0.4 * (1.0 - smoothstep(0.0, 0.22, v)), R * 0.14) * (1.0 - soak);
            if (rp > R * 0.12) {
                d = min(d, sdEllipsoid(q, vec3<f32>(rp, tp, rp)));
                // ripple rings running out across the puddle
                for (var k = 0; k < 2; k++) {
                    let fk = f32(k);
                    let w = v - 0.06 - fk * 0.14;
                    let rad = R * (0.4 + 2.4 * w);
                    if (w > 0.0 && rad < rp * 0.85) {
                        let amp = R * 0.08 * (1.0 - v) * (1.0 - 0.3 * fk);
                        let yr = tp * sqrt(max(0.0, 1.0 - (rad / rp) * (rad / rp)));
                        d = smin(d, sdTorus(q - vec3<f32>(0.0, yr - amp * 0.4, 0.0), rad, amp), amp);
                    }
                }
            }
            // the rebound jet, with a bead on top
            if (v > 0.1 && v < 0.62) {
                let j = (v - 0.1) / 0.52;
                let hj = R * 2.3 * sin(PI * j);
                let top = vec3<f32>(0.0, hj, 0.0);
                let col = sdRoundCone(q, vec3<f32>(0.0, 0.0, 0.0), top, R * 0.42 * (1.0 - 0.5 * j), R * 0.2);
                let bead = sdSphere(q - top - vec3<f32>(0.0, R * 0.22, 0.0), R * 0.3 * (1.0 - 0.4 * j));
                d = min(d, smin(col, bead, R * 0.15));
            }
            // a crown of droplets thrown up and out, falling back into the glaze
            let w = clamp(v / 0.7, 0.0, 1.0);
            if (w < 1.0) {
                for (var i = 0; i < 7; i++) {
                    let fi = f32(i);
                    let a = fi * TAU / 7.0 + 0.35 + 0.3 * hash1(fi + 3.0);
                    let sp = 0.8 + 0.45 * hash1(fi + 11.0);
                    let rad = R * (0.9 + 2.9 * w * sp);
                    let hh = R * 3.6 * sp * w * (1.0 - w);
                    let c = vec3<f32>(cos(a) * rad, hh, sin(a) * rad);
                    d = min(d, sdSphere(q - c, R * (0.21 + 0.08 * hash1(fi)) * (1.0 - 0.55 * w)));
                }
            }
        }
    }
    return d;
}

// ------------------------------------------------------------------ mode 2: orbit rings

fn ringFrame(p: vec3<f32>, i: f32) -> vec3<f32> {
    // ring i lies in its own xz plane: precessed about y, inclined about x, rolled about z
    let incl = u.p1.x + i * u.p2.z;
    let prec = u.p2.x + i * 1.2;
    return rotX(rotY(rotZ(p, -u.p2.y), -prec), -incl);
}

fn dropPos(k: f32) -> vec3<f32> {
    let R = u.p0.x;
    let a = u.p1.y + k * TAU / 5.0 + 0.25 * sin(k * 1.7);
    let wob = sin(a * 2.0 + k) * u.p0.y * 1.2;
    let q = vec3<f32>(cos(a) * R, wob, sin(a) * R);
    // back from the ring frame of ring 0 to view space
    return rotZ(rotY(rotX(q, u.p1.x), u.p2.x), u.p2.y);
}

fn mapOrbit(p: vec3<f32>) -> vec2<f32> {
    var d = 1e3;
    var m = 0.0;
    let R = u.p0.x;
    let n = i32(u.p1.z + 0.5);
    let tube = u.p0.y * u.p0.z;
    if (tube > 0.01) {
        for (var i = 0; i < 3; i++) {
            if (i < n) {
                let fi = f32(i);
                let q = ringFrame(p, fi);
                let dt = sdTorus(q, R * (1.0 + 0.09 * fi), tube * (1.0 - 0.25 * fi));
                if (dt < d) {
                    d = dt;
                    m = 1.0;
                }
            }
        }
    }
    let dr = u.p1.w * u.p0.w;
    if (dr > 0.01) {
        for (var k = 0; k < 5; k++) {
            let fk = f32(k);
            let ds = sdSphere(p - dropPos(fk), dr * (0.7 + 0.55 * hash1(fk + 5.0)));
            if (ds < d) {
                d = ds;
                m = 2.0;
            }
        }
    }
    return vec2<f32>(d, m);
}

// ------------------------------------------------------------------ mode 3: gift box

fn wallAngle(i: f32) -> f32 {
    // walls fold up one after another (back, sides, front) with a cardboard bounce
    let x = u.p0.x * 1.75 - i * 0.25;
    return 1.5707963 * easeOutBack(x);
}

fn tissueAmt(k: f32) -> f32 {
    return ease(u.p0.y * 1.45 - k * 0.08);
}

// returns distance, material (1 kraft, 2 ribbon, 3 tissue, 4 floor)
fn mapBox(p: vec3<f32>) -> vec2<f32> {
    let B = u.p1.x;
    let Hw = u.p1.y;
    let th = 3.0;
    var d = sdBox(p - vec3<f32>(0.0, -th * 0.5, 0.0), vec3<f32>(B, th * 0.5, B), 0.6);
    var m = 4.0;
    let hr = Hw * 0.46;
    let rw = 7.0;
    let rib = u.p0.z;
    let theta = atan2(p.x, p.z);
    let ribMask = (abs(theta) - rib * PI) * max(length(p.xz), 1.0);
    for (var i = 0; i < 4; i++) {
        let fi = f32(i);
        // 0 back, 1 left, 2 right, 3 front
        var nout = vec2<f32>(0.0, -1.0);
        if (i == 1) {
            nout = vec2<f32>(-1.0, 0.0);
        } else if (i == 2) {
            nout = vec2<f32>(1.0, 0.0);
        } else if (i == 3) {
            nout = vec2<f32>(0.0, 1.0);
        }
        let tang = vec2<f32>(nout.y, -nout.x);
        let phi = wallAngle(select(fi, 1.0, i == 2));
        let a = dot(p.xz, nout) - B;
        let b = p.y;
        let uu = dot(p.xz, tang);
        let v = a * cos(phi) + b * sin(phi);
        let w = -a * sin(phi) + b * cos(phi);
        let hl = select(B, B - th, i == 1 || i == 2);
        let dw = sdBox(vec3<f32>(uu, v - Hw * 0.5, w - th * 0.5), vec3<f32>(hl, Hw * 0.5, th * 0.5), 0.7);
        if (dw < d) {
            d = dw;
            m = 1.0;
        }
        if (rib > 0.001) {
            let dr = sdBox(vec3<f32>(uu, v - hr, w + 0.75), vec3<f32>(B + 1.6, rw, 0.75), 0.3);
            let drm = max(dr, ribMask);
            if (drm < d) {
                d = drm;
                m = 2.0;
            }
        }
    }
    // the bow on the front wall
    let bs = u.p0.w;
    if (bs > 0.01) {
        let s = easeOutBack(bs) * 1.4;
        // tied to the front wall: it folds with it
        let phiF = wallAngle(3.0);
        let af = p.z - B;
        let vf = af * cos(phiF) + p.y * sin(phiF);
        let wf = -af * sin(phiF) + p.y * cos(phiF);
        let q0 = vec3<f32>(p.x, vf - hr, -wf - 2.2) / max(s, 0.05);
        var db = sdEllipsoid(q0 - vec3<f32>(0.0, 0.0, 2.2), vec3<f32>(4.6, 4.2, 3.2));
        for (var k = 0; k < 2; k++) {
            let sg = select(-1.0, 1.0, k == 1);
            // a loop: a flattened ring standing out from the knot
            var q = q0 - vec3<f32>(sg * 10.5, 3.0, 2.6);
            q = rotZ(q, -sg * 0.42);
            q = rotY(q, sg * 0.35);
            let lq = vec3<f32>(q.x / 1.55, q.z, q.y);
            let loopD = (length(vec2<f32>(length(vec2<f32>(lq.x, lq.z)) - 6.8, lq.y)) - 2.2) * 0.8;
            db = smin(db, loopD, 1.6);
            // a tail hanging down, cut at an angle
            var t = q0 - vec3<f32>(sg * 6.5, -9.5, 2.0);
            t = rotZ(t, sg * 0.5);
            let tail = max(sdBox(t, vec3<f32>(3.4, 9.5, 0.7), 0.4), (t.y + t.x * sg * 0.4) - 8.0);
            db = min(db, tail);
        }
        db = db * s;
        if (db < d) {
            d = db;
            m = 2.0;
        }
    }
    // tissue paper blooming out of the box, between the walls and the cup
    if (u.p0.y > 0.001) {
        for (var k = 0; k < 6; k++) {
            let fk = f32(k);
            let amt = tissueAmt(fk);
            if (amt > 0.001) {
                let th0 = fk * TAU / 6.0 + 0.45 + 0.2 * sin(fk * 2.1);
                let rdir = vec3<f32>(sin(th0), 0.0, cos(th0));
                let tdir = vec3<f32>(cos(th0), 0.0, -sin(th0));
                let lean = 0.17 + 0.07 * sin(fk * 1.3) + 0.3 * (1.0 - amt);
                let up = rdir * sin(lean) + vec3<f32>(0.0, cos(lean), 0.0);
                let nrm = cross(tdir, up);
                let base = rdir * (B - th - 15.0) + vec3<f32>(0.0, 4.0, 0.0);
                let q = p - base;
                let sx = dot(q, tdir);
                let hy = dot(q, up);
                // each sheet curls round the cup, with soft creases rather than foil crinkles
                var wz = dot(q, nrm) + sx * sx / 150.0;
                wz = wz + 0.9 * sin(sx * 0.22 + fk * 1.7) * sin(hy * 0.18 + fk) + 0.35 * sin(sx * 0.7 + hy * 0.4);
                let Ht = (Hw + 26.0 + 8.0 * sin(fk * 2.7)) * amt * (1.0 - 0.1 * sin(sx * 0.12 + fk * 2.0));
                let hn = clamp(hy / max(Ht, 1.0), 0.0, 1.0);
                let hw = 40.0 * (1.0 - pow(hn, 2.2)) + 3.0;
                let dt = max(max(abs(wz) - 0.6, abs(sx) - hw), max(-hy, hy - Ht)) * 0.6;
                if (dt < d) {
                    d = dt;
                    m = 3.0;
                }
            }
        }
    }
    return vec2<f32>(d, m);
}

// ------------------------------------------------------------------ dispatch

fn mapAll(p: vec3<f32>) -> vec2<f32> {
    let mode = u.md.x;
    if (mode < 1.5) {
        return vec2<f32>(mapDrop(p), 1.0);
    }
    if (mode < 2.5) {
        return mapOrbit(p);
    }
    return mapBox(p);
}

fn normalAt(p: vec3<f32>) -> vec3<f32> {
    let e = 0.05;
    let k1 = vec3<f32>(1.0, -1.0, -1.0);
    let k2 = vec3<f32>(-1.0, -1.0, 1.0);
    let k3 = vec3<f32>(-1.0, 1.0, -1.0);
    let k4 = vec3<f32>(1.0, 1.0, 1.0);
    return normalize(k1 * mapAll(p + k1 * e).x + k2 * mapAll(p + k2 * e).x + k3 * mapAll(p + k3 * e).x
        + k4 * mapAll(p + k4 * e).x);
}

// ------------------------------------------------------------------ materials (view space)

const LV: vec3<f32> = vec3<f32>(-0.5499, 0.6199, 0.5599); // key light, top left (vessel3d's)

fn softbox(r: vec3<f32>) -> f32 {
    let box = smoothstep(-0.82, -0.58, r.x) * (1.0 - smoothstep(-0.28, -0.1, r.x))
        * smoothstep(0.1, 0.28, r.y) * (1.0 - smoothstep(0.7, 0.86, r.y));
    let box2 = smoothstep(0.45, 0.62, r.x) * (1.0 - smoothstep(0.78, 0.92, r.x))
        * smoothstep(-0.1, 0.1, r.y) * (1.0 - smoothstep(0.45, 0.6, r.y));
    return box * 0.9 + box2 * 0.3;
}

// wet glaze / liquid: deep body, light focused through it on the far side, a sharp
// highlight, studio window reflections and a darker reflective rim
fn liquid(n: vec3<f32>, base: vec3<f32>, gloss: f32) -> vec3<f32> {
    let V = vec3<f32>(0.0, 0.0, 1.0);
    let ndl = dot(n, LV);
    let wrap = clamp((ndl + 0.35) / 1.35, 0.0, 1.0);
    let fres = pow(1.0 - clamp(n.z, 0.0, 1.0), 2.5);
    var col = base * (0.22 + 0.58 * wrap);
    // refraction: the drop acts as a lens, light gathers opposite the key light
    let caustic = pow(clamp(dot(n, normalize(vec3<f32>(0.55, -0.6, 0.6))), 0.0, 1.0), 3.0);
    col = col + (base * 1.35 + vec3<f32>(0.10, 0.13, 0.28)) * caustic * 0.75;
    // inner core slightly deeper
    col = col * mix(0.82, 1.0, fres);
    let h = normalize(LV + V);
    let spec = pow(max(dot(n, h), 0.0), 220.0) * 2.2 + pow(max(dot(n, h), 0.0), 30.0) * 0.18;
    let r = reflect(-V, n);
    let env = mix(vec3<f32>(0.10, 0.10, 0.14), vec3<f32>(0.92, 0.92, 0.95), clamp(r.y * 0.5 + 0.5, 0.0, 1.0));
    col = mix(col, env * mix(vec3<f32>(1.0), base * 1.6 + 0.25, 0.4), fres * 0.38 * gloss);
    col = col + (spec + softbox(r) * 0.55) * gloss * vec3<f32>(1.0, 0.99, 0.97);
    return col;
}

fn paper(n: vec3<f32>, base: vec3<f32>, ao: f32, sh: f32, translucent: f32) -> vec3<f32> {
    let ndl = dot(n, LV);
    let wrap = clamp((ndl + 0.4) / 1.4, 0.0, 1.0);
    let bk = clamp(-ndl, 0.0, 1.0) * translucent;
    let sky = vec3<f32>(1.0, 0.975, 0.94);
    let ground = vec3<f32>(0.62, 0.52, 0.46);
    let hemi = mix(ground, sky, n.y * 0.5 + 0.5);
    let fres = pow(1.0 - clamp(n.z, 0.0, 1.0), 3.0);
    var col = base * (0.42 * hemi * ao + 0.66 * wrap * mix(0.45, 1.0, sh));
    col = col + base * vec3<f32>(1.0, 0.92, 0.84) * bk * 0.45;
    col = col + sky * fres * 0.06;
    let h = normalize(LV + vec3<f32>(0.0, 0.0, 1.0));
    col = col + pow(max(dot(n, h), 0.0), 24.0) * 0.06 * sh;
    return col;
}

// ------------------------------------------------------------------ fragment

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let lx = u.fr.x + i.uv.x * u.fr.z;
    let ly = u.fr.y + i.uv.y * u.fr.w;
    let side = u.md.y;
    let split = u.md.z;
    let px = max(u.md.w, 0.05);
    // the ray: straight into the screen, clipped to this instance's half of the scene
    var z0 = FAR;
    var z1 = -FAR;
    if (side > 0.5) {
        z1 = split;
    } else if (side < -0.5) {
        z0 = split;
    }
    let o = toObj(vec3<f32>(lx, -ly, z0));
    let dir = toObj(vec3<f32>(0.0, 0.0, -1.0));
    let tMax = z0 - z1;
    var t = 0.0;
    var hit = false;
    var minD = 1e9;
    var tMin = 0.0;
    var mid = 0.0;
    for (var k = 0; k < 140; k++) {
        let p = o + dir * t;
        let h = mapAll(p);
        if (h.x < minD) {
            minD = h.x;
            tMin = t;
        }
        if (h.x < 0.02) {
            hit = true;
            mid = h.y;
            break;
        }
        t = t + max(h.x * 0.8, 0.04);
        if (t > tMax) {
            break;
        }
    }
    var alpha = 1.0;
    var tt = t;
    if (!hit) {
        // anti-aliased silhouette from the closest approach, but never at the clip plane
        // (geometry just behind the split belongs to the other half)
        if (minD > px * 1.2 || tMin > tMax - px * 3.0) {
            return vec4<f32>(0.0);
        }
        alpha = clamp(1.0 - minD / (px * 1.2), 0.0, 1.0);
        tt = tMin;
        mid = mapAll(o + dir * tMin).y;
    }
    let p = o + dir * tt;
    let nObj = normalAt(p);
    let n = normalize(toView(nObj));
    let mode = u.md.x;
    var col = vec3<f32>(0.0);
    var a = alpha;
    if (mode < 1.5) {
        col = liquid(n, u.c0.rgb, 1.0);
        // a glaze drop is dense but not opaque: thin edges let a little light through
        a = alpha * mix(0.94, 1.0, pow(1.0 - clamp(n.z, 0.0, 1.0), 1.5));
    } else if (mode < 2.5) {
        if (mid < 1.5) {
            col = liquid(n, u.c0.rgb, u.c2.x);
            a = alpha * u.c0.a;
        } else {
            col = liquid(n, u.c1.rgb, 1.0);
            a = alpha * u.c1.a;
        }
    } else {
        // occlusion of the cup's own footprint: what lies inside it is the cup's
        if (side > 0.5) {
            let cupR = u.p1.z * (0.72 + 0.28 * clamp(p.y / max(u.p1.w, 1.0), 0.0, 1.0)) + 1.5;
            if (length(p.xz) < cupR && p.y < u.p1.w) {
                return vec4<f32>(0.0);
            }
        }
        // ambient occlusion and a soft shadow from the key light
        var ao = 0.0;
        for (var k = 1; k < 5; k++) {
            let hh = f32(k) * 3.5;
            ao = ao + (hh - mapAll(p + nObj * hh).x) / hh;
        }
        ao = clamp(1.0 - ao * 0.22, 0.25, 1.0);
        let lo = toObj(LV);
        var sh = 1.0;
        var st = 1.5;
        for (var k = 0; k < 28; k++) {
            let h = mapAll(p + nObj * 0.6 + lo * st).x;
            sh = min(sh, 7.0 * h / st);
            st = st + clamp(h, 0.8, 12.0);
            if (sh < 0.02 || st > 160.0) {
                break;
            }
        }
        sh = clamp(sh, 0.0, 1.0);
        if (mid < 1.5 || mid > 3.5) {
            // kraft board: warm fibres and a fine mottling
            let fib = vnoise(p * vec3<f32>(0.9, 0.12, 0.9)) - 0.5;
            let mot = vnoise(p * 0.08 + 3.0) - 0.5;
            var base = u.c0.rgb * (1.0 + fib * 0.07 + mot * 0.1);
            if (mid > 3.5) {
                base = base * 0.86;
            }
            col = paper(n, base, ao, sh, 0.0);
        } else if (mid < 2.5) {
            // satin ribbon: a soft sheen along its length
            let h = normalize(LV + vec3<f32>(0.0, 0.0, 1.0));
            col = paper(n, u.c1.rgb, ao, sh, 0.0) + pow(max(dot(n, h), 0.0), 40.0) * 0.28 * sh
                + u.c1.rgb * pow(1.0 - clamp(n.z, 0.0, 1.0), 2.0) * 0.12;
        } else {
            let cr = vnoise(p * 0.35) - 0.5;
            col = paper(n, u.c2.rgb * (1.0 + cr * 0.04), mix(ao, 1.0, 0.4), mix(sh, 1.0, 0.35), 1.0) * 1.06;
        }
    }
    a = a * u.cam.y;
    return vec4<f32>(clamp(col, vec3<f32>(0.0), vec3<f32>(1.0)) * a, a);
}
