// Stash arcade screen: a CRT treatment over scene 6's month windows.
//
// One fullscreen triangle over the window board. It draws no windows itself
// (the vector windows underneath keep every binding); it adds what vector
// cannot: phosphor bloom that spills from each lit window by how lit it is,
// fine scanlines, a slow soft refresh band, a curved-glass sheen and a vignette.
// Output is premultiplied with the glow in rgb and only the darkening in alpha,
// so the glow composites additively over the board.

struct U {
    a: vec4<f32>,     // canvas half width, half height (pt), refresh band y (pt), opacity
    lit0: vec4<f32>,  // lit amount per window, row-major
    lit1: vec4<f32>,
    lit2: vec4<f32>,
    glow: vec4<f32>,  // glow rgb, strength
    grid: vec4<f32>,  // column pitch, row pitch, window half width, window half height
    board: vec4<f32>, // board half width, half height, corner radius, scanline pitch
};

@group(0) @binding(0) var<uniform> u: U;

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) p: vec2<f32>,
};

@vertex
fn vs_main(@builtin(vertex_index) vi: u32) -> VOut {
    var o: VOut;
    let x = f32((vi << 1u) & 2u) * 2.0 - 1.0;
    let y = f32(vi & 2u) * 2.0 - 1.0;
    o.clip = vec4<f32>(x, y, 0.0, 1.0);
    o.p = vec2<f32>(x * u.a.x, -y * u.a.y);
    return o;
}

fn sdRound(p: vec2<f32>, b: vec2<f32>, r: f32) -> f32 {
    let q = abs(p) - b + vec2<f32>(r);
    return length(max(q, vec2<f32>(0.0))) + min(max(q.x, q.y), 0.0) - r;
}

fn litAt(i: i32) -> f32 {
    let r = i / 4;
    let c = i % 4;
    var v = u.lit0;
    if (r == 1) { v = u.lit1; }
    if (r == 2) { v = u.lit2; }
    if (c == 0) { return v.x; }
    if (c == 1) { return v.y; }
    if (c == 2) { return v.z; }
    return v.w;
}

@fragment
fn fs_main(i: VOut) -> @location(0) vec4<f32> {
    let p = i.p;
    let board = sdRound(p, u.board.xy, u.board.z);
    // soft outer bloom may spill a little past the board; nothing beyond it
    if (board > 26.0) {
        return vec4<f32>(0.0);
    }
    var glow = 0.0;
    var inside = 0.0;
    for (var k = 0; k < 12; k++) {
        let r = f32(k / 4);
        let c = f32(k % 4);
        let centre = vec2<f32>((c - 1.5) * u.grid.x, (r - 1.0) * u.grid.y);
        let d = sdRound(p - centre, u.grid.zw, 9.0);
        let l = litAt(k);
        glow = glow + l * exp(-max(d, 0.0) / 13.0) * select(0.5, 0.22, d < 0.0);
        inside = max(inside, l * (1.0 - smoothstep(-1.0, 1.0, d)));
    }
    let inBoard = 1.0 - smoothstep(-1.0, 1.0, board);
    // scanlines: darker gaps between lines, a little brighter where phosphor glows
    let pitch = u.board.w;
    let line = 0.5 + 0.5 * cos(p.y * 6.2831853 / pitch);
    var dark = inBoard * (0.06 + 0.1 * line) * (1.0 - inside * 0.6);
    // a slow refresh band rolls down the glass
    let band = exp(-pow((p.y - u.a.z) / 16.0, 2.0)) * inBoard;
    // curved glass: a broad sheen top-left and a vignette into the corners
    let sheen = exp(-pow(length((p - vec2<f32>(-u.board.x * 0.45, -u.board.y * 0.55)) / vec2<f32>(u.board.x * 0.7, u.board.y * 0.38)), 2.0) * 2.2);
    let edge = smoothstep(-34.0, 0.0, board) * inBoard;
    dark = dark + edge * 0.28;
    let g = u.glow.rgb * u.glow.a;
    var col = g * glow * (0.85 + 0.15 * line) + g * inside * line * 0.12;
    col = col + vec3<f32>(1.0, 0.95, 0.9) * (band * 0.05 + sheen * 0.07 * inBoard);
    let a = u.a.w;
    return vec4<f32>(col * a, clamp(dark, 0.0, 1.0) * a);
}
