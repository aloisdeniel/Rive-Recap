// Patchwork persona medallion: a quilted indigo cushion behind the persona
// emblem. Pieced like a Dresden plate (16 wedges, the outer ring offset half a
// wedge like brickwork, a plain hub), every piece puffed with loft, sunk at its
// seams, running-stitched in cream, woven, and lit by a light that sweeps round
// during the reveal and then rests. Transparent outside the disc.

struct U {
    geo: vec4<f32>,    // x canvas px, y px per point, z disc diameter (pt), w seed
    light: vec4<f32>,  // xyz toward the light, w ambient
    look: vec4<f32>,   // x sheen strength, y stitch alpha, zw unused
};

@group(0) @binding(0) var<uniform> u: U;

const PI: f32 = 3.14159265;
const IND = vec3<f32>(0.188, 0.294, 0.459);
const IND_D = vec3<f32>(0.137, 0.227, 0.369);
const IND_L = vec3<f32>(0.357, 0.451, 0.612);
const CREAM = vec3<f32>(0.984, 0.965, 0.933);
const TER = vec3<f32>(0.800, 0.439, 0.318);

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

const R1: f32 = 46.0;   // hub
const R2: f32 = 98.0;   // inner wedge ring
const WEDGES: f32 = 16.0;

struct Piece {
    d: f32,      // distance to the nearest seam (pt)
    along: f32,  // coordinate along that seam, for stitch dashes
    id: vec2<f32>,
    ring: f32,
};

fn piece(p: vec2<f32>) -> Piece {
    let r = length(p);
    let a = atan2(p.y, p.x) + PI;               // 0..2pi
    let Rout = u.geo.z * 0.5 - 7.0;            // inside the binding
    var pc: Piece;
    if (r < R1) {
        pc.d = R1 - r;
        pc.along = a * r;
        pc.id = vec2<f32>(0.0, 0.0);
        pc.ring = 0.0;
        return pc;
    }
    let ring = select(2.0, 1.0, r < R2);
    let off = select(0.5, 0.0, ring < 1.5);
    let sec = a / (2.0 * PI) * WEDGES + off;
    let fs = fract(sec);
    let dw = min(fs, 1.0 - fs) * (2.0 * PI / WEDGES) * r;
    let lo = select(R2, R1, ring < 1.5);
    let hi = select(Rout, R2, ring < 1.5);
    let dr = min(r - lo, hi - r);
    if (dw < dr) {
        pc.d = dw;
        pc.along = r;
    } else {
        pc.d = dr;
        pc.along = a * r;
    }
    pc.id = vec2<f32>(floor(sec), ring);
    pc.ring = ring;
    return pc;
}

fn loft(p: vec2<f32>) -> f32 {
    let r = length(p);
    let edge = u.geo.z * 0.5;
    if (r > edge - 7.0) {
        // the rolled binding
        let t = clamp((edge - r) / 7.0, 0.0, 1.0);
        return 0.5 + 0.5 * sin(PI * t);
    }
    let pc = piece(p);
    return sqrt(clamp(pc.d / 15.0, 0.0, 1.0));
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
    let span = u.geo.x / u.geo.y;                 // canvas size in points
    let p = (i.uv - vec2<f32>(0.5)) * span;
    let r = length(p);
    let edge = u.geo.z * 0.5;
    let aa = 1.0 - smoothstep(edge - 0.6 / u.geo.y - 0.4, edge + 0.6, r);
    if (aa <= 0.0) {
        return vec4<f32>(0.0);
    }
    let pc = piece(p);
    // piecing: indigo family, alternating, the hub a deeper indigo
    var col: vec3<f32>;
    let h = hash(pc.id + vec2<f32>(u.geo.w, 3.0));
    if (pc.ring < 0.5) {
        col = IND_D;
    } else {
        let alt = (i32(pc.id.x) & 1) == 0;
        col = select(mix(IND, IND_L, 0.28 + 0.12 * h), mix(IND_D, IND, 0.35 + 0.3 * h), alt);
        if (pc.ring > 1.5) {
            col = select(mix(IND, IND_D, 0.45), mix(IND, IND_L, 0.15 + 0.1 * h), alt);
        }
    }
    let inBinding = r > edge - 7.0;
    if (inBinding) {
        col = IND_D * 0.92;
    }
    // running stitches 4 pt inside every seam, and round the binding
    let dash = step(0.45, fract(pc.along / 6.5));
    var st = (1.0 - smoothstep(0.45, 1.0, abs(pc.d - 4.0))) * dash;
    let bd = abs(r - (edge - 11.0));
    st = max(st, (1.0 - smoothstep(0.45, 1.0, bd)) * step(0.45, fract(atan2(p.y, p.x) * edge / 6.5)));
    if (!inBinding) {
        col = mix(col, CREAM, st * u.look.y);
    }
    // woven cotton
    let q = p / 2.4;
    let over = ((i32(floor(q.x)) + i32(floor(q.y))) & 1) == 1;
    let wv = select(sin(PI * fract(q.y)), sin(PI * fract(q.x)), over);
    col = col * (0.92 + 0.11 * wv) * (0.97 + 0.06 * vnoise(p * 0.15));
    // loft -> normal
    let e = 0.8;
    let h0 = loft(p);
    let gx = (loft(p + vec2<f32>(e, 0.0)) - h0) / e;
    let gy = (loft(p + vec2<f32>(0.0, e)) - h0) / e;
    let N = normalize(vec3<f32>(-gx * 4.2, -gy * 4.2, 1.0));
    col = col * (0.80 + 0.20 * h0);
    let L = normalize(u.light.xyz);
    let amb = u.light.w;
    let flatLit = amb + (1.0 - amb) * max(L.z, 0.0);
    let lit = amb + (1.0 - amb) * max(dot(N, L), 0.0);
    col = col * clamp(lit / flatLit, 0.62, 1.18);
    let H = normalize(L + vec3<f32>(0.0, 0.0, 1.0));
    let sheen = max(pow(max(dot(N, H), 0.0), 14.0) - pow(max(H.z, 0.0), 14.0) * 0.6, 0.0);
    col = col + vec3<f32>(0.85, 0.88, 1.0) * sheen * u.look.x;
    return vec4<f32>(clamp(col, vec3<f32>(0.0), vec3<f32>(1.0)) * aa, aa);
}
