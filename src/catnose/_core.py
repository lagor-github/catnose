# -*- coding: utf-8 -*-
"""
Lógica central de transformación declarativa de JSON.

El JSON transformado parte de un objeto vacío; sólo se incluyen los campos
que aparecen explícitamente en el mapeador.  El JSON original actúa como
contexto de evaluación (junto con los campos ya calculados en orden).

Formato del mapeador::

  {
    "<campo_destino>": "<campo_origen>",        # shorthand: equiv. a {"_name": "<campo_origen>"}
    "<campo_destino>": {                        # mapping completo
      "_name":   "<campo_origen>",              # campo del JSON original (por defecto: <campo_destino>)
      "_cases":  {"v1": "nv1", ..., "_default": "<por_defecto>"},
      "_value":  "cadena con {{ expr }}"
    },
    "<campo_lista>": {                          # lista-de-objetos (sin claves de control)
      "<sub_campo>": {
        "_name":   "<campo_origen>",
        "_cases":  {...},
        "_value":  "{{ expr }}"
      }
    }
  }

Un mapping dict se trata como lista-de-objetos cuando no contiene ninguna de
las claves de control ('_name', '_cases', '_value') en su nivel raíz.
"""

import ast

from . import _template as template_engine

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_K_NAME    = "_name"
_K_CASES   = "_cases"
_K_VALUE   = "_value"
_K_DEFAULT = "_default"

_MAPPING_CONTROL_KEYS = frozenset((_K_NAME, _K_CASES, _K_VALUE))


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _parse_list(val) -> list:
  """Parsea un campo que puede ser lista Python o string repr de lista."""
  if isinstance(val, list):
    return val
  if isinstance(val, str):
    try:
      return ast.literal_eval(val)
    except Exception:
      return []
  return []


def _apply_field_to_item(item: dict, field: str, mapping: dict, ctx: dict) -> None:
  """Escribe en item[field] el valor calculado desde ctx. `_name` indica el campo fuente en ctx."""
  src = mapping.get(_K_NAME, field)
  if _K_CASES in mapping:
    original = ctx.get(src)
    new_value = mapping[_K_CASES].get(str(original), mapping[_K_CASES].get(_K_DEFAULT, original))
  elif _K_VALUE in mapping:
    new_value = template_engine.render(mapping[_K_VALUE], ctx)
  else:
    new_value = ctx.get(src)
  item[field] = new_value


def _apply_list_sub_mappings(lst: list, sub_mappings: dict, row_ctx: dict) -> list:
  """Aplica sub_mappings a cada elemento de una lista de objetos."""
  result = []
  for elem in _parse_list(lst):
    if not isinstance(elem, dict):
      result.append(elem)
      continue
    new_elem = dict(elem)
    elem_ctx = {**row_ctx, **elem}
    for sub_field, sub_mapping in sub_mappings.items():
      _apply_field_to_item(new_elem, sub_field, sub_mapping, elem_ctx)
    result.append(new_elem)
  return result


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def transform(items: list | dict, mapper: dict) -> list | dict:
  """
  Transforma cada elemento de `items` aplicando `mapper`.

  Si `items` es un objeto JSON (dict), se trata como una lista con un único
  elemento y se le asigna ``_rownum = 1``.

  El resultado de cada elemento parte de un objeto vacío; sólo se incluyen los
  campos definidos en el mapeador.  El elemento original (más ``_rownum`` y
  los campos ya calculados) actúa como contexto de evaluación.

  :param items:  Array de objetos a transformar, o un único objeto JSON.
  :param mapper: Descripción de las transformaciones (ver formato arriba).
  """
  is_list = True
  if isinstance(items, dict):
    items = [items]
    is_list = False
  elif not isinstance(items, list):
    raise TypeError("La entrada debe ser una lista o un objeto JSON")

  result = []
  for _rownum, row in enumerate(items, 1):
    new_item: dict = {}
    ctx = {**row, "_rownum": _rownum}
    for field, mapping in mapper.items():
      if isinstance(mapping, str):
        new_item[field] = ctx.get(mapping)
      elif not _MAPPING_CONTROL_KEYS.intersection(mapping):
        new_item[field] = _apply_list_sub_mappings(ctx.get(field) or [], mapping, ctx)
      else:
        _apply_field_to_item(new_item, field, mapping, ctx)
      ctx.update(new_item)
    result.append(new_item)
  if not is_list:
    return result[0]
  return result
