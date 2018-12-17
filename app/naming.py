import random
import typing as t

from app.reporting import get_logger


log = get_logger("naming")

adjectives = [
    "adroit",
    "angelic",
    "arcane",
    "austere",
    "baleful",
    "blessed",
    "blighted",
    "broken",
    "budget",
    "cruel",
    "cursed",
    "cynical",
    "despairing",
    "divine",
    "doomed",
    "eternal",
    "evil",
    "fanciful",
    "feathered",
    "flaming",
    "fluorescent",
    "frail",
    "fragile",
    "gruff",
    "hearty",
    "infernal",
    "irritating",
    "lazy",
    "leeching",
    "magnanimous",
    "magnificent",
    "malevolent",
    "merciful",
    "mischievous",
    "onerous",
    "pious",
    "robust",
    "royal",
    "sacred",
    "splendid",
    "sturdy",
    "terrible",
    "vicious",
    "woeful",
]

nouns = [
    "axe",
    "amulet",
    "blade",
    "bow",
    "brooch",
    "cloak",
    "crossbow",
    "cuirass",
    "dagger",
    "elixir",
    "flamberge",
    "flail",
    "gauntlets",
    "gladius",
    "glave",
    "gloves",
    "greaves",
    "halberd",
    "helm",
    "key",
    "lance",
    "longbow",
    "lute",
    "mantle",
    "morningstar",
    "ocarina",
    "pauldron",
    "pendant",
    "polearm",
    "potion",
    "quiver",
    "relic",
    "robe",
    "sceptre",
    "scythe",
    "spear",
    "staff",
    "tiara",
    "torch",
    "wand",
]


def maxify(a: str, b: str) -> t.List[str]:
    """Applies the Max Woodhams naming algorithm to word pair a-b."""
    if a[0] == b[0]:
        start = 1
    else:
        start = 0
    for i, ch in enumerate(a[start:], start):
        if b[0] == ch:
            name = a[:i] + b
            log.debug(f"Name {a}-{b} has been maxified to {name}.")
            return [name]
    return [a, b]


def new() -> str:
    a, b = random.choice(adjectives), random.choice(nouns)
    if random.random() <= 0.5:
        return "-".join(maxify(random.choice(adjectives), random.choice(nouns)))
    else:
        return f"{a}-{b}"
