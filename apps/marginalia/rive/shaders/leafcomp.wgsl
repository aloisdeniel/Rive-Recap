// Marginalia leaf compositing: puts a page's scripted 3D objects (books,
// theatre, lamp - scripts/etch3d.luau) onto the page texture of a turning leaf.
//
// A 2D canvas cannot draw an image that the GPU rendered in the same frame,
// so while a page is rendered into its leaf canvas its 3D objects draw
// nothing; a second, half-resolution render of the page has them draw a pure
// magenta key over their box instead. This pass then draws each object's own
// GPU texture as a quad (its box, placed by the object's world transform) into
// the leaf canvas, kept only where the key survived - i.e. where nothing on
// the page lies above the object - so the page's layering is preserved
// (ribbons over the book, the door over the book, the light cone over the
// stage). Premultiplied over; no `discard`.

struct U {
    c01: vec4<f32>,   // quad corners in leaf pixels: p0.xy, p1.xy (top-left, top-right)
    c23: vec4<f32>,   // p2.xy, p3.xy (bottom-left, bottom-right)
    size: vec4<f32>,  // leaf canvas size (px), opacity, unused
};

@group(0) @binding(0) var<uniform> u: U;
@group(0) @binding(1) var objTex: texture_2d<f32>;
@group(0) @binding(2) var keyTex: texture_2d<f32>;
@group(0) @binding(3) var smp: sampler;

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) uv: vec2<f32>,
    @location(1) kp: vec2<f32>,
};

@vertex
fn vs_main(@builtin(vertex_index) vi: u32) -> VOut {
    var ids = array<u32, 6>(0u, 1u, 2u, 2u, 1u, 3u);
    var uvs = array<vec2<f32>, 4>(vec2<f32>(0.0, 0.0), vec2<f32>(1.0, 0.0), vec2<f32>(0.0, 1.0), vec2<f32>(1.0, 1.0));
    let k = ids[vi];
    var p = u.c01.xy;
    if (k == 1u) { p = u.c01.zw; }
    if (k == 2u) { p = u.c23.xy; }
    if (k == 3u) { p = u.c23.zw; }
    var o: VOut;
    o.clip = vec4<f32>(p.x / u.size.x * 2.0 - 1.0, 1.0 - p.y / u.size.y * 2.0, 0.0, 1.0);
    o.uv = uvs[k];
    o.kp = p / u.size.xy;
    return o;
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let obj = textureSample(objTex, smp, i.uv);
    let key = textureSample(keyTex, smp, i.kp);
    // pure magenta only where the object was the top-most thing drawn
    let m = smoothstep(0.45, 0.9, min(key.r, key.b) - key.g);
    let a = m * u.size.z;
    return obj * a;
}
