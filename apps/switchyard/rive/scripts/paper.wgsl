// Switchyard print stock: the whole recap is laid over one sheet of uncoated
// poster paper - a fine tooth, long soft fibres, faint cloudy mottling and a few
// flecks - rendered once into a canvas around mid grey and drawn on top in
// soft-light, so flat ink fields read as printed rather than as screen colour.

struct U {
    a: vec4<f32>, // x, y: canvas size in pixels; z: pixels per point; w: seed
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
    // work in points so the texture has the same scale on every screen density
    let pt = i.uv * u.a.xy / max(u.a.z, 1.0) + u.a.w;
    let px = i.uv * u.a.xy;
    // fine tooth (per device pixel, very light)
    let tooth = hash2(floor(px)) - 0.5;
    // long fibres: anisotropic noise stretched along a slight diagonal
    let fp = vec2<f32>(pt.x * 0.9 + pt.y * 0.25, pt.y * 0.12 - pt.x * 0.03);
    let fib = vnoise(fp * vec2<f32>(0.22, 2.6)) - 0.5;
    // cloudy formation of the sheet
    let cloud = (vnoise(pt * 0.012) - 0.5) + (vnoise(pt * 0.035 + 7.3) - 0.5) * 0.5;
    // sparse flecks
    let cell = floor(pt * 0.11);
    let fr = fract(pt * 0.11) - 0.5;
    let fleck = step(0.994, hash2(cell + 3.0)) * (1.0 - smoothstep(0.08, 0.22, length(fr)));
    let v = 0.5 + tooth * 0.07 + fib * 0.07 + cloud * 0.09 - fleck * 0.22;
    return vec4<f32>(v, v, v, 1.0);
}
