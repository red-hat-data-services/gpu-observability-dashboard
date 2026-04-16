#!/usr/bin/env python3
"""
Spec Sync Validator
====================
Parses SPEC.md and validates it matches actual code in gpu_tools.py.
Exits non-zero on drift with clear error messages.

Usage:
    python scripts/check_spec.py
"""

import inspect
import re
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gpu_tools


def parse_spec_tools(spec_path: str) -> dict[str, dict]:
    """Parse tool definitions from SPEC.md between markers."""
    with open(spec_path) as f:
        content = f.read()

    # Extract tools section
    match = re.search(
        r"<!-- SPEC:TOOLS:START -->(.*?)<!-- SPEC:TOOLS:END -->",
        content,
        re.DOTALL,
    )
    if not match:
        print("ERROR: SPEC.md missing SPEC:TOOLS:START/END markers")
        sys.exit(1)

    tools_section = match.group(1)
    tools = {}

    # Parse each tool heading
    tool_blocks = re.split(r"^### (\w+)", tools_section, flags=re.MULTILINE)
    # tool_blocks[0] is before first heading, then alternating name/content
    for i in range(1, len(tool_blocks), 2):
        tool_name = tool_blocks[i].strip()
        tool_content = tool_blocks[i + 1] if i + 1 < len(tool_blocks) else ""

        # Extract source_function
        source_match = re.search(r"source_function:\s*(\S+)", tool_content)
        source_fn = source_match.group(1) if source_match else None

        # Extract params
        params = {}
        param_matches = re.finditer(
            r"-\s*name:\s*(\w+)\n\s*type:\s*(.+)\n\s*required:\s*(true|false)",
            tool_content,
        )
        for pm in param_matches:
            params[pm.group(1)] = {
                "type": pm.group(2).strip(),
                "required": pm.group(3) == "true",
            }

        tools[tool_name] = {
            "source_function": source_fn,
            "params": params,
        }

    return tools


def get_code_tools() -> dict[str, dict]:
    """Extract tool info from actual gpu_tools.py code."""
    tools = {}

    for name, fn in gpu_tools.TOOL_REGISTRY.items():
        sig = inspect.signature(fn)
        params = {}
        for pname, param in sig.parameters.items():
            required = param.default is inspect.Parameter.empty
            params[pname] = {"required": required}
        tools[name] = {"params": params}

    return tools


def get_schema_tools() -> dict[str, dict]:
    """Extract tool info from TOOL_SCHEMAS in gpu_tools.py."""
    tools = {}

    for name, schema in gpu_tools.TOOL_SCHEMAS.items():
        params = {}
        input_schema = schema.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required_list = input_schema.get("required", [])

        for pname in properties:
            params[pname] = {"required": pname in required_list}

        tools[name] = {"params": params, "description": schema.get("description", "")}

    return tools


def validate(spec_path: str) -> list[str]:
    """Compare spec against code and return list of errors."""
    errors = []

    spec_tools = parse_spec_tools(spec_path)
    code_tools = get_code_tools()
    schema_tools = get_schema_tools()

    # 1. Check tool names match
    spec_names = set(spec_tools.keys())
    code_names = set(code_tools.keys())
    schema_names = set(schema_tools.keys())

    missing_in_code = spec_names - code_names
    missing_in_spec = code_names - spec_names
    missing_in_schema = code_names - schema_names

    # Tools in spec but not code are "planned" — warn but don't fail
    for name in missing_in_code:
        print(f"  PLANNED: Tool '{name}' in SPEC.md but not yet implemented (OK)")
    for name in missing_in_spec:
        errors.append(f"Tool '{name}' in gpu_tools.TOOL_REGISTRY but not in SPEC.md")
    for name in missing_in_schema:
        errors.append(f"Tool '{name}' in gpu_tools.TOOL_REGISTRY but not in gpu_tools.TOOL_SCHEMAS")

    # 2. Check param names match (spec vs code)
    for name in spec_names & code_names:
        spec_params = set(spec_tools[name]["params"].keys())
        code_params = set(code_tools[name]["params"].keys())

        extra_in_spec = spec_params - code_params
        extra_in_code = code_params - spec_params

        for p in extra_in_spec:
            errors.append(f"Tool '{name}': param '{p}' in SPEC.md but not in function signature")
        for p in extra_in_code:
            errors.append(f"Tool '{name}': param '{p}' in function signature but not in SPEC.md")

        # Check required matches
        for p in spec_params & code_params:
            spec_required = spec_tools[name]["params"][p]["required"]
            code_required = code_tools[name]["params"][p]["required"]
            if spec_required != code_required:
                errors.append(
                    f"Tool '{name}': param '{p}' required mismatch — "
                    f"SPEC says {spec_required}, code says {code_required}"
                )

    # 3. Check schema vs code param names match
    for name in schema_names & code_names:
        schema_params = set(schema_tools[name]["params"].keys())
        code_params = set(code_tools[name]["params"].keys())

        extra_in_schema = schema_params - code_params
        extra_in_code = code_params - schema_params

        for p in extra_in_schema:
            errors.append(f"Tool '{name}': param '{p}' in TOOL_SCHEMAS but not in function signature")
        for p in extra_in_code:
            errors.append(f"Tool '{name}': param '{p}' in function signature but not in TOOL_SCHEMAS")

    return errors


def main():
    spec_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SPEC.md")

    if not os.path.exists(spec_path):
        print(f"ERROR: {spec_path} not found")
        sys.exit(1)

    print(f"Validating SPEC.md against code...")
    errors = validate(spec_path)

    if errors:
        print(f"\nSPEC DRIFT DETECTED — {len(errors)} error(s):\n")
        for err in errors:
            print(f"  - {err}")
        print(f"\nFix SPEC.md or code to match, then re-run.")
        sys.exit(1)
    else:
        spec_tools = parse_spec_tools(spec_path)
        code_tools = get_code_tools()
        planned = set(spec_tools.keys()) - set(code_tools.keys())
        implemented = set(spec_tools.keys()) & set(code_tools.keys())
        msg = f"OK — {len(implemented)} implemented, {len(planned)} planned, {len(code_tools)} in code."
        print(msg)
        sys.exit(0)


if __name__ == "__main__":
    main()
