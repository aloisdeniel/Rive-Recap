// Marginalia page turn: a paper leaf rolled over a moving cylinder.
//
// The leaf is a fine grid in page space (uv 0..1). Every vertex is curled in
// the vertex shader: points behind the roll axis stay flat; points past it wrap
// around a cylinder of radius R lying on the page, and points past half a turn
// lie flat on top, travelling back over the page. The camera is a pinhole above
// the page centre, so the roll swells toward the reader.
//
// Shading keeps the flat part pixel-exact (it is the frozen page), lights the
// roll relative to that, gives the back of the paper its own tone with the
// print showing faintly through (mirrored by the geometry itself), and casts
// shadows: onto the flat page from the roll and the flipped part, and onto the
// revealed page underneath (a separate full-canvas pass on the base plane).

struct U {
    page: vec4<f32>,   // x W, y H (px), zw page origin inside the canvas (px)
    view: vec4<f32>,   // x,y canvas size (px), z camera distance (px), w 1 = board cover (marbled endpaper)
    axis: vec4<f32>,   // xy a point on the roll axis (page px), zw unit normal toward the free edge
    curl: vec4<f32>,   // x radius (px), y shadow strength, z print show-through, w turn progress
    light: vec4<f32>,  // xyz light direction (toward the light), w ambient
    paper: vec4<f32>,  // rgb back-of-leaf paper, a grain amount
};

@group(0) @binding(0) var<uniform> u: U;
@group(0) @binding(1) var pageTex: texture_2d<f32>;
@group(0) @binding(2) var pageSmp: sampler;

const PI: f32 = 3.14159265;

struct Curl {
    pos: vec3<f32>,
    a: f32,
};

fn curlPoint(P: vec2<f32>) -> Curl {
    let A = u.axis.xy;
    let n = u.axis.zw;
    let R = max(u.curl.x, 1.0);
    let d = dot(P - A, n);
    var c: Curl;
    if (d <= 0.0) {
        c.pos = vec3<f32>(P, 0.0);
        c.a = 0.0;
        return c;
    }
    let foot = P - d * n;
    if (d < PI * R) {
        let a = d / R;
        c.pos = vec3<f32>(foot + R * sin(a) * n, R * (1.0 - cos(a)));
        c.a = a;
    } else {
        c.pos = vec3<f32>(foot - (d - PI * R) * n, 2.0 * R);
        c.a = PI;
    }
    return c;
}

// Pinhole projection into canvas clip space, perspective-correct varyings.
fn project(p: vec3<f32>) -> vec4<f32> {
    let cam = u.page.xy * 0.5;
    let D = u.view.z;
    let f = D / max(D - p.z, 1.0);
    let q = cam + (p.xy - cam) * f + u.page.zw;
    let ndc = vec2<f32>(q.x / u.view.x * 2.0 - 1.0, 1.0 - q.y / u.view.y * 2.0);
    let w = 1.0 / f;
    let depth = 0.5 - p.z / (8.0 * max(u.curl.x, 1.0));
    return vec4<f32>(ndc * w, depth * w, w);
}

// Signed distance to the page rectangle (negative inside).
fn pageSdf(p: vec2<f32>) -> f32 {
    let h = u.page.xy * 0.5;
    let q = abs(p - h) - h;
    return length(max(q, vec2<f32>(0.0))) + min(max(q.x, q.y), 0.0);
}

fn hash(p: vec2<f32>) -> f32 {
    var q = fract(p * vec2<f32>(0.1031, 0.1030));
    q = q + dot(q, q.yx + 33.33);
    return fract((q.x + q.y) * q.x);
}

fn vnoise(p: vec2<f32>) -> f32 {
    let i = floor(p);
    let f = fract(p);
    let w = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2<f32>(1.0, 0.0)), w.x),
               mix(hash(i + vec2<f32>(0.0, 1.0)), hash(i + vec2<f32>(1.0, 1.0)), w.x), w.y);
}

fn fbm(p: vec2<f32>) -> f32 {
    var s = 0.0;
    var a = 0.5;
    var q = p;
    for (var k = 0; k < 4; k = k + 1) {
        s = s + a * vnoise(q);
        q = q * 2.02 + vec2<f32>(7.3, 3.1);
        a = a * 0.5;
    }
    return s;
}

// Combed marbling for the inside of the board cover: domain-warped bands of
// ink blue, oxblood and cream with gilt veins, as on a bookbinder's endpaper.
fn marbled(pp: vec2<f32>) -> vec3<f32> {
    let q = pp / u.page.x * 3.2;
    let warp = vec2<f32>(fbm(q * 1.3 + vec2<f32>(1.7, 9.2)), fbm(q * 1.3 + vec2<f32>(8.3, 2.8)));
    let r = q + 1.9 * warp;
    let comb = sin(r.x * 22.0) * 0.08;
    let t = fract(r.y * 1.6 + fbm(r * 2.2) * 1.4 + comb);
    let ink = vec3<f32>(0.145, 0.18, 0.24);
    let ox = vec3<f32>(0.47, 0.18, 0.24);
    let cream = vec3<f32>(0.93, 0.89, 0.80);
    let gilt = vec3<f32>(0.74, 0.57, 0.30);
    var c = mix(ink, ox, smoothstep(0.18, 0.32, t));
    c = mix(c, cream, smoothstep(0.52, 0.60, t) * (1.0 - smoothstep(0.78, 0.86, t)));
    c = mix(c, ink, smoothstep(0.90, 0.97, t));
    let vein = 1.0 - smoothstep(0.0, 0.035, abs(t - 0.5));
    return mix(c, gilt, vein * 0.85);
}

// ------------------------------------------------------------------ leaf
struct LeafOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) uv: vec2<f32>,
    @location(1) a: f32,
    @location(2) pp: vec2<f32>,
};

@vertex
fn vs_leaf(@location(0) uv: vec2<f32>) -> LeafOut {
    let P = uv * u.page.xy;
    let c = curlPoint(P);
    var o: LeafOut;
    o.clip = project(c.pos);
    o.uv = uv;
    o.a = c.a;
    o.pp = P;
    return o;
}

// Shadow falling on the still-flat part of the leaf from the flipped-over part
// hovering 2R above it (offset away from the light, softened at its edges).
fn flatShadow(S: vec2<f32>) -> f32 {
    let A = u.axis.xy;
    let n = u.axis.zw;
    let R = max(u.curl.x, 1.0);
    let L = normalize(u.light.xyz);
    let off = -L.xy / max(L.z, 0.25) * (2.0 * R) * 0.55;
    let Q = S - off;
    let s = dot(Q - A, n);
    // the flipped leaf above Q started life at page point P
    let P = Q + (PI * R - 2.0 * s) * n;
    let flip = (1.0 - smoothstep(-R * 0.8, R * 0.5, pageSdf(P))) * (1.0 - smoothstep(-R * 0.2, R * 0.3, s));
    return clamp(u.curl.y * 0.30 * flip, 0.0, 0.5);
}

@fragment
fn fs_leaf(i: LeafOut) -> @location(0) vec4<f32> {
    let texel = textureSample(pageTex, pageSmp, i.uv);
    let n = u.axis.zw;
    // the curl angle, exact per pixel (interpolating it per vertex would let
    // triangles that straddle the axis shade as stair-steps)
    let a = clamp(dot(i.pp - u.axis.xy, n) / max(u.curl.x, 1.0), 0.0, PI);
    let Nf = normalize(vec3<f32>(-sin(a) * n, cos(a)));
    let L = normalize(u.light.xyz);
    let amb = u.light.w;
    let flatLit = amb + (1.0 - amb) * max(L.z, 0.0);
    var col: vec3<f32>;
    var N: vec3<f32>;
    if (cos(a) >= 0.0) {
        col = texel.rgb;
        N = Nf;
    } else {
        // the back of the paper: its own tone, the print faintly through it
        // seen from behind, the print loses its colour and most of its weight
        let lum = dot(texel.rgb, vec3<f32>(0.30, 0.59, 0.11));
        let through = clamp(lum / 0.905, 0.0, 1.0);
        col = u.paper.rgb * mix(1.0, through, u.curl.z);
        let g = hash(floor(i.pp * 0.9)) - 0.5;
        col = col * (1.0 + g * u.paper.a);
        if (u.view.w > 0.5) {
            col = marbled(i.pp);
        }
        N = -Nf;
    }
    let lit = amb + (1.0 - amb) * max(dot(N, L), 0.0);
    let k = clamp(lit / flatLit, 0.5, 1.1);
    // paper shadows stay warm: darker tones lean toward sepia
    col = col * k * mix(vec3<f32>(1.03, 0.985, 0.90), vec3<f32>(1.0), smoothstep(0.55, 1.0, k));
    // a soft paper sheen along the crest of the roll
    let H = normalize(L + vec3<f32>(0.0, 0.0, 1.0));
    let sheen = max(pow(max(dot(N, H), 0.0), 22.0) - pow(max(H.z, 0.0), 22.0), 0.0);
    col = col + vec3<f32>(1.0, 0.98, 0.94) * sheen * 0.16;
    // occlusion deep inside the roll, where it nearly touches itself
    let inner = smoothstep(PI * 0.55, PI * 0.95, a) * (1.0 - smoothstep(PI * 0.95, PI, a));
    col = col * (1.0 - 0.18 * inner);
    if (a <= 0.0) {
        col = col * (1.0 - flatShadow(i.pp));
    }
    return vec4<f32>(col, 1.0);
}

// ------------------------------------------------------------------ cast shadow on the page beneath
struct ShadowOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) pp: vec2<f32>,
};

@vertex
fn vs_shadow(@builtin(vertex_index) vi: u32) -> ShadowOut {
    var corners = array<vec2<f32>, 6>(
        vec2<f32>(0.0, 0.0), vec2<f32>(1.0, 0.0), vec2<f32>(0.0, 1.0),
        vec2<f32>(0.0, 1.0), vec2<f32>(1.0, 0.0), vec2<f32>(1.0, 1.0));
    let c = corners[vi];
    var o: ShadowOut;
    o.clip = vec4<f32>(c.x * 2.0 - 1.0, 1.0 - c.y * 2.0, 0.99, 1.0);
    o.pp = c * u.view.xy - u.page.zw;
    return o;
}

@fragment
fn fs_shadow(i: ShadowOut) -> @location(0) vec4<f32> {
    let S = i.pp;
    let A = u.axis.xy;
    let n = u.axis.zw;
    let R = max(u.curl.x, 1.0);
    let s = dot(S - A, n);
    let foot = S - s * n;
    let along = 1.0 - smoothstep(-R * 0.5, R * 0.9, pageSdf(foot));
    let inPage = 1.0 - smoothstep(-2.0, 2.0, pageSdf(S));
    // the roll casts a soft band beyond itself; the lifted leaf darkens broadly
    let band = (1.0 - smoothstep(R * 0.5, R * 3.4, s)) * step(0.0, s);
    let broad = (1.0 - smoothstep(0.0, u.page.x * 1.1, s)) * step(0.0, s);
    let k = u.curl.y * along * inPage * (0.40 * band + 0.10 * broad);
    let tint = vec3<f32>(0.09, 0.07, 0.06);
    return vec4<f32>(tint * k, k);
}
