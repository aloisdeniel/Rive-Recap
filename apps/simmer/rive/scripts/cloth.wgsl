// Simmer tablecloth: the simulated gingham cloth (scripts/cloth.luau), drawn
// as a lit 3D mesh. World space: x across the screen, y down the table (the
// screen's vertical), z up off the table toward the viewer. The table is
// seen from above, so a lifted point moves up the screen by `lift` per unit
// of height. Two passes share one vertex buffer:
//
//   vs_shadow/fs_shadow  the cloth flattened onto the table, offset down-right
//                        like every cutout's ink layer, softer as it lifts
//   vs_cloth/fs_cloth    the cloth itself: woven gingham (two basil stripe
//                        sets that darken where they cross), a tomato hem,
//                        a paler underside where a fold turns over, and
//                        risograph shading (posterised light, shadow printed
//                        as an aubergine halftone).

struct U {
    view: vec4<f32>,   // stage w, h (pt), band top y (pt), lift (screen pt per unit z)
    light: vec4<f32>,  // light dir xyz, ambient
    look: vec4<f32>,   // checks across, checks down, shadow strength, px per point
};

@group(0) @binding(0) var<uniform> u: U;

struct VIn {
    @location(0) pos: vec3<f32>,
    @location(1) nrm: vec3<f32>,
    @location(2) uv: vec2<f32>,
};

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) nrm: vec3<f32>,
    @location(1) uv: vec2<f32>,
    @location(2) z: f32,
    @location(3) pt: vec2<f32>,
};

fn toClip(sx: f32, sy: f32, depth: f32) -> vec4<f32> {
    let x = sx / u.view.x * 2.0 - 1.0;
    let y = 1.0 - (sy - u.view.z) / u.view.y * 2.0;
    return vec4<f32>(x, y, depth, 1.0);
}

@vertex
fn vs_cloth(v: VIn) -> VOut {
    var o: VOut;
    let sx = v.pos.x;
    let sy = v.pos.y - v.pos.z * u.view.w;
    o.clip = toClip(sx, sy, clamp(0.5 - v.pos.z * 0.0015, 0.01, 0.98));
    o.nrm = v.nrm;
    o.uv = v.uv;
    o.z = v.pos.z;
    o.pt = vec2<f32>(sx, sy);
    return o;
}

@vertex
fn vs_shadow(v: VIn) -> VOut {
    var o: VOut;
    let h = max(v.pos.z, 0.0);
    let sx = v.pos.x + 6.0 + h * 0.22;
    let sy = v.pos.y + 8.0 + h * 0.1;
    o.clip = toClip(sx, sy, 0.99);
    o.nrm = v.nrm;
    o.uv = v.uv;
    o.z = h;
    o.pt = vec2<f32>(sx, sy);
    return o;
}

@fragment
fn fs_shadow(i: VOut) -> @location(0) vec4<f32> {
    let a = u.look.z * clamp(1.0 - i.z / 220.0, 0.25, 1.0);
    let aub = vec3<f32>(0.282, 0.161, 0.239);
    return vec4<f32>(aub * a, a);
}

fn halftone(pt: vec2<f32>, amount: f32, period: f32) -> f32 {
    let r = vec2<f32>(pt.x + pt.y, pt.y - pt.x) * 0.70710678;
    let cell = fract(r / period) - 0.5;
    let dist = length(cell) * period;
    let rad = sqrt(clamp(amount, 0.0, 1.0)) * period * 0.62;
    return 1.0 - smoothstep(rad - 0.5, rad + 0.5, dist);
}

@fragment
fn fs_cloth(i: VOut) -> @location(0) vec4<f32> {
    let cream = vec3<f32>(0.992, 0.961, 0.882);
    let basil = vec3<f32>(0.302, 0.463, 0.333);
    let tomato = vec3<f32>(0.894, 0.286, 0.196);
    let aub = vec3<f32>(0.282, 0.161, 0.239);

    // woven gingham: soft-edged stripes so the checks stay crisp but never alias
    let cu = i.uv.x * u.look.x;
    let cv = i.uv.y * u.look.y;
    let wu = fwidth(cu) * 0.75 + 0.01;
    let wv = fwidth(cv) * 0.75 + 0.01;
    let su = smoothstep(0.5 - wu, 0.5 + wu, abs(fract(cu) - 0.5) * 2.0);
    let sv = smoothstep(0.5 - wv, 0.5 + wv, abs(fract(cv) - 0.5) * 2.0);
    var col = mix(cream, basil, 0.42 * su + 0.42 * sv + 0.16 * su * sv);
    // tomato hem round the edge, with a cream stitch line inside it
    let edge = min(min(i.uv.x, 1.0 - i.uv.x) * 1.9, min(i.uv.y, 1.0 - i.uv.y));
    let hem = 1.0 - smoothstep(0.022, 0.03, edge);
    col = mix(col, tomato, hem);
    let stitch = (1.0 - smoothstep(0.0, 0.004, abs(edge - 0.042))) * step(0.5, fract((i.uv.x + i.uv.y) * 60.0));
    col = mix(col, cream, stitch * 0.85);

    // the viewer looks down the z axis: a normal pointing away is the underside
    var n = normalize(i.nrm);
    if (n.z < 0.0) {
        // the underside: the print shows through, paler
        n = -n;
        col = mix(col, cream, 0.45);
    }
    let l = normalize(u.light.xyz);
    let lam = dot(n, l);
    // posterised: highlight, body, and a dot-screened shadow
    let hi = smoothstep(0.86, 0.9, lam);
    col = mix(col, vec3<f32>(1.0, 0.99, 0.95), hi * 0.35);
    let sh = clamp((0.62 - lam) * 2.0, 0.0, 1.0);
    col = mix(col, col * 0.84, smoothstep(0.0, 0.25, sh));
    let dots = halftone(i.pt, sh * 0.55, 3.4);
    col = mix(col, mix(col, aub, 0.75), dots);
    return vec4<f32>(col, 1.0);
}
