"""UserRecap view model, fixture instances, fonts, scripts and converters."""
import json
import os
from rml import E, col

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

VM_ID = '0:10'

# (name, type, default) -- the brief's schema, in order, followed by the
# documented additions (templates + runtime-owned sequencing state).
SCHEMA = [
    ('userName', 'string'), ('year', 'number'), ('periodLabel', 'string'), ('locale', 'string'),
    ('mealsCooked', 'number'), ('recipesTried', 'number'), ('cuisinesExplored', 'number'),
    ('newIngredients', 'number'), ('repeatRecipeCount', 'number'), ('sharedMeals', 'number'),
    ('cookingDays', 'number'), ('personaIndex', 'number'), ('personaName', 'string'),
    ('personaDescription', 'string'), ('personaColor', 'color'), ('autoAdvanceSeconds', 'number'),
    ('autoAdvanceEnabled', 'bool'), ('isPaused', 'bool'), ('reducedMotion', 'bool'),
    ('soundEnabled', 'bool'), ('currentScreen', 'number'), ('screenProgress', 'number'),
    ('shareIncludeName', 'bool'), ('shareIncludeSensitiveValues', 'bool'),
    ('continueLabel', 'string'), ('previousLabel', 'string'), ('pauseLabel', 'string'),
    ('playLabel', 'string'), ('shareLabel', 'string'), ('replayLabel', 'string'),
    ('introHeadline', 'string'), ('introSupport', 'string'), ('summaryHeadline', 'string'),
    ('summarySupport', 'string'), ('emptyHeadline', 'string'), ('emptySupport', 'string'),
    ('personaLabel', 'string'),
] + [(f'showScreen{i}', 'bool') for i in range(1, 11)] + [
    p for i in range(2, 9) for p in ((f'screen{i}Headline', 'string'), (f'screen{i}Support', 'string'), (f'screen{i}Unit', 'string'))
] + [('favoriteRecipeName', 'string')]

ADDITIONS = [
    # localized templates (host-supplied); the director assembles the derived sentence
    ('greetingTemplate', 'string', 'Hello, {name}!'),
    ('introHeadlineTemplate', 'string', 'Your {year} on Simmer'),
    ('screen6SupportTemplate', 'string', 'Your most-cooked recipe: {recipe}.'),
    ('greetingLine', 'string', ''),            # derived
    ('summaryNameLine', 'string', ''),         # derived (respects shareIncludeName)
    ('summaryRecipeLine', 'string', ''),       # derived (respects shareIncludeSensitiveValues)
    ('isSharing', 'bool', False),              # host clears it when the share sheet closes
    # runtime-owned sequencing state (written by the in-file director script)
    ('navDirection', 'number', 1),
    ('visibleCount', 'number', 10),
    ('currentSegment', 'number', 0),
    ('countProgress', 'number', 0),
    ('motionFrozen', 'bool', False),
    ('isEmptyRecap', 'bool', False),
    ('focusedControl', 'number', 0),
    ('recapComplete', 'bool', False),
    # requests written by controls / pot, consumed by the director
    ('navNextRequest', 'trigger', None), ('navPrevRequest', 'trigger', None),
    ('pauseToggleRequest', 'trigger', None), ('shareRequest', 'trigger', None),
    ('replayRequest', 'trigger', None), ('potTap', 'trigger', None),
    # signals written by the director, consumed by state machines / event listeners
    ('handoffForward', 'trigger', None), ('handoffBack', 'trigger', None),
    ('recapFinishedSignal', 'trigger', None),
]

PROPS = {}
TYPES = {}
_n = 11
for name, t in SCHEMA:
    PROPS[name] = f'0:{_n}'
    TYPES[name] = t
    _n += 1
for name, t, _d in ADDITIONS:
    PROPS[name] = f'0:{_n}'
    TYPES[name] = t
    _n += 1
assert _n < 400


def P(name):
    return f'{VM_ID}-{PROPS[name]}'


PERSONAS = [
    ('Flavor Explorer', 'Always room for a new flavor.', 'FFFFEDB0'),
    ('Comfort Cook', 'You make familiar things feel special.', 'FF48293D'),
    ('Batch Wizard', 'You turn a little planning into good meals.', 'FF4D7655'),
    ('Weekend Baker', 'You make time for something warm from the oven.', 'FFE44932'),
]


def load_fixture(name):
    with open(os.path.join(ROOT, 'fixtures', name)) as f:
        return json.load(f)


def _inst_value(name, t, v):
    pid = PROPS[name]
    if t == 'number':
        return E('ViewModelInstanceNumber', propertyValue=float(v), viewModelPropertyId=pid)
    if t == 'string':
        return E('ViewModelInstanceString', propertyValue=str(v), viewModelPropertyId=pid)
    if t == 'bool':
        return E('ViewModelInstanceBoolean', propertyValue=bool(v), viewModelPropertyId=pid)
    if t == 'color':
        s = str(v).lstrip('#')
        if len(s) == 6:
            s = 'FF' + s
        return E('ViewModelInstanceColor', propertyValue=s.upper(), viewModelPropertyId=pid)
    if t == 'trigger':
        return E('ViewModelInstanceTrigger', viewModelPropertyId=pid)
    raise ValueError(t)


def instance(inst_name, fixture, inst_id):
    vi = E('ViewModelInstance', exports=True, name=inst_name, id=inst_id)
    for name, t in SCHEMA:
        vi.add(_inst_value(name, t, fixture[name]))
    for name, t, d in ADDITIONS:
        v = fixture.get(name, d)
        vi.add(_inst_value(name, t, v))
    return vi


def view_model(instances):
    vm = E('ViewModel', name='UserRecap', id=VM_ID, defaultInstanceId=instances[0].id)
    for name, t in SCHEMA:
        vm.add(_prop(name, t))
    for name, t, _d in ADDITIONS:
        vm.add(_prop(name, t))
    vm.add(*instances)
    return vm


def _prop(name, t):
    tag = {'number': 'ViewModelPropertyNumber', 'string': 'ViewModelPropertyString', 'bool': 'ViewModelPropertyBoolean',
           'color': 'ViewModelPropertyColor', 'trigger': 'ViewModelPropertyTrigger'}[t]
    return E(tag, name=name, id=PROPS[name])


# ------------------------------------------------------------- fonts
FONT_DISPLAY = '0:501'
FONT_BODY = '0:502'
FONT_HAND = '0:503'
SCRIPT_DIRECTOR = '0:511'
SCRIPT_FORMAT = '0:512'
SCRIPT_AUDIT = '0:513'
SCRIPT_RISO = '0:514'
SCRIPT_STEAM = '0:515'
SCRIPT_CLOTH = '0:516'
SCRIPT_LETTERS = '0:517'
CONV_FORMAT = '0:521'
CONV_INT = '0:522'


def assets():
    return [
        E('FontAsset', file='assets/fonts/BricolageGrotesque.ttf', name='Bricolage Grotesque', id=FONT_DISPLAY),
        E('FontAsset', file='assets/fonts/SourceSans3.ttf', name='Source Sans 3', id=FONT_BODY),
        E('FontAsset', file='assets/fonts/Caveat.ttf', name='Caveat', id=FONT_HAND),
        E('ScriptAsset', file='scripts/director.luau', name='director', id=SCRIPT_DIRECTOR),
        E('ScriptAsset', file='scripts/formatCount.luau', name='formatCount', id=SCRIPT_FORMAT),
        E('ScriptAsset', file='scripts/eventAudit.luau', name='eventAudit', id=SCRIPT_AUDIT),
        E('ScriptAsset', file='scripts/riso.luau', name='riso', id=SCRIPT_RISO),
        E('ScriptAsset', file='scripts/steam.luau', name='steam', id=SCRIPT_STEAM),
        E('ScriptAsset', file='scripts/cloth.luau', name='cloth', id=SCRIPT_CLOTH),
        E('ScriptAsset', file='scripts/letters.luau', name='letters', id=SCRIPT_LETTERS),
        E('ScriptedDataConverter', scriptAssetId=SCRIPT_FORMAT, name='Format count (locale)', id=CONV_FORMAT),
        E('DataConverterToString', decimals=0, round=True, name='Integer', id=CONV_INT),
    ]


# ------------------------------------------------------------- converters registry
CONVERTERS = []


def add_conv(el):
    CONVERTERS.append(el)
    return el.id


def formula(name, tokens):
    return add_conv(E('DataConverterFormula', tokens, name=name))


def T_in():
    return E('FormulaTokenInput')


def T_v(v):
    return E('FormulaTokenValue', operationValue=float(v))


def T_p(prop):
    from rml import bind
    return E('FormulaTokenValue', [bind(P(prop), 777)])


def T_op(o):
    return E('FormulaTokenOperation', operationType={'+': 0, '-': 1, '*': 2, '/': 3}[o])


def T_fn(f):
    return E('FormulaTokenFunction', functionType={'min': 0, 'max': 1, 'round': 2, 'sqrt': 5, 'pow': 6}[f])


def T_sep():
    return E('FormulaTokenArgumentSeparator')


def T_open():
    return E('FormulaTokenParenthesisOpen')


def T_close():
    return E('FormulaTokenParenthesisClose')


_count_cache = {}


def count_converter(scene):
    """value * gate, gate = max(countProgress, min(1, sqrt(pow(currentScreen-scene,2)))), rounded, then locale formatted."""
    if scene in _count_cache:
        return _count_cache[scene]
    f = formula(f'Count-up scene {scene}', [
        T_fn('round'),
        T_in(), T_op('*'),
        T_fn('max'), T_p('countProgress'), T_sep(),
        T_fn('min'), T_v(1), T_sep(),
        T_fn('sqrt'), T_fn('pow'), T_p('currentScreen'), T_op('-'), T_v(scene), T_sep(), T_v(2), T_close(), T_close(),
        T_close(), T_close(),
        T_close(),
    ])
    g = E('DataConverterGroup', [E('DataConverterGroupItem', converterId=f), E('DataConverterGroupItem', converterId=CONV_FORMAT)],
          name=f'Count-up + format scene {scene}')
    add_conv(g)
    _count_cache[scene] = g.id
    return g.id
