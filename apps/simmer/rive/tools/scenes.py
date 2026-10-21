"""Scene dispatch."""
from scene_base import Scene, hero_number, copy_styles
from data import count_converter
from text import style, text

NAMES = {1: 'S1 Invitation', 2: 'S2 Meals cooked', 3: 'S3 Recipes tried', 4: 'S4 Cuisines explored', 5: 'S5 New ingredients',
         6: 'S6 Favorite recipe', 7: 'S7 Shared meals', 8: 'S8 Cooking days', 9: 'S9 Persona', 10: 'S10 Summary'}
METRIC = {2: 'mealsCooked', 3: 'recipesTried', 4: 'cuisinesExplored', 5: 'newIngredients', 6: 'repeatRecipeCount', 7: 'sharedMeals', 8: 'cookingDays'}


def stub(k, x_stage):
    sc = Scene(k, NAMES[k], x_stage)
    if k in METRIC:
        hn = hero_number(sc, METRIC[k], count_converter(k), 24, 100)
        u, h, s = copy_styles()
        tb = sc.text_block(24, 226, 342, [(u, 'unit', f'screen{k}Unit'), (h, 'Headline', f'screen{k}Headline'), (s, 'Support', f'screen{k}Support')])
        sc.reveal_text(tb, 900, 1800)
        sc.key(hn, 'opacity', [(0, 0.0, 'hold'), (200, 0.0, 'soft'), (500, 1.0)])
        sc.inner.add(hn, tb)
    return sc


def build_scene(k, x_stage):
    import scenes_impl
    fn = getattr(scenes_impl, f'scene{k}', None)
    if fn is None:
        return stub(k, x_stage)
    return fn(x_stage)


def extra_components():
    import scenes_impl
    return getattr(scenes_impl, 'EXTRA', [])
