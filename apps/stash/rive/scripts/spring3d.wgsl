// Stash 3D spring: a chrome coil spring built on the GPU.
//
// The mesh is only a (u, v) grid: u runs along the wire, v around it. The
// vertex shader winds it into a helix whose length comes from a uniform, so
// keying `height` compresses or stretches a real spring: the coils close up
// and the wire stays round (a vector zigzag scaled in y flattens instead).
// Closed, ground ends like a toy spring. Two passes: an ink inverted hull
// (the chunky outline of the art direction) and a chrome body reflecting a
// studio: bright cream sky, a sharp horizon, a dark grape floor.

struct U {
    a: vec4<f32>,     // height, coil radius, wire radius, turns
    b: vec4<f32>,     // twist (rad), view tilt (rad), canvas half width, outline
    c: vec4<f32>,     // canvas top (local y, negative), canvas bottom, light roll, opacity
    tint: vec4<f32>,  // steel tint rgb, mirror (0..1)
    ink: vec4<f32>,   // outline rgb, unused
};

@group(0) @binding(0) var<uniform> u: U;

const PI: f32 = 3.14159265;
const TAU: f32 = 6.2831853;

struct VIn {
    @location(0) uv: vec2<f32>,
};

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) n: vec3<f32>,
    @location(1) along: f32,
};

// height of the wire centre after `t` turns: ground ends, open middle
fn rise(t: f32) -> f32 {
    let turns = u.a.w;
    let w = u.a.z;
    let endT = 0.85;
    let solid = 2.0 * w;
    let h = max(u.a.x, solid * turns * 1.02);
    let mid = max(h - 2.0 * w - 2.0 * endT * solid, 0.0);
    let midT = max(turns - 2.0 * endT, 0.001);
    if (t < endT) {
        return w + solid * t;
    }
    if (t > turns - endT) {
        return w + solid * endT + mid + solid * (t - (turns - endT));
    }
    return w + solid * endT + mid * (t - endT) / midT;
}

fn centre(t: f32) -> vec3<f32> {
    let ang = t * TAU + u.b.x;
    let r = u.a.y;
    return vec3<f32>(r * cos(ang), rise(t), r * sin(ang));
}

fn toView(p: vec3<f32>) -> vec3<f32> {
    // the camera looks slightly down onto the coil
    let a = u.b.y;
    let c = cos(a);
    let s = sin(a);
    return vec3<f32>(p.x, p.y * c - p.z * s, p.y * s + p.z * c);
}

fn place(uv: vec2<f32>, grow: f32) -> VOut {
    var o: VOut;
    let turns = u.a.w;
    let t = uv.x * turns;
    let phi = uv.y * TAU;
    let c = centre(t);
    let e = 0.01;
    let tan = normalize(centre(t + e) - centre(t - e));
    let ang = t * TAU + u.b.x;
    let rad = vec3<f32>(cos(ang), 0.0, sin(ang));
    let bi = normalize(cross(tan, rad));
    let nr = normalize(rad - tan * dot(rad, tan));
    let nObj = normalize(cos(phi) * nr + sin(phi) * bi);
    let p = c + nObj * (u.a.z + grow);
    let v = toView(p);
    // local node space: y grows downward on screen, the base sits at y = 0
    let sx = v.x;
    let sy = -v.y;
    let top = u.c.x;
    let bottom = u.c.y;
    let hw = u.b.z;
    let span = u.a.y + u.a.z + 4.0;
    o.clip = vec4<f32>(sx / hw, 1.0 - 2.0 * (sy - top) / (bottom - top), 0.5 - v.z / span * 0.35, 1.0);
    o.n = toView(nObj);
    o.along = uv.x;
    return o;
}

@vertex
fn vs_main(v: VIn) -> VOut {
    return place(v.uv, 0.0);
}

@vertex
fn vs_outline(v: VIn) -> VOut {
    return place(v.uv, u.b.w);
}

@fragment
fn fs_ink(i: VOut) -> @location(0) vec4<f32> {
    let a = u.c.w;
    return vec4<f32>(u.ink.rgb * a, a);
}

fn studio(r: vec3<f32>) -> vec3<f32> {
    let sky = mix(vec3<f32>(0.80, 0.95, 0.88), vec3<f32>(1.0, 0.98, 0.92), smoothstep(0.0, 0.7, r.y));
    let ground = mix(vec3<f32>(0.32, 0.22, 0.6), vec3<f32>(0.12, 0.09, 0.22), smoothstep(-0.05, -0.6, r.y));
    var c = mix(ground, sky, smoothstep(-0.04, 0.04, r.y));
    // two softboxes: a big key top-left, a thin strip right
    let key = pow(max(dot(r, normalize(vec3<f32>(-0.6, 0.6, 0.5))), 0.0), 24.0);
    let strip = smoothstep(0.86, 0.95, r.x) * smoothstep(-0.3, 0.2, r.y);
    c = c + vec3<f32>(1.0) * (key * 0.9 + strip * 0.55);
    return c;
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let n = normalize(i.n);
    let lr = u.c.z;
    let V = vec3<f32>(0.0, 0.0, 1.0);
    var r = reflect(-V, n);
    r = vec3<f32>(r.x * cos(lr) + r.y * sin(lr), -r.x * sin(lr) + r.y * cos(lr), r.z);
    let env = studio(r);
    let L = normalize(vec3<f32>(-0.5, 0.7, 0.55));
    let dif = clamp(dot(n, L) * 0.5 + 0.5, 0.0, 1.0);
    let base = u.tint.rgb * mix(0.35, 1.0, dif);
    var col = mix(base, env * u.tint.rgb * 1.12, u.tint.a);
    // fresnel brightening at grazing angles
    let f = pow(1.0 - clamp(n.z, 0.0, 1.0), 3.0);
    col = col + f * 0.18;
    let a = u.c.w;
    return vec4<f32>(clamp(col, vec3<f32>(0.0), vec3<f32>(1.0)) * a, a);
}
