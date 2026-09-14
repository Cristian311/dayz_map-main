# -*- coding: utf-8 -*-
"""
Stratul urban al generatorului: catalog de arhetipuri vanilla, retea stradala, cvartale,
loturi, zonare, plasare de cladiri si mobilier urban.

Nu depinde de Blender - totul e numpy + json, la fel ca `dayzgen.terrain`.
"""
from .catalog import Archetype, Catalog, CATEGORIES, STYLES  # noqa: F401

__all__ = ["Archetype", "Catalog", "CATEGORIES", "STYLES"]
