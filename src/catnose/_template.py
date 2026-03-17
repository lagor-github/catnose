# -*- coding: utf-8 -*-
"""
Motor de plantillas con semántica Python eval.

Sintaxis soportada (anidable):
  {{ expr }}                  — evalúa expr Python, inserta resultado como str
  {% for var in list_expr %}  — itera lista; var queda disponible en el contexto
  {% endfor %}
  {% if bool_expr %}          — bloque condicional
  {% else %}                  — rama else (opcional)
  {% endif %}

El contexto de evaluación usa DotDict para acceso por punto (x.y).
"""

import re

# ---------------------------------------------------------------------------
# Colector de errores de evaluación (opcional)
# ---------------------------------------------------------------------------
_error_collector: list | None = None
_error_seen: set = set()


def set_error_collector(lst: list | None) -> None:
  """Activa (con una lista) o desactiva (con None) la recogida de errores."""
  global _error_collector, _error_seen
  _error_collector = lst
  _error_seen = set()


def _collect_error(expr: str, exc: Exception) -> None:
  if _error_collector is not None and expr not in _error_seen:
    _error_seen.add(expr)
    _error_collector.append((expr, exc))

# ---------------------------------------------------------------------------
# Builtins seguros expuestos a eval
# ---------------------------------------------------------------------------
_BUILTINS: dict = {
  '__builtins__': {},
  'str': str, 'int': int, 'float': float, 'bool': bool,
  'len': len, 'list': list, 'dict': dict, 'tuple': tuple,
  'range': range, 'enumerate': enumerate, 'zip': zip,
  'min': min, 'max': max, 'sum': sum, 'abs': abs, 'round': round,
  'sorted': sorted, 'reversed': reversed,
  'True': True, 'False': False, 'None': None,
  'isinstance': isinstance, 'hasattr': hasattr,
  'repr': repr, 'chr': chr, 'ord': ord,
  're': re,
}

# ---------------------------------------------------------------------------
# Tokenizador
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r'\{\{(.*?)\}\}|\{%(.*?)%\}', re.DOTALL)


def _tokenize(s: str) -> list[tuple]:
  """Divide la cadena de plantilla en una lista plana de tokens."""
  s = str(s)
  tokens: list[tuple] = []
  pos = 0
  for m in _TAG_RE.finditer(s):
    if m.start() > pos:
      tokens.append(('text', s[pos:m.start()]))
    if m.group(1) is not None:
      tokens.append(('expr', m.group(1).strip()))
    else:
      inner = m.group(2).strip()
      if fm := re.match(r'^for\s+(\w+)\s+in\s+(.+)$', inner, re.DOTALL):
        tokens.append(('for', fm.group(1), fm.group(2).strip()))
      elif fm := re.match(r'^if\s+(.+)$', inner, re.DOTALL):
        tokens.append(('if', fm.group(1).strip()))
      elif inner == 'else':
        tokens.append(('else',))
      elif inner == 'endfor':
        tokens.append(('endfor',))
      elif inner == 'endif':
        tokens.append(('endif',))
      else:
        tokens.append(('text', m.group(0)))  # tag desconocido — conservar tal cual
    pos = m.end()
  if pos < len(s):
    tokens.append(('text', s[pos:]))
  return tokens

# ---------------------------------------------------------------------------
# Helpers de contexto
# ---------------------------------------------------------------------------

class _StrictDotDict(dict):
  """DotDict que lanza AttributeError en acceso a clave inexistente."""
  def __getattr__(self, name: str):
    try:
      return self[name]
    except KeyError:
      raise AttributeError(f"'{name}' no existe en el contexto") from None
  __setattr__ = dict.__setitem__
  __delattr__ = dict.__delitem__


def _to_dotdict(obj):
  """Convierte recursivamente dicts (y listas de dicts) a _StrictDotDict."""
  if isinstance(obj, dict):
    return _StrictDotDict({k: _to_dotdict(v) for k, v in obj.items()})
  if isinstance(obj, list):
    return [_to_dotdict(v) for v in obj]
  return obj


def _eval(expr: str, ctx: dict):
  return eval(expr, {**_BUILTINS, **ctx})  # noqa: S307

# ---------------------------------------------------------------------------
# Renderizador recursivo
# ---------------------------------------------------------------------------

class _Runner:
  """Renderizador con estado sobre una lista de tokens (compartida o slice)."""

  def __init__(self, tokens: list[tuple]):
    self.tokens = tokens
    self.pos = 0

  def _peek_kind(self) -> str | None:
    return self.tokens[self.pos][0] if self.pos < len(self.tokens) else None

  def _consume(self) -> tuple:
    t = self.tokens[self.pos]
    self.pos += 1
    return t

  def _collect_for_body(self) -> list[tuple]:
    """Recoge tokens hasta el endfor coincidente (consumido). Devuelve el cuerpo."""
    body_start = self.pos
    depth = 1
    while self.pos < len(self.tokens):
      t = self._consume()
      if t[0] == 'for':
        depth += 1
      elif t[0] == 'endfor':
        depth -= 1
        if depth == 0:
          return self.tokens[body_start: self.pos - 1]
    return self.tokens[body_start:]  # sin terminar — devolver lo que haya

  def _render_expr(self, tok: tuple, ctx: dict) -> str:
    try:
      val = _eval(tok[1], ctx)
      return '' if val is None else str(val)
    except Exception as exc:
      _collect_error(tok[1], exc)
      return f'{{ERROR:{exc}}}'

  def _render_for(self, tok: tuple, ctx: dict) -> str:
    var, list_expr = tok[1], tok[2]
    try:
      items = _eval(list_expr, ctx)
    except Exception as exc:
      _collect_error(list_expr, exc)
      items = []
    body = self._collect_for_body()
    return ''.join(_Runner(body).render({**ctx, var: _to_dotdict(item)}) for item in (items or []))

  def _render_if(self, tok: tuple, ctx: dict) -> str:
    try:
      cond = bool(_eval(tok[1], ctx))
    except Exception as exc:
      _collect_error(tok[1], exc)
      cond = False
    then_text = self.render(ctx, stop_at=frozenset({'else', 'endif'}))
    if self._peek_kind() == 'else':
      self._consume()
      else_text = self.render(ctx, stop_at=frozenset({'endif'}))
    else:
      else_text = ''
    if self._peek_kind() == 'endif':
      self._consume()
    return then_text if cond else else_text

  def render(self, ctx: dict, stop_at: frozenset = frozenset()) -> str:
    parts: list[str] = []
    while self.pos < len(self.tokens):
      kind = self._peek_kind()
      if kind in stop_at:
        break
      tok = self._consume()
      if kind == 'text':
        parts.append(tok[1])
      elif kind == 'expr':
        parts.append(self._render_expr(tok, ctx))
      elif kind == 'for':
        parts.append(self._render_for(tok, ctx))
      elif kind == 'if':
        parts.append(self._render_if(tok, ctx))
      elif kind in ('endfor', 'endif', 'else'):
        break  # terminador sin stop_at activo — ignorar
    return ''.join(parts)

# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def render(template: str, context: dict) -> str:
  """
  Renderiza *template* usando *context* como espacio de nombres de evaluación.

  Los valores de *context* se envuelven automáticamente en DotDict para que
  el acceso por punto (``x.y``) funcione en las expresiones.
  """
  ctx = {k: _to_dotdict(v) for k, v in context.items()}
  return _Runner(_tokenize(template)).render(ctx)
