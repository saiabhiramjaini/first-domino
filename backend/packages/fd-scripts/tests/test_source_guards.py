"""Rules from `backend/AGENTS.md` that ruff cannot enforce, checked over every package's source."""

import ast
import importlib.util
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

ALLOWED_INTERNAL_IMPORTS: dict[str, frozenset[str]] = {
    "fd_shared": frozenset(),
    "fd_database": frozenset({"fd_shared"}),
    "fd_engine": frozenset({"fd_shared"}),
    "fd_api": frozenset({"fd_shared", "fd_database", "fd_engine"}),
    "first_domino": frozenset(),
    "fd_demo_agent": frozenset({"first_domino"}),
}
INTERNAL = frozenset({*ALLOWED_INTERNAL_IMPORTS, "fd_scripts"})
SERVER_PACKAGES = frozenset({"fd_shared", "fd_database", "fd_engine", "fd_api"})
OPENAI_OWNER = "fd_engine.llm"
ENGINE_BANNED_THIRD_PARTY = frozenset({"httpx", "fastapi", "starlette", "sqlalchemy"})
MAPPING_NAMES = frozenset({"dict", "Dict", "Mapping", "MutableMapping"})
LOOSE_VALUE_NAMES = frozenset({"Any", "object"})
MODEL_ID = re.compile(r"^(gpt-|chatgpt-|o[1-9](-|$)|claude-|gemini-)")
GENERATED_DIR = "_generated"
MIXED_DICT_EXCEPTIONS: dict[str, str] = {
    "fd_api.errors.error_responses": "FastAPI's `responses=` parameter takes exactly this type",
}


def _source_root(package: str) -> Path:
    spec = importlib.util.find_spec(package)
    assert spec is not None
    assert spec.submodule_search_locations
    return Path(next(iter(spec.submodule_search_locations)))


def _modules(package: str) -> Iterator[tuple[str, Path, ast.Module]]:
    root = _source_root(package)
    for path in sorted(root.rglob("*.py")):
        if GENERATED_DIR in path.parts:
            continue
        relative = path.relative_to(root.parent).with_suffix("")
        name = ".".join(part for part in relative.parts if part != "__init__")
        yield name, path, ast.parse(path.read_text(), filename=str(path))


def _imported_roots(tree: ast.Module) -> Iterator[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module


@pytest.mark.parametrize("package", sorted(ALLOWED_INTERNAL_IMPORTS))
def test_layer_imports(package: str) -> None:
    allowed = ALLOWED_INTERNAL_IMPORTS[package] | {package}
    broken = [
        f"{name} imports {imported}"
        for name, _, tree in _modules(package)
        for imported in _imported_roots(tree)
        if imported.split(".")[0] in INTERNAL and imported.split(".")[0] not in allowed
    ]
    assert broken == []


@pytest.mark.parametrize("package", sorted(SERVER_PACKAGES))
def test_only_the_engine_llm_module_imports_openai(package: str) -> None:
    broken = [
        name
        for name, _, tree in _modules(package)
        if name != OPENAI_OWNER
        and any(imported.split(".")[0] == "openai" for imported in _imported_roots(tree))
    ]
    assert broken == []


def test_engine_does_no_io_of_its_own() -> None:
    broken = [
        f"{name} imports {imported}"
        for name, _, tree in _modules("fd_engine")
        for imported in _imported_roots(tree)
        if imported.split(".")[0] in ENGINE_BANNED_THIRD_PARTY
    ]
    assert broken == []


def _is_mixed_mapping(annotation: ast.expr | None) -> bool:
    """A bare `dict`, or a mapping whose values are `Any`, `object` or a union, at any depth."""
    if annotation is None:
        return False
    if isinstance(annotation, ast.Name):
        return annotation.id == "dict"
    if isinstance(annotation, ast.BinOp):
        return _is_mixed_mapping(annotation.left) or _is_mixed_mapping(annotation.right)
    if not isinstance(annotation, ast.Subscript):
        return False
    base = annotation.value
    base_name = base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
    arguments = (
        annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else [annotation.slice]
    )
    if base_name not in MAPPING_NAMES:
        return any(_is_mixed_mapping(argument) for argument in arguments)
    value = arguments[-1]
    if isinstance(value, ast.Name) and value.id in LOOSE_VALUE_NAMES:
        return True
    return isinstance(value, ast.BinOp) or _is_mixed_mapping(value)


def _public_functions(tree: ast.Module) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    functions = (ast.FunctionDef, ast.AsyncFunctionDef)
    for node in tree.body:
        if isinstance(node, functions) and not node.name.startswith("_"):
            yield node
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            yield from (
                item
                for item in node.body
                if isinstance(item, functions) and not item.name.startswith("_")
            )


@pytest.mark.parametrize("package", sorted(INTERNAL))
def test_no_mixed_value_dict_in_a_public_signature(package: str) -> None:
    broken = [
        f"{name}.{function.name}"
        for name, _, tree in _modules(package)
        for function in _public_functions(tree)
        for annotation in [
            *(arg.annotation for arg in function.args.args + function.args.kwonlyargs),
            function.returns,
        ]
        if _is_mixed_mapping(annotation) and f"{name}.{function.name}" not in MIXED_DICT_EXCEPTIONS
    ]
    assert broken == []


@pytest.mark.parametrize("package", sorted(INTERNAL))
def test_no_model_id_outside_a_settings_module(package: str) -> None:
    broken = [
        f"{path.name}:{node.lineno} {node.value!r}"
        for _, path, tree in _modules(package)
        if path.name != "settings.py"
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and MODEL_ID.match(node.value)
    ]
    assert broken == []


@pytest.mark.parametrize(
    ("annotation", "mixed"),
    [
        ("dict[str, object]", True),
        ("dict[str, str | int]", True),
        ("dict", True),
        ("Mapping[str, Any]", True),
        ("list[dict[str, object]]", True),
        ("dict[str, object] | None", True),
        ("dict[str, int]", False),
        ("list[dict[str, int]]", False),
        ("dict[str, list[str]]", False),
        ("str | None", False),
    ],
)
def test_mixed_mapping_detector(annotation: str, mixed: bool) -> None:
    expression = ast.parse(annotation, mode="eval").body
    assert _is_mixed_mapping(expression) is mixed
