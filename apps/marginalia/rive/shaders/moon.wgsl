// Marginalia etched moon: a lit sphere rendered as a copperplate engraving.
//
// Every pixel of a quad is a point on a unit sphere. Its tone comes from a
// soft key light plus dark "seas" (3D value noise) and a few craters with lit
// rims. That tone is then *printed* rather than shaded: as engraved hatch lines
// that follow the moon's latitude (swelling where the tone is dark), with a
// second, crossing family only in the deepest shadow - the way an etcher
// would build a moon in a frontispiece. The sphere slowly turns (longitude
// offset), so the lines and seas drift across it like a real libration.

struct U {
    look: vec4<f32>,   // x longitude (turn), y hatch density, z canvas px, w unused
    paper: vec4<f32>,  // rgb lit paper tone
    ink: vec4<f32>,    // rgb engraving ink
    rim: vec4<f32>,    // rgb rim / outline, a rim width (0..1 of radius)
};

@group(0) @binding(0) var<uniform> u: U;

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
    let x00 = mix(n000, n100, w.x);
    let x10 = mix(n010, n110, w.x);
    let x01 = mix(n001, n101, w.x);
    let x11 = mix(n011, n111, w.x);
    return mix(mix(x00, x10, w.y), mix(x01, x11, w.y), w.z);
}

fn crater(s: vec3<f32>, c: vec3<f32>, r: f32) -> vec2<f32> {
    // x: floor darkening, y: lit rim
    let d = acos(clamp(dot(s, normalize(c)), -1.0, 1.0)) / r;
    let floorMask = 1.0 - smoothstep(0.75, 1.0, d);
    let rimMask = smoothstep(0.8, 1.0, d) * (1.0 - smoothstep(1.0, 1.25, d));
    return vec2<f32>(floorMask, rimMask);
}

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) p: vec2<f32>,
};

@vertex
fn vs_main(@builtin(vertex_index) vi: u32) -> VOut {
    var corners = array<vec2<f32>, 6>(
        vec2<f32>(-1.0, -1.0), vec2<f32>(1.0, -1.0), vec2<f32>(-1.0, 1.0),
        vec2<f32>(-1.0, 1.0), vec2<f32>(1.0, -1.0), vec2<f32>(1.0, 1.0));
    let c = corners[vi];
    var o: VOut;
    o.clip = vec4<f32>(c, 0.0, 1.0);
    o.p = vec2<f32>(c.x, c.y) * 1.04;   // a little margin for the antialiased edge
    return o;
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let p = i.p;
    let r2 = dot(p, p);
    let r = sqrt(r2);
    let px = 2.0 / u.look.z;                     // one canvas pixel in sphere units
    let cover = 1.0 - smoothstep(1.0 - px * 1.5, 1.0, r);
    let z = sqrt(max(1.0 - min(r2, 1.0), 0.0));
    let n = vec3<f32>(p.x, p.y, z);              // view space, y up
    // turn the sphere about its axis
    let ca = cos(u.look.x);
    let sa = sin(u.look.x);
    let s = vec3<f32>(ca * n.x + sa * n.z, n.y, -sa * n.x + ca * n.z);
    // light: a soft key from the upper left, so the terminator falls lower right
    let L = normalize(vec3<f32>(-0.42, 0.38, 0.82));
    var tone = clamp(dot(n, L) * 0.78 + 0.40, 0.0, 1.0);
    // seas
    let sea = smoothstep(0.50, 0.66, noise3(s * 2.1 + vec3<f32>(3.0, 1.0, 7.0)) * 0.7 + noise3(s * 4.3) * 0.3);
    tone = tone * (1.0 - 0.30 * sea);
    // craters
    var rim = 0.0;
    let c1 = crater(s, vec3<f32>(-0.35, -0.42, 0.84), 0.20);
    let c2 = crater(s, vec3<f32>(0.42, 0.30, 0.86), 0.13);
    let c3 = crater(s, vec3<f32>(0.10, -0.75, 0.65), 0.11);
    let c4 = crater(s, vec3<f32>(-0.62, 0.40, 0.67), 0.09);
    let c5 = crater(s, vec3<f32>(0.75, -0.25, 0.61), 0.15);
    tone = tone * (1.0 - 0.22 * (c1.x + c2.x + c3.x + c4.x + c5.x));
    rim = (c1.y + c2.y + c3.y + c4.y + c5.y) * max(dot(n, L), 0.0);
    tone = clamp(tone + rim * 0.25, 0.0, 1.0);
    // engraving: latitude hatching, swelling with darkness
    let lat = asin(clamp(s.y, -1.0, 1.0));
    let lon = atan2(s.x, s.z);
    let h1 = lat * u.look.y + sin(lon * 2.0) * 0.35;
    let f1 = fwidth(h1) * 1.2;
    let d1 = abs(fract(h1) - 0.5) * 2.0;
    let w1 = clamp((1.0 - tone) * 1.15 - 0.04, 0.0, 0.95);
    let line1 = 1.0 - smoothstep(w1 - f1, w1 + f1, d1);
    // cross hatching only in the deepest shadow
    let h2 = (lon * 0.9 + lat * 0.5) * u.look.y;
    let f2 = fwidth(h2) * 1.2;
    let d2 = abs(fract(h2) - 0.5) * 2.0;
    let w2 = clamp((0.52 - tone) * 1.6, 0.0, 0.8);
    let line2 = 1.0 - smoothstep(w2 - f2, w2 + f2, d2);
    // stipple in the mid-tones of the seas
    let dots = step(0.86 - sea * 0.12 * (1.0 - tone), noise3(vec3<f32>(p * 46.0, 1.0)));
    let ink = clamp(max(line1, line2 * 0.9) + dots * 0.25 * sea, 0.0, 1.0);
    var col = mix(u.paper.rgb, u.ink.rgb, ink * 0.92);
    // engraved outline
    let edge = smoothstep(1.0 - u.rim.a - px, 1.0 - px, r);
    col = mix(col, u.rim.rgb, edge * 0.9);
    let a = cover;
    return vec4<f32>(col * a, a);
}
