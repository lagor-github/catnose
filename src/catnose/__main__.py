#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI de catnose. Invocable como `catnose` (console script) o `python -m catnose`."""

import argparse
import json
import sys
from pathlib import Path

from ._core import transform


def main() -> None:
  parser = argparse.ArgumentParser(prog="catnose", description="Transforma un array JSON o un objeto JSON aplicando un mapeador declarativo.", epilog="\nEjemplos:\n  %(prog)s input.json transform.json\n  %(prog)s input.json transform.json -o output.json\n")
  parser.add_argument("input", help="Fichero JSON de entrada (array de objetos o un único objeto)")
  parser.add_argument("transform_file", metavar="transform", help="Fichero JSON de transformación (mapeador)")
  parser.add_argument("-o", "--output", metavar="FILE", help="Escribe el resultado en FILE (por defecto: stdout)")
  args = parser.parse_args()

  input_path = Path(args.input)
  if not input_path.exists():
    print(f"ERROR: '{input_path}' no encontrado", file=sys.stderr)
    sys.exit(1)
  transform_path = Path(args.transform_file)
  if not transform_path.exists():
    print(f"ERROR: '{transform_path}' no encontrado", file=sys.stderr)
    sys.exit(1)

  items = json.loads(input_path.read_text(encoding="utf-8"))
  if not isinstance(items, (list, dict)):
    print("ERROR: el fichero de entrada debe ser un array JSON o un objeto JSON", file=sys.stderr)
    sys.exit(1)

  mapper = json.loads(transform_path.read_text(encoding="utf-8"))
  result = transform(items, mapper)
  output = json.dumps(result, ensure_ascii=False, indent=2)

  if args.output:
    Path(args.output).write_text(output, encoding="utf-8")
    print(f"OK: {len(result)} elementos escritos en '{args.output}'")
  else:
    print(output)


if __name__ == "__main__":
  main()
