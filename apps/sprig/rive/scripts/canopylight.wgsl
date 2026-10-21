// Sprig paper + canopy light.
//
// fs_paper: a static paper stock (long soft fibres, fine tooth, pulp mottling, a gentle
// vignette), centred on mid grey so it can be laid over every scene in soft-light.
// fs_light: light falling through a canopy of leaves (komorebi): soft dappled spots,
// rounded like light through gaps between leaves, drifting and swaying in a breeze.
// Also centred on mid grey: bright patches lift, leaf shadows darken (overlay).

struct U {
    a: vec4<f32>, // width, height (px), time (s), seed
    b: vec4<f32>, // light direction x, y, spot scale, sway
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

fn fbm(p0: vec2<f32>) -> f32 {
    var p = p0;
    var a = 0.5;
    var s = 0.0;
    for (var i = 0; i < 4; i = i + 1) {
        s = s + a * vnoise(p);
        p = vec2<f32>(p.x * 1.62 - p.y * 1.18, p.x * 1.18 + p.y * 1.62) + 7.3;
        a = a * 0.5;
    }
    return s;
}

fn rot(p: vec2<f32>, a: f32) -> vec2<f32> {
    let c = cos(a); let s = sin(a);
    return vec2<f32>(p.x * c - p.y * s, p.x * s + p.y * c);
}

@fragment
fn fs_paper(i: VOut) -> @location(0) vec4<f32> {
    // positions in artboard units (the canvas covers the whole artboard)
    let p = i.uv * vec2<f32>(390.0, 844.0) + u.a.w * 13.0;
    // fibres: stretched noise in three orientations, the strongest wins
    var fib = 0.0;
    for (var k = 0; k < 3; k = k + 1) {
        let q = rot(p, f32(k) * 1.05 + 0.3) * vec2<f32>(0.07, 0.9);
        fib = max(fib, smoothstep(0.62, 0.95, vnoise(q + f32(k) * 17.0)));
    }
    let tooth = hash2(floor(p * 1.5)) - 0.5;
    let mott = fbm(p * 0.012) - 0.5;
    let fleck = step(0.9965, hash2(floor(p * 0.5) + 3.0));
    // a gentle vignette so the paper reads as a lit sheet
    let c = i.uv - vec2<f32>(0.5, 0.46);
    let vig = smoothstep(0.35, 0.95, length(c * vec2<f32>(1.0, 0.62)) * 1.25);
    let v = 0.5 + fib * 0.07 + tooth * 0.11 + mott * 0.14 - fleck * 0.12 - vig * 0.16;
    return vec4<f32>(v, v, v, 1.0);
}

@fragment
fn fs_light(i: VOut) -> @location(0) vec4<f32> {
    let t = u.a.z;
    let p = i.uv * vec2<f32>(390.0, 844.0);
    // the canopy: leaf clusters from warped noise, swaying slowly in a breeze
    let sway = vec2<f32>(sin(t * 0.37) * 10.0 + sin(t * 0.91 + 1.3) * 4.0,
                         cos(t * 0.29) * 7.0) * u.b.w;
    let q = (p + sway) * u.b.z / 44.0;
    let warp = vec2<f32>(fbm(q * 0.6 + vec2<f32>(t * 0.04, 0.0)), fbm(q * 0.6 + 5.2 - vec2<f32>(0.0, t * 0.03)));
    let leaves = fbm(q + warp * 1.3);
    // gaps between leaves let light through as soft round flecks (pinhole images of the sun);
    // only the gaps lift, the canopy itself casts a light shade
    let fleck = smoothstep(0.62, 0.7, leaves);
    let shade = smoothstep(0.5, 0.3, leaves);
    // light falls from the upper left: flecks are brightest there and fade down the page
    let dir = normalize(u.b.xy);
    let along = dot(i.uv - 0.5, dir);
    let shaft = smoothstep(0.75, -0.55, along);
    let flick = 0.9 + 0.1 * sin(t * 1.7 + leaves * 9.0);
    let v = 0.5 + fleck * shaft * flick * 0.36 - shade * 0.05;
    return vec4<f32>(v, v, v, 1.0);
}
