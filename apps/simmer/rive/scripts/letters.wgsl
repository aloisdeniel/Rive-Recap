// Simmer intro: steam that condenses into the wordmark.
//
// The region is the band of scene 1 between the period ticket and the pot.
// `mask` is the wordmark itself (a small vector artboard rendered into a
// canvas by scripts/letters.luau), so the target is the real glyph outlines,
// not an approximation. Over `progress`:
//   0.00-0.40  a plume rises off the pot lid and widens as it climbs
//   0.25-0.65  it is drawn into the letterforms: the target is the mask seen
//              through a blur and a noise warp that both relax to zero
//   0.70-1.00  the steam letters lift and evaporate through a dot screen,
//              uncovering the inked vector wordmark printed underneath
// Shaded like the handoff steam: paper-white body, tomato halftone shadow,
// an aubergine misregistered ink layer.

struct U {
    frame: vec4<f32>,  // canvas w, h (px), px per point, progress
    geo: vec4<f32>,    // region w, h (pt), lid x, lid y (region pt)
};

@group(0) @binding(0) var<uniform> u: U;
@group(0) @binding(1) var mask: texture_2d<f32>;
@group(0) @binding(2) var smp: sampler;

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

fn hash(p: vec2<f32>) -> f32 {
    var q = fract(vec3<f32>(p.x, p.y, p.x) * 0.1031);
    q = q + dot(q, q.yzx + 33.33);
    return fract((q.x + q.y) * q.z);
}

fn noise(p: vec2<f32>) -> f32 {
    let i = floor(p);
    let f = fract(p);
    let w = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2<f32>(1.0, 0.0)), w.x),
               mix(hash(i + vec2<f32>(0.0, 1.0)), hash(i + vec2<f32>(1.0, 1.0)), w.x), w.y);
}

fn fbm(p0: vec2<f32>) -> f32 {
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

// the wordmark seen through a blur of radius r (points): 13 taps
fn glyphs(pt: vec2<f32>, r: f32) -> f32 {
    let size = u.geo.xy;
    var s = 0.0;
    var wsum = 0.0;
    for (var k = 0; k < 13; k = k + 1) {
        let fk = f32(k);
        let ang = fk * 2.39996;
        let rad = sqrt(fk / 12.0) * r;
        let o = vec2<f32>(cos(ang), sin(ang)) * rad;
        let w = 1.0 - 0.5 * fk / 12.0;
        s = s + textureSampleLevel(mask, smp, (pt + o) / size, 0.0).a * w;
        wsum = wsum + w;
    }
    return s / wsum;
}

fn density(pt: vec2<f32>) -> f32 {
    let p = u.frame.w;
    let t = p * 2.4;
    let lid = u.geo.zw;
    // the rising plume
    let rise = smoothstep(0.0, 0.42, p);
    let front = lid.y - 10.0 - (lid.y + 40.0) * rise;
    let hgt = max(lid.y - pt.y, 0.0);
    let sway = sin(pt.y * 0.035 - t * 4.0) * (8.0 + hgt * 0.12);
    let halfw = 22.0 + hgt * 0.55;
    let col = 1.0 - smoothstep(halfw * 0.35, halfw, abs(pt.x - lid.x - sway));
    let plume = col * smoothstep(front - 10.0, front + 40.0, pt.y) * (1.0 - smoothstep(lid.y - 4.0, lid.y + 8.0, pt.y));
    // condensing into the letters
    let k = smoothstep(0.24, 0.66, p);
    let lift = smoothstep(0.7, 1.0, p);
    let wq = pt / 46.0 + vec2<f32>(0.0, t);
    let warp = (vec2<f32>(fbm(wq), fbm(wq + vec2<f32>(4.7, 2.2))) - 0.5) * (70.0 * (1.0 - k) + 18.0 * lift);
    let tgt = glyphs(pt + warp + vec2<f32>(0.0, 26.0 * lift * lift), 3.0 + 22.0 * (1.0 - k));
    let n = fbm(pt / 30.0 + vec2<f32>(3.0, -t * 1.5));
    var d = mix(plume * (0.75 + 0.5 * n), tgt * 1.25, k);
    // the plume above the letters keeps feeding them until they set
    d = max(d, plume * (1.0 - k) * 0.9);
    // evaporation: thin parts first
    d = d - lift * (0.55 + 1.1 * (1.0 - fbm(pt / 24.0 + vec2<f32>(9.0, -t * 2.0))));
    return d + (n - 0.5) * 0.18;
}

fn halftone(pt: vec2<f32>, amount: f32, period: f32) -> f32 {
    let r = vec2<f32>(pt.x + pt.y, pt.y - pt.x) * 0.70710678;
    let cell = fract(r / period) - 0.5;
    let dist = length(cell) * period;
    let rad = sqrt(clamp(amount, 0.0, 1.0)) * period * 0.62;
    return 1.0 - smoothstep(rad - 0.5, rad + 0.5, dist);
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let pt = i.uv * u.geo.xy;
    let d = density(pt);
    let di = density(pt - vec2<f32>(3.0, 3.5));
    let f = d - 0.5;
    let fi = di - 0.5;
    if (f < -0.28 && fi < 0.0) {
        return vec4<f32>(0.0);
    }
    let e = 2.5;
    let gx = density(pt + vec2<f32>(e, 0.0)) - d;
    let gy = density(pt + vec2<f32>(0.0, e)) - d;
    let nrm = normalize(vec3<f32>(-gx * 7.0, -gy * 7.0, 1.0));
    let lit = dot(nrm, normalize(vec3<f32>(-0.55, -0.7, 0.45)));

    let paper = vec3<f32>(1.0, 0.998, 0.99);
    let body = vec3<f32>(0.99, 0.95, 0.87);
    let tomato = vec3<f32>(0.894, 0.286, 0.196);
    let aub = vec3<f32>(0.282, 0.161, 0.239);

    let core = smoothstep(0.0, 0.03, f);
    let fa = clamp((f + 0.28) / 0.28, 0.0, 1.0);
    let fringe = halftone(pt, fa * fa, 3.4) * step(f, 0.0) * step(-0.28, f);
    let cov = max(core, fringe);
    var c = mix(body, paper, smoothstep(0.5, 0.56, lit));
    let shade = clamp((0.36 - lit) * 2.2, 0.0, 1.0);
    c = mix(c, mix(body, tomato, 0.7), halftone(pt + vec2<f32>(1.1, 0.4), shade * 0.5, 3.2));
    let inkA = smoothstep(0.0, 0.04, fi) * 0.28 * (1.0 - cov);
    return vec4<f32>(c * cov + aub * inkA, clamp(cov + inkA, 0.0, 1.0));
}
