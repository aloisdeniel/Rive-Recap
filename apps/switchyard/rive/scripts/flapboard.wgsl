// Switchyard split-flap departure board (scene 8).
//
// Twelve modules drawn as instanced quads in perspective: a static top half
// (next character), a static bottom half (current character) and the falling flap,
// which shows the current top half on its face and the next bottom half on its back
// as it swings past vertical toward the viewer. Characters are two-digit month
// numbers printed as a 5x7 dot matrix. Everything about the roll - stagger, the
// random numbers a module passes through, gravity on the flap, the idle "ticks" -
// is computed here from three uniforms, so the timeline only keys `roll` and `idle`.

struct U {
    vp: mat4x4<f32>,
    // x: roll 0..1, y: idle phase 0..1, z: active months (lit modules), w: flips per module
    a: vec4<f32>,
    // x: tile width, y: tile height, z: columns, w: stagger (roll units per module)
    b: vec4<f32>,
    // x: column pitch, y: row pitch, z: unused, w: unused
    c: vec4<f32>,
};

@group(0) @binding(0) var<uniform> u: U;

struct VIn {
    @location(0) corner: vec3<f32>,   // x: role (0 top, 1 bottom, 2 flap), y: u 0..1, z: v 0..1 (0 = hinge)
    @location(1) tile: vec2<f32>,     // instance: x: module index, y: unused
};

struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) uv: vec2<f32>,                 // u across, v away from the hinge
    @location(1) @interpolate(flat) chars: vec4<f32>,   // x: current code, y: next code, z: role, w: lit
    @location(2) shade: f32,
};

fn hash1(n: f32) -> f32 {
    return fract(sin(n * 12.9898 + 4.1414) * 43758.5453);
}

// two-digit code shown by module i after k flips (k >= flips: its month; 0: blank)
fn code_at(i: f32, k: f32) -> f32 {
    let flips = u.a.w;
    if (k >= flips) {
        return i + 1.0;
    }
    if (k < 0.5) {
        return -1.0;
    }
    return floor(hash1(i * 17.0 + k * 3.0) * 99.0);
}

// flap progress of module i: (flips completed, fraction of the current flip)
fn progress(i: f32) -> vec2<f32> {
    let flips = u.a.w;
    let stagger = u.b.w;
    let r = clamp((u.a.x - i * stagger) / max(1.0 - 11.0 * stagger, 0.01), 0.0, 1.0) * flips;
    var k = floor(r);
    var f = r - k;
    if (r >= flips) {
        k = flips;
        f = 0.0;
        // idle ticks: two modules at a time make one same-character flip per window
        let ph = u.a.y;
        let w0 = hash1(i * 5.0 + 1.0) * 0.85;
        let t = (ph - w0) / 0.06;
        if (t > 0.0 && t < 1.0) {
            f = t;
        }
    }
    return vec2<f32>(k, f);
}

@vertex
fn vs_main(v: VIn) -> VOut {
    var o: VOut;
    let i = v.tile.x;
    let cols = u.b.z;
    let col = i - floor(i / cols) * cols;
    let row = floor(i / cols);
    let cx = (col - (cols - 1.0) * 0.5) * u.c.x;
    let cy = -(row - 1.0) * u.c.y;
    let hw = u.b.x * 0.5;
    let hh = u.b.y * 0.5;
    let role = v.corner.x;
    let x = cx + (v.corner.y - 0.5) * u.b.x;
    let pr = progress(i);
    // gravity: the flap accelerates as it falls and lands with a small rebound
    let f = pr.y;
    var th = 3.14159265 * f * f * (1.0 + 0.6 * (1.0 - f));
    th = min(th, 3.14159265);
    var p = vec3<f32>(x, cy, 0.0);
    var shade = 1.0;
    if (role < 0.5) {
        p = vec3<f32>(x, cy + v.corner.z * hh, -0.002);
    } else if (role < 1.5) {
        p = vec3<f32>(x, cy - v.corner.z * hh, -0.002);
        // the falling flap shades the lower half as it closes in
        shade = 1.0 - 0.35 * smoothstep(0.35, 0.9, f) * (1.0 - smoothstep(0.95, 1.0, f));
    } else {
        let y = v.corner.z * hh;
        p = vec3<f32>(x, cy + y * cos(th), y * sin(th) + 0.002);
        shade = 0.55 + 0.45 * abs(cos(th));
    }
    o.clip = u.vp * vec4<f32>(p, 1.0);
    o.uv = vec2<f32>(v.corner.y, v.corner.z);
    let cur = code_at(i, pr.x);
    let nxt = code_at(i, pr.x + 1.0);
    var lit = 0.0;
    if (i < u.a.z) {
        lit = 1.0;
    }
    o.chars = vec4<f32>(cur, nxt, role, lit);
    o.shade = shade;
    return o;
}

// 5x7 dot-matrix digits: rows top->bottom, bit 4 = left column
fn row_bits(d: i32, r: i32) -> u32 {
    var g = array<u32, 7>(0u, 0u, 0u, 0u, 0u, 0u, 0u);
    switch d {
        case 0: { g = array<u32, 7>(14u, 17u, 17u, 17u, 17u, 17u, 14u); }
        case 1: { g = array<u32, 7>(4u, 12u, 4u, 4u, 4u, 4u, 14u); }
        case 2: { g = array<u32, 7>(14u, 17u, 1u, 2u, 4u, 8u, 31u); }
        case 3: { g = array<u32, 7>(31u, 2u, 4u, 2u, 1u, 17u, 14u); }
        case 4: { g = array<u32, 7>(2u, 6u, 10u, 18u, 31u, 2u, 2u); }
        case 5: { g = array<u32, 7>(31u, 16u, 30u, 1u, 1u, 17u, 14u); }
        case 6: { g = array<u32, 7>(6u, 8u, 16u, 30u, 17u, 17u, 14u); }
        case 7: { g = array<u32, 7>(31u, 1u, 2u, 4u, 8u, 8u, 8u); }
        case 8: { g = array<u32, 7>(14u, 17u, 17u, 14u, 17u, 17u, 14u); }
        case 9: { g = array<u32, 7>(14u, 17u, 17u, 15u, 1u, 2u, 12u); }
        default: { g = array<u32, 7>(0u, 0u, 0u, 0u, 0u, 0u, 0u); }
    }
    return g[r];
}

// coverage of the dot matrix for a two-digit code at tile-space point q (0..1 x, 0..1 y top->bottom)
fn matrix(code: f32, q: vec2<f32>, aspect: f32) -> vec2<f32> {
    // 11 x 7 grid of dot cells centred on the tile
    let cell = 0.118;                 // in tile-height units
    let gw = 11.0 * cell;
    let gh = 7.0 * cell;
    let px = (q.x - 0.5) * aspect + gw * 0.5;
    let py = q.y - 0.5 + gh * 0.5;
    let cx = floor(px / cell);
    let cy = floor(py / cell);
    if (cx < 0.0 || cx > 10.0 || cy < 0.0 || cy > 6.0) {
        return vec2<f32>(0.0, 0.0);
    }
    let local = vec2<f32>(px - (cx + 0.5) * cell, py - (cy + 0.5) * cell);
    let d = length(local) / cell;
    let dotc = 1.0 - smoothstep(0.33, 0.42, d);
    var on = 0.0;
    if (cx != 5.0 && code >= 0.0) {
        var digit = i32(floor(code / 10.0));
        var colx = i32(cx);
        if (cx > 5.0) {
            digit = i32(code - floor(code / 10.0) * 10.0);
            colx = i32(cx) - 6;
        }
        let bits = row_bits(digit, i32(cy));
        if (((bits >> u32(4 - colx)) & 1u) == 1u) {
            on = 1.0;
        }
    }
    return vec2<f32>(dotc * on, dotc);
}

@fragment
fn fs_main(i: VOut, @builtin(front_facing) ff: bool) -> @location(0) vec4<f32> {
    let role = i.chars.z;
    let aspect = u.b.x / u.b.y;
    // which character and which half
    var code = i.chars.x;
    var top = true;
    if (role < 0.5) {
        code = i.chars.y;
    } else if (role < 1.5) {
        top = false;
    } else if (!ff) {
        code = i.chars.y;
        top = false;
    }
    // tile-space y (0 top .. 1 bottom); v runs away from the hinge in both halves
    var ty = 0.5 - i.uv.y * 0.5;
    if (!top) {
        ty = 0.5 + i.uv.y * 0.5;
    }
    let q = vec2<f32>(i.uv.x, ty);
    let lit = i.chars.w;
    let m = matrix(code, q, aspect);
    // tile body: dark grey, slightly lighter on the top half, rounded hinge gap
    var body = vec3<f32>(0.165, 0.188, 0.22);
    if (!top) {
        body = vec3<f32>(0.14, 0.16, 0.19);
    }
    let edge = smoothstep(0.0, 0.035, i.uv.y);
    body = body * mix(0.45, 1.0, edge);
    let on_col = mix(vec3<f32>(0.42, 0.42, 0.4), vec3<f32>(1.0, 0.839, 0.294), lit);
    let off_col = body * 1.35;
    var c = mix(body, off_col, m.y * 0.6);
    c = mix(c, on_col, m.x);
    c = c * i.shade;
    return vec4<f32>(c, 1.0);
}
