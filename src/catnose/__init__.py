# -*- coding: utf-8 -*-
"""
catnose — Motor de transformación declarativa de JSON.

Uso básico::

    from catnose import transform

    result = transform(items, mapper)

Para usar el motor de plantillas directamente::

    from catnose import template_engine

    html = template_engine.render("Hola {{ name }}", {"name": "mundo"})
"""

from ._core import transform
from . import _template as template_engine

__all__ = ["transform", "template_engine"]
__version__ = "0.1.0"
