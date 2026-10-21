// Stash 3D coin: a minted toy coin lathed on the GPU.
//
// The mesh is only a (u, s) grid. The vertex shader turns it into a coin
// (flat face, raised rim, rounded reeded edge, mirrored back) and spins it by
// yaw / pitch / roll uniforms, so the state machine keys a real 3D spin.
// Two passes draw it: an inverted hull in ink (the chunky cut-out outline of
// the vector art) and the gold body, whose faces carry an embossed icon
// (star, house, graduation cap, palm) from 2D signed distance fields.
//
//   s in [0.0, 0.2]   front face           seg 0
//   s in [0.2, 0.3]   front rim (wall, top) seg 1
//   s in [0.3, 0.7]   rounded edge          seg 2
//   s in [0.7, 0.8]   back rim              seg 3
//   s in [0.8, 1.0]   back face             seg 4

struct U {
    rot: vec4<f32>,   // yaw, pitch, roll, canvas extent (object units, half width)
    shape: vec4<f32>, // half thickness, icon (0 star, 1 house, 2 cap, 3 palm, 4 none), outline width, opacity
    gold: vec4<f32>,  // body rgb, shine (0 matte .. 1 mirror)
    ink: vec4<f32>,   // outline rgb, light roll compensation (rad)
};

@group(0) @binding(0) var<uniform> u: U;

const PI: f32 = 3.14159265;
const TAU: f32 = 6.2831853;
const RF: f32 = 0.74;   // face radius
const RW: f32 = 0.79;   // rim inner wall top
const RC: f32 = 0.86;   // edge curve start
const LIP: f32 = 0.055; // rim height above the face

struct VIn {
    @location(0) uv: vec2<f32>,
};

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) n: vec3<f32>,  // view-space normal
    @location(1) op: vec3<f32>, // object position
    @location(2) seg: f32,
};

// cross-section of the coin: x = radius, y = z (thickness), z = normal r, w = normal z
fn section(sIn: f32) -> vec4<f32> {
    let h = u.shape.x;
    let zt = h + LIP;
    let back = sIn > 0.5;
    let s = select(sIn, 1.0 - sIn, back);
    var r = 0.0;
    var z = 0.0;
    var nr = 0.0;
    var nz = 1.0;
    if (s <= 0.2) {
        r = RF * s / 0.2;
        z = h;
    } else if (s <= 0.25) {
        let k = (s - 0.2) / 0.05;
        r = mix(RF, RW, k);
        z = mix(h, zt, k);
        let d = normalize(vec2<f32>(-(zt - h), RW - RF));
        nr = d.x;
        nz = d.y;
    } else if (s <= 0.3) {
        let k = (s - 0.25) / 0.05;
        r = mix(RW, RC, k);
        z = zt;
    } else {
        let phi = (s - 0.3) / 0.2 * PI * 0.5;
        let a = 1.0 - RC;
        r = RC + a * sin(phi);
        z = zt * cos(phi);
        let d = normalize(vec2<f32>(sin(phi) / a, cos(phi) / zt));
        nr = d.x;
        nz = d.y;
    }
    if (back) {
        z = -z;
        nz = -nz;
    }
    return vec4<f32>(r, z, nr, nz);
}

fn rotX(p: vec3<f32>, a: f32) -> vec3<f32> {
    let c = cos(a);
    let s = sin(a);
    return vec3<f32>(p.x, p.y * c - p.z * s, p.y * s + p.z * c);
}

fn rotY(p: vec3<f32>, a: f32) -> vec3<f32> {
    let c = cos(a);
    let s = sin(a);
    return vec3<f32>(p.x * c + p.z * s, p.y, -p.x * s + p.z * c);
}

fn rotZ(p: vec3<f32>, a: f32) -> vec3<f32> {
    let c = cos(a);
    let s = sin(a);
    return vec3<f32>(p.x * c - p.y * s, p.x * s + p.y * c, p.z);
}

// object -> view: roll about the coin's own axis, then yaw (spin), then pitch (tilt)
fn toView(p: vec3<f32>) -> vec3<f32> {
    return rotX(rotY(rotZ(p, u.rot.z), u.rot.x), u.rot.y);
}

fn segOf(s: f32) -> f32 {
    if (s <= 0.2) { return 0.0; }
    if (s <= 0.3) { return 1.0; }
    if (s <= 0.7) { return 2.0; }
    if (s <= 0.8) { return 3.0; }
    return 4.0;
}

fn place(uv: vec2<f32>, grow: f32) -> VOut {
    var o: VOut;
    let th = uv.x * TAU;
    let c = section(uv.y);
    var p = vec3<f32>(c.x * cos(th), c.x * sin(th), c.y);
    var nObj = vec3<f32>(c.z * cos(th), c.z * sin(th), c.w);
    // the field is very slightly domed, so light rolls across the face
    if (abs(c.z) < 0.001 && c.x < RF + 0.001) {
        nObj = normalize(vec3<f32>(p.x * 0.24, p.y * 0.24, c.w));
    }
    // the hull grows along a smoothed normal so the outline keeps one width
    let sn = normalize(vec3<f32>(p.x, p.y, p.z * 2.4) + nObj * 0.35);
    p = p + sn * grow;
    let v = toView(p);
    let e = u.rot.w;
    o.clip = vec4<f32>(v.x / e, v.y / e, 0.5 - v.z * 0.2, 1.0);
    o.n = toView(nObj);
    o.op = p;
    o.seg = segOf(uv.y);
    return o;
}

@vertex
fn vs_main(v: VIn) -> VOut {
    return place(v.uv, 0.0);
}

@vertex
fn vs_outline(v: VIn) -> VOut {
    return place(v.uv, u.shape.z);
}

@fragment
fn fs_ink(i: VOut) -> @location(0) vec4<f32> {
    let a = u.shape.w;
    return vec4<f32>(u.ink.rgb * a, a);
}

// ------------------------------------------------------------------ icons

fn sdBox(p: vec2<f32>, b: vec2<f32>) -> f32 {
    let d = abs(p) - b;
    return length(max(d, vec2<f32>(0.0))) + min(max(d.x, d.y), 0.0);
}

fn sdSeg(p: vec2<f32>, a: vec2<f32>, b: vec2<f32>) -> f32 {
    let pa = p - a;
    let ba = b - a;
    let h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h);
}

fn sdTri(p: vec2<f32>, p0: vec2<f32>, p1: vec2<f32>, p2: vec2<f32>) -> f32 {
    let e0 = p1 - p0;
    let e1 = p2 - p1;
    let e2 = p0 - p2;
    let v0 = p - p0;
    let v1 = p - p1;
    let v2 = p - p2;
    let pq0 = v0 - e0 * clamp(dot(v0, e0) / dot(e0, e0), 0.0, 1.0);
    let pq1 = v1 - e1 * clamp(dot(v1, e1) / dot(e1, e1), 0.0, 1.0);
    let pq2 = v2 - e2 * clamp(dot(v2, e2) / dot(e2, e2), 0.0, 1.0);
    let s = sign(e0.x * e2.y - e0.y * e2.x);
    let d = min(min(vec2<f32>(dot(pq0, pq0), s * (v0.x * e0.y - v0.y * e0.x)),
                    vec2<f32>(dot(pq1, pq1), s * (v1.x * e1.y - v1.y * e1.x))),
                vec2<f32>(dot(pq2, pq2), s * (v2.x * e2.y - v2.y * e2.x)));
    return -sqrt(d.x) * sign(d.y);
}

fn sdStar5(p0: vec2<f32>, r: f32, rf: f32) -> f32 {
    let k1 = vec2<f32>(0.809016994375, -0.587785252292);
    let k2 = vec2<f32>(-k1.x, k1.y);
    var p = vec2<f32>(abs(p0.x), p0.y);
    p = p - 2.0 * max(dot(k1, p), 0.0) * k1;
    p = p - 2.0 * max(dot(k2, p), 0.0) * k2;
    p.x = abs(p.x);
    p.y = p.y - r;
    let ba = rf * vec2<f32>(-k1.y, k1.x) - vec2<f32>(0.0, 1.0);
    let h = clamp(dot(p, ba) / dot(ba, ba), 0.0, r);
    return length(p - ba * h) * sign(p.y * ba.x - p.x * ba.y);
}

fn icon(q: vec2<f32>) -> f32 {
    let k = u.shape.y;
    if (k < 0.5) {
        return sdStar5(q - vec2<f32>(0.0, -0.04), 0.66, 0.46) - 0.05;
    }
    if (k < 1.5) {
        let roof = sdTri(q, vec2<f32>(-0.62, 0.06), vec2<f32>(0.62, 0.06), vec2<f32>(0.0, 0.6)) - 0.04;
        let body = sdBox(q - vec2<f32>(0.0, -0.22), vec2<f32>(0.4, 0.3)) - 0.03;
        let door = sdBox(q - vec2<f32>(0.0, -0.33), vec2<f32>(0.11, 0.2));
        return max(min(roof, body), -door);
    }
    if (k < 2.5) {
        let top = min(sdTri(q, vec2<f32>(-0.7, 0.2), vec2<f32>(0.7, 0.2), vec2<f32>(0.0, 0.5)),
                      sdTri(q, vec2<f32>(-0.7, 0.2), vec2<f32>(0.0, -0.08), vec2<f32>(0.7, 0.2))) - 0.03;
        let band = sdBox(q - vec2<f32>(0.0, -0.16), vec2<f32>(0.34, 0.17)) - 0.05;
        let tassel = sdSeg(q, vec2<f32>(0.5, 0.2), vec2<f32>(0.52, -0.3)) - 0.05;
        return min(min(top, band), tassel);
    }
    if (k < 3.5) {
        let trunk = sdSeg(q, vec2<f32>(0.1, -0.62), vec2<f32>(-0.02, 0.18)) - 0.08;
        let c = vec2<f32>(0.0, 0.22);
        var l = sdSeg(q, c, vec2<f32>(-0.56, 0.02)) - 0.09;
        l = min(l, sdSeg(q, c, vec2<f32>(0.56, 0.02)) - 0.09);
        l = min(l, sdSeg(q, c, vec2<f32>(-0.36, 0.52)) - 0.08);
        l = min(l, sdSeg(q, c, vec2<f32>(0.38, 0.5)) - 0.08);
        return min(trunk, l);
    }
    return 10.0;
}

// ------------------------------------------------------------------ material

fn env(r: vec3<f32>) -> f32 {
    // studio: bright sky band above, warm floor bounce below, a dark horizon gap
    let sky = smoothstep(-0.05, 0.55, r.y);
    let bounce = smoothstep(-0.2, -0.75, r.y) * 0.45;
    let soft = pow(max(dot(r, normalize(vec3<f32>(-0.55, 0.7, 0.45))), 0.0), 18.0);
    let rim = pow(max(dot(r, normalize(vec3<f32>(0.8, -0.2, 0.55))), 0.0), 10.0) * 0.5;
    return clamp(0.18 + sky * 0.62 + bounce + soft * 0.9 + rim, 0.0, 1.6);
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let lr = u.ink.w;
    var n = normalize(i.n);
    let seg = i.seg;
    let gold = u.gold.rgb;
    let dark = gold * vec3<f32>(0.74, 0.5, 0.26);
    let lite = mix(gold, vec3<f32>(1.0, 0.98, 0.84), 0.7);
    var tint = 0.0;
    var line = 0.0;
    // faces: embossed icon (raised, bevelled, outlined like the vector art)
    if (seg < 0.5 || seg > 3.5) {
        var q = i.op.xy / RF;
        if (seg > 3.5) {
            q.x = -q.x;
        }
        let d = icon(q);
        let e = 0.012;
        let gx = icon(q + vec2<f32>(e, 0.0)) - icon(q - vec2<f32>(e, 0.0));
        let gy = icon(q + vec2<f32>(0.0, e)) - icon(q - vec2<f32>(0.0, e));
        let g = vec2<f32>(gx, gy) / (2.0 * e);
        let bevel = 1.0 - smoothstep(0.0, 0.07, abs(d + 0.035));
        var side = 1.0;
        if (seg > 3.5) {
            side = -1.0;
        }
        // raised where d < 0: the bevel tilts the normal outward, along +grad d
        let pert = vec3<f32>(g.x * side, g.y, 0.0) * bevel * 0.9;
        n = normalize(n + toView(pert));
        tint = 1.0 - smoothstep(-0.02, 0.01, d);
        line = 1.0 - smoothstep(0.0, 0.028, abs(d - 0.008));
        // a minted ring just inside the rim
        let rr = length(q);
        line = max(line, (1.0 - smoothstep(0.0, 0.022, abs(rr - 0.9))) * 0.45);
    }
    // reeded edge
    if (seg > 1.5 && seg < 2.5) {
        let th = atan2(i.op.y, i.op.x);
        let t = toView(vec3<f32>(-sin(th), cos(th), 0.0));
        let flat = 1.0 - smoothstep(0.55, 1.0, abs(i.op.z) / (u.shape.x + LIP));
        n = normalize(n + t * sin(th * 96.0) * 0.32 * flat);
    }
    // the light stays top-left on screen however the hosting node is rolled
    let L = normalize(vec3<f32>(-0.55 * cos(lr) - 0.7 * sin(lr), 0.7 * cos(lr) - 0.55 * sin(lr), 0.62));
    let V = vec3<f32>(0.0, 0.0, 1.0);
    let ndl = dot(n, L);
    let hl = clamp(ndl * 0.5 + 0.5, 0.0, 1.0);
    // cel-ish diffuse: three tones softened, like the vector coin's bevel
    let q4 = floor(hl * 4.0 + 0.5) / 4.0;
    let dd = mix(hl, q4, 0.45);
    var col = mix(dark, gold, smoothstep(0.22, 0.6, dd));
    col = mix(col, lite, smoothstep(0.72, 0.98, dd) * 0.7);
    // metal: reflect the studio
    let r = reflect(-V, n);
    let ev = env(vec3<f32>(r.x * cos(lr) + r.y * sin(lr), -r.x * sin(lr) + r.y * cos(lr), r.z));
    let metal = mix(dark * 0.7, lite, clamp(ev, 0.0, 1.0)) + vec3<f32>(1.0, 0.95, 0.8) * max(ev - 1.0, 0.0) * 0.9;
    col = mix(col, metal, u.gold.a);
    // raised icon catches more light; the edge line prints like ink on the face
    col = mix(col, col * 1.08 + vec3<f32>(0.05, 0.04, 0.0), tint * 0.8);
    col = mix(col, dark * 0.82, line * 0.75);
    // the rim wall facing inward sits in its own shadow
    if ((seg > 0.5 && seg < 1.5) || (seg > 2.5 && seg < 3.5)) {
        col = col * mix(1.0, 0.9, smoothstep(0.75, 0.8, length(i.op.xy)));
    }
    // specular glint
    let hv = normalize(L + V);
    let sp = pow(max(dot(n, hv), 0.0), 60.0);
    col = col + vec3<f32>(1.0, 0.97, 0.88) * sp * 0.85;
    let a = u.shape.w;
    return vec4<f32>(clamp(col, vec3<f32>(0.0), vec3<f32>(1.0)) * a, a);
}
