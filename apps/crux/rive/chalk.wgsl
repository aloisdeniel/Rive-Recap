// Crux chalk burst: a procedural, lit chalk-dust cloud with a powdery stippled
// fringe. It blooms from the yank point, occludes the scene cut, then thins out.

struct U {
    // xy: canvas size (px), zw: origin (px)
    frame: vec4<f32>,
    // x: amount 0..1, y: seed, z: drift (px), w: pull direction (+1 up / -1 down)
    p: vec4<f32>,
    chalk: vec4<f32>,
    shade: vec4<f32>,
    // x: clear 0..1 (dissolve), y: canvas px per point
    q: vec4<f32>,
};

@group(0) @binding(0) var<uniform> u: U;

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) uv: vec2<f32>,
};

// One triangle that covers the canvas.
@vertex
fn vs_main(@builtin(vertex_index) idx: u32) -> VOut {
    var o: VOut;
    let x = f32((idx << 1u) & 2u);
    let y = f32(idx & 2u);
    o.clip = vec4<f32>(x * 2.0 - 1.0, 1.0 - y * 2.0, 0.0, 1.0);
    o.uv = vec2<f32>(x, y);
    return o;
}

fn hash2(p: vec2<f32>) -> f32 {
    var q = fract(vec3<f32>(p.x, p.y, p.x) * 0.1031);
    q = q + dot(q, q.yzx + 33.33);
    return fract((q.x + q.y) * q.z);
}

fn noise(p: vec2<f32>) -> f32 {
    let i = floor(p);
    let f = fract(p);
    let w = f * f * (3.0 - 2.0 * f);
    let a = hash2(i);
    let b = hash2(i + vec2<f32>(1.0, 0.0));
    let c = hash2(i + vec2<f32>(0.0, 1.0));
    let d = hash2(i + vec2<f32>(1.0, 1.0));
    return mix(mix(a, b, w.x), mix(c, d, w.x), w.y);
}

fn fbm3(p0: vec2<f32>) -> f32 {
    var p = p0;
    var s = 0.0;
    var a = 0.5;
    for (var k = 0; k < 3; k = k + 1) {
        s = s + a * noise(p);
        p = p * 2.07 + vec2<f32>(5.3, 1.9);
        a = a * 0.5;
    }
    return s;
}

// Low-frequency billow field in points: positive inside the cloud.
fn billow(pt: vec2<f32>) -> f32 {
    let amt = u.p.x;
    let size = u.frame.xy / u.q.y;
    let rel = (pt - u.frame.zw) / length(size);
    let pull = vec2<f32>(0.0, u.p.z * u.p.w);
    let q = (pt + pull) / vec2<f32>(130.0, 150.0) + u.p.y * 3.7;
    let warp = vec2<f32>(fbm3(q * 0.7 + 4.0), fbm3(q * 0.7 + 9.0));
    let n = fbm3(q + warp * 0.8);
    let r = length(vec2<f32>(rel.x * 1.2, rel.y));
    // `clear` eats the thin parts first, so the cloud thins into drifting clumps
    return amt * 2.1 - r * 2.0 + (n - 0.5) * 1.0 - u.q.x * (1.35 - n * 0.9);
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let pt = i.uv * u.frame.xy / u.q.y;
    let b = billow(pt);
    let f = b + (noise(pt / 7.0 + u.p.y * 11.0) - 0.5) * 0.05;
    // stippled, powdery fringe: coverage dithered by grain instead of a clean edge
    let fringe = smoothstep(-0.07, 0.02, f);
    let dither = hash2(floor(pt / 1.5) + u.p.y * 17.0);
    let alpha = max(smoothstep(0.0, 0.01, f), step(dither, fringe * fringe) * 0.92);
    // light the billows from the top-left with the low-frequency gradient
    let e = 4.0;
    let gx = billow(pt + vec2<f32>(e, 0.0)) - b;
    let gy = billow(pt + vec2<f32>(0.0, e)) - b;
    let nrm = normalize(vec3<f32>(-gx * 60.0, -gy * 60.0, 1.0));
    let lit = clamp(dot(nrm, normalize(vec3<f32>(-0.55, -0.7, 0.55))), 0.0, 1.0);
    // a printed shadow band under every billow edge, flat chalk inside
    let edge = 1.0 - smoothstep(0.0, 0.16, f);
    let shadeAmt = clamp(edge * (1.0 - lit) * 1.6, 0.0, 1.0);
    var c = mix(u.chalk.rgb, u.shade.rgb, shadeAmt);
    c = mix(c, vec3<f32>(1.0, 1.0, 1.0), clamp((lit - 0.75) * 2.0, 0.0, 1.0) * edge * 0.6);
    // mineral grain
    let g = hash2(floor(pt / 1.5) + u.p.y * 91.0);
    c = mix(c, u.shade.rgb * 0.7, step(0.988, g) * 0.8);
    // dust motes beyond the edge
    let mote = step(0.993, hash2(floor(pt / 2.0) + u.p.y * 41.0)) * smoothstep(-0.3, 0.0, f) * (1.0 - alpha);
    let a = max(alpha, mote * 0.85);
    let col = mix(u.chalk.rgb, c, alpha);
    return vec4<f32>(col * a, a);
}
