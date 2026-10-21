// Patchwork cloth ground: a fine plain-weave cotton texture with slubbed
// threads and soft felted mottling, generated once on the GPU and multiplied
// over the whole recap so every patch, panel and button reads as fabric.
// Output is a multiply layer: 1.0 leaves the artwork untouched.

struct U {
    size: vec4<f32>,  // x,y canvas px, z px per point, w seed
    look: vec4<f32>,  // x weave depth, y slub, z mottle, w edge shade
};

@group(0) @binding(0) var<uniform> u: U;

const PI: f32 = 3.14159265;

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
    for (var i = 0; i < 4; i = i + 1) {
        s = s + a * vnoise(q);
        q = q * 2.03 + vec2<f32>(17.1, 9.7);
        a = a * 0.5;
    }
    return s;
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
    let pt = i.uv * u.size.xy / u.size.z;           // points
    let seed = vec2<f32>(u.size.w, u.size.w * 1.7);
    // plain weave: warp and weft alternate over/under; each thread is rounded
    let per = 2.2;
    let a = pt / per;
    let cx = i32(floor(a.x));
    let cy = i32(floor(a.y));
    let over = ((cx + cy) & 1) == 1;
    let fx = fract(a.x);
    let fy = fract(a.y);
    // thread body: bright crown, darker where it dives under its neighbour
    let warp = sin(PI * fx) * (0.65 + 0.35 * sin(PI * fy));
    let weft = sin(PI * fy) * (0.65 + 0.35 * sin(PI * fx));
    let thread = select(weft, warp, over);
    // slubs: each thread is a little thicker / lighter along its length
    let slubW = vnoise(vec2<f32>(floor(a.x) * 3.1, pt.y * 0.05) + seed);
    let slubF = vnoise(vec2<f32>(pt.x * 0.05, floor(a.y) * 3.1) + seed);
    let slub = select(slubF, slubW, over) - 0.5;
    // felted mottling at a larger scale, and a whisper of fibre fuzz
    let mottle = fbm(pt * 0.03 + seed * 0.3) - 0.5;
    let fuzz = vnoise(pt * 0.9 + seed) - 0.5;
    var m = 1.0 - u.look.x * (1.0 - thread) - u.look.y * slub - u.look.z * mottle - 0.012 * fuzz;
    // soft edge shade, as if the whole recap were a piece of cloth on a table
    let e = min(min(i.uv.x, 1.0 - i.uv.x) * u.size.x, min(i.uv.y, 1.0 - i.uv.y) * u.size.y) / u.size.z;
    m = m * (1.0 - u.look.w * (1.0 - smoothstep(0.0, 34.0, e)));
    m = clamp(m, 0.0, 1.0);
    let warm = vec3<f32>(1.0, 0.985, 0.96);
    let col = mix(vec3<f32>(1.0), warm, clamp((1.0 - m) * 5.0, 0.0, 1.0)) * m;
    return vec4<f32>(col, 1.0);
}
