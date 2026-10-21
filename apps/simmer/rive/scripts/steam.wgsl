// Simmer signature steam: a ribbon of steam leaves the pot, curls through the
// layout and billows until it veils the cut, then evaporates through a
// risograph dot screen to reveal the next scene.
//
// The ribbon is a polyline (path[], built by scripts/steam.luau) whose points
// carry their own radius and opacity, so it can be born thin at the pot,
// thicken as it ages and travel along a curl. Every pixel finds its nearest
// segment through a domain-warped position (billows), and is shaded like a
// risograph print: paper-white highlights, a cream body, shadow printed as a
// 45-degree tomato halftone, an aubergine misregistered ink layer offset
// under it (the same offset every cutout in the recap has) and the tomato
// ink thread drawn along the ribbon while it is still young. As it clears,
// the fringe breaks into halftone dots that shrink away.

const N: i32 = 24;

struct U {
    frame: vec4<f32>,   // canvas w, h (px), px per point, time (s)
    p: vec4<f32>,       // progress 0..1, warp, seed, clear 0..1
    q: vec4<f32>,       // thread opacity, curl centre x, y, swirl
    path: array<vec4<f32>, 24>,  // x, y (pt), radius (pt), opacity
};

@group(0) @binding(0) var<uniform> u: U;

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
    for (var k = 0; k < 4; k = k + 1) {
        s = s + a * noise(p);
        p = p * 2.03 + vec2<f32>(5.3, 1.9);
        a = a * 0.5;
    }
    return s;
}

fn fbm3(p0: vec2<f32>) -> f32 {
    var p = p0;
    var s = 0.0;
    var a = 0.55;
    for (var k = 0; k < 3; k = k + 1) {
        s = s + a * noise(p);
        p = p * 2.1 + vec2<f32>(3.7, 8.1);
        a = a * 0.45;
    }
    return s;
}

// The billowed position: a slow domain warp that flows upward, plus a swirl
// around the curl centre that tightens as the steam ages.
fn warped(pt: vec2<f32>) -> vec2<f32> {
    let t = u.frame.w;
    let s = u.p.z;
    let c = u.q.yz;
    let rel = pt - c;
    let r = length(rel);
    let ang = u.q.w * exp(-r / 230.0);
    let cs = cos(ang);
    let sn = sin(ang);
    let sw = c + vec2<f32>(rel.x * cs - rel.y * sn, rel.x * sn + rel.y * cs);
    let q = sw / 150.0 + vec2<f32>(s * 3.1, s * 1.7 + t * 0.45);
    let w = vec2<f32>(fbm(q), fbm(q + vec2<f32>(7.3, 2.9))) - 0.5;
    return sw + w * u.p.y;
}

struct Hit {
    f: f32,      // normalised field: > 0 inside the steam
    d: f32,      // distance to the ribbon's spine (pt)
    a: f32,      // opacity of the nearest point
};

fn ribbon(pw: vec2<f32>) -> Hit {
    var best = -4.0;
    var dmin = 1e5;
    var amin = 0.0;
    for (var i = 0; i < N - 1; i = i + 1) {
        let a = u.path[i];
        let b = u.path[i + 1];
        let ab = b.xy - a.xy;
        let h = clamp(dot(pw - a.xy, ab) / max(dot(ab, ab), 1e-3), 0.0, 1.0);
        let d = length(pw - a.xy - ab * h);
        let r = mix(a.z, b.z, h);
        let o = mix(a.w, b.w, h);
        if (r > 0.25 && o > 0.001) {
            let f = (r - d) / max(r, 6.0) - (1.0 - o) * 1.2;
            if (f > best) {
                best = f;
            }
            if (d < dmin) {
                dmin = d;
                amin = o;
            }
        }
    }
    return Hit(best, dmin, amin);
}

fn field(pt: vec2<f32>) -> f32 {
    let pw = warped(pt);
    let h = ribbon(pw);
    // billows on the edge, and the dissolve: thin parts go first
    let t = u.frame.w;
    let n = fbm3(pt / 95.0 + vec2<f32>(u.p.z * 9.0, -t * 0.7));
    let holes = fbm3(pt / 120.0 + vec2<f32>(u.p.z * 4.0 + 3.0, -t * 0.35));
    return h.f + (n - 0.5) * 0.7 - u.p.w * (0.35 + 1.25 * (1.0 - holes));
}

// ridged (billowy) noise for the cumulus lobes
fn puffs(pt: vec2<f32>) -> f32 {
    let t = u.frame.w;
    let q = pt / 120.0 + vec2<f32>(u.p.z * 2.0, t * 0.5 + u.p.z);
    let n1 = smoothstep(0.25, 0.85, noise(q));
    let n2 = smoothstep(0.3, 0.9, noise(q * 2.3 + vec2<f32>(4.1, 1.3)));
    return n1 * 0.72 + n2 * 0.28;
}

fn halftone(pt: vec2<f32>, amount: f32, period: f32) -> f32 {
    // 45-degree screen; dot area grows with the amount, like a riso screen
    let r = vec2<f32>(pt.x + pt.y, pt.y - pt.x) * 0.70710678;
    let cell = fract(r / period) - 0.5;
    let dist = length(cell) * period;
    let rad = sqrt(clamp(amount, 0.0, 1.0)) * period * 0.62;
    return 1.0 - smoothstep(rad - 0.55, rad + 0.55, dist);
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let pt = i.uv * u.frame.xy / u.frame.z;
    let f = field(pt);
    // misregistered ink layer: the same field, printed 4 pt down-right
    let fi = field(pt - vec2<f32>(4.0, 4.5));
    if (f < -0.22 && fi < 0.0) {
        return vec4<f32>(0.0);
    }
    // relief for the lighting: the field's own falloff plus puffy cumulus
    // lobes (ridged noise) that drift up with the steam
    let e = 4.0;
    let fx = field(pt + vec2<f32>(e, 0.0));
    let fy = field(pt + vec2<f32>(0.0, e));
    let b0 = puffs(pt);
    let bx = puffs(pt + vec2<f32>(e, 0.0));
    let by = puffs(pt + vec2<f32>(0.0, e));
    let hz = smoothstep(-0.05, 0.45, f);
    let gx = (smoothstep(-0.05, 0.45, fx) - hz) * 1.4 + (bx - b0) * 1.1 * hz;
    let gy = (smoothstep(-0.05, 0.45, fy) - hz) * 1.4 + (by - b0) * 1.1 * hz;
    let nrm = normalize(vec3<f32>(-gx * 9.0, -gy * 9.0, 1.0));
    let lit = dot(nrm, normalize(vec3<f32>(-0.55, -0.7, 0.45))) + (b0 - 0.5) * 0.25;

    let paper = vec3<f32>(1.0, 0.998, 0.99);
    let body = vec3<f32>(0.985, 0.94, 0.85);
    let tomato = vec3<f32>(0.894, 0.286, 0.196);
    let aub = vec3<f32>(0.282, 0.161, 0.239);

    // solid core and a halftone fringe that shrinks to nothing as it clears
    let core = smoothstep(0.0, 0.02, f);
    let fringeAmt = clamp((f + 0.2) / 0.2, 0.0, 1.0);
    let fringe = halftone(pt, fringeAmt * fringeAmt, 4.2) * step(f, 0.0) * step(-0.2, f);
    let cov = max(core, fringe);

    // posterised riso shading: paper-white lit lobes, a cream mid tone, and
    // the shadow side printed as a tomato dot screen
    var col = body;
    col = mix(col, paper, smoothstep(0.5, 0.56, lit));
    let shade = clamp((0.32 - lit) * 2.2, 0.0, 1.0);
    let dots = halftone(pt + vec2<f32>(1.3, 0.7), shade * 0.5, 3.8);
    col = mix(col, mix(body, tomato, 0.7), dots);

    // the ink thread along the spine while the ribbon is young
    let h = ribbon(warped(pt));
    let thread = (1.0 - smoothstep(1.1, 2.0, h.d)) * u.q.x * h.a;
    col = mix(col, tomato, thread * core);

    // ink layer under the steam (misregistration), 30% aubergine
    let inkA = smoothstep(0.0, 0.03, fi) * 0.3 * (1.0 - cov);
    let a = clamp(cov + inkA, 0.0, 1.0);
    let rgb = col * cov + aub * inkA;
    return vec4<f32>(rgb, a);
}
