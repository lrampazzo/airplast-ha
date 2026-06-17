#!/usr/bin/env python3
"""Regenerate ``airplast_client/openapi_models.py`` from the checked-in spec.

Usage::

    python3 openapi/generate_models.py

Requires: pydantic >= 2, no other extra deps needed at generation time.
The script reads ``openapi/airplast-openapi.json`` and overwrites
``custom_components/airplast/client/openapi_models.py``.
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).parent.parent
SPEC_PATH = Path(__file__).parent / "airplast-openapi.json"
OUT_PATH = ROOT / "custom_components" / "airplast" / "client" / "openapi_models.py"

# Primitive type mapping (OpenAPI type → Python annotation)
_TYPE_MAP = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
}

_FORMAT_OVERRIDE = {
    "date-time": "datetime",
    "date-span": "str",  # TimeSpan serialised as string
}


def _ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def _py_type(prop_def: dict, schemas: dict) -> str:
    ref = prop_def.get("$ref")
    if ref:
        return _ref_name(ref)

    t = prop_def.get("type", "")
    fmt = prop_def.get("format", "")

    if t == "array":
        items = prop_def.get("items", {})
        item_type = _py_type(items, schemas)
        return f"List[{item_type}]"

    if fmt in _FORMAT_OVERRIDE:
        return _FORMAT_OVERRIDE[fmt]

    return _TYPE_MAP.get(t, "Any")


def _is_nullable(prop_def: dict, required: list[str], name: str) -> bool:
    return prop_def.get("nullable", False) or name not in required


def generate(spec: dict) -> str:
    schemas: dict = spec["components"]["schemas"]
    lines: list[str] = []

    header = textwrap.dedent('''
        """Pydantic v2 models generated from openapi/airplast-openapi.json.

        Run ``scripts/generate_openapi_models.py`` to regenerate.
        """

        from __future__ import annotations

        from datetime import datetime
        from enum import Enum
        from typing import Any, List, Optional

        from pydantic import BaseModel, ConfigDict


        class _AirplastModel(BaseModel):
            model_config = ConfigDict(
                populate_by_name=True,
                extra="allow",
                use_enum_values=False,
            )


        class _ResilientStrEnum(str, Enum):
            """Unknown API values are returned as dynamic members."""

            @classmethod
            def _missing_(cls, value: object) -> "_ResilientStrEnum":  # type: ignore[override]
                obj = str.__new__(cls, str(value))
                obj._name_ = str(value)
                obj._value_ = str(value)
                return obj

    ''').strip()

    lines.append(header)
    lines.append("")

    # Enums first
    for name, defn in schemas.items():
        if defn.get("type") != "string" or "enum" not in defn:
            continue
        lines.append("")
        lines.append(f"class {name}(_ResilientStrEnum):")
        for value in defn["enum"]:
            # CamelCase → UPPER_SNAKE: insert _ before each uppercase run
            import re as _re
            py_name = _re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
            py_name = _re.sub(r"([a-z\d])([A-Z])", r"\1_\2", py_name)
            py_name = py_name.upper().replace("-", "_").replace(" ", "_")
            if py_name == "NONE":
                py_name = "NONE_VALUE"
            lines.append(f'    {py_name} = "{value}"')
        lines.append("")

    lines.append("")
    lines.append("# ---------------------------------------------------------------------------")
    lines.append("# Object models")
    lines.append("# ---------------------------------------------------------------------------")
    lines.append("")

    # Object models
    for name, defn in schemas.items():
        if defn.get("type") == "string" and "enum" in defn:
            continue  # already done

        props: dict = defn.get("properties", {})
        required: list[str] = defn.get("required", [])

        base = "_AirplastModel"
        lines.append(f"class {name}({base}):")

        if not props:
            lines.append("    pass")
            lines.append("")
            continue

        for pname, pdef in props.items():
            py_type = _py_type(pdef, schemas)
            nullable = _is_nullable(pdef, required, pname)
            if nullable:
                annotation = f"Optional[{py_type}] = None"
            else:
                annotation = py_type
            lines.append(f"    {pname}: {annotation}")
        lines.append("")

    lines.append("")
    lines.append("# Backwards-compatibility aliases")
    lines.append("LoginRequest = AuthenticateRequest")
    lines.append("ChangeEmailRequest = ChangeUsernameRequest")
    lines.append("ChangePasswordRequest = UpdatePasswordRequest")
    lines.append("CompleteRegistrationRequest = ConfirmRegisterRequest")
    lines.append("CompleteRecoverPasswordRequest = RecoverPasswordRequest")
    lines.append("UpdateUserDetailsRequest = UpdateFirstLastNameRequest")
    lines.append("AddZoneRequest = NewZoneWithRoomsRequest")
    lines.append("LightSensorLevel = LightSensorLevelEnum")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    if not SPEC_PATH.exists():
        print(f"ERROR: spec not found at {SPEC_PATH}", file=sys.stderr)
        sys.exit(1)

    spec = json.loads(SPEC_PATH.read_text())
    code = generate(spec)
    OUT_PATH.write_text(code)
    print(f"Written {OUT_PATH}")


if __name__ == "__main__":
    main()
