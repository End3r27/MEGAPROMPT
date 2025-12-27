"""Static code scanner for extracting structural information from codebase."""

import ast
import json
import re
from pathlib import Path
from typing import Optional

from megaprompt.schemas.analysis import CodebaseStructure


class CodebaseScanner:
    """Scans codebase to extract structural information without AI."""

    # Language file extensions mapping
    LANGUAGE_EXTENSIONS = {
        "python": [".py"],
        "javascript": [".js", ".jsx"],
        "typescript": [".ts", ".tsx"],
        "java": [".java"],
        "go": [".go"],
        "rust": [".rs"],
        "csharp": [".cs"],
        "ruby": [".rb"],
        "php": [".php"],
        "swift": [".swift"],
        "kotlin": [".kt"],
        "dart": [".dart"],
        "vue": [".vue"],
        "svelte": [".svelte"],
    }

    def __init__(self, depth: str = "high"):
        """
        Initialize codebase scanner.

        Args:
            depth: Scanning depth: "low", "medium", "high"
        """
        self.depth = depth

    def _detect_language(self, file_path: Path) -> str | None:
        """
        Detect programming language from file extension.

        Args:
            file_path: Path to the file

        Returns:
            Language name or None if unknown
        """
        suffix = file_path.suffix.lower()
        for language, extensions in self.LANGUAGE_EXTENSIONS.items():
            if suffix in extensions:
                return language
        return None

    def scan(self, codebase_path: str | Path) -> CodebaseStructure:
        """
        Scan codebase and extract structural information.

        Args:
            codebase_path: Path to codebase directory (can be absolute or relative)

        Returns:
            CodebaseStructure with extracted information

        Raises:
            ValueError: If path does not exist or is not a directory
            PermissionError: If path cannot be accessed
        """
        # Resolve path to handle relative paths, ~ expansion, and symlinks
        codebase_path = Path(codebase_path).expanduser().resolve()
        
        if not codebase_path.exists():
            raise ValueError(f"Codebase path does not exist: {codebase_path}")
        
        if not codebase_path.is_dir():
            raise ValueError(f"Codebase path is not a directory: {codebase_path}")
        
        # Check if we can read the directory
        try:
            codebase_path.iterdir()
        except PermissionError as e:
            raise PermissionError(f"Cannot read codebase directory: {codebase_path}") from e

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
        has_docker = False
        has_entrypoint = False
        has_readme = False
        file_count = 0

        # Filter out common exclusion patterns
        excluded_dirs = {
            ".git", "__pycache__", ".venv", "venv", "env", ".pytest_cache", ".mypy_cache",
            "node_modules", "build", "dist", ".next", ".nuxt", "out", "bin", "obj",
            "target", ".idea", ".vscode", ".gradle", ".mvn"
        }

        # Find all source files grouped by language
        files_by_language: dict[str, list[Path]] = {}
        for language, extensions in self.LANGUAGE_EXTENSIONS.items():
            files_by_language[language] = []
            for ext in extensions:
                pattern = f"*{ext}"
                files = list(codebase_path.rglob(pattern))
                # Filter out excluded directories
                files = [
                    f for f in files
                    if not any(excluded in f.parts for excluded in excluded_dirs)
                ]
                files_by_language[language].extend(files)

        # Process Python files (keep existing AST-based parsing)
        python_files = files_by_language.get("python", [])
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

        # Process JavaScript/TypeScript files
        js_ts_files = files_by_language.get("javascript", []) + files_by_language.get("typescript", [])
        for js_ts_file in js_ts_files:
            try:
                result = self._parse_js_ts_file(js_ts_file, codebase_path)
                if result:
                    module_name = result.get("module_name")
                    if module_name:
                        modules.append(module_name)
                    if result.get("entry_points"):
                        entry_points.extend(result["entry_points"])
                    if result.get("apis"):
                        if module_name and module_name in public_apis:
                            public_apis[module_name].extend(result["apis"])
                        elif module_name:
                            public_apis[module_name] = result["apis"]
                    if result.get("data_models"):
                        data_models.extend(result["data_models"])
                    if result.get("has_api"):
                        has_api = True
                    if result.get("has_cli"):
                        has_cli = True
                    if result.get("has_loop") and module_name:
                        core_loops.append(module_name)
            except (UnicodeDecodeError, Exception):
                # Skip files that can't be parsed
                continue

        # Process all other language files
        for language in files_by_language:
            if language in ("python", "javascript", "typescript"):
                continue  # Already processed
            
            for file_path in files_by_language[language]:
                try:
                    result = self._parse_file_by_language(file_path, codebase_path, language)
                    if result:
                        module_name = result.get("module_name")
                        if module_name:
                            modules.append(module_name)
                        if result.get("entry_points"):
                            entry_points.extend(result["entry_points"])
                        if result.get("apis"):
                            if module_name and module_name in public_apis:
                                public_apis[module_name].extend(result["apis"])
                            elif module_name:
                                public_apis[module_name] = result["apis"]
                        if result.get("data_models"):
                            data_models.extend(result["data_models"])
                        if result.get("has_api"):
                            has_api = True
                        if result.get("has_cli"):
                            has_cli = True
                        if result.get("has_loop") and module_name:
                            core_loops.append(module_name)
                except (UnicodeDecodeError, Exception):
                    # Skip files that can't be parsed
                    continue

        # Scan for config files
        config_patterns = [
            # Python config files
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "requirements-dev.txt",
            "setup.cfg",
            "tox.ini",
            "pytest.ini",
            ".flake8",
            # Node.js/TypeScript config files
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "tsconfig.json",
            "jsconfig.json",
            "next.config.js",
            "next.config.ts",
            "next.config.mjs",
            ".eslintrc.js",
            ".eslintrc.json",
            ".eslintrc.yml",
            ".eslintrc.yaml",
            "eslint.config.js",
            ".prettierrc",
            ".prettierrc.json",
            ".prettierrc.js",
            "tailwind.config.js",
            "tailwind.config.ts",
            "vite.config.js",
            "vite.config.ts",
            "webpack.config.js",
            "rollup.config.js",
            # Java config files
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "settings.gradle",
            "application.properties",
            "application.yml",
            "application.yaml",
            # Go config files
            "go.mod",
            "go.sum",
            "Gopkg.toml",
            "Gopkg.lock",
            # Rust config files
            "Cargo.toml",
            "Cargo.lock",
            # C# config files
            "appsettings.json",
            "web.config",
            "app.config",
            # Ruby config files
            "Gemfile",
            "Gemfile.lock",
            "Rakefile",
            "config.ru",
            # PHP config files
            "composer.json",
            "composer.lock",
            "phpunit.xml",
            # Swift config files
            "Package.swift",
            # Kotlin config files (Gradle shared with Java)
            # Dart config files
            "pubspec.yaml",
            "pubspec.lock",
            # Vue config files
            "vue.config.js",
            "vite.config.js",
            # Svelte config files
            "svelte.config.js",
            # General config files
            "docker-compose.yml",
            "Dockerfile",
            "Makefile",
        ]
        for pattern in config_patterns:
            matches = list(codebase_path.rglob(pattern))
            config_files.extend([str(f.relative_to(codebase_path)) for f in matches])
        
        # Handle wildcard patterns
        # tsconfig.*.json
        tsconfig_matches = [f for f in codebase_path.rglob("tsconfig*.json")
                           if f.name.startswith("tsconfig") and f.name.endswith(".json")]
        config_files.extend([str(f.relative_to(codebase_path)) for f in tsconfig_matches])
        # *.csproj, *.sln
        csproj_matches = list(codebase_path.rglob("*.csproj"))
        config_files.extend([str(f.relative_to(codebase_path)) for f in csproj_matches])
        sln_matches = list(codebase_path.rglob("*.sln"))
        config_files.extend([str(f.relative_to(codebase_path)) for f in sln_matches])
        # *.xcodeproj (directories, but we'll look for project.pbxproj)
        pbxproj_matches = list(codebase_path.rglob("project.pbxproj"))
        config_files.extend([str(f.relative_to(codebase_path)) for f in pbxproj_matches])
        
        # Extract entry points from package.json scripts
        package_json = codebase_path / "package.json"
        if package_json.exists():
            try:
                package_data = json.loads(package_json.read_text(encoding="utf-8"))
                scripts = package_data.get("scripts", {})
                for script_name in scripts.keys():
                    if script_name in ["start", "dev", "build", "serve"] or script_name.startswith("start:"):
                        entry_points.append(f"package.json:{script_name}")
            except Exception:
                pass

        # Check for Docker
        dockerfile = codebase_path / "Dockerfile"
        if not dockerfile.exists():
            dockerfile = codebase_path / "docker-compose.yml"
        has_docker = dockerfile.exists()

        # Check for Docker ENTRYPOINT/CMD
        if has_docker:
            try:
                dockerfile_path = codebase_path / "Dockerfile"
                if dockerfile_path.exists():
                    dockerfile_content = dockerfile_path.read_text(encoding="utf-8")
                    has_entrypoint = "ENTRYPOINT" in dockerfile_content or "CMD" in dockerfile_content
            except Exception:
                pass

        # Check for README
        readme_patterns = ["README.md", "README.txt", "README.rst", "README"]
        for pattern in readme_patterns:
            if (codebase_path / pattern).exists():
                has_readme = True
                break

        # Count source files (excluding config/test files)
        file_count = sum(len(files) for files in files_by_language.values())

        # Check for tests
        # Python test patterns
        test_files = list(codebase_path.rglob("test_*.py"))
        test_files.extend(codebase_path.rglob("*_test.py"))
        # JavaScript/TypeScript test patterns
        test_files.extend(codebase_path.rglob("*.test.js"))
        test_files.extend(codebase_path.rglob("*.test.ts"))
        test_files.extend(codebase_path.rglob("*.test.jsx"))
        test_files.extend(codebase_path.rglob("*.test.tsx"))
        test_files.extend(codebase_path.rglob("*.spec.js"))
        test_files.extend(codebase_path.rglob("*.spec.ts"))
        test_files.extend(codebase_path.rglob("*.spec.jsx"))
        test_files.extend(codebase_path.rglob("*.spec.tsx"))
        # Filter out excluded directories
        test_files = [
            f for f in test_files
            if not any(excluded in f.parts for excluded in excluded_dirs)
        ]
        has_tests = len(test_files) > 0

        # Check for persistence (database imports, file I/O patterns)
        # Python patterns
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
        # JavaScript/TypeScript patterns
        js_ts_persistence_patterns = [
            "prisma",
            "@prisma/client",
            "mongoose",
            "sequelize",
            "typeorm",
            "drizzle-orm",
            "knex",
            "pg",
            "mysql2",
            "sqlite3",
            "better-sqlite3",
            "redis",
            "ioredis",
            "mongodb",
            "firebase",
            "supabase",
        ]
        # Java patterns
        java_persistence_patterns = [
            "JPA",
            "Hibernate",
            "MyBatis",
            "Spring Data",
            "javax.persistence",
            "jakarta.persistence",
        ]
        # Go patterns
        go_persistence_patterns = [
            "gorm",
            "sqlx",
            "database/sql",
            "mongo-go-driver",
            "go-redis",
        ]
        # Rust patterns
        rust_persistence_patterns = [
            "sqlx",
            "diesel",
            "sea-orm",
            "mongodb",
            "redis",
        ]
        # C# patterns
        csharp_persistence_patterns = [
            "Entity Framework",
            "NHibernate",
            "Dapper",
            "MongoDB.Driver",
            "System.Data",
        ]
        # Ruby patterns
        ruby_persistence_patterns = [
            "ActiveRecord",
            "Sequel",
            "Mongoid",
        ]
        # PHP patterns
        php_persistence_patterns = [
            "Eloquent",
            "Doctrine",
            "MongoDB",
        ]
        # Swift patterns
        swift_persistence_patterns = [
            "CoreData",
            "Realm",
            "GRDB",
        ]
        # Kotlin patterns
        kotlin_persistence_patterns = [
            "Room",
            "Exposed",
            "Ktorm",
        ]
        # Dart patterns
        dart_persistence_patterns = [
            "sqflite",
            "hive",
            "moor",
        ]
        
        # Combine all patterns
        all_persistence_patterns = (
            persistence_patterns + js_ts_persistence_patterns + java_persistence_patterns +
            go_persistence_patterns + rust_persistence_patterns + csharp_persistence_patterns +
            ruby_persistence_patterns + php_persistence_patterns + swift_persistence_patterns +
            kotlin_persistence_patterns + dart_persistence_patterns
        )
        
        # Check all source files for persistence patterns
        if not has_persistence:
            for language_files in files_by_language.values():
                for file_path in language_files:
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        if any(pattern in content for pattern in all_persistence_patterns):
                            has_persistence = True
                            break
                    except Exception:
                        continue
                if has_persistence:
                    break

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
            has_docker=has_docker,
            has_entrypoint=has_entrypoint,
            has_source_code=file_count > 0,
            has_readme=has_readme,
            file_count=file_count,
        )

    def _merge_parse_result(
        self,
        result: dict,
        modules: list[str],
        entry_points: list[str],
        public_apis: dict[str, list[str]],
        data_models: list[str],
        core_loops: list[str],
        has_api: bool,
        has_cli: bool,
    ) -> None:
        """
        Merge parse result into the main collections.

        Args:
            result: Parse result dictionary
            modules: List to append module names
            entry_points: List to append entry points
            public_apis: Dict to merge APIs
            data_models: List to append data models
            core_loops: List to append core loops
            has_api: Boolean flag for API detection
            has_cli: Boolean flag for CLI detection
        """
        module_name = result.get("module_name")
        if module_name:
            modules.append(module_name)
        if result.get("entry_points"):
            entry_points.extend(result["entry_points"])
        if result.get("apis"):
            if module_name and module_name in public_apis:
                public_apis[module_name].extend(result["apis"])
            elif module_name:
                public_apis[module_name] = result["apis"]
        if result.get("data_models"):
            data_models.extend(result["data_models"])
        if result.get("has_api"):
            # Note: has_api and has_cli are mutable flags, need to modify in-place
            pass  # Will be handled by caller
        if result.get("has_cli"):
            pass  # Will be handled by caller
        if result.get("has_loop") and module_name:
            core_loops.append(module_name)

    def _parse_file_by_language(
        self, file_path: Path, codebase_path: Path, language: str
    ) -> dict | None:
        """
        Route file to appropriate parser based on language.

        Args:
            file_path: Path to the file
            codebase_path: Root path of the codebase
            language: Detected language name

        Returns:
            Dictionary with extracted information, or None
        """
        parser_map = {
            "python": self._parse_python_file,
            "javascript": self._parse_js_ts_file,
            "typescript": self._parse_js_ts_file,
            "java": self._parse_java_file,
            "go": self._parse_go_file,
            "rust": self._parse_rust_file,
            "csharp": self._parse_csharp_file,
            "ruby": self._parse_ruby_file,
            "php": self._parse_php_file,
            "swift": self._parse_swift_file,
            "kotlin": self._parse_kotlin_file,
            "dart": self._parse_dart_file,
            "vue": self._parse_vue_file,
            "svelte": self._parse_svelte_file,
        }
        parser = parser_map.get(language)
        if parser:
            return parser(file_path, codebase_path)
        return None

    def _parse_python_file(
        self, file_path: Path, codebase_path: Path
    ) -> dict | None:
        """
        Parse a Python file (existing AST-based parsing logic).

        This is a wrapper around the existing Python parsing logic.
        """
        # This will be handled separately in the main scan loop
        # since it uses AST parsing, not regex
        return None

    def _parse_js_ts_file(
        self, file_path: Path, codebase_path: Path
    ) -> dict | None:
        """
        Parse a JavaScript/TypeScript file to extract structural information.

        Args:
            file_path: Path to the JS/TS file
            codebase_path: Root path of the codebase

        Returns:
            Dictionary with extracted information, or None if parsing fails
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        # Extract module name from file path
        relative_path = file_path.relative_to(codebase_path)
        # Use forward slashes for JS/TS module names (consistent with import paths)
        module_name = str(relative_path.with_suffix("")).replace("\\", "/")

        result: dict = {
            "module_name": module_name,
            "entry_points": [],
            "apis": [],
            "data_models": [],
            "has_api": False,
            "has_cli": False,
            "has_loop": False,
        }

        # Check for Next.js API route (route.ts, route.js in app directory)
        if "route.ts" in str(file_path) or "route.js" in str(file_path):
            result["has_api"] = True
            result["entry_points"].append(f"{module_name}.route")
            # Extract HTTP methods
            for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                if re.search(rf"export\s+(async\s+)?function\s+{method}\b", content, re.IGNORECASE):
                    result["apis"].append(f"{method.lower()}_handler")

        # Check for Next.js middleware
        if file_path.name == "middleware.ts" or file_path.name == "middleware.js":
            result["entry_points"].append(f"{module_name}.middleware")

        # Check for Express routes
        if re.search(r"(app|router)\.(get|post|put|delete|patch|all)\s*\(", content):
            result["has_api"] = True
            # Extract route definitions
            route_pattern = r"(app|router)\.(get|post|put|delete|patch|all)\s*\(\s*['\"]([^'\"]+)['\"]"
            for match in re.finditer(route_pattern, content):
                method = match.group(2)
                route_path = match.group(3)
                result["apis"].append(f"{method}:{route_path}")

        # Extract exported functions and classes
        # Match: export function name() or export async function name()
        func_pattern = r"export\s+(async\s+)?function\s+(\w+)"
        for match in re.finditer(func_pattern, content):
            func_name = match.group(2)
            if not func_name.startswith("_"):
                result["apis"].append(func_name)

        # Match: export const name = () => {} or export const name = function() {}
        const_func_pattern = r"export\s+(const|let|var)\s+(\w+)\s*=\s*(async\s+)?\([^)]*\)\s*=>"
        const_func_pattern2 = r"export\s+(const|let|var)\s+(\w+)\s*=\s*(async\s+)?function"
        for pattern in [const_func_pattern, const_func_pattern2]:
            for match in re.finditer(pattern, content):
                func_name = match.group(2)
                if not func_name.startswith("_"):
                    result["apis"].append(func_name)

        # Match: export class Name
        class_pattern = r"export\s+class\s+(\w+)"
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            if not class_name.startswith("_"):
                result["apis"].append(class_name)

        # Extract TypeScript interfaces and types (data models)
        # Match: export interface Name
        interface_pattern = r"export\s+interface\s+(\w+)"
        for match in re.finditer(interface_pattern, content):
            interface_name = match.group(1)
            if not interface_name.startswith("_"):
                result["data_models"].append(f"{module_name}.{interface_name}")

        # Match: export type Name
        type_pattern = r"export\s+type\s+(\w+)"
        for match in re.finditer(type_pattern, content):
            type_name = match.group(1)
            if not type_name.startswith("_"):
                result["data_models"].append(f"{module_name}.{type_name}")

        # Check for entry points (main files)
        if file_path.name in ["index.js", "index.ts", "main.js", "main.ts", "server.js", "server.ts", "app.js", "app.ts"]:
            result["entry_points"].append(module_name)

        # Check for CLI patterns (commander, yargs, etc.)
        if re.search(r"(commander|yargs|meow|minimist)", content, re.IGNORECASE):
            result["has_cli"] = True
            if re.search(r"\.parse\s*\(|\.command\s*\(", content):
                result["entry_points"].append(f"{module_name}.cli")

        # Check for core loops (update/tick functions with loops)
        loop_keywords = ["update", "tick", "run", "main", "loop", "simulate", "animate"]
        for keyword in loop_keywords:
            if re.search(rf"\bfunction\s+{keyword}\b", content, re.IGNORECASE):
                # Check if it contains a loop
                func_match = re.search(rf"(async\s+)?function\s+{keyword}\s*\([^)]*\)\s*{{", content, re.IGNORECASE)
                if func_match:
                    # Extract function body and check for loops
                    start_pos = func_match.end()
                    brace_count = 1
                    end_pos = start_pos
                    for i, char in enumerate(content[start_pos:], start_pos):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_pos = i
                                break
                    func_body = content[start_pos:end_pos]
                    if re.search(r"\b(for|while)\s*\(", func_body):
                        result["has_loop"] = True
                        break

        return result

    def _parse_java_file(
        self, file_path: Path, codebase_path: Path
    ) -> dict | None:
        """Parse a Java file to extract structural information."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        relative_path = file_path.relative_to(codebase_path)
        module_name = str(relative_path.with_suffix("")).replace("\\", "/")

        result: dict = {
            "module_name": module_name,
            "entry_points": [],
            "apis": [],
            "data_models": [],
            "has_api": False,
            "has_cli": False,
            "has_loop": False,
        }

        # Extract package
        package_match = re.search(r"^package\s+(\S+);", content, re.MULTILINE)
        if package_match:
            package_name = package_match.group(1)
            module_name = f"{package_name}.{module_name.replace('/', '.')}"

        # Extract public classes
        class_pattern = r"public\s+class\s+(\w+)"
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            result["apis"].append(class_name)

        # Extract Spring Boot application entry point
        if re.search(r"@SpringBootApplication", content):
            result["entry_points"].append(f"{module_name}.SpringBootApplication")
        if re.search(r"public\s+static\s+void\s+main\s*\(", content):
            result["entry_points"].append(f"{module_name}.main")

        # Extract Spring controllers and API endpoints
        if re.search(r"@(RestController|Controller)", content):
            result["has_api"] = True
            # Extract @RequestMapping, @GetMapping, etc.
            for annotation in ["RequestMapping", "GetMapping", "PostMapping", "PutMapping", "DeleteMapping"]:
                if re.search(rf"@{annotation}", content):
                    result["has_api"] = True

        # Extract entities/data models
        if re.search(r"@Entity", content):
            for match in re.finditer(r"@Entity\s+public\s+class\s+(\w+)", content):
                result["data_models"].append(f"{module_name}.{match.group(1)}")

        return result

    def _parse_go_file(
        self, file_path: Path, codebase_path: Path
    ) -> dict | None:
        """Parse a Go file to extract structural information."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        relative_path = file_path.relative_to(codebase_path)
        module_name = str(relative_path.with_suffix("")).replace("\\", "/")

        result: dict = {
            "module_name": module_name,
            "entry_points": [],
            "apis": [],
            "data_models": [],
            "has_api": False,
            "has_cli": False,
            "has_loop": False,
        }

        # Extract package
        package_match = re.search(r"^package\s+(\w+)", content, re.MULTILINE)
        if package_match:
            package_name = package_match.group(1)
            module_name = f"{package_name}/{module_name}"

        # Extract exported functions (capitalized)
        func_pattern = r"^func\s+([A-Z]\w*)\s*\("
        for match in re.finditer(func_pattern, content, re.MULTILINE):
            func_name = match.group(1)
            result["apis"].append(func_name)

        # Extract main function (entry point)
        if re.search(r"^func\s+main\s*\(", content, re.MULTILINE):
            result["entry_points"].append(f"{module_name}.main")

        # Extract structs (data models)
        struct_pattern = r"^type\s+([A-Z]\w*)\s+struct"
        for match in re.finditer(struct_pattern, content, re.MULTILINE):
            struct_name = match.group(1)
            result["data_models"].append(f"{module_name}.{struct_name}")

        # Extract interfaces
        interface_pattern = r"^type\s+([A-Z]\w*)\s+interface"
        for match in re.finditer(interface_pattern, content, re.MULTILINE):
            interface_name = match.group(1)
            result["apis"].append(interface_name)

        # Check for HTTP handlers
        if re.search(r"(http\.|gin\.|fiber\.|echo\.)", content):
            result["has_api"] = True

        return result

    def _parse_rust_file(
        self, file_path: Path, codebase_path: Path
    ) -> dict | None:
        """Parse a Rust file to extract structural information."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        relative_path = file_path.relative_to(codebase_path)
        module_name = str(relative_path.with_suffix("")).replace("\\", "/")

        result: dict = {
            "module_name": module_name,
            "entry_points": [],
            "apis": [],
            "data_models": [],
            "has_api": False,
            "has_cli": False,
            "has_loop": False,
        }

        # Extract module declarations
        mod_pattern = r"^(pub\s+)?mod\s+(\w+)"
        for match in re.finditer(mod_pattern, content, re.MULTILINE):
            mod_name = match.group(2)
            module_name = f"{module_name}::{mod_name}"

        # Extract public functions
        pub_func_pattern = r"pub\s+fn\s+(\w+)"
        for match in re.finditer(pub_func_pattern, content):
            func_name = match.group(1)
            result["apis"].append(func_name)

        # Extract main function (entry point)
        if re.search(r"^fn\s+main\s*\(", content, re.MULTILINE) or re.search(r"#\[tokio::main\]", content):
            result["entry_points"].append(f"{module_name}::main")

        # Extract structs (data models)
        struct_pattern = r"pub\s+struct\s+(\w+)"
        for match in re.finditer(struct_pattern, content):
            struct_name = match.group(1)
            result["data_models"].append(f"{module_name}::{struct_name}")

        # Extract enums
        enum_pattern = r"pub\s+enum\s+(\w+)"
        for match in re.finditer(enum_pattern, content):
            enum_name = match.group(1)
            result["data_models"].append(f"{module_name}::{enum_name}")

        # Extract traits
        trait_pattern = r"pub\s+trait\s+(\w+)"
        for match in re.finditer(trait_pattern, content):
            trait_name = match.group(1)
            result["apis"].append(f"{module_name}::{trait_name}")

        # Check for web frameworks
        if re.search(r"(actix|warp|rocket|axum)", content, re.IGNORECASE):
            result["has_api"] = True

        return result

    def _parse_csharp_file(
        self, file_path: Path, codebase_path: Path
    ) -> dict | None:
        """Parse a C# file to extract structural information."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        relative_path = file_path.relative_to(codebase_path)
        module_name = str(relative_path.with_suffix("")).replace("\\", "/")

        result: dict = {
            "module_name": module_name,
            "entry_points": [],
            "apis": [],
            "data_models": [],
            "has_api": False,
            "has_cli": False,
            "has_loop": False,
        }

        # Extract namespace
        namespace_match = re.search(r"^namespace\s+([\w.]+)", content, re.MULTILINE)
        if namespace_match:
            namespace = namespace_match.group(1)
            module_name = f"{namespace}.{module_name.replace('/', '.')}"

        # Extract public classes
        class_pattern = r"public\s+class\s+(\w+)"
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            result["apis"].append(class_name)

        # Extract Main method (entry point)
        if re.search(r"static\s+void\s+Main\s*\(", content):
            result["entry_points"].append(f"{module_name}.Main")

        # Extract ASP.NET API controllers
        if re.search(r"\[ApiController\]|Controller\s*:\s*ControllerBase", content):
            result["has_api"] = True
            # Extract HTTP action methods
            for method in ["HttpGet", "HttpPost", "HttpPut", "HttpDelete"]:
                if re.search(rf"\[{method}\]", content):
                    result["has_api"] = True

        # Extract interfaces (data models/APIs)
        interface_pattern = r"public\s+interface\s+(\w+)"
        for match in re.finditer(interface_pattern, content):
            interface_name = match.group(1)
            result["apis"].append(interface_name)

        return result

    def _parse_ruby_file(
        self, file_path: Path, codebase_path: Path
    ) -> dict | None:
        """Parse a Ruby file to extract structural information."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        relative_path = file_path.relative_to(codebase_path)
        module_name = str(relative_path.with_suffix("")).replace("\\", "/")

        result: dict = {
            "module_name": module_name,
            "entry_points": [],
            "apis": [],
            "data_models": [],
            "has_api": False,
            "has_cli": False,
            "has_loop": False,
        }

        # Extract module/class definitions
        module_pattern = r"^(module|class)\s+([A-Z]\w*)"
        for match in re.finditer(module_pattern, content, re.MULTILINE):
            name = match.group(2)
            result["apis"].append(name)
            if match.group(1) == "class":
                result["data_models"].append(f"{module_name}.{name}")

        # Extract public methods
        def_pattern = r"^\s*def\s+(\w+)"
        for match in re.finditer(def_pattern, content, re.MULTILINE):
            method_name = match.group(1)
            if not method_name.startswith("_"):
                result["apis"].append(method_name)

        # Check for Rails controllers
        if "ApplicationController" in content or re.search(r"class\s+\w+Controller", content):
            result["has_api"] = True

        # Check for entry point
        if re.search(r"if\s+__FILE__\s*==\s*\$0", content):
            result["entry_points"].append(module_name)

        return result

    def _parse_php_file(
        self, file_path: Path, codebase_path: Path
    ) -> dict | None:
        """Parse a PHP file to extract structural information."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        relative_path = file_path.relative_to(codebase_path)
        module_name = str(relative_path.with_suffix("")).replace("\\", "/")

        result: dict = {
            "module_name": module_name,
            "entry_points": [],
            "apis": [],
            "data_models": [],
            "has_api": False,
            "has_cli": False,
            "has_loop": False,
        }

        # Extract namespace
        namespace_match = re.search(r"^namespace\s+([\w\\]+)", content, re.MULTILINE)
        if namespace_match:
            namespace = namespace_match.group(1).replace("\\", ".")
            module_name = f"{namespace}.{module_name.replace('/', '.')}"

        # Extract classes
        class_pattern = r"class\s+(\w+)"
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            result["apis"].append(class_name)

        # Extract public methods
        method_pattern = r"public\s+function\s+(\w+)"
        for match in re.finditer(method_pattern, content):
            method_name = match.group(1)
            result["apis"].append(method_name)

        # Check for Laravel controllers
        if re.search(r"extends\s+Controller|extends\s+ApiController", content):
            result["has_api"] = True

        # Check for entry point
        if file_path.name == "index.php" or re.search(r"\$_SERVER\['REQUEST_URI'\]", content):
            result["entry_points"].append(module_name)

        return result

    def _parse_swift_file(
        self, file_path: Path, codebase_path: Path
    ) -> dict | None:
        """Parse a Swift file to extract structural information."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        relative_path = file_path.relative_to(codebase_path)
        module_name = str(relative_path.with_suffix("")).replace("\\", "/")

        result: dict = {
            "module_name": module_name,
            "entry_points": [],
            "apis": [],
            "data_models": [],
            "has_api": False,
            "has_cli": False,
            "has_loop": False,
        }

        # Extract classes
        class_pattern = r"^(public\s+)?class\s+(\w+)"
        for match in re.finditer(class_pattern, content, re.MULTILINE):
            class_name = match.group(2)
            result["apis"].append(class_name)

        # Extract structs
        struct_pattern = r"^(public\s+)?struct\s+(\w+)"
        for match in re.finditer(struct_pattern, content, re.MULTILINE):
            struct_name = match.group(2)
            result["data_models"].append(f"{module_name}.{struct_name}")

        # Extract protocols
        protocol_pattern = r"^(public\s+)?protocol\s+(\w+)"
        for match in re.finditer(protocol_pattern, content, re.MULTILINE):
            protocol_name = match.group(2)
            result["apis"].append(protocol_name)

        # Extract @main entry point
        if re.search(r"@main", content):
            result["entry_points"].append(f"{module_name}.main")

        # Extract public functions
        func_pattern = r"^public\s+func\s+(\w+)"
        for match in re.finditer(func_pattern, content, re.MULTILINE):
            func_name = match.group(1)
            result["apis"].append(func_name)

        return result

    def _parse_kotlin_file(
        self, file_path: Path, codebase_path: Path
    ) -> dict | None:
        """Parse a Kotlin file to extract structural information."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        relative_path = file_path.relative_to(codebase_path)
        module_name = str(relative_path.with_suffix("")).replace("\\", "/")

        result: dict = {
            "module_name": module_name,
            "entry_points": [],
            "apis": [],
            "data_models": [],
            "has_api": False,
            "has_cli": False,
            "has_loop": False,
        }

        # Extract package
        package_match = re.search(r"^package\s+([\w.]+)", content, re.MULTILINE)
        if package_match:
            package_name = package_match.group(1)
            module_name = f"{package_name}.{module_name.replace('/', '.')}"

        # Extract classes
        class_pattern = r"^(public\s+)?class\s+(\w+)"
        for match in re.finditer(class_pattern, content, re.MULTILINE):
            class_name = match.group(2)
            result["apis"].append(class_name)

        # Extract data classes
        data_class_pattern = r"data\s+class\s+(\w+)"
        for match in re.finditer(data_class_pattern, content):
            class_name = match.group(1)
            result["data_models"].append(f"{module_name}.{class_name}")

        # Extract objects (singletons)
        object_pattern = r"^object\s+(\w+)"
        for match in re.finditer(object_pattern, content, re.MULTILINE):
            object_name = match.group(1)
            result["apis"].append(object_name)

        # Extract interfaces
        interface_pattern = r"interface\s+(\w+)"
        for match in re.finditer(interface_pattern, content):
            interface_name = match.group(1)
            result["apis"].append(interface_name)

        # Extract main function (entry point)
        if re.search(r"fun\s+main\s*\(", content):
            result["entry_points"].append(f"{module_name}.main")

        # Check for Android Activity
        if re.search(r":\s*AppCompatActivity|:\s*Activity", content):
            result["has_api"] = True

        return result

    def _parse_dart_file(
        self, file_path: Path, codebase_path: Path
    ) -> dict | None:
        """Parse a Dart file to extract structural information."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        relative_path = file_path.relative_to(codebase_path)
        module_name = str(relative_path.with_suffix("")).replace("\\", "/")

        result: dict = {
            "module_name": module_name,
            "entry_points": [],
            "apis": [],
            "data_models": [],
            "has_api": False,
            "has_cli": False,
            "has_loop": False,
        }

        # Extract library
        library_match = re.search(r"^library\s+([\w.]+)", content, re.MULTILINE)
        if library_match:
            library_name = library_match.group(1)
            module_name = library_name

        # Extract classes
        class_pattern = r"^class\s+(\w+)"
        for match in re.finditer(class_pattern, content, re.MULTILINE):
            class_name = match.group(1)
            result["apis"].append(class_name)
            result["data_models"].append(f"{module_name}.{class_name}")

        # Extract main function (entry point)
        if re.search(r"^void\s+main\s*\(", content, re.MULTILINE):
            result["entry_points"].append(f"{module_name}.main")

        # Check for Flutter widgets
        if re.search(r"extends\s+StatelessWidget|extends\s+StatefulWidget", content):
            result["has_api"] = True

        return result

    def _parse_vue_file(
        self, file_path: Path, codebase_path: Path
    ) -> dict | None:
        """Parse a Vue file to extract structural information."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        relative_path = file_path.relative_to(codebase_path)
        module_name = str(relative_path.with_suffix("")).replace("\\", "/")

        result: dict = {
            "module_name": module_name,
            "entry_points": [],
            "apis": [],
            "data_models": [],
            "has_api": False,
            "has_cli": False,
            "has_loop": False,
        }

        # Extract component name from <script> tag
        script_match = re.search(r"<script[^>]*>([\s\S]*?)</script>", content)
        if script_match:
            script_content = script_match.group(1)
            # Extract export default
            export_match = re.search(r"export\s+default\s+{\s*name:\s*['\"](\w+)['\"]", script_content)
            if export_match:
                component_name = export_match.group(1)
                result["apis"].append(component_name)

        # Extract props (data models)
        props_match = re.search(r"props:\s*(\[[\s\S]*?\]|\{[\s\S]*?\})", content)
        if props_match:
            result["data_models"].append(f"{module_name}.props")

        # Vue components are typically API endpoints in SPA
        result["has_api"] = True

        return result

    def _parse_svelte_file(
        self, file_path: Path, codebase_path: Path
    ) -> dict | None:
        """Parse a Svelte file to extract structural information."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        relative_path = file_path.relative_to(codebase_path)
        module_name = str(relative_path.with_suffix("")).replace("\\", "/")

        result: dict = {
            "module_name": module_name,
            "entry_points": [],
            "apis": [],
            "data_models": [],
            "has_api": False,
            "has_cli": False,
            "has_loop": False,
        }

        # Extract script section
        script_match = re.search(r"<script[^>]*>([\s\S]*?)</script>", content)
        if script_match:
            script_content = script_match.group(1)
            # Extract exported variables/functions
            export_pattern = r"export\s+(let|const|function)\s+(\w+)"
            for match in re.finditer(export_pattern, script_content):
                export_name = match.group(2)
                result["apis"].append(export_name)

        # Svelte components are typically API endpoints
        result["has_api"] = True

        return result


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

