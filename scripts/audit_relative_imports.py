"""Audit repository-relative import bindings with AST only; import no project code."""

import argparse
import ast
import importlib.util
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Module:
    name: str
    path: Path
    package: str
    bindings: set = field(default_factory=set)
    exports: tuple | None = None
    stars: list = field(default_factory=list)
    relative_imports: list = field(default_factory=list)
    dynamic: bool = False


def _source(module, node):
    return importlib.util.resolve_name("."*node.level+(node.module or ""), module.package)


def scan(root):
    modules = {}
    for path in sorted((root/"src"/"h2physics").rglob("*.py")):
        parts = path.relative_to(root/"src").with_suffix("").parts
        package_file = parts[-1] == "__init__"
        name = ".".join(parts[:-1] if package_file else parts)
        module = Module(name, path, name if package_file else name.rpartition(".")[0])
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))

        def visit(node):
            if isinstance(node, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                return
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                module.bindings.add(node.name)
                if node.name == "__getattr__":
                    module.dynamic = True
                return
            if isinstance(node, ast.Import):
                module.bindings.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    try:
                        source = _source(module, node)
                    except (ImportError, ValueError):
                        source = "<invalid-relative-level>"
                    for alias in node.names:
                        module.relative_imports.append((source, alias.name, node.lineno))
                        if alias.name == "*":
                            module.stars.append(source)
                if any(alias.name == "*" for alias in node.names):
                    if not node.level:
                        module.stars.append("<external-star>")
                else:
                    module.bindings.update(alias.asname or alias.name for alias in node.names)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                module.bindings.add(node.id)
            elif (isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name)
                  and node.target.id == "__all__"):
                module.dynamic = True
            elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "__all__"
                                                     for target in node.targets):
                try:
                    value = ast.literal_eval(node.value)
                    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
                        raise ValueError("computed exports")
                    module.exports = tuple(value)
                except (ValueError, TypeError):
                    module.dynamic = True
            for child in ast.iter_child_nodes(node):
                visit(child)

        visit(tree)
        modules[name] = module
    return modules


def resolve(modules, source, symbol, seen=()):
    if source not in modules:
        return "missing", "source module is absent"
    module = modules[source]
    if symbol in module.bindings:
        return "bound", "explicit definition/import/assignment binding"
    if source+"."+symbol in modules:
        return "bound", "package submodule exists"
    key = (source, symbol)
    if key in seen:
        return "unresolved", "cyclic star import; runtime order is not evaluated"
    uncertain = module.dynamic or bool(module.exports and symbol in module.exports)
    for star in module.stars:
        target = modules.get(star)
        if target is None or target.exports is None:
            uncertain = True
            continue
        if target.dynamic:
            uncertain = True
        if symbol not in target.exports:
            continue
        state, reason = resolve(modules, star, symbol, (*seen, key))
        if state == "bound":
            return state, "literal-export star binding from "+star
        uncertain = True
    if uncertain:
        return "unresolved", "star/dynamic/export-only binding requires manual inspection"
    return "missing", "no definition, import binding or package submodule found"


def audit(root):
    modules = scan(root)
    rows = []
    for module in modules.values():
        for source, symbol, line in module.relative_imports:
            if symbol == "*":
                state, reason = "unresolved", "star import is not treated as proof of exported runtime bindings"
                if source not in modules:
                    state, reason = "missing", "star source module is absent"
            else:
                state, reason = resolve(modules, source, symbol)
            rows.append((module, source, symbol, line, state, reason))
    return modules, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    modules, rows = audit(root)
    counts = {state: sum(row[4] == state for row in rows) for state in ("bound", "missing", "unresolved")}
    lines = ["# Relative import source audit", "",
             f"AST inventory: {len(modules)} modules; {len(rows)} relative imported symbols; "
             f"{counts['bound']} statically bound, {counts['missing']} missing, {counts['unresolved']} unresolved.",
             "Generated by `python scripts/audit_relative_imports.py`. No project/scientific imports or runtime execution occur.", "",
             "A bound result identifies a source definition, explicit import/assignment, known package submodule, or literal-export star binding.",
             "Bindings inside TYPE_CHECKING, try/except and conditionals are inventoried, but runtime branch selection and import order are not evaluated.",
             "This audit does not prove runtime availability, circular-import safety, dependency installation or physical validity.",
             "Star imports, dynamic __getattr__, and export names without visible bindings remain unresolved rather than passing silently.", "",
             "| Import location | Requested source symbol | Status | Evidence |", "|---|---|---|---|"]
    for module, source, symbol, line, state, reason in rows:
        location = "../"+module.path.relative_to(root).as_posix()+f"#L{line}"
        lines.append(f"| [`{module.name}:{line}`]({location}) | `{source}.{symbol}` | {state} | {reason} |")
    (root/"docs"/"RELATIVE_IMPORT_AUDIT.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"AST relative import audit: {counts}; {len(modules)} modules")
    for module, source, symbol, line, state, reason in rows:
        if state != "bound":
            print(f"{state}: {module.name}:{line}: {source}.{symbol}: {reason}")
    return 1 if counts["missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
