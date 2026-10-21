// Stash 3D glass jar: the motif's mint jar as a lathed glass shell.
//
// Drawn in two layers by two drawables so the vector coin pile can sit between
// them: layer 0 is the far wall seen through the glass (darker, with a caustic
// ring where light focuses near the floor), layer 1 the near wall (clear in the
// middle, thick and tinted at grazing angles, with softbox streaks). Neither
// needs depth: each layer keeps only the faces that point its way, so the
// fragments it drops return transparent instead of discarding.
//
// The profile matches the vector outline exactly (a rounded rectangle body with
// 46 pt corners and a 64 pt neck), so the ink stroke drawn on top fits it.

struct U {
    a: vec4<f32>,     // layer (0 back, 1 front), canvas half width, canvas top, canvas bottom
    tint: vec4<f32>,  // glass rgb, strength
    deep: vec4<f32>,  // edge rgb, caustic
    misc: vec4<f32>,  // spin of the streaks (rad), shimmer (0..1), opacity, unused
};

@group(0) @binding(0) var<uniform> u: U;

const PI: f32 = 3.14159265;
const TAU: f32 = 6.2831853;
const R: f32 = 89.0;      // body radius
const RC: f32 = 46.0;     // corner radius
const BODY_H: f32 = 198.0;
const NECK: f32 = 64.0;
const TOP: f32 = 217.0;

struct VIn {
    @location(0) uv: vec2<f32>,
};

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) n: vec3<f32>,
    @location(1) h: f32,
    @location(2) th: f32,
};

// profile: x = radius, y = height above the jar floor
fn profile(s: f32) -> vec2<f32> {
    let flat = R - RC;                       // 43
    let side = BODY_H - 2.0 * RC;            // 106
    let dh = sqrt(RC * RC - (NECK - flat) * (NECK - flat));
    let neckH = BODY_H - RC + dh;            // where the top corner reaches the neck radius
    let topArc = asin(clamp(dh / RC, 0.0, 1.0));
    // arc-length parametrisation of the half outline
    let l0 = flat;
    let l1 = l0 + RC * PI * 0.5;
    let l2 = l1 + side;
    let l3 = l2 + RC * topArc;
    let l4 = l3 + (TOP - neckH);
    let d = s * l4;
    if (d <= l0) {
        return vec2<f32>(d, 0.0);
    }
    if (d <= l1) {
        let a = (d - l0) / RC - PI * 0.5;
        return vec2<f32>(flat + RC * cos(a), RC + RC * sin(a));
    }
    if (d <= l2) {
        return vec2<f32>(R, RC + (d - l1));
    }
    if (d <= l3) {
        let a = (d - l2) / RC;
        return vec2<f32>(flat + RC * cos(a), BODY_H - RC + RC * sin(a));
    }
    return vec2<f32>(NECK, neckH + (d - l3));
}

@vertex
fn vs_main(v: VIn) -> VOut {
    var o: VOut;
    let th = v.uv.x * TAU;
    let s = v.uv.y;
    let p = profile(s);
    let e = 0.002;
    let pa = profile(max(s - e, 0.0));
    let pb = profile(min(s + e, 1.0));
    let t = pb - pa;
    var nr = vec2<f32>(t.y, -t.x);
    if (length(nr) < 1e-5) {
        nr = vec2<f32>(0.0, -1.0);
    }
    nr = normalize(nr);
    let n = vec3<f32>(nr.x * sin(th), nr.y, nr.x * cos(th));
    // local node space: x right, y down; the jar floor sits at y = 0
    let x = p.x * sin(th);
    let y = -p.y;
    let hw = u.a.y;
    let top = u.a.z;
    let bottom = u.a.w;
    o.clip = vec4<f32>(x / hw, 1.0 - 2.0 * (y - top) / (bottom - top), 0.5, 1.0);
    o.n = n;
    o.h = p.y;
    o.th = th;
    return o;
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    var n = normalize(i.n);
    let front = u.a.x > 0.5;
    let facing = n.z;
    if ((front && facing < 0.0) || (!front && facing > 0.0)) {
        return vec4<f32>(0.0);
    }
    if (!front) {
        n = -n;
    }
    let op = u.misc.z;
    let fres = pow(1.0 - clamp(abs(facing), 0.0, 1.0), 2.0);
    let glass = u.tint.rgb;
    let edge = u.deep.rgb;
    var col = mix(glass, edge, fres * 0.85);
    var a = 0.0;
    if (front) {
        a = u.tint.a * (0.05 + 0.72 * fres);
        // thick glass floor and the shoulder catch more tint
        a = a + (1.0 - smoothstep(0.0, 9.0, i.h)) * 0.28;
        // softbox reflections: two tall streaks left, a thin one right
        let V = vec3<f32>(0.0, 0.0, 1.0);
        let r = reflect(-V, n);
        let sway = u.misc.x;
        let rx = r.x * cos(sway) + r.z * sin(sway);
        let tall = smoothstep(0.18, 0.95, i.h / TOP) * (1.0 - smoothstep(0.86, 0.97, i.h / TOP));
        let s1 = (1.0 - smoothstep(0.0, 0.07, abs(rx + 0.52))) * smoothstep(12.0, 40.0, i.h) * (1.0 - smoothstep(170.0, 195.0, i.h));
        let s2 = (1.0 - smoothstep(0.0, 0.035, abs(rx + 0.33))) * tall * 0.7;
        let s3 = (1.0 - smoothstep(0.0, 0.03, abs(rx - 0.7))) * tall * 0.55;
        // a curved glint across the shoulder
        let sh = (1.0 - smoothstep(0.0, 6.0, abs(i.h - 176.0))) * (1.0 - smoothstep(0.1, 0.5, abs(rx + 0.25)));
        let st = clamp(s1 * 0.95 + s2 * 1.1 + s3 + sh * 0.6, 0.0, 1.0) * (0.85 + 0.15 * u.misc.y);
        col = mix(col, vec3<f32>(1.0, 1.0, 0.97), st);
        a = max(a, st * 0.9);
    } else {
        a = u.tint.a * (0.32 + 0.3 * fres);
        col = mix(col, edge * 0.82, 0.45);
        // caustic: light focused by the curved floor, a bright soft band near the bottom
        let ca = u.deep.a * (1.0 - smoothstep(0.0, 26.0, abs(i.h - 22.0)));
        col = mix(col, vec3<f32>(0.95, 1.0, 0.9), ca * 0.6);
        a = a + ca * 0.15;
    }
    a = clamp(a, 0.0, 1.0) * op;
    return vec4<f32>(col * a, a);
}
