"""Static code scanner for extracting structural information from codebase."""

import ast
from pathlib import Path
from typing import Optional

from megaprompt.schemas.analysis import CodebaseStructure


class CodebaseScanner:
    """Scans codebase to extract structural information without AI."""

    def __init__(self, depth: str = "high"):
        """
        Initialize codebase scanner.

        Args:
            depth: Scanning depth: "low", "medium", "high"
        """
        self.depth = depth

    def scan(self, codebase_path: str | Path) -> CodebaseStructure:
        """
        Scan codebase and extract structural information.

        Args:
            codebase_path: Path to codebase directory

        Returns:
            CodebaseStructure with extracted information
        """
        codebase_path = Path(codebase_path)
        if not codebase_path.exists():
            raise ValueError(f"Codebase path does not exist: {codebase_path}")

        modules: list[str] = []
        entry_points: list[str] = []
        public_apis: dict[str, list[str]] = {}
        core_loops: list[str] = []
        data_models: list[str] = []
        config_files: list[str] = []
        has_tests = False
        has_persistence = False
        has_cli = False
        has_api = False

        # Find all Python files
        python_files = list(codebase_path.rglob("*.py"))
        
        # Filter out common exclusion patterns
        excluded_dirs = {".git", "__pycache__", ".venv", "venv", "env", ".pytest_cache", ".mypy_cache", "node_modules", "build", "dist"}
        python_files = [
            f for f in python_files
            if not any(excluded in f.parts for excluded in excluded_dirs)
        ]

        for py_file in python_files:
            try:
                # Parse AST
                tree = ast.parse(py_file.read_text(encoding="utf-8"), str(py_file))
                
                # Extract module information
                relative_path = py_file.relative_to(codebase_path)
                module_name = str(relative_path.with_suffix("")).replace("/", ".").replace("\\", ".")
                if not module_name.startswith("."):
                    modules.append(module_name)

                # Extract public APIs and data models
                file_apis: list[str] = []
                visitor = ASTVisitor(module_name)
                visitor.visit(tree)
                
                file_apis.extend(visitor.classes)
                file_apis.extend(visitor.functions)
                
                if file_apis:
                    public_apis[module_name] = file_apis
                
                # Check for data models
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Check for Pydantic BaseModel inheritance
                        for base in node.bases:
                            # Handle "BaseModel" directly (from pydantic import BaseModel)
                            if isinstance(base, ast.Name) and base.id == "BaseModel":
                                data_models.append(f"{module_name}.{node.name}")
                                break
                            # Handle "pydantic.BaseModel" or similar attribute access
                            elif isinstance(base, ast.Attribute) and base.attr == "BaseModel":
                                data_models.append(f"{module_name}.{node.name}")
                                break
                        # Check for dataclass decorator
                        if f"{module_name}.{node.name}" not in data_models:
                            for decorator in node.decorator_list:
                                if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                                    data_models.append(f"{module_name}.{node.name}")
                                    break
                
                # Check for entry points
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if node.name in ("main", "__main__"):
                            entry_points.append(f"{module_name}.{node.name}")
                        # Check for CLI entry points (click, argparse)
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Call):
                                if isinstance(decorator.func, ast.Attribute):
                                    if decorator.func.attr in ("command", "group"):
                                        entry_points.append(f"{module_name}.{node.name}")
                                        has_cli = True
                
                # Check for core loops
                loop_visitor = LoopVisitor()
                loop_visitor.visit(tree)
                if loop_visitor.has_loop:
                    core_loops.append(module_name)
                
                # Check for API endpoints (Flask, FastAPI, etc.)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Call):
                                if isinstance(decorator.func, ast.Attribute):
                                    if decorator.func.attr in ("route", "get", "post", "put", "delete", "api"):
                                        has_api = True

            except (SyntaxError, UnicodeDecodeError, Exception):
                # Skip files that can't be parsed
                continue

        # Scan for config files
        config_patterns = [
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "requirements-dev.txt",
            "setup.cfg",
            "tox.ini",
            "pytest.ini",
            ".flake8",
            "docker-compose.yml",
            "Dockerfile",
            "Makefile",
        ]
        for pattern in config_patterns:
            matches = list(codebase_path.rglob(pattern))
            config_files.extend([str(f.relative_to(codebase_path)) for f in matches])

        # Check for tests
        test_files = list(codebase_path.rglob("test_*.py"))
        test_files.extend(codebase_path.rglob("*_test.py"))
        has_tests = len(test_files) > 0

        # Check for persistence (database imports, file I/O patterns)
        persistence_patterns = [
            "sqlite3",
            "psycopg2",
            "mysql",
            "sqlalchemy",
            "peewee",
            "mongodb",
            "pymongo",
            "redis",
            "pickle",
            "json.dump",
            "yaml.dump",
        ]
        for py_file in python_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                if any(pattern in content for pattern in persistence_patterns):
                    has_persistence = True
                    break
            except Exception:
                continue

        return CodebaseStructure(
            modules=sorted(set(modules)),
            entry_points=sorted(set(entry_points)),
            public_apis=public_apis,
            core_loops=sorted(set(core_loops)),
            data_models=sorted(set(data_models)),
            config_files=sorted(set(config_files)),
            tests=has_tests,
            persistence=has_persistence,
            has_cli=has_cli,
            has_api=has_api,
        )


class ASTVisitor(ast.NodeVisitor):
    """AST visitor to extract classes and functions."""

    def __init__(self, module_name: str):
        """Initialize visitor."""
        self.module_name = module_name
        self.classes: list[str] = []
        self.functions: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions."""
        # Only include classes that are not private (don't start with _)
        if not node.name.startswith("_"):
            self.classes.append(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        # Only include functions that are not private
        if not node.name.startswith("_"):
            self.functions.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        if not node.name.startswith("_"):
            self.functions.append(node.name)
        self.generic_visit(node)


class LoopVisitor(ast.NodeVisitor):
    """AST visitor to detect core loops."""

    def __init__(self):
        """Initialize visitor."""
        self.has_loop = False
        self.loop_keywords = {"update", "tick", "run", "main", "loop", "simulate"}

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to detect loop patterns."""
        # Check function name
        if any(keyword in node.name.lower() for keyword in self.loop_keywords):
            # Check if function contains while loop or for loop
            for child in ast.walk(node):
                if isinstance(child, (ast.While, ast.For)):
                    self.has_loop = True
                    return
        self.generic_visit(node)

