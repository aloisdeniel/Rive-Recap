// Switchyard poster 3D: transit objects rendered like a printed Swiss poster.
//
// One vertex format serves every kind (a tram, two isometric transit maps):
//   pos, normal (object space), colour + material, outline normal, build anim.
// The build anim makes the scene assemble from the timeline alone: each vertex
// scales in around its own centre `c` once `build` passes its start time `t0`,
// with an overshoot - route ribbons swell into being along their length, station
// pucks pop up one by one.
//
// Shading is "printed": flat poster colours, a light fixed in object space and
// quantised into three ink tones (top, lit side, shade side), an ink outline drawn
// as an inverted hull, and procedural livery decals on the tram body.

struct U {
    vp: mat4x4<f32>,      // projection * view
    model: mat4x4<f32>,   // object -> view-space world
    light: vec4<f32>,     // xyz: light direction (object space), w: outline width (object units)
    params: vec4<f32>,    // x: build 0..1, y: build spread (seconds-ish), z: fog start, w: fog end (view depth)
    ink: vec4<f32>,       // rgb: ink colour, a: shadow alpha
    extra: vec4<f32>,     // x: tram length, y: unused, z: dim (0..1), w: vehicle travel along z
};

@group(0) @binding(0) var<uniform> u: U;

struct VIn {
    @location(0) pos: vec3<f32>,
    @location(1) nrm: vec3<f32>,
    @location(2) col: vec4<f32>,
    @location(3) sn: vec3<f32>,
    @location(4) anim: vec4<f32>,
};

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) n: vec3<f32>,
    @location(1) op: vec3<f32>,
    @location(2) col: vec4<f32>,
    @location(3) depth: f32,
};

fn build_scale(t0: f32) -> f32 {
    // 0 before t0, then an overshooting pop over ~0.16 of the build
    let k = clamp((u.params.x - t0) / 0.16, 0.0, 1.0);
    let s = 1.70158 * 1.2;
    let q = k - 1.0;
    return 1.0 + (s + 1.0) * q * q * q + s * q * q;
}

fn place(v: VIn, push: f32) -> vec3<f32> {
    let c = v.anim.yzw;
    let k = build_scale(v.anim.x);
    var p = c + (v.pos + v.sn * push - c) * k;
    // the vehicle (materials 0, 1) and its contact shadow (3) travel; the ground (2) stays
    let m = v.col.a;
    if (m < 1.5 || m > 2.5) {
        p.z = p.z + u.extra.w;
    }
    return p;
}

@vertex
fn vs_main(v: VIn) -> VOut {
    var o: VOut;
    let p = place(v, 0.0);
    let w = u.model * vec4<f32>(p, 1.0);
    o.clip = u.vp * w;
    o.n = v.nrm;
    o.op = v.pos;
    o.col = v.col;
    o.depth = -w.z;
    return o;
}

// Inverted hull: pushed out along the outline normal, front faces culled.
@vertex
fn vs_outline(v: VIn) -> VOut {
    var o: VOut;
    let p = place(v, u.light.w * length(v.sn));
    let w = u.model * vec4<f32>(p, 1.0);
    o.clip = u.vp * w;
    o.n = v.nrm;
    o.op = v.pos;
    o.col = v.col;
    o.depth = -w.z;
    return o;
}

@fragment
fn fs_ink(i: VOut) -> @location(0) vec4<f32> {
    return vec4<f32>(u.ink.rgb, 1.0);
}

fn hash2(p: vec2<f32>) -> f32 {
    var q = fract(p * vec2<f32>(123.34, 456.21));
    q = q + dot(q, q + 45.32);
    return fract(q.x * q.y);
}

// Tram livery, painted from object-space position (front faces +z, body runs to -len).
fn livery(op: vec3<f32>, n: vec3<f32>, base: vec3<f32>) -> vec3<f32> {
    let blue = base;
    let red = vec3<f32>(0.957, 0.271, 0.2);
    let ink = vec3<f32>(0.09, 0.106, 0.125);
    let glass = vec3<f32>(0.13, 0.17, 0.22);
    let yellow = vec3<f32>(1.0, 0.84, 0.294);
    let roof = vec3<f32>(0.91, 0.9, 0.86);
    var c = blue;
    if (n.y > 0.55) {
        return roof;
    }
    if (op.y < 0.14) {
        return ink;
    }
    if (op.y < 0.21) {
        return red;
    }
    if (n.z > 0.45) {
        // front: windscreen with one diagonal glint, headlights, destination blind
        if (op.y > 0.5 && op.y < 0.93 && abs(op.x) < 0.37) {
            c = glass;
            let g = op.x * 0.9 + op.y * 1.4;
            if (g > 0.98 && g < 1.08) {
                c = mix(glass, vec3<f32>(0.85, 0.9, 0.95), 0.55);
            }
        }
        if (op.y > 0.95 && op.y < 1.03 && abs(op.x) < 0.27) {
            c = ink;
            if (abs(op.x) < 0.2 && op.y > 0.975 && op.y < 1.005) {
                c = yellow;
            }
        }
        let hl = vec2<f32>(abs(op.x) - 0.29, op.y - 0.33);
        if (length(hl) < 0.055) {
            c = yellow;
        }
        return c;
    }
    if (abs(n.x) > 0.45) {
        // sides: a ribbon of windows broken by blue pillars and two doors
        let len = u.extra.x;
        if (op.y > 0.52 && op.y < 0.86 && op.z < -0.5 && op.z > -(len - 0.3)) {
            let s = fract((-op.z - 0.5) / 0.62);
            if (s > 0.08 && s < 0.92) {
                c = glass;
                if (op.y > 0.79) {
                    c = mix(glass, vec3<f32>(0.6, 0.68, 0.78), 0.35);
                }
            }
        }
        let dz = abs(-op.z - 1.55);
        let dz2 = abs(-op.z - (len - 1.25));
        if ((dz < 0.2 || dz2 < 0.2) && op.y > 0.21 && op.y < 0.88) {
            c = mix(blue, ink, 0.45);
            if (op.y > 0.5 && (dz < 0.15 || dz2 < 0.15)) {
                c = glass;
            }
        }
        return c;
    }
    return c;
}

fn tone(n: vec3<f32>) -> f32 {
    let l = normalize(u.light.xyz);
    let d = dot(normalize(n), l);
    // three printed tones: shade side, lit side, top
    var t = 0.62;
    if (d > -0.1) {
        t = 0.8;
    }
    if (d > 0.55) {
        t = 1.0;
    }
    return t;
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    var base = i.col.rgb;
    let m = i.col.a;
    if (m > 0.5 && m < 1.5) {
        base = livery(i.op, i.n, base);
    }
    let t = tone(i.n);
    // shade toward ink rather than black, so the palette stays printed
    let ink = u.ink.rgb;
    var c = mix(ink, base, t);
    if (t > 0.99) {
        c = base;
    }
    c = mix(c, ink, u.extra.z);
    return vec4<f32>(c, 1.0);
}

// Translucent layer: ground stripes (fade into the distance) and soft shadows.
@fragment
fn fs_ground(i: VOut) -> @location(0) vec4<f32> {
    let m = i.col.a;
    var a = 1.0;
    var c = i.col.rgb;
    if (m > 2.5) {
        // shadow decal
        c = u.ink.rgb;
        a = u.ink.a;
    }
    let fog = 1.0 - smoothstep(u.params.z, u.params.w, i.depth);
    a = a * fog;
    c = mix(c, u.ink.rgb, u.extra.z * 0.5);
    return vec4<f32>(c * a, a);
}
