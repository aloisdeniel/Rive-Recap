// Nocturne orbs: lit 3D celestial bodies rendered per pixel (orthographic).
//
// kind 0, moon: a cratered sphere lit by a sun whose angle is the lunar phase
//   (0 new, 0.5 first quarter, 1 full), so the "successive masked
//   illumination" is real lighting: the terminator sweeps across relief.
//   Maria from 3D value noise, named-shape-free craters with lit rims and dark
//   floors, one ray crater, a Lommel-Seeliger-style flat lunar shading, faint
//   earthshine on the night side and a warm amber limb on the lit side.
// kind 1, planet: a banded gas giant with a storm and a tilted ring system
//   (gaps, the planet's shadow on the rings, the rings occluding the near side).
// kind 2, eclipse: a dark disk with earthshine detail, a streamered corona and
//   a diamond-ring bead.
// The surface turns slowly (`turn`); under reduced motion / pause the script
// stops turning. Output is premultiplied; no discard.

struct U {
    frame: vec4<f32>,  // canvas w px, h px, px per point, kind
    geo: vec4<f32>,    // radius (pt), extent (canvas half-size / radius), phase, turn
    tint: vec4<f32>,   // rgb tint, tint amount
    look: vec4<f32>,   // earthshine, rim warmth, ring tilt, ring opacity
    more: vec4<f32>,   // exposure, halo, axial tilt (rad), seed
};

@group(0) @binding(0) var<uniform> u: U;

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

fn hash3(p: vec3<f32>) -> f32 {
    var q = fract(p * vec3<f32>(0.1031, 0.1030, 0.0973));
    q = q + dot(q, q.yxz + 33.33);
    return fract((q.x + q.y) * q.z);
}

fn noise3(p: vec3<f32>) -> f32 {
    let i = floor(p);
    let f = fract(p);
    let w = f * f * (3.0 - 2.0 * f);
    let n000 = hash3(i);
    let n100 = hash3(i + vec3<f32>(1.0, 0.0, 0.0));
    let n010 = hash3(i + vec3<f32>(0.0, 1.0, 0.0));
    let n110 = hash3(i + vec3<f32>(1.0, 1.0, 0.0));
    let n001 = hash3(i + vec3<f32>(0.0, 0.0, 1.0));
    let n101 = hash3(i + vec3<f32>(1.0, 0.0, 1.0));
    let n011 = hash3(i + vec3<f32>(0.0, 1.0, 1.0));
    let n111 = hash3(i + vec3<f32>(1.0, 1.0, 1.0));
    return mix(mix(mix(n000, n100, w.x), mix(n010, n110, w.x), w.y),
               mix(mix(n001, n101, w.x), mix(n011, n111, w.x), w.y), w.z);
}

fn fbm3(p0: vec3<f32>) -> f32 {
    var p = p0;
    var s = 0.0;
    var a = 0.5;
    for (var k = 0; k < 5; k = k + 1) {
        s = s + a * noise3(p);
        p = p * 2.03 + vec3<f32>(1.7, 9.2, 3.1);
        a = a * 0.5;
    }
    return s;
}

// x: floor (0..1), y: rim (0..1), z: ray streaks
fn crater(s: vec3<f32>, c: vec3<f32>, r: f32) -> vec2<f32> {
    let d = acos(clamp(dot(s, normalize(c)), -1.0, 1.0)) / r;
    let fl = 1.0 - smoothstep(0.7, 1.0, d);
    let rim = smoothstep(0.78, 1.0, d) * (1.0 - smoothstep(1.0, 1.32, d));
    return vec2<f32>(fl, rim);
}

const ICE = vec3<f32>(0.737, 0.894, 0.910);
const BLUE = vec3<f32>(0.376, 0.545, 1.0);
const AMBER = vec3<f32>(0.969, 0.745, 0.384);
const PI = 3.14159265;

fn rotY(v: vec3<f32>, a: f32) -> vec3<f32> {
    let c = cos(a);
    let s = sin(a);
    return vec3<f32>(c * v.x + s * v.z, v.y, -s * v.x + c * v.z);
}

fn rotZ(v: vec3<f32>, a: f32) -> vec3<f32> {
    let c = cos(a);
    let s = sin(a);
    return vec3<f32>(c * v.x - s * v.y, s * v.x + c * v.y, v.z);
}

fn moonAlbedo(s: vec3<f32>, seed: f32) -> vec3<f32> {
    // x albedo, y crater-rim light, z sea mask
    let sea = smoothstep(0.44, 0.70, fbm3(s * 1.5 + vec3<f32>(seed, 1.0, 7.0)) * 0.7 + noise3(s * 3.3 + seed) * 0.3);
    var alb = mix(0.84, 0.60, sea);
    alb = alb * (0.86 + 0.20 * fbm3(s * 11.0 + seed * 3.0)) * (0.94 + 0.08 * noise3(s * 38.0));
    var rim = 0.0;
    let c1 = crater(s, vec3<f32>(-0.30, -0.55, 0.78), 0.11);
    let c2 = crater(s, vec3<f32>(0.42, 0.28, 0.86), 0.14);
    let c3 = crater(s, vec3<f32>(0.10, 0.70, 0.70), 0.08);
    let c4 = crater(s, vec3<f32>(-0.62, 0.30, 0.72), 0.10);
    let c5 = crater(s, vec3<f32>(0.70, -0.38, 0.60), 0.12);
    let c6 = crater(s, vec3<f32>(-0.05, 0.05, 1.0), 0.06);
    let c7 = crater(s, vec3<f32>(0.25, -0.85, 0.45), 0.07);
    let c8 = crater(s, vec3<f32>(-0.78, -0.20, 0.58), 0.09);
    alb = alb * (1.0 - 0.10 * (c1.x + c2.x + c3.x + c4.x + c5.x + c6.x + c7.x + c8.x));
    rim = (c1.y + c2.y + c3.y + c4.y + c5.y + c6.y + c7.y + c8.y) * 0.45;
    // a young ray crater: bright streaks radiating from it
    let rc = normalize(vec3<f32>(-0.18, -0.78, 0.60));
    let rd = acos(clamp(dot(s, rc), -1.0, 1.0));
    let tangent = normalize(cross(rc, vec3<f32>(0.0, 1.0, 0.0)));
    let bit = normalize(cross(rc, tangent));
    let ang = atan2(dot(s, bit), dot(s, tangent));
    let rays = pow(noise3(vec3<f32>(ang * 6.0, 0.5, seed)), 3.0) * exp(-rd * 3.2) * smoothstep(0.05, 0.12, rd);
    alb = alb + rays * 0.45 + exp(-pow(rd / 0.035, 2.0)) * 0.3;
    return vec3<f32>(clamp(alb, 0.0, 1.2), rim, sea);
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let kind = u.frame.w;
    let ext = u.geo.y;
    let res = u.frame.z;
    let R = u.geo.x;
    let px = 1.0 / (R * res);                         // one pixel in sphere units
    var p = (i.uv * 2.0 - 1.0) * ext;
    p.y = -p.y;                                       // y up
    let r2 = dot(p, p);
    let r = sqrt(r2);
    let seed = u.more.w;
    let tintc = mix(vec3<f32>(1.0), u.tint.rgb * 1.25, u.tint.a);
    let cover = 1.0 - smoothstep(1.0 - px * 1.2, 1.0 + px * 0.2, r);
    let z = sqrt(max(1.0 - min(r2, 1.0), 0.0));
    let n = vec3<f32>(p.x, p.y, z);
    var col = vec3<f32>(0.0);
    var a = 0.0;

    if (kind < 0.5) {
        // ---------------- moon
        let ph = clamp(u.geo.z, 0.0, 1.0) * PI;
        let L = normalize(vec3<f32>(sin(ph), 0.18 * sin(ph), -cos(ph)));
        let s = rotZ(rotY(n, u.geo.w), u.more.z);
        let m = moonAlbedo(s, seed);
        let mu0 = dot(n, L);
        let mu = max(n.z, 0.02);
        let ls = max(mu0, 0.0) / (max(mu0, 0.0) + mu);         // flat lunar look
        let lam = max(mu0, 0.0);
        var lit = (ls * 1.25 + lam * 0.45) * m.x;
        // relief: rims catch light near the terminator, shadowed opposite
        lit = lit + m.y * 0.30 * smoothstep(-0.05, 0.35, mu0) * (1.0 - smoothstep(0.35, 0.9, mu0)) * 1.4;
        let term = smoothstep(-0.06, 0.10, mu0);
        let day = mix(vec3<f32>(0.36, 0.46, 0.64), vec3<f32>(0.84, 0.89, 0.95), clamp((m.x - 0.45) * 2.2, 0.0, 1.0));
        col = day * lit * term * tintc;
        // warm terminator glow and amber limb on the lit side
        col = col + AMBER * 0.22 * u.look.y * exp(-pow(mu0 / 0.12, 2.0)) * smoothstep(-0.2, 0.05, mu0) * m.x;
        let fres = pow(1.0 - mu, 2.5);
        col = col + AMBER * fres * smoothstep(0.0, 0.5, mu0) * 0.9 * u.look.y;
        // earthshine on the night side
        let es = u.look.x * (1.0 - term) * (0.35 + 0.65 * m.x);
        col = col + vec3<f32>(0.09, 0.15, 0.28) * es * tintc;
        // limb darkening + cool rim
        col = col * (0.82 + 0.18 * mu);
        col = col + vec3<f32>(0.25, 0.40, 0.75) * fres * 0.18;
        a = cover;
        col = col * u.more.x;
        // halo: light scattered round the lit limb
        let lf = clamp(0.5 - 0.5 * cos(ph), 0.0, 1.0);
        let h = exp(-max(r - 1.0, 0.0) * 9.0) * (1.0 - cover) * u.more.y * (0.25 + 0.75 * lf);
        col = col * a + mix(ICE, AMBER, 0.25) * h * 0.35;
        return vec4<f32>(col, a);
    } else if (kind < 1.5) {
        // ---------------- ringed planet
        let L = normalize(vec3<f32>(-0.55, 0.45, 0.70));
        let s = rotZ(rotY(n, u.geo.w), u.more.z);
        let lat = s.y;
        let warp = fbm3(s * 3.0 + seed) * 0.6;
        let bands = sin(lat * 15.0 + warp * 4.0 + sin(lat * 5.0) * 1.5);
        let fine = fbm3(vec3<f32>(lat * 40.0, s.x * 2.0, s.z * 2.0) + seed);
        var surf = mix(u.tint.rgb * 0.72, mix(u.tint.rgb, vec3<f32>(1.0, 0.95, 0.88), 0.45), 0.5 + 0.5 * bands);
        surf = surf * (0.85 + 0.3 * fine);
        let storm = exp(-dot(s - normalize(vec3<f32>(0.35, -0.32, 0.88)), s - normalize(vec3<f32>(0.35, -0.32, 0.88))) * 60.0);
        surf = mix(surf, vec3<f32>(0.95, 0.55, 0.32), storm * 0.6);
        let mu0 = dot(n, L);
        var lit = smoothstep(-0.1, 0.25, mu0) * (0.25 + 0.85 * max(mu0, 0.0));
        // ring geometry (plane through the centre, tilted toward the viewer)
        let tilt = u.look.z;
        let nr = normalize(vec3<f32>(-sin(tilt) * 0.35, cos(tilt), sin(tilt)));
        let zr = -(nr.x * p.x + nr.y * p.y) / nr.z;
        let P = vec3<f32>(p.x, p.y, zr);
        let dr = length(P);
        var ring = smoothstep(1.32, 1.36, dr) * (1.0 - smoothstep(2.15, 2.22, dr));
        ring = ring * (0.55 + 0.45 * sin(dr * 38.0)) * (1.0 - 0.85 * exp(-pow((dr - 1.78) / 0.025, 2.0)));
        ring = ring * u.look.w;
        // planet shadow on the ring
        let along = dot(P, L);
        let perp = length(P - along * L);
        let shadowed = select(1.0, 0.18, along < 0.0 && perp < 1.0);
        var planetCol = surf * lit;
        planetCol = planetCol + u.tint.rgb * pow(1.0 - max(n.z, 0.0), 3.0) * 0.35 * smoothstep(0.0, 0.4, mu0);
        let ringCol = mix(vec3<f32>(0.80, 0.86, 0.92), u.tint.rgb, 0.35) * (0.55 + 0.45 * smoothstep(-0.2, 0.6, dot(nr, L) * 0.5 + 0.5)) * shadowed;
        let ringA = clamp(ring, 0.0, 1.0) * 0.85;
        let front = zr > z;                          // ring point in front of the sphere
        if (r < 1.0) {
            col = planetCol * cover;
            a = cover;
            if (front) {
                col = mix(col, ringCol, ringA);
                a = max(a, ringA);
            }
        } else {
            col = ringCol * ringA;
            a = ringA;
            col = col + planetCol * cover;
            a = max(a, cover);
        }
        col = col * u.more.x;
        let h = exp(-max(r - 1.0, 0.0) * 10.0) * (1.0 - cover) * u.more.y;
        col = col + u.tint.rgb * h * 0.25;
        return vec4<f32>(col, a);
    }
    // ---------------- eclipse
    let s = rotZ(rotY(n, u.geo.w), u.more.z);
    let m = moonAlbedo(s, seed);
    var disk = u.tint.rgb * 0.55 + vec3<f32>(0.03, 0.05, 0.09) * m.x * u.look.x * 3.0;
    disk = disk * (0.75 + 0.25 * n.z);
    let ang = atan2(p.y, p.x);
    let streak = 0.55 + 0.45 * noise3(vec3<f32>(ang * 5.0, 0.0, seed)) + 0.35 * pow(noise3(vec3<f32>(ang * 13.0, 3.0, seed)), 2.0);
    let corona = exp(-max(r - 1.0, 0.0) * mix(9.0, 3.5, streak)) * (1.0 - cover) * u.more.y;
    let inner = exp(-pow((r - 1.0) / 0.018, 2.0));
    let beadDir = vec2<f32>(cos(0.75), sin(0.75));
    let bead = exp(-dot(p - beadDir, p - beadDir) * 900.0) * 1.4 + exp(-dot(p - beadDir, p - beadDir) * 40.0) * 0.25;
    col = disk * cover + (ICE * corona * 0.55 + ICE * inner * 0.9 + vec3<f32>(1.0, 0.97, 0.9) * bead) * u.more.x;
    a = max(cover, clamp(corona * 0.0, 0.0, 1.0));
    return vec4<f32>(col, a);
}
