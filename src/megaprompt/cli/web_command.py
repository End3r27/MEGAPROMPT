"""CLI command for launching the web application."""

import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional

import click


def check_port_available(port: int) -> bool:
    """Check if a port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def find_available_port(start_port: int, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port."""
    for i in range(max_attempts):
        port = start_port + i
        if check_port_available(port):
            return port
    raise RuntimeError(f"Could not find available port starting from {start_port}")


def check_python_version() -> bool:
    """Check if Python version is >= 3.10."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        click.echo(f"Error: Python 3.10+ required, found {version.major}.{version.minor}", err=True)
        return False
    return True


def check_node_installed() -> tuple[bool, Optional[str]]:
    """Check if Node.js is installed and return version."""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            # Check if version is >= 18
            version_num = int(version.lstrip("v").split(".")[0])
            if version_num < 18:
                return False, version
            return True, version
        return False, None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, None


def check_npm_installed() -> tuple[bool, Optional[str]]:
    """Check if npm is installed and return version."""
    # On Windows, use shell=True to help with PATH issues
    use_shell = platform.system() == "Windows"
    
    try:
        # Try npm command directly
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=use_shell,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Fallback: try using node to find npm (Windows sometimes has PATH issues)
    if platform.system() == "Windows":
        try:
            # Check if npm.cmd exists in common Node.js locations
            node_paths = [
                Path(os.environ.get("ProgramFiles", "")) / "nodejs" / "npm.cmd",
                Path(os.environ.get("ProgramFiles(x86)", "")) / "nodejs" / "npm.cmd",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "bin" / "npm.cmd",
            ]
            for npm_path in node_paths:
                if npm_path.exists():
                    result = subprocess.run(
                        [str(npm_path), "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        return True, result.stdout.strip()
        except Exception:
            pass
    
    return False, None


def setup_backend(webapp_dir: Path, skip_setup: bool, reinstall: bool) -> bool:
    """Set up Django backend."""
    backend_dir = webapp_dir / "backend"

    # Check if manage.py exists
    manage_py = backend_dir / "manage.py"
    
    if not manage_py.exists():
        click.echo("Creating Django backend project...")
        try:
            # Create backend directory
            backend_dir.mkdir(parents=True, exist_ok=True)

            # Create Django project using django-admin
            # django-admin startproject creates the project in the specified directory
            use_shell = platform.system() == "Windows"
            result = subprocess.run(
                ["django-admin", "startproject", "megaprompt_web", str(backend_dir)],
                check=True,
                shell=use_shell,
                capture_output=True,
                text=True,
            )
            
            # Verify manage.py was created
            if not manage_py.exists():
                click.echo("Warning: manage.py not found after project creation", err=True)
                click.echo("Attempting to create manage.py manually...", err=True)
                # Create a basic manage.py if it doesn't exist
                manage_py_content = '''#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "megaprompt_web.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
'''
                manage_py.write_text(manage_py_content, encoding="utf-8")
            
            click.echo("✓ Django project created")
        except subprocess.CalledProcessError:
            click.echo("Error: Failed to create Django project. Is Django installed?", err=True)
            return False
        except FileNotFoundError:
            click.echo("Error: django-admin not found. Install Django first: pip install Django", err=True)
            return False

    # Ensure manage.py exists (create if missing)
    if not manage_py.exists():
        click.echo("Creating manage.py...")
        manage_py_content = '''#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "megaprompt_web.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
'''
        manage_py.write_text(manage_py_content, encoding="utf-8")
        click.echo("✓ manage.py created")
    
    # Ensure Django project directory exists
    project_dir = backend_dir / "megaprompt_web"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure __init__.py exists
    init_py = project_dir / "__init__.py"
    if not init_py.exists():
        init_py.write_text("", encoding="utf-8")
    
    # Ensure settings.py exists (create basic one if missing)
    settings_py = project_dir / "settings.py"
    if not settings_py.exists():
        click.echo("Creating basic settings.py...")
        # We'll create a minimal settings.py that can be extended
        # The actual configuration will be added via the template merging logic
        basic_settings = '''"""
Django settings for megaprompt_web project.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-dev-key-change-in-production"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "channels",
    "api",
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "megaprompt_web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "megaprompt_web.wsgi.application"
ASGI_APPLICATION = "megaprompt_web.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
}

CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
CORS_ALLOW_CREDENTIALS = True

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
'''
        settings_py.write_text(basic_settings, encoding="utf-8")
        click.echo("✓ settings.py created")
    
    # Ensure urls.py exists
    urls_py = project_dir / "urls.py"
    if not urls_py.exists():
        click.echo("Creating urls.py...")
        basic_urls = '''"""
URL configuration for megaprompt_web project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]
'''
        urls_py.write_text(basic_urls, encoding="utf-8")
        click.echo("✓ urls.py created")
    
    # Ensure wsgi.py and asgi.py exist
    wsgi_py = project_dir / "wsgi.py"
    if not wsgi_py.exists():
        wsgi_content = '''"""
WSGI config for megaprompt_web project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "megaprompt_web.settings")
application = get_wsgi_application()
'''
        wsgi_py.write_text(wsgi_content, encoding="utf-8")
    
    asgi_py = project_dir / "asgi.py"
    if not asgi_py.exists():
        asgi_content = '''"""
ASGI config for megaprompt_web project.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "megaprompt_web.settings")
application = get_asgi_application()
'''
        asgi_py.write_text(asgi_content, encoding="utf-8")

    # Install dependencies
    requirements_file = backend_dir / "requirements.txt"
    if not requirements_file.exists():
        click.echo("Creating backend requirements.txt...")
        requirements_content = """Django>=5.0
djangorestframework>=3.14
django-cors-headers>=4.0
channels>=4.0
"""
        requirements_file.write_text(requirements_content)

    if not skip_setup or reinstall:
        click.echo("Installing backend dependencies...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                check=True,
                cwd=backend_dir,
            )
            click.echo("✓ Backend dependencies installed")
        except subprocess.CalledProcessError:
            click.echo("Error: Failed to install backend dependencies", err=True)
            return False

    return True


def setup_frontend(webapp_dir: Path, skip_setup: bool, reinstall: bool) -> bool:
    """Set up Next.js frontend."""
    frontend_dir = webapp_dir / "frontend"
    project_root = webapp_dir.parent

    if not frontend_dir.exists():
        click.echo("Creating Next.js frontend project...")
        try:
            # Create frontend directory
            frontend_dir.mkdir(parents=True, exist_ok=True)

            # Copy template files if they exist
            import shutil
            template_dir = project_root / "webapp" / "frontend"
            if template_dir.exists() and (template_dir / "package.json").exists():
                # Copy all files from template
                click.echo("Copying frontend template files...")
                for item in template_dir.iterdir():
                    if item.name not in ["node_modules", ".next", "__pycache__", ".git"]:
                        dest = frontend_dir / item.name
                        try:
                            if item.is_dir():
                                if dest.exists():
                                    shutil.rmtree(dest)
                                shutil.copytree(item, dest, dirs_exist_ok=True)
                            else:
                                shutil.copy2(item, dest)
                        except Exception as e:
                            click.echo(f"Warning: Could not copy {item.name}: {e}", err=True)
                click.echo("✓ Next.js project structure created from templates")
            else:
                # Create Next.js app from scratch using npx
                click.echo("Creating Next.js app from scratch...")
                use_shell = platform.system() == "Windows"
                subprocess.run(
                    [
                        "npx",
                        "create-next-app@latest",
                        str(frontend_dir),
                        "--typescript",
                        "--tailwind",
                        "--app",
                        "--no-import-alias",
                        "--yes",
                    ],
                    check=True,
                    shell=use_shell,
                )
                click.echo("✓ Next.js project created")
        except subprocess.CalledProcessError as e:
            click.echo(f"Error: Failed to create Next.js project: {e}", err=True)
            return False
        except Exception as e:
            click.echo(f"Error: Could not set up frontend: {e}", err=True)
            return False

    # Install shadcn/ui (optional, components are already in template)
    components_json = frontend_dir / "components.json"
    if not components_json.exists():
        click.echo("Initializing shadcn/ui...")
        try:
            use_shell = platform.system() == "Windows"
            subprocess.run(
                ["npx", "shadcn@latest", "init", "-y", "-d"],
                check=True,
                cwd=frontend_dir,
                shell=use_shell,
            )
            click.echo("✓ shadcn/ui initialized")
        except (subprocess.CalledProcessError, FileNotFoundError):
            click.echo("Warning: Failed to initialize shadcn/ui, continuing anyway...", err=True)

    # Check if package.json exists
    package_json = frontend_dir / "package.json"
    if not package_json.exists():
        click.echo("Error: package.json not found in frontend directory", err=True)
        click.echo("Please ensure the frontend template files are properly copied", err=True)
        return False

    if not skip_setup or reinstall:
        click.echo("Installing frontend dependencies...")
        try:
            use_shell = platform.system() == "Windows"
            subprocess.run(
                ["npm", "install"],
                check=True,
                cwd=frontend_dir,
                shell=use_shell,
            )
            click.echo("✓ Frontend dependencies installed")
        except subprocess.CalledProcessError as e:
            click.echo(f"Error: Failed to install frontend dependencies: {e}", err=True)
            return False
        except FileNotFoundError:
            click.echo("Error: npm command not found. Make sure npm is in your PATH", err=True)
            return False

    return True


def start_backend_server(backend_dir: Path, port: int) -> Optional[subprocess.Popen]:
    """Start Django backend server."""
    click.echo(f"Starting backend server on port {port}...")
    try:
        process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", str(port)],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait a bit to check if server started successfully
        time.sleep(2)
        if process.poll() is None:
            click.echo(f"✓ Backend server running on http://localhost:{port}")
            return process
        else:
            stdout, stderr = process.communicate()
            click.echo(f"Error: Backend server failed to start: {stderr.decode()}", err=True)
            return None
    except Exception as e:
        click.echo(f"Error starting backend server: {e}", err=True)
        return None


def start_frontend_server(frontend_dir: Path, port: int) -> Optional[subprocess.Popen]:
    """Start Next.js frontend server."""
    click.echo(f"Starting frontend server on port {port}...")
    try:
        env = os.environ.copy()
        env["PORT"] = str(port)
        use_shell = platform.system() == "Windows"
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=use_shell,
        )
        # Wait a bit to check if server started successfully
        time.sleep(3)
        if process.poll() is None:
            click.echo(f"✓ Frontend server running on http://localhost:{port}")
            return process
        else:
            stdout, stderr = process.communicate()
            error_msg = stderr.decode() if stderr else "Unknown error"
            click.echo(f"Error: Frontend server failed to start: {error_msg}", err=True)
            return None
    except Exception as e:
        click.echo(f"Error starting frontend server: {e}", err=True)
        return None


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Wait for server to be ready."""
    import urllib.request

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


@click.command()
@click.option(
    "--port-backend",
    type=int,
    default=8000,
    help="Backend server port (default: 8000)",
)
@click.option(
    "--port-frontend",
    type=int,
    default=3000,
    help="Frontend server port (default: 3000)",
)
@click.option(
    "--no-browser",
    is_flag=True,
    help="Don't open browser automatically",
)
@click.option(
    "--skip-setup",
    is_flag=True,
    help="Skip dependency installation (assume already set up)",
)
@click.option(
    "--reinstall",
    is_flag=True,
    help="Force reinstall all dependencies",
)
def web(
    port_backend: int,
    port_frontend: int,
    no_browser: bool,
    skip_setup: bool,
    reinstall: bool,
):
    """
    Launch the MEGAPROMPT web application.
    
    Automatically sets up and launches both backend (Django) and frontend (Next.js) servers.
    Opens the web app in your default browser.
    """
    # Check Python version
    if not check_python_version():
        sys.exit(1)

    # Check Node.js
    node_ok, node_version = check_node_installed()
    if not node_ok:
        if node_version:
            click.echo(f"Error: Node.js 18+ required, found {node_version}", err=True)
        else:
            click.echo("Error: Node.js not found. Install Node.js 18+ from https://nodejs.org/", err=True)
        sys.exit(1)
    click.echo(f"✓ Node.js {node_version} found")

    # Check npm
    npm_ok, npm_version = check_npm_installed()
    if not npm_ok:
        click.echo("Error: npm not found. Install npm (comes with Node.js)", err=True)
        click.echo("Hint: On Windows, try restarting your terminal or check if npm is in your PATH", err=True)
        sys.exit(1)
    click.echo(f"✓ npm {npm_version} found")

    # Find available ports
    try:
        port_backend = find_available_port(port_backend)
        port_frontend = find_available_port(port_frontend)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Get webapp directory
    project_root = Path(__file__).parent.parent.parent.parent
    webapp_dir = project_root / "webapp"

    # Setup backend
    click.echo("\n=== Setting up backend ===")
    if not setup_backend(webapp_dir, skip_setup, reinstall):
        sys.exit(1)

    # Setup frontend
    click.echo("\n=== Setting up frontend ===")
    if not setup_frontend(webapp_dir, skip_setup, reinstall):
        sys.exit(1)

    # Start servers
    click.echo("\n=== Starting servers ===")
    backend_dir = webapp_dir / "backend"
    frontend_dir = webapp_dir / "frontend"

    backend_process = start_backend_server(backend_dir, port_backend)
    if not backend_process:
        sys.exit(1)

    frontend_process = start_frontend_server(frontend_dir, port_frontend)
    if not frontend_process:
        backend_process.terminate()
        sys.exit(1)

    # Wait for servers to be ready
    click.echo("\nWaiting for servers to be ready...")
    frontend_url = f"http://localhost:{port_frontend}"
    if wait_for_server(frontend_url, timeout=30):
        click.echo(f"\n✓ Web app is ready!")
        click.echo(f"\nAccess the web app at: {frontend_url}")
        click.echo(f"Backend API at: http://localhost:{port_backend}")
        click.echo("\nPress Ctrl+C to stop the servers")

        # Open browser
        if not no_browser:
            try:
                webbrowser.open(frontend_url)
            except Exception:
                pass

        # Wait for user interrupt
        try:
            while True:
                time.sleep(1)
                # Check if processes are still running
                if backend_process.poll() is not None:
                    click.echo("\nBackend server stopped unexpectedly", err=True)
                    break
                if frontend_process.poll() is not None:
                    click.echo("\nFrontend server stopped unexpectedly", err=True)
                    break
        except KeyboardInterrupt:
            click.echo("\n\nStopping servers...")
            backend_process.terminate()
            frontend_process.terminate()
            backend_process.wait()
            frontend_process.wait()
            click.echo("✓ Servers stopped")
    else:
        click.echo(f"Error: Frontend server did not become ready in time", err=True)
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(1)

