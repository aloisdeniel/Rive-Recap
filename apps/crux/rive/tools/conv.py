"""Data converters (root elements), deduplicated by name."""
from rml import E, bind
import model

CONVS = []
_BY_NAME = {}

OPS = {"+": 0, "-": 1, "*": 2, "/": 3}
FNS = {"min": 0, "max": 1, "round": 2, "ceil": 3, "floor": 4}


def _reg(name, el):
    if name in _BY_NAME:
        return _BY_NAME[name]
    CONVS.append(el)
    _BY_NAME[name] = el.id
    return el.id


def formula(name, toks):
    f = E("DataConverterFormula", name=name)
    for t in toks:
        kind = t[0]
        if kind == "in":
            f.add(E("FormulaTokenInput"))
        elif kind == "v":
            f.add(E("FormulaTokenValue", operationValue=t[1]))
        elif kind == "b":
            f.add(E("FormulaTokenValue", operationValue=0, kids=[bind(model.path(t[1]), 777)]))
        elif kind == "rb":
            f.add(E("FormulaTokenValue", operationValue=0, kids=[bind(model.rig_path(t[1]), 777)]))
        elif kind == "op":
            f.add(E("FormulaTokenOperation", operationType=OPS[t[1]]))
        elif kind == "fn":
            f.add(E("FormulaTokenFunction", functionType=FNS[t[1]]))
        elif kind == "(":
            f.add(E("FormulaTokenParenthesisOpen"))
        elif kind == ")":
            f.add(E("FormulaTokenParenthesisClose"))
        elif kind == ",":
            f.add(E("FormulaTokenArgumentSeparator"))
    return _reg(name, f)


def clamp01(inner):
    return [("fn", "min"), ("v", 1), (",",), ("fn", "max"), ("v", 0), (",",)] + inner + [(")",), (")",)]


def range_map(name, i0, i1, o0, o1, clamp=True):
    return _reg(name, E("DataConverterRangeMapper", minInput=i0, maxInput=i1, minOutput=o0, maxOutput=o1,
                        clampLower=clamp or None, clampUpper=clamp or None, name=name))


def to_string0():
    return _reg("ToString0", E("DataConverterToString", decimals=0, round=True, name="ToString0"))


def equals(n, name_prefix="Is"):
    """1 when input == n (integers), else 0:  max(0, 1 - (in-n)*(in-n))."""
    return formula(f"{name_prefix} {n}", [("fn", "max"), ("v", 0), (",",), ("v", 1), ("op", "-"),
                                          ("(",), ("in",), ("op", "-"), ("v", n), (")",), ("op", "*"),
                                          ("(",), ("in",), ("op", "-"), ("v", n), (")",), (")",)])


def step_visible(c, name):
    """clamp(input - c, 0, 1): visible once input exceeds c."""
    return formula(name, clamp01([("in",), ("op", "-"), ("v", c)]))


def hidden_after(j, name):
    """displayValue for progress slot j: 0 (flex) when j <= input, 1 (none) otherwise."""
    return formula(name, clamp01([("v", j), ("op", "-"), ("in",)]))


def lerp(a, b):
    """a + (b - a) * input: bound to the rig's `wide` (0 tall .. 1 wide) it morphs a value
    between the portrait (tall) and the landscape (wide) arrangement."""
    a, b = round(float(a), 2), round(float(b), 2)
    return formula(f"Lerp {a} {b}", [("v", a), ("op", "+"), ("(",), ("v", round(b - a, 2)), ("op", "*"), ("in",), (")",)])


def affine(mul, add, name=None):
    """input * mul + add."""
    mul, add = round(float(mul), 4), round(float(add), 2)
    return formula(name or f"Affine {mul} {add}", [("(",), ("in",), ("op", "*"), ("v", mul), (")",), ("op", "+"), ("v", add)])


def scaled_progress(div, offset, name):
    """clamp((input - offset)/div, 0, 1) * heroProgress."""
    return formula(name, clamp01([("(",), ("in",), ("op", "-"), ("v", offset), (")",), ("op", "/"), ("v", div)])
                   + [("op", "*"), ("b", "heroProgress")])
