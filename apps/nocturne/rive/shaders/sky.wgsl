// Nocturne sky: a procedural, decorative night sky (never a real sky map).
//
// Three parallax layers of point stars (hash grid, power-law brightness, ice /
// white / blue / rare amber colours, four-point diffraction spikes on the few
// bright ones), a Milky Way band built from warped value noise with dark dust
// lanes and a warm amber core, and a faint haze of unresolved stars inside the
// band. The camera (offset, scale, rotation) is keyed per scene pose, so every
// scene opens on a different scale and angle of the same sky; the near layer
// moves more than the far one.
//
// mode 0: the full-stage background (opaque, with the midnight gradient).
// mode 1: a luminous disk (premultiplied alpha, soft lens edge, vignette).
//
// Twinkle is a gentle brightness modulation (at most +-30 %, 0.2-0.7 Hz), never
// a flash; under reduced motion or pause the script stops `time`, which freezes it.

struct U {
    frame: vec4<f32>,   // canvas w px, canvas h px, px per point, time (s)
    origin: vec4<f32>,  // canvas top-left in points (x, y), mode, seed
    view: vec4<f32>,    // camera offset x, y (pt), scale, rotation (rad)
    look: vec4<f32>,    // star density, band strength, twinkle, band angle (rad)
    disk: vec4<f32>,    // centre x, y (pt), radius (pt), edge softness (pt)
    extra: vec4<f32>,   // band width (pt), warm amount, vignette, exposure
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

fn hash21(p: vec2<f32>) -> f32 {
    var q = fract(vec3<f32>(p.x, p.y, p.x) * 0.1031);
    q = q + dot(q, q.yzx + 33.33);
    return fract((q.x + q.y) * q.z);
}

fn hash24(p: vec2<f32>) -> vec4<f32> {
    var q = fract(vec4<f32>(p.x, p.y, p.x, p.y) * vec4<f32>(0.1031, 0.1030, 0.0973, 0.1099));
    q = q + dot(q, q.wzxy + 33.33);
    return fract((q.xxyz + q.yzzw) * q.zywx);
}

fn vnoise(p: vec2<f32>) -> f32 {
    let i = floor(p);
    let f = fract(p);
    let w = f * f * (3.0 - 2.0 * f);
    let a = hash21(i);
    let b = hash21(i + vec2<f32>(1.0, 0.0));
    let c = hash21(i + vec2<f32>(0.0, 1.0));
    let d = hash21(i + vec2<f32>(1.0, 1.0));
    return mix(mix(a, b, w.x), mix(c, d, w.x), w.y);
}

fn fbm(p0: vec2<f32>) -> f32 {
    var p = p0;
    var s = 0.0;
    var a = 0.5;
    for (var k = 0; k < 4; k = k + 1) {
        s = s + a * vnoise(p);
        p = mat2x2<f32>(1.6, 1.2, -1.2, 1.6) * p + vec2<f32>(3.1, 1.7);
        a = a * 0.5;
    }
    return s;
}

fn rot(a: f32) -> mat2x2<f32> {
    let c = cos(a);
    let s = sin(a);
    return mat2x2<f32>(c, s, -s, c);
}

const ICE = vec3<f32>(0.737, 0.894, 0.910);
const WHITE = vec3<f32>(0.96, 0.98, 0.99);
const BLUE = vec3<f32>(0.376, 0.545, 1.0);
const AMBER = vec3<f32>(0.969, 0.745, 0.384);

// One star per cell. `sc` is in sky points; `cell` the cell size in points.
fn starLayer(sc: vec2<f32>, cell: f32, density: f32, gain: f32, seed: f32, px: f32, spikes: f32) -> vec3<f32> {
    let g = floor(sc / cell);
    let h = hash24(g + vec2<f32>(seed * 17.0, seed * 31.0));
    if (h.x > density) {
        return vec3<f32>(0.0);
    }
    let c = (vec2<f32>(0.22, 0.22) + 0.56 * h.yz) * cell;
    let d = sc - g * cell - c;
    let mag = pow(h.w, 5.0);
    let rc = 0.42 + 1.5 * mag;
    let sig = max(rc * 0.62, 0.55 * px);
    let r2 = dot(d, d);
    var lum = exp(-r2 / (2.0 * sig * sig)) * (0.35 + 0.9 * mag);
    lum = lum + exp(-sqrt(r2) / (rc * 2.6 + px)) * 0.22 * mag;
    if (mag > 0.42 && spikes > 0.0) {
        let len = cell * 0.28 * mag;
        let w = max(0.32, 0.6 * px);
        let sx = exp(-abs(d.y) / w) * exp(-abs(d.x) / len);
        let sy = exp(-abs(d.x) / w) * exp(-abs(d.y) / len);
        lum = lum + (sx + sy) * 0.55 * (mag - 0.3) * spikes;
    }
    let tw = 1.0 + u.look.z * 0.30 * sin(u.frame.w * (1.3 + 3.0 * h.y) + h.z * 40.0) * (1.0 - 0.6 * mag);
    let hc = fract(h.y * 7.31 + h.z * 3.17);
    var col = WHITE;
    if (hc < 0.06) {
        col = AMBER;
    } else if (hc < 0.30) {
        col = mix(ICE, BLUE, 0.55);
    } else if (hc < 0.62) {
        col = ICE;
    }
    return col * lum * tw * gain;
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let res = u.frame.z;
    let px = 1.0 / res;                                  // one pixel in points
    let pt = u.origin.xy + i.uv * u.frame.xy / res;      // this pixel, in points
    let mode = u.origin.z;
    let seed = u.origin.w;
    var centre = vec2<f32>(195.0, 422.0);
    if (mode > 0.5) {
        centre = u.disk.xy;
    }
    let rel = pt - centre;
    let sc0 = max(u.view.z, 0.05);

    // ---- sky camera: three depths
    let far = rot(u.view.w * 0.6) * rel / (1.0 + (sc0 - 1.0) * 0.5) + u.view.xy * 0.35;
    let mid = rot(u.view.w * 0.85) * rel / (1.0 + (sc0 - 1.0) * 0.8) + u.view.xy * 0.7;
    let near = rot(u.view.w) * rel / sc0 + u.view.xy;

    // ---- Milky Way band (mid depth)
    let b = rot(u.look.w) * mid;
    let bw = max(u.extra.x, 10.0);
    let across = b.y / bw;
    let core = exp(-across * across * 1.5);
    let q = b * vec2<f32>(0.0065, 0.013) * (180.0 / bw) + seed;
    let warp = vec2<f32>(fbm(q * 1.3 + 5.2), fbm(q * 1.3 + 1.7));
    let cloud = fbm(q + warp * 0.9);
    let dust = smoothstep(0.42, 0.72, fbm(q * 2.3 + warp * 1.4 + 9.0)) * exp(-across * across * 3.2);
    var band = core * (0.35 + 1.25 * cloud * cloud) * (1.0 - 0.85 * dust);
    band = band * u.look.y;
    let warmMask = exp(-pow((b.x + bw * 1.3) / (bw * 2.6), 2.0)) * core;
    var bandCol = mix(BLUE * 0.55, ICE, clamp(core * cloud * 1.2, 0.0, 1.0));
    bandCol = mix(bandCol, AMBER, clamp(warmMask * u.extra.y * (0.4 + cloud), 0.0, 0.85));

    // ---- stars: sparse far dust, a mid layer, a few bright near stars with spikes
    let dens = u.look.x;
    var stars = starLayer(far, 12.0, dens * 0.22, 0.5, seed + 1.0, px, 0.0);
    stars = stars + starLayer(mid, 22.0, dens * 0.35, 0.85, seed + 2.0, px, 0.0);
    stars = stars + starLayer(near, 52.0, dens * 0.5, 1.2, seed + 3.0, px, 1.0);
    // unresolved haze: tiny stars only inside the band (much fainter on the background)
    let hazeGain = select(0.16, 0.45, mode > 0.5);
    let haze = starLayer(mid * 1.7, 4.2, clamp(core * 0.8 * u.look.y, 0.0, 0.8), hazeGain * min(u.look.y, 1.4), seed + 4.0, px, 0.0);
    stars = stars + haze;

    var col = vec3<f32>(0.0);
    var alpha = 1.0;
    if (mode < 0.5) {
        // midnight gradient + a faint ambient nebula glow behind the hero zone
        let t = clamp(pt.y / 844.0, 0.0, 1.0);
        let top = vec3<f32>(0.043, 0.110, 0.200);
        let midc = vec3<f32>(0.031, 0.082, 0.149);
        let bot = vec3<f32>(0.020, 0.051, 0.094);
        col = mix(mix(top, midc, smoothstep(0.0, 0.55, t)), bot, smoothstep(0.5, 1.0, t));
        let gl = exp(-dot((pt - vec2<f32>(195.0, 300.0)) / vec2<f32>(250.0, 190.0), (pt - vec2<f32>(195.0, 300.0)) / vec2<f32>(250.0, 190.0)));
        col = col + BLUE * 0.055 * gl;
        col = col + bandCol * band * 0.16;
        // keep the copy zone calm: fewer, dimmer stars behind the text block
        let calm = 1.0 - 0.55 * smoothstep(470.0, 560.0, pt.y) * (1.0 - smoothstep(740.0, 800.0, pt.y));
        col = col + stars * calm * u.extra.w;
    } else {
        let r = length(rel);
        let R = u.disk.z;
        alpha = 1.0 - smoothstep(R - max(u.disk.w, px), R, r);
        let rr = clamp(r / R, 0.0, 1.0);
        let base = mix(vec3<f32>(0.075, 0.165, 0.30), vec3<f32>(0.030, 0.075, 0.150), rr);
        col = base + bandCol * band * 0.85 + stars * u.extra.w;
        // lens vignette and a cool chromatic rim
        col = col * (1.0 - u.extra.z * pow(rr, 3.0));
        let rim = exp(-pow((R - r) / (2.2 + R * 0.015), 2.0));
        col = col + vec3<f32>(0.20, 0.32, 0.65) * rim * 0.55;
        col = col + vec3<f32>(0.55, 0.30, 0.10) * exp(-pow((R - 3.0 - r) / 1.6, 2.0)) * 0.10;
    }
    col = col / (1.0 + col * 0.35);       // soft shoulder so dense stars never clip harshly
    return vec4<f32>(col * alpha, alpha);
}
