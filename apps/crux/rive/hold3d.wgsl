// Crux 3D climbing hold.
// One faceted mesh draws three ways: a graphic wall shadow, a coal cutout outline
// (inverted hull) and the lit, chalk-speckled body with its bolt socket.

struct U {
    vp: mat4x4<f32>,     // projection * view
    model: mat4x4<f32>,  // translate * scale * rotation (one copy of the hold)
    rot: mat4x4<f32>,    // rotation only, for normals
    color: vec4<f32>,    // rgb body, a = copy opacity (ghosts in a trail)
    shade: vec4<f32>,    // rgb core shadow / flat colour, a = flat alpha
    // x: chalk speckle amount, y: seed, z: bolt radius (object units), w: outline width
    params: vec4<f32>,
    // xyz: light direction (view space), w: wall shadow offset
    light: vec4<f32>,
};

@group(0) @binding(0) var<uniform> u: U;

struct VIn {
    @location(0) pos: vec3<f32>,
    @location(1) nrm: vec3<f32>,
    @location(2) sn: vec3<f32>,
};

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) n: vec3<f32>,
    @location(1) op: vec3<f32>,
};

@vertex
fn vs_main(v: VIn) -> VOut {
    var o: VOut;
    o.clip = u.vp * u.model * vec4<f32>(v.pos, 1.0);
    o.n = (u.rot * vec4<f32>(v.nrm, 0.0)).xyz;
    o.op = v.pos;
    return o;
}

// Inverted hull: the mesh pushed out along its smooth normal; front faces are culled.
@vertex
fn vs_outline(v: VIn) -> VOut {
    var o: VOut;
    o.clip = u.vp * u.model * vec4<f32>(v.pos + v.sn * u.params.w, 1.0);
    o.n = v.sn;
    o.op = v.pos;
    return o;
}

// Wall shadow: the volume flattened onto the wall plane, pushed down-right by its depth.
@vertex
fn vs_shadow(v: VIn) -> VOut {
    var o: VOut;
    let w = (u.model * vec4<f32>(v.pos, 1.0)).xyz;
    let k = u.light.w * (0.35 + max(w.z, 0.0));
    o.clip = u.vp * vec4<f32>(w.x + k, w.y - k * 1.4, -0.05, 1.0);
    o.n = vec3<f32>(0.0, 0.0, 1.0);
    o.op = v.pos;
    return o;
}

@fragment
fn fs_flat(i: VOut) -> @location(0) vec4<f32> {
    return vec4<f32>(u.shade.rgb * u.shade.a, u.shade.a);
}

fn hash3(p: vec3<f32>) -> f32 {
    var q = fract(p * 0.1031);
    q = q + dot(q, q.zyx + 31.32);
    return fract((q.x + q.y) * q.z);
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let n = normalize(i.n);
    let l = normalize(u.light.xyz);
    let ndl = dot(n, l);
    let base = u.color.rgb;
    let hi = mix(base, vec3<f32>(1.0, 1.0, 0.97), 0.5);
    let lo = u.shade.rgb;
    // half-lambert ramp, partly posterised so each facet prints as one tone
    let d = clamp(ndl * 0.5 + 0.5, 0.0, 1.0);
    let q = floor(d * 5.0 + 0.5) / 5.0;
    let dd = mix(d, q, 0.6);
    var c = mix(lo, base, smoothstep(0.3, 0.62, dd));
    c = mix(c, hi, smoothstep(0.78, 0.97, dd));
    // contact occlusion where the volume meets the wall
    c = c * mix(0.62, 1.0, smoothstep(0.0, 0.3, i.op.z));
    let rim = pow(1.0 - clamp(n.z, 0.0, 1.0), 3.0);
    c = c + rim * 0.08;
    // bolt socket where the bolt axis crosses the front of the volume
    let br = u.params.z;
    let bd = length(i.op.xy - vec2<f32>(0.06, 0.04));
    var hole = 0.0;
    if (br > 0.0 && i.op.z > 0.05) {
        hole = 1.0 - smoothstep(br * 0.9, br, bd);
        let ring = (1.0 - smoothstep(br * 1.5, br * 1.65, bd)) * (1.0 - hole);
        c = mix(c, lo * 0.85, ring * 0.6);
        c = mix(c, vec3<f32>(0.07, 0.075, 0.07), hole);
    }
    // chalk: sparse fine speckles, denser on the upward faces, none in the socket
    let cell = floor(i.op * 70.0 + u.params.y);
    let h = hash3(cell);
    let up = clamp(n.y * 0.7 + 0.45, 0.0, 1.0);
    let speck = step(1.0 - u.params.x * 0.22 * (0.3 + up), h) * (1.0 - hole);
    c = mix(c, vec3<f32>(0.98, 0.97, 0.94), speck * 0.9);
    let a = u.color.a;
    return vec4<f32>(c * a, a);
}
