// Matte mineral grain: a static, procedural paper-and-clay texture laid over the
// backgrounds (soft-light, low opacity) so flat colour fields read as a fired
// surface. Rendered once into a canvas; drawing it costs one image per frame.

struct U {
    a: vec4<f32>, // width, height (points: the pattern is resolution independent), seed, unused
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

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let p = i.uv * u.a.xy + u.a.z;
    // fine tooth, soft mottling, and a few darker mineral specks; centred on mid grey
    let tooth = hash2(floor(p)) - 0.5;
    let mott = vnoise(p * 0.018) - 0.5 + (vnoise(p * 0.06 + 3.1) - 0.5) * 0.5;
    let fr = fract(p * 0.09) - 0.5;
    let speck = step(0.992, hash2(floor(p * 0.09) + 7.0)) * (1.0 - smoothstep(0.12, 0.3, length(fr)));
    let v = 0.5 + tooth * 0.2 + mott * 0.12 - speck * 0.18;
    return vec4<f32>(v, v, v, 1.0);
}
