// Kiln chamber: the inside of the arch in scene 5, as one fragment shader.
//
// Firebrick courses heat from the floor up (dull red -> orange -> yellow-white,
// with rising heat haze and ember flicker), then cool from the crown down into
// the six bands of the ceramic palette. One input drives it all:
//   fire 0 = cold, 1 = full heat, 2 = cooled into the palette.

struct U {
    a: vec4<f32>, // width, height (local units), fire, time
    b: vec4<f32>, // still (1 = no haze motion), unused x3
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

fn fbm(p: vec2<f32>) -> f32 {
    return vnoise(p) * 0.55 + vnoise(p * 2.1 + 7.3) * 0.3 + vnoise(p * 4.3 + 1.7) * 0.15;
}

fn blackbody(t: f32) -> vec3<f32> {
    let k = clamp(t, 0.0, 1.0);
    var c = mix(vec3<f32>(0.10, 0.06, 0.05), vec3<f32>(0.62, 0.10, 0.03), smoothstep(0.0, 0.3, k));
    c = mix(c, vec3<f32>(0.95, 0.36, 0.08), smoothstep(0.25, 0.6, k));
    c = mix(c, vec3<f32>(1.0, 0.70, 0.36), smoothstep(0.6, 0.9, k));
    c = mix(c, vec3<f32>(1.0, 0.92, 0.74), smoothstep(0.9, 1.0, k));
    return c;
}

fn palette(i: i32) -> vec3<f32> {
    // porcelain, sand, blush, clay, cobalt light, ultramarine (Kiln's ceramic palette)
    var P = array<vec3<f32>, 6>(
        vec3<f32>(0.949, 0.925, 0.886),
        vec3<f32>(0.890, 0.804, 0.706),
        vec3<f32>(0.788, 0.604, 0.494),
        vec3<f32>(0.737, 0.439, 0.341),
        vec3<f32>(0.361, 0.424, 0.722),
        vec3<f32>(0.208, 0.278, 0.635));
    return P[clamp(i, 0, 5)];
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let W = u.a.x;
    let H = u.a.y;
    let fire = u.a.z;
    let t = u.a.w;
    let p = vec2<f32>(i.uv.x * W, i.uv.y * H);
    let yb = 1.0 - i.uv.y; // 0 floor .. 1 crown

    // firebrick courses: 13 courses, running bond, mortar joints
    let ch = H / 13.0;
    let row = floor(p.y / ch);
    let bw = 58.0;
    let off = select(0.0, bw * 0.5, (row % 2.0) > 0.5);
    let col = floor((p.x + off) / bw);
    let lx = fract((p.x + off) / bw) * bw;
    let ly = fract(p.y / ch) * ch;
    let mortar = 1.0 - smoothstep(0.6, 1.8, min(min(lx, bw - lx), min(ly, ch - ly)));
    let brickVar = hash2(vec2<f32>(col, row)) - 0.5;
    let grain = fbm(p * 0.09 + vec2<f32>(col * 3.1, row * 1.7)) - 0.5;

    // heating rises from the floor; cooling sweeps from the crown down
    let heatF = clamp(fire * 1.35 - (yb * 0.35), 0.0, 1.0);
    let coolF = clamp((fire - 1.0) * 1.6 - (1.0 - yb) * 0.6, 0.0, 1.0);
    var heat = heatF * (1.0 - coolF);

    // heat haze and ember flicker: turbulent, rising
    let still = u.b.x;
    let tt = t * (1.0 - still);
    let haze = fbm(vec2<f32>(p.x * 0.025, p.y * 0.02 + tt * 0.9));
    let flame = fbm(vec2<f32>(p.x * 0.04 + sin(tt * 0.7) * 0.3, p.y * 0.035 + tt * 1.6));
    heat = clamp(heat * (0.62 + 0.5 * haze) + heat * (1.0 - yb) * 0.3 * flame, 0.0, 1.1);

    // cold brick: dark kiln interior
    let cold = vec3<f32>(0.16, 0.13, 0.12) * (1.0 + brickVar * 0.25 + grain * 0.2);
    // peak heat stays an orange-yellow glow (a kiln at temperature, not a white screen)
    var c = mix(cold, blackbody(heat * 0.78 + brickVar * 0.06), smoothstep(0.0, 0.25, heat + heatF * 0.3));
    c = c * (1.0 + grain * 0.12 * (1.0 - heat));

    // cooled: the courses settle into the six palette bands (two courses each, crown first)
    let band = i32(clamp(floor(i.uv.y * 6.0), 0.0, 5.0));
    let pc = palette(band) * (1.0 + brickVar * 0.06 + grain * 0.08);
    c = mix(c, pc, coolF);

    // mortar, chamber vignette and floor glow
    c = mix(c, c * mix(mix(0.5, 0.38, heatF), 0.82, coolF), mortar);
    let vx = abs(i.uv.x - 0.5) * 2.0;
    c = c * (1.0 - 0.32 * vx * vx) * mix(0.82, 1.0, smoothstep(0.0, 0.25, i.uv.y));
    c = c + vec3<f32>(1.0, 0.45, 0.12) * heatF * (1.0 - coolF) * pow(1.0 - yb, 3.0) * 0.25;
    return vec4<f32>(c, 1.0);
}
