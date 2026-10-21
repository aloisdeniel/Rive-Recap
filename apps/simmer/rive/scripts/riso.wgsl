// Simmer risograph stock: two static layers generated once on the GPU and laid
// over the whole recap so every cutout, number and control sits on the same
// printed sheet.
//
//   fs_paper  multiply layer: warm uncoated tooth, long pulp fibres, soft
//             mottling and the odd inclusion speck (1.0 = untouched).
//   fs_voids  screen layer: riso "ink starvation", the clustered pin-holes
//             where the drum did not lay ink. Black = untouched, so it only
//             shows on the inked areas (tomato, aubergine, basil) and never
//             greys the paper.

struct U {
    size: vec4<f32>,  // x,y canvas px, z px per point, w seed
    look: vec4<f32>,  // x tooth, y fibres, z specks, w voids
};

@group(0) @binding(0) var<uniform> u: U;

fn hash(p: vec2<f32>) -> f32 {
    var q = fract(p * vec2<f32>(0.1031, 0.1030));
    q = q + dot(q, q.yx + 33.33);
    return fract((q.x + q.y) * q.x);
}

fn vnoise(p: vec2<f32>) -> f32 {
    let i = floor(p);
    let f = fract(p);
    let w = f * f * (3.0 - 2.0 * f);
    let a = hash(i);
    let b = hash(i + vec2<f32>(1.0, 0.0));
    let c = hash(i + vec2<f32>(0.0, 1.0));
    let d = hash(i + vec2<f32>(1.0, 1.0));
    return mix(mix(a, b, w.x), mix(c, d, w.x), w.y);
}

fn fbm(p: vec2<f32>) -> f32 {
    var s = 0.0;
    var a = 0.5;
    var q = p;
    for (var i = 0; i < 4; i = i + 1) {
        s = s + a * vnoise(q);
        q = q * 2.03 + vec2<f32>(17.1, 9.7);
        a = a * 0.5;
    }
    return s;
}

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) uv: vec2<f32>,
};

@vertex
fn vs_main(@builtin(vertex_index) vi: u32) -> VOut {
    let x = f32((vi << 1u) & 2u);
    let y = f32(vi & 2u);
    var o: VOut;
    o.clip = vec4<f32>(x * 2.0 - 1.0, 1.0 - y * 2.0, 0.0, 1.0);
    o.uv = vec2<f32>(x, y);
    return o;
}

@fragment
fn fs_paper(i: VOut) -> @location(0) vec4<f32> {
    let pt = i.uv * u.size.xy / u.size.z;
    let seed = vec2<f32>(u.size.w, u.size.w * 1.7);
    // pulp fibres: anisotropic noise stretched along a shallow diagonal
    let fib = fbm(vec2<f32>(pt.x * 0.05 + pt.y * 0.42, pt.y * 0.06 - pt.x * 0.015) + seed);
    let mottle = fbm(pt * 0.022 + seed * 0.3);
    let tooth = hash(floor(pt * 1.6) + seed) - 0.5;
    var m = 1.0 - u.look.y * (fib - 0.45) - u.look.x * tooth - 0.035 * (mottle - 0.5);
    // inclusions: tiny dark flecks in the pulp
    let cell = floor(pt * 0.45);
    let h = hash(cell + seed * 3.0);
    let spot = smoothstep(0.8, 0.15, length(fract(pt * 0.45) - 0.5) * 2.0);
    m = m - u.look.z * step(0.9972, h) * spot;
    let warm = vec3<f32>(1.0, 0.982, 0.95);
    let col = mix(vec3<f32>(1.0), warm, clamp((1.0 - m) * 5.0, 0.0, 1.0)) * clamp(m, 0.0, 1.0);
    return vec4<f32>(col, 1.0);
}

@fragment
fn fs_voids(i: VOut) -> @location(0) vec4<f32> {
    let pt = i.uv * u.size.xy / u.size.z;
    let seed = vec2<f32>(u.size.w * 2.3, u.size.w);
    // starvation comes in patches (where the drum ran dry) ...
    let dry = smoothstep(0.52, 0.78, fbm(pt * 0.03 + seed));
    // ... made of 1-2 pt pin-holes
    let grain = hash(floor(pt * 1.2) + seed);
    let fine = step(1.0 - (0.025 + 0.16 * dry), grain);
    // a sparse scatter everywhere too, so no inked area looks digital
    let scatter = step(0.994, hash(floor(pt * 0.9) + seed * 5.0));
    let v = clamp(fine * (0.45 + 0.55 * dry) + scatter * 0.6, 0.0, 1.0) * u.look.w;
    let c = vec3<f32>(1.0, 0.97, 0.9) * v;
    return vec4<f32>(c, 1.0);
}
