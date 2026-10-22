// Patchwork backdrop: the larger quilt the camera reveals when it pulls back
// during a hand-off. A diamond-in-square quilt of half-square triangles (the
// piecing of the 3D sheet the fold lays down), with running stitches along
// every seam, a quilted loft that sinks at the seams and a woven thread
// texture. Procedural, so it covers any canvas size; rendered once per size.

struct U {
    size: vec4<f32>,  // x,y canvas px, z px per point, w unused
};

@group(0) @binding(0) var<uniform> u: U;

const PI: f32 = 3.14159265;
const CELL: f32 = 74.0;
const ORIGIN = vec2<f32>(-25.0, -16.0); // the master's quilt origin, in points

const IND = vec3<f32>(0.188, 0.294, 0.459);
const IND_D = vec3<f32>(0.137, 0.227, 0.369);
const TER_D = vec3<f32>(0.663, 0.353, 0.251);
const TEAL = vec3<f32>(0.302, 0.561, 0.514);
const TEAL_D = vec3<f32>(0.227, 0.431, 0.396);
const ROSE_D = vec3<f32>(0.831, 0.549, 0.584);
const OAT = vec3<f32>(0.961, 0.922, 0.867);
const OAT_D = vec3<f32>(0.910, 0.851, 0.765);
const OAT_DD = vec3<f32>(0.851, 0.776, 0.659);
const SAND = vec3<f32>(0.804, 0.722, 0.627);

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) uv: vec2<f32>,
};

@vertex
fn vs_main(@builtin(vertex_index) vi: u32) -> VOut {
    var c = array<vec2<f32>, 6>(
        vec2<f32>(0.0, 0.0), vec2<f32>(1.0, 0.0), vec2<f32>(0.0, 1.0),
        vec2<f32>(0.0, 1.0), vec2<f32>(1.0, 0.0), vec2<f32>(1.0, 1.0));
    let p = c[vi];
    var o: VOut;
    o.clip = vec4<f32>(p.x * 2.0 - 1.0, 1.0 - p.y * 2.0, 0.0, 1.0);
    o.uv = p;
    return o;
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

fn imod(a: i32, b: i32) -> i32 {
    return ((a % b) + b) % b;
}

fn darkOf(i: i32) -> vec3<f32> {
    switch (imod(i, 6)) {
        case 0: { return IND_D; }
        case 1: { return TER_D; }
        case 2: { return TEAL_D; }
        case 3: { return IND; }
        case 4: { return ROSE_D; }
        default: { return TEAL; }
    }
}

fn lightOf(i: i32) -> vec3<f32> {
    switch (imod(i, 3)) {
        case 0: { return OAT_DD; }
        case 1: { return OAT_D; }
        default: { return SAND; }
    }
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let pt = i.uv * u.size.xy / u.size.z;      // points
    let q = pt - ORIGIN;
    let cf = q / CELL;
    let cell = floor(cf);
    let f = fract(cf);
    let c = i32(cell.x);
    let r = i32(cell.y);
    // 2x2 blocks: the dark triangle of each cell points at its block centre
    let bi = (c + 2 - imod(c + 2, 2)) / 2;
    let bj = (r + 2 - imod(r + 2, 2)) / 2;
    let ix = imod(c, 2);
    let iy = imod(r, 2);
    var dd: f32;
    var dark: bool;
    var along: f32;
    if (ix == iy) {
        // corners (0,0)->(1,1) diagonal: (0,0) cell dark at bottom-right, (1,1) dark at top-left
        dd = (f.x + f.y - 1.0) * 0.7071;
        dark = select((dd > 0.0), (dd < 0.0), ix == 1);
        along = (f.x - f.y) * 0.7071 * CELL;
    } else {
        dd = (f.y - f.x) * 0.7071;
        dark = select((dd < 0.0), (dd > 0.0), ix == 1);
        along = (f.x + f.y) * 0.7071 * CELL;
    }
    var col = select(lightOf(bi + bj * 2), darkOf(bi * 3 + bj * 5), dark);
    // seams: cell edges and the HST diagonal (distances in points)
    let edge = min(min(f.x, 1.0 - f.x), min(f.y, 1.0 - f.y)) * CELL;
    let diag = abs(dd) * CELL;
    let seam = min(edge, diag);
    // quilted loft: sunk and shaded at every seam, puffed between them
    let loft = sqrt(clamp(seam / 12.0, 0.0, 1.0));
    col = col * (0.80 + 0.20 * loft);
    // soft light from the upper left across each puff
    let shade = clamp(0.5 + 0.5 * (f.x - f.y) * 0.4, 0.0, 1.0);
    col = col * (0.97 + 0.05 * shade);
    // running stitches 4 pt inside every seam, cream on the dark, rust on the light
    let thread = select(vec3<f32>(0.663, 0.353, 0.251), vec3<f32>(0.984, 0.965, 0.933), dark);
    let onEdge = (1.0 - smoothstep(0.4, 0.9, abs(edge - 4.2))) * step(0.45, fract((q.x + q.y) / 7.0));
    let onDiag = (1.0 - smoothstep(0.4, 0.9, abs(diag - 4.2))) * step(0.45, fract(along / 7.0));
    col = mix(col, thread, max(onEdge, onDiag) * 0.7);
    // woven thread texture and a little felted mottling
    let a = pt / 2.6;
    let over = ((i32(floor(a.x)) + i32(floor(a.y))) & 1) == 1;
    let wv = select(sin(PI * fract(a.y)), sin(PI * fract(a.x)), over);
    col = col * (0.95 + 0.06 * wv) * (0.97 + 0.05 * vnoise(pt * 0.11));
    return vec4<f32>(clamp(col, vec3<f32>(0.0), vec3<f32>(1.0)), 1.0);
}
