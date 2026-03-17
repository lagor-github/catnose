![catnose](https://raw.githubusercontent.com/lagor-github/catnose/main/logo/catnose256.png)
# catnose

Motor de transformación declarativa de JSON con lenguaje de plantillas integrado.

## Instalación

```bash
pip install catnose
```

## Uso rápido

### API

```python
from catnose import transform

items = [{"id": 1, "first_name": "Ana", "role": "admin"}]

mapper = {
  "id":   "id",
  "name": "first_name",
  "role": {
    "_cases": {
      "admin": "Administrador",
      "user":  "Usuario",
      "_default": "Otro"
    }
  },
  "label": {"_value": "{{ name }} ({{ role }})"}
}

result = transform(items, mapper)
# [{"id": 1, "name": "Ana", "role": "Administrador", "label": "Ana (Administrador)"}]
```

### CLI

```bash
catnose input.json transform.json
catnose input.json transform.json -o output.json
```

## Formato del mapeador

El JSON transformado **parte de un objeto vacío**; sólo se incluyen los campos declarados explícitamente. El JSON original actúa como contexto de evaluación junto con los campos ya calculados (en orden de definición).

```json
{
  "<campo_destino>": "<campo_origen>",
  "<campo_destino>": {
    "_name":   "<campo_origen>",
    "_cases":  {"v1": "nuevo_v1", "_default": "<por_defecto>"},
    "_value":  "cadena con {{ expr }}"
  },
  "<campo_lista>": {
    "<sub_campo>": {
      "_name":  "<campo_origen>",
      "_cases": {"v1": "nv1"},
      "_value": "{{ expr }}"
    }
  }
}
```

| Clave | Descripción |
|-------|-------------|
| `"<campo>": "<origen>"` | Shorthand — copia el valor de `<origen>` del JSON original |
| `_name` | Campo fuente en el JSON original (por defecto: la clave del mapper) |
| `_cases` | Tabla de sustitución de valores; `_default` se usa si no hay coincidencia |
| `_value` | Plantilla evaluada con el motor de expresiones |

Un mapping dict sin ninguna clave de control (`_name`, `_cases`, `_value`) se trata como **lista de objetos**, aplicando los sub-mapeos a cada elemento.

## Motor de plantillas

Las expresiones `_value` usan la sintaxis `{{ expr }}` con evaluación Python completa. También se soportan bloques `{% for %}`, `{% if %}` / `{% else %}` / `{% endif %}`:

```json
{
  "summary": {"_value": "{{ title.upper() }} — {{ cwss_score }} puntos"},
  "tags":    {"_value": "{% for t in tags %}[{{ t }}]{% endfor %}"}
}
```

El contexto de evaluación incluye:
- Todos los campos del JSON original
- Los campos ya calculados por mappings anteriores (en orden)
- `_rownum` (1..N, posición del elemento en el array)

Para campos de tipo lista, el contexto incluye además los campos de cada elemento de la lista.

## Licencia

MIT
