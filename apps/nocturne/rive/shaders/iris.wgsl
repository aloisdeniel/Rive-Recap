// Nocturne observatory aperture: lit iris blades, analytic, one pass.
//
// The hole is the intersection of N blade edges. Each edge is an arc (concave
// toward the centre, like real diaphragm blades), so a wide hole reads almost
// round and a nearly closed one reads as an N-sided pupil. Which blade lies on
// top is decided by logarithmic-spiral sector boundaries that start at the
// hole's vertices, which produces the pinwheel overlap of a real iris.
//
// Shading treats every blade as a thin, slightly curved anodised plate:
// - a per-blade tilt plus a curvature across the blade, lit by a key from the
//   upper left (so neighbouring blades differ in brightness and the set rotates
//   light as the iris spins);
// - brushed-metal streaks along each blade;
// - a bevel highlight on each upper blade's trailing edge and a soft contact
//   shadow on the blade beneath it;
// - a lit edge face (blade thickness) and a hairline rim with a slight
//   chromatic split at the hole, plus a bloom of the sky spilling through a
//   small pupil.
// No discard; output is premultiplied. `hand` = -1 mirrors the iris (the
// reverse transition spins and overlaps the other way).

struct U {
    frame: vec4<f32>,   // canvas w px, canvas h px, px per point, mode (0 stage, 1 motif)
    origin: vec4<f32>,  // canvas top-left in points (x, y), outer radius (pt, mode 1), opacity
    iris: vec4<f32>,    // centre x, y (pt), hole radius (pt), spin (rad)
    look: vec4<f32>,    // blades, curl, edge curvature, hand (+1 / -1)
    glow: vec4<f32>,    // bloom, rim brightness, blade lightness, edge thickness (pt)
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

const PI = 3.14159265;
const ICE = vec3<f32>(0.737, 0.894, 0.910);
const BLUE = vec3<f32>(0.376, 0.545, 1.0);
const AMBER = vec3<f32>(0.969, 0.745, 0.384);

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let res = u.frame.z;
    let px = 1.0 / res;
    let pt = u.origin.xy + i.uv * u.frame.xy / res;
    let hand = select(1.0, -1.0, u.look.w < 0.0);
    var p = pt - u.iris.xy;
    p.y = p.y * hand;                       // mirror for the reverse iris
    let spin = u.iris.w * hand;
    let rho = length(p);
    let theta = atan2(p.y, p.x);
    let N = max(u.look.x, 3.0);
    let D = 2.0 * PI / N;
    let r = max(u.iris.z, 0.5);
    let rv = r / cos(D * 0.5);
    let kc = u.look.z / (2.0 * r);

    // ---- coverage: the hole is inside every blade edge
    var dmax = -1e9;
    var jbest = 0.0;
    for (var j = 0; j < 16; j = j + 1) {
        if (f32(j) >= N) {
            break;
        }
        let a = spin + f32(j) * D;
        let n = vec2<f32>(cos(a), sin(a));
        let t = dot(p, vec2<f32>(-n.y, n.x));
        let dj = dot(p, n) - r + kc * t * t;
        if (dj > dmax) {
            dmax = dj;
            jbest = f32(j);
        }
    }
    let d = dmax;                             // > 0 on a blade, < 0 in the hole (points)
    var cover = smoothstep(-0.7 * px, 0.7 * px, d);

    // ---- which blade is on top: log-spiral sectors from the hole's vertices
    let s0 = 26.0;
    let psi = theta - spin - u.look.y * log((max(rho, rv) + s0) / (rv + s0));
    let k = floor(psi / D + 0.5);
    let ul = psi - k * D;                     // -D/2 .. D/2 across the blade
    let phi = spin + k * D;                   // this blade's centre direction
    let across = ul / (D * 0.5);              // -1 leading (under the previous blade) .. +1 trailing

    // ---- plate lighting
    let dir = vec2<f32>(cos(phi), sin(phi));
    let tng = vec2<f32>(-dir.y, dir.x);
    var nxy = dir * 0.20 + tng * (0.16 * across);
    nxy.y = nxy.y * hand;                     // back to screen space for lighting
    let nrm = normalize(vec3<f32>(nxy, 1.0));
    let L = normalize(vec3<f32>(-0.42, -0.62, 0.66));
    let diff = max(dot(nrm, L), 0.0);
    let h = normalize(L + vec3<f32>(0.0, 0.0, 1.0));
    let spec = pow(max(dot(nrm, h), 0.0), 38.0);
    let lightness = u.glow.z;
    let dark = vec3<f32>(0.035, 0.075, 0.135);
    let lit = vec3<f32>(0.115, 0.215, 0.345);
    var col = mix(dark, lit, diff * lightness);
    // brushed streaks along the blade
    let streak = vnoise(vec2<f32>(ul * max(rho, 8.0) * 1.4, rho * 0.035 + k * 13.0));
    col = col * (0.90 + 0.18 * streak);
    col = col + ICE * spec * 0.22 * lightness;

    // bevel highlight on the trailing edge, contact shadow on the leading edge
    let eT = (D * 0.5 - ul) * max(rho, rv);   // points to the trailing boundary
    let eL = (ul + D * 0.5) * max(rho, rv);   // points to the leading boundary
    let beyond = smoothstep(0.0, 6.0, d);     // fade these near the hole edge
    col = col * (1.0 - 0.55 * exp(-eL / 7.0) * beyond);
    col = col + ICE * 0.42 * exp(-pow(eT / (0.55 + px), 2.0)) * beyond * (0.4 + 0.6 * diff);
    col = col + BLUE * 0.10 * exp(-eT / 4.0) * beyond;

    // ---- hole edge: blade thickness face + hairline rim + chromatic split
    let th = max(u.glow.w, px);
    let aE = spin + jbest * D;
    var ne = -vec2<f32>(cos(aE), sin(aE));
    ne.y = ne.y * hand;
    let faceN = normalize(vec3<f32>(ne * 0.9, 0.45));
    let faceLit = max(dot(faceN, L), 0.0);
    let face = 1.0 - smoothstep(th * 0.6, th, d);
    col = mix(col, mix(dark * 0.6, ICE * 0.85, faceLit), face * 0.85);
    let rim = exp(-pow(d / (0.45 + 0.6 * px), 2.0)) * u.glow.y;
    col = col + ICE * rim * 0.75;
    col = col + vec3<f32>(0.85, 0.42, 0.20) * exp(-pow((d - 1.1) / 0.6, 2.0)) * 0.12 * u.glow.y;
    col = col + vec3<f32>(0.25, 0.45, 1.0) * exp(-pow((d + 0.9) / 0.7, 2.0)) * 0.25 * u.glow.y;

    // ---- the pupil bloom: light from the next sky spilling over the blades
    let bloom = u.glow.x;
    let spill = exp(-max(d, 0.0) / (5.0 + r * 0.35)) * bloom;
    col = col + mix(ICE, BLUE, 0.35) * spill * 0.38;

    // ---- motif mode: the blades live inside a housing ring
    var a = cover;
    if (u.frame.w > 0.5) {
        let outer = u.origin.z;
        a = a * (1.0 - smoothstep(outer - px, outer + px * 0.5, rho));
        col = col * (0.78 + 0.22 * (1.0 - smoothstep(outer * 0.55, outer, rho)));
    } else {
        // stage mode: a deep vignette toward the far blades keeps the frame quiet
        col = col * (1.0 - 0.35 * smoothstep(180.0, 620.0, rho));
    }
    a = a * u.origin.w;
    // glow inside the hole is additive light (alpha stays 0 there)
    let inner = mix(ICE, vec3<f32>(1.0), 0.3) * bloom * 0.55 * exp(-rho / (r * 0.55 + 2.0)) * (1.0 - cover) * u.origin.w;
    return vec4<f32>(col * a + inner, a);
}
