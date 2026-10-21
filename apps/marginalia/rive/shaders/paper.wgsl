// Marginalia paper: laid paper texture generated once on the GPU and
// multiplied over the whole recap. Fine fibre grain, faint chain and laid
// lines (as in hand-made book paper), sparse specks, and a soft worn edge.
// Output is a multiply layer: 1.0 leaves the artwork untouched.

struct U {
    size: vec4<f32>,  // x,y canvas px, z px per point, w seed
    look: vec4<f32>,  // x grain, y laid lines, z specks, w edge wear
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
    var corners = array<vec2<f32>, 6>(
        vec2<f32>(0.0, 0.0), vec2<f32>(1.0, 0.0), vec2<f32>(0.0, 1.0),
        vec2<f32>(0.0, 1.0), vec2<f32>(1.0, 0.0), vec2<f32>(1.0, 1.0));
    let c = corners[vi];
    var o: VOut;
    o.clip = vec4<f32>(c.x * 2.0 - 1.0, 1.0 - c.y * 2.0, 0.0, 1.0);
    o.uv = c;
    return o;
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let pt = i.uv * u.size.xy / u.size.z;          // position in points
    let seed = vec2<f32>(u.size.w, u.size.w * 1.7);
    // fibres: anisotropic noise, long along a gentle diagonal
    let fib = fbm(vec2<f32>(pt.x * 0.06 + pt.y * 0.55, pt.y * 0.07 - pt.x * 0.02) + seed);
    let mottle = fbm(pt * 0.035 + seed * 0.3);
    let tooth = vnoise(pt * 1.4 + seed) - 0.5;
    var g = (fib - 0.5) * 0.9 + (mottle - 0.5) * 1.1 + tooth * 0.5;
    // laid lines (fine, horizontal) and chain lines (sparse, vertical)
    let laid = 0.5 + 0.5 * sin(pt.y * 2.4);
    let chain = smoothstep(0.92, 1.0, 0.5 + 0.5 * cos(pt.x * 0.25));
    var m = 1.0 - u.look.x * g - u.look.y * (laid * 0.35 + chain * 0.65);
    // sparse specks (inclusions in the pulp)
    let cell = floor(pt * 0.5);
    let h = hash(cell + seed);
    let spot = smoothstep(0.9, 0.2, length(fract(pt * 0.5) - 0.5) * 2.0);
    m = m - u.look.z * step(0.9965, h) * spot;
    // worn edge: a warm, slightly darker margin
    let e = min(min(i.uv.x, 1.0 - i.uv.x) * u.size.x, min(i.uv.y, 1.0 - i.uv.y) * u.size.y) / u.size.z;
    let wear = 1.0 - smoothstep(0.0, 26.0, e + (mottle - 0.5) * 14.0);
    m = m * (1.0 - u.look.w * wear);
    let warm = vec3<f32>(1.0, 0.985, 0.955);
    let col = mix(vec3<f32>(1.0), warm, clamp((1.0 - m) * 6.0, 0.0, 1.0)) * m;
    return vec4<f32>(col, 1.0);
}
