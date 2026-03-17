![catnose](logo/catnose256.png)

Motor de transformación declarativa de JSON con lenguaje de plantillas integrado.

## Instalación

```bash
pip install catnose
```

## Uso rápido


```bash
> PYTHONPATH=src python3 -m catnose test/input.json test/transform.json
> PYTHONPATH=src python3 -m catnose test/input.json test/transform.json -o output.json
```

La entrada puede ser un array JSON o un objeto JSON. Si es un objeto, se trata
como una lista de un único elemento y recibe `_rownum = 1`.

**`input.json`**

```json
[
  {
    "id": 1,
    "first_name": "ana",
    "last_name": "garcía",
    "email": "ana.garcia@empresa.com",
    "phone": "612-345-678",
    "role": "admin",
    "tags": ["ventas", "soporte", "formación"],
    "bio": "Responsable del área de  ventas  y soporte técnico.",
    "salary": 62000
  },
  {
    "id": 2,
    "first_name": "luis",
    "last_name": "martínez",
    "email": "luis.martinez@empresa.com",
    "phone": "699 876 543",
    "role": "user",
    "tags": ["desarrollo", "backend"],
    "bio": "Desarrollador  backend  con experiencia en Python.",
    "salary": 38000
  }
]
```

**`transform.json`**

```json
{
  "id":   "id",
  "email": "email",

  "nombre": {
    "_value": "{{ first_name.capitalize() }} {{ last_name.capitalize() }}",
    "_comment": "Capitaliza nombre y apellido, que en la entrada vienen en minúsculas"
  },

  "rol_codigo": {
    "_value": "{{ role.upper() }}",
    "_comment": "Código de rol en mayúsculas para sistemas externos"
  },

  "rol_label": {
    "_name": "role",
    "_cases": {
      "admin":    "Administrador",
      "user":     "Usuario",
      "manager":  "Responsable",
      "_default": "Otro"
    },
    "_comment": "Traduce el rol técnico a la etiqueta visible en la interfaz"
  },

  "telefono": {
    "_value": "{{ re.sub(r'[\\s\\-.]', '', phone) }}",
    "_comment": "Normaliza el número de teléfono quitando puntos, espacios o rayas separadoras"
  },

  "bio_normalizada": {
    "_value": "{{ re.sub(r'\\s{2,}', ' ', bio).strip() }}",
    "_comment": "Colapsa los espacios dobles o múltiples que pueda contener la bio"
  },

  "etiquetas": {
    "_value": "{% for t in tags %}[{{ t }}]{% endfor %}",
    "_comment": "Serializa la lista de etiquetas como cadena de tokens entre corchetes"
  },

  "nivel": {
    "_value": "{% if salary >= 55000 %}Senior{% else %}{% if salary >= 45000 %}Mid{% else %}Junior{% endif %}{% endif %}",
    "_comment": "Clasifica al empleado en Senior / Mid / Junior según su salario bruto anual"
  },

  "resumen": {
    "_value": "{{ nombre }} · {{ rol_label }} · {{ nivel }}",
    "_comment": "Descripción compacta que combina campos calculados anteriores"
  }
}
```

**Resultado**

```json
[
  {
    "id": 1,
    "email": "ana.garcia@empresa.com",
    "nombre": "Ana García",
    "rol_codigo": "ADMIN",
    "rol_label": "Administrador",
    "telefono": "612345678",
    "etiquetas": "[ventas][soporte][formación]",
    "bio_normalizada": "Responsable del área de ventas y soporte técnico.",
    "nivel": "Senior",
    "resumen": "Ana García · Administrador · Senior"
  },
  {
    "id": 2,
    "email": "luis.martinez@empresa.com",
    "nombre": "Luis Martínez",
    "rol_codigo": "USER",
    "rol_label": "Usuario",
    "telefono": "699876543",
    "etiquetas": "[desarrollo][backend]",
    "bio_normalizada": "Desarrollador backend con experiencia en Python.",
    "nivel": "Junior",
    "resumen": "Luis Martínez · Usuario · Junior"
  }
]
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
| `_comment` | Comentario — ignorado por el motor, documenta la intención de la transformación |

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
- `_rownum` (1..N, posición del elemento en el array; si la entrada es un
  objeto único, vale `1`)

Para campos de tipo lista, el contexto incluye además los campos de cada elemento de la lista.

## Historial de cambios

### 1.2.0
- Soporte para `_comment` en los mappings del JSON de transformación: se puede añadir `"_comment": "..."` junto a `_value`, `_name` o `_cases` para documentar la intención de cada campo. El motor lo ignora y no produce ningún campo en el resultado.

### 1.1.0
- `transform` acepta ahora un objeto JSON (`dict`) además de un array. Si la entrada es un objeto, devuelve un objeto en lugar de una lista.
- CLI actualizado para admitir ficheros de entrada que sean un objeto JSON único, asignándole `_rownum = 1`.

### 1.0.1
- Añadido logotipo del proyecto.

### 1.0.0
- `rownum` renombrado a `_rownum` en el contexto de evaluación para evitar colisiones con campos del JSON original.
- `_parse_list` eliminada del API pública (era un detalle de implementación interno).

### 0.0.1
- Versión inicial: motor de transformación declarativa, motor de plantillas `{{ expr }}` / `{% for %}` / `{% if %}`, y CLI.

## Licencia

MIT
