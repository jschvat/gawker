import os
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from ..utils.logging import get_logger

class AppType(Enum):
    NODEJS_API = "nodejs_api"
    REACT_SPA = "react_spa"
    NEXTJS_APP = "nextjs_app"
    VITE_REACT = "vite_react"
    EXPRESS_API = "express_api"
    FASTIFY_API = "fastify_api"
    NESTJS_API = "nestjs_api"
    PYTHON_FLASK = "python_flask"
    PYTHON_DJANGO = "python_django"
    PYTHON_FASTAPI = "python_fastapi"
    GO_API = "go_api"
    RUST_API = "rust_api"
    JAVA_SPRING = "java_spring"
    DOCKER_COMPOSE = "docker_compose"
    GENERIC = "generic"

@dataclass
class MonitoringPattern:
    ports: List[int]
    processes_to_watch: List[str]
    log_files: List[str]
    health_endpoints: List[str]
    dependency_services: List[str]
    performance_metrics: List[str]
    environment_variables: List[str]

@dataclass
class AppConfig:
    app_type: AppType
    name: str
    working_dir: str
    command: str
    environment: str
    monitoring_pattern: MonitoringPattern
    crash_policy: Dict[str, Any]
    dependencies: List[str]

class AppWizard:
    """Intelligent app configuration wizard"""

    def __init__(self):
        self.logger = get_logger(__name__)

    async def analyze_project(self, project_path: str) -> Dict[str, Any]:
        """Analyze a project directory and suggest configuration"""
        project_path = Path(project_path)

        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        # Scan project files
        files_found = self._scan_project_files(project_path)

        # Detect app type
        app_type, confidence = self._detect_app_type(project_path, files_found)

        # Parse package.json if exists
        package_info = {}
        if "package.json" in files_found:
            package_info = self._parse_package_json(project_path / "package.json")

        # Generate monitoring suggestions
        monitoring_patterns = self._generate_monitoring_suggestions(
            app_type, project_path, package_info
        )

        # Detect frameworks and package managers
        frameworks = self._detect_frameworks(project_path, package_info, files_found)
        package_managers = self._detect_package_managers(project_path, files_found)

        # Generate suggested commands
        suggested_commands = self._generate_suggested_commands(app_type, package_info, frameworks)

        # Detect environment variables
        environment_variables = monitoring_patterns.get("environment_variables", {})
        if isinstance(environment_variables, list):
            # Convert list to dict with default values
            env_dict = {}
            for var in environment_variables:
                if var == "PORT":
                    env_dict[var] = str(monitoring_patterns.get("ports", [3000])[0])
                elif var.endswith("_*"):
                    # Wildcard variables, show as example
                    env_dict[var] = "example_value"
                else:
                    env_dict[var] = ""
            environment_variables = env_dict

        # Detect dependencies
        dependencies = self._detect_project_dependencies(project_path, package_info)

        # Extract ports
        ports = monitoring_patterns.get("ports", [])

        return {
            "app_type": app_type.value if app_type else "generic",
            "detected_frameworks": frameworks,
            "package_managers": package_managers,
            "suggested_commands": suggested_commands,
            "environment_variables": environment_variables,
            "monitoring_patterns": monitoring_patterns,
            "ports": ports,
            "dependencies": dependencies,
            "confidence": confidence,
            "project_path": str(project_path),
            "files_found": files_found
        }

    def _detect_frameworks(self, project_path: Path, package_info: Dict, files_found: List[str]) -> List[str]:
        """Detect frameworks used in the project"""
        frameworks = []

        if package_info:
            deps = {**package_info.get("dependencies", {}), **package_info.get("devDependencies", {})}

            framework_mapping = {
                "react": ["react"],
                "vue": ["vue"],
                "angular": ["@angular/core"],
                "next.js": ["next"],
                "nuxt": ["nuxt"],
                "gatsby": ["gatsby"],
                "svelte": ["svelte"],
                "express": ["express"],
                "fastify": ["fastify"],
                "koa": ["koa"],
                "nestjs": ["@nestjs/core"],
                "flask": ["flask"],
                "django": ["django"],
                "fastapi": ["fastapi"],
                "spring": ["spring-boot-starter"],
                "gin": ["github.com/gin-gonic/gin"]
            }

            for framework, identifiers in framework_mapping.items():
                if any(identifier in deps for identifier in identifiers):
                    frameworks.append(framework)

        # Check for framework-specific files
        framework_files = {
            "react": ["src/App.js", "src/App.jsx", "src/App.tsx"],
            "vue": ["src/App.vue", "vue.config.js"],
            "angular": ["angular.json", "src/app/app.component.ts"],
            "next.js": ["next.config.js", "pages/index.js"],
            "django": ["manage.py", "settings.py"],
            "flask": ["app.py", "wsgi.py"],
            "spring": ["pom.xml", "src/main/java"]
        }

        for framework, file_indicators in framework_files.items():
            if any(file_name in files_found or (project_path / file_name).exists()
                   for file_name in file_indicators):
                if framework not in frameworks:
                    frameworks.append(framework)

        return frameworks

    def _detect_package_managers(self, project_path: Path, files_found: List[str]) -> List[str]:
        """Detect package managers used in the project"""
        managers = []

        manager_files = {
            "npm": ["package.json", "package-lock.json"],
            "yarn": ["yarn.lock"],
            "pnpm": ["pnpm-lock.yaml"],
            "pip": ["requirements.txt", "Pipfile"],
            "cargo": ["Cargo.toml"],
            "go modules": ["go.mod"],
            "maven": ["pom.xml"],
            "gradle": ["build.gradle", "gradlew"]
        }

        for manager, file_indicators in manager_files.items():
            if any(file_name in files_found for file_name in file_indicators):
                managers.append(manager)

        return managers

    def _generate_suggested_commands(self, app_type: Optional[AppType], package_info: Dict,
                                   frameworks: List[str]) -> Dict[str, str]:
        """Generate suggested commands for the project"""
        commands = {}

        if not app_type:
            return {"start": "npm start", "build": "npm run build", "test": "npm test"}

        # Get commands from package.json if available
        if package_info and "scripts" in package_info:
            scripts = package_info["scripts"]

            # Map common script names
            script_mapping = {
                "start": ["start", "serve", "dev"],
                "build": ["build", "compile"],
                "test": ["test"],
                "lint": ["lint", "eslint"],
                "format": ["format", "prettier"]
            }

            for cmd_type, script_names in script_mapping.items():
                for script_name in script_names:
                    if script_name in scripts:
                        commands[cmd_type] = f"npm run {script_name}"
                        break

        # App type specific defaults
        type_commands = {
            AppType.REACT_SPA: {
                "start": "npm start",
                "build": "npm run build",
                "test": "npm test"
            },
            AppType.NEXTJS_APP: {
                "start": "npm run dev",
                "build": "npm run build",
                "production": "npm start"
            },
            AppType.VITE_REACT: {
                "start": "npm run dev",
                "build": "npm run build",
                "preview": "npm run preview"
            },
            AppType.EXPRESS_API: {
                "start": "npm start",
                "dev": "npm run dev",
                "test": "npm test"
            },
            AppType.PYTHON_FLASK: {
                "start": "python app.py",
                "dev": "flask run",
                "test": "python -m pytest"
            },
            AppType.PYTHON_FASTAPI: {
                "start": "uvicorn main:app --reload",
                "production": "uvicorn main:app --host 0.0.0.0 --port 8000",
                "test": "python -m pytest"
            },
            AppType.GO_API: {
                "start": "go run main.go",
                "build": "go build",
                "test": "go test"
            },
            AppType.RUST_API: {
                "start": "cargo run",
                "build": "cargo build --release",
                "test": "cargo test"
            }
        }

        # Fill in missing commands with defaults
        default_commands = type_commands.get(app_type, {})
        for cmd_type, cmd in default_commands.items():
            if cmd_type not in commands:
                commands[cmd_type] = cmd

        return commands

    def _detect_project_dependencies(self, project_path: Path, package_info: Dict) -> List[str]:
        """Detect project dependencies that need to be managed"""
        dependencies = []

        # Check for database dependencies
        if package_info:
            deps = {**package_info.get("dependencies", {}), **package_info.get("devDependencies", {})}

            db_deps = ["mongodb", "postgresql", "mysql", "redis", "sqlite"]
            for db in db_deps:
                db_indicators = {
                    "mongodb": ["mongodb", "mongoose"],
                    "postgresql": ["pg", "postgres"],
                    "mysql": ["mysql", "mysql2"],
                    "redis": ["redis", "ioredis"],
                    "sqlite": ["sqlite3", "better-sqlite3"]
                }

                if any(indicator in deps for indicator in db_indicators.get(db, [])):
                    dependencies.append(db)

        # Check for docker-compose dependencies
        if (project_path / "docker-compose.yml").exists():
            dependencies.append("docker-compose")

        return dependencies

    def _scan_project_files(self, project_path: Path) -> List[str]:
        """Scan project directory for relevant files"""
        important_files = [
            "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
            "requirements.txt", "pyproject.toml", "setup.py",
            "go.mod", "go.sum", "Cargo.toml", "Cargo.lock",
            "pom.xml", "build.gradle", "build.gradle.kts",
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
            ".env", ".env.example", ".env.local", ".env.production",
            "next.config.js", "vite.config.js", "webpack.config.js",
            "tsconfig.json", "jsconfig.json",
            "server.js", "app.js", "index.js", "main.js",
            "app.py", "main.py", "server.py", "wsgi.py",
            "main.go", "server.go", "main.rs",
            "README.md", "CONTRIBUTING.md"
        ]

        found_files = []
        for file_name in important_files:
            if (project_path / file_name).exists():
                found_files.append(file_name)

        return found_files

    def _detect_app_type(self, project_path: Path, files_found: List[str]) -> Tuple[Optional[AppType], float]:
        """Detect application type with confidence score"""

        # Check for specific framework indicators
        if "package.json" in files_found:
            package_info = self._parse_package_json(project_path / "package.json")

            # Next.js detection
            if any("next" in dep for dep in package_info.get("dependencies", {}).keys()):
                return AppType.NEXTJS_APP, 0.95

            # Vite React detection
            if any("vite" in dep for dep in package_info.get("devDependencies", {}).keys()) and \
               any("react" in dep for dep in package_info.get("dependencies", {}).keys()):
                return AppType.VITE_REACT, 0.90

            # React SPA detection
            if any("react-scripts" in dep for dep in package_info.get("dependencies", {}).keys()):
                return AppType.REACT_SPA, 0.90

            # Express API detection
            if any("express" in dep for dep in package_info.get("dependencies", {}).keys()):
                return AppType.EXPRESS_API, 0.85

            # Fastify API detection
            if any("fastify" in dep for dep in package_info.get("dependencies", {}).keys()):
                return AppType.FASTIFY_API, 0.85

            # NestJS detection
            if any("@nestjs" in dep for dep in package_info.get("dependencies", {}).keys()):
                return AppType.NESTJS_API, 0.90

            # Generic Node.js
            if package_info.get("dependencies") or package_info.get("devDependencies"):
                return AppType.NODEJS_API, 0.70

        # Python detection
        if "requirements.txt" in files_found or "pyproject.toml" in files_found:
            if "app.py" in files_found:
                # Check if it's Flask
                try:
                    with open(project_path / "app.py", "r") as f:
                        content = f.read()
                        if "from flask import" in content or "import flask" in content:
                            return AppType.PYTHON_FLASK, 0.85
                        elif "from fastapi import" in content or "import fastapi" in content:
                            return AppType.PYTHON_FASTAPI, 0.85
                except:
                    pass

            if any(f in files_found for f in ["manage.py", "settings.py"]):
                return AppType.PYTHON_DJANGO, 0.85

        # Go detection
        if "go.mod" in files_found:
            return AppType.GO_API, 0.85

        # Rust detection
        if "Cargo.toml" in files_found:
            return AppType.RUST_API, 0.85

        # Java detection
        if "pom.xml" in files_found or any("build.gradle" in f for f in files_found):
            return AppType.JAVA_SPRING, 0.80

        # Docker Compose detection
        if any("docker-compose" in f for f in files_found):
            return AppType.DOCKER_COMPOSE, 0.75

        return AppType.GENERIC, 0.30

    def _parse_package_json(self, package_path: Path) -> Dict[str, Any]:
        """Parse package.json file"""
        try:
            with open(package_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to parse package.json: {e}")
            return {}

    def _generate_monitoring_suggestions(self, app_type: Optional[AppType],
                                       project_path: Path, package_info: Dict) -> Dict[str, Any]:
        """Generate intelligent monitoring pattern suggestions based on app type and project analysis"""

        if not app_type:
            return self._generate_generic_monitoring_pattern(project_path, package_info)

        # Advanced monitoring patterns by app type
        patterns = {
            AppType.REACT_SPA: {
                "ports": [3000, 3001],
                "processes": ["npm", "node", "react-scripts"],
                "health_endpoints": ["/", "/health"],
                "log_files": ["build/static/js/*.js.map"],
                "performance_metrics": ["bundle_size", "build_time", "hot_reload_time"],
                "environment_variables": ["PORT", "NODE_ENV", "PUBLIC_URL", "GENERATE_SOURCEMAP"]
            },
            AppType.NEXTJS_APP: {
                "ports": [3000, 3001],
                "processes": ["npm", "node", "next"],
                "health_endpoints": ["/", "/api/health", "/_next/static"],
                "log_files": [".next/trace"],
                "performance_metrics": ["build_time", "page_load_time", "api_response_time"],
                "environment_variables": ["PORT", "NODE_ENV", "NEXT_PUBLIC_*"]
            },
            AppType.VITE_REACT: {
                "ports": [5173, 5174],
                "processes": ["npm", "node", "vite"],
                "health_endpoints": ["/", "/@vite/client"],
                "log_files": ["dist/**/*.js"],
                "performance_metrics": ["build_time", "hmr_time", "bundle_size"],
                "environment_variables": ["PORT", "NODE_ENV", "VITE_*"]
            },
            AppType.EXPRESS_API: {
                "ports": [3000, 3001, 8000, 8080],
                "processes": ["npm", "node", "nodemon"],
                "health_endpoints": ["/health", "/status", "/ping"],
                "log_files": ["logs/*.log"],
                "performance_metrics": ["response_time", "request_rate", "error_rate"],
                "environment_variables": ["PORT", "NODE_ENV", "DB_URL", "JWT_SECRET"]
            },
            AppType.NODEJS_API: {
                "ports": [3000, 3001, 8000, 8080],
                "processes": ["npm", "node"],
                "health_endpoints": ["/health", "/status"],
                "log_files": ["logs/*.log"],
                "performance_metrics": ["response_time", "cpu_usage", "memory_usage"],
                "environment_variables": ["PORT", "NODE_ENV"]
            },
            AppType.PYTHON_FLASK: {
                "ports": [5000, 5001, 8000],
                "processes": ["python", "flask", "gunicorn", "uwsgi"],
                "health_endpoints": ["/health", "/status"],
                "log_files": ["logs/*.log", "flask.log"],
                "performance_metrics": ["response_time", "request_rate", "error_rate"],
                "environment_variables": ["FLASK_APP", "FLASK_ENV", "PORT"]
            },
            AppType.PYTHON_FASTAPI: {
                "ports": [8000, 8001, 8080],
                "processes": ["python", "uvicorn", "gunicorn"],
                "health_endpoints": ["/health", "/docs", "/redoc"],
                "log_files": ["logs/*.log"],
                "performance_metrics": ["response_time", "request_rate", "async_performance"],
                "environment_variables": ["PORT", "HOST", "WORKERS"]
            },
            AppType.GO_API: {
                "ports": [8080, 8000, 3000],
                "processes": ["go", "./main", "./server"],
                "health_endpoints": ["/health", "/ping"],
                "log_files": ["logs/*.log"],
                "performance_metrics": ["response_time", "goroutines", "memory_usage"],
                "environment_variables": ["PORT", "GO_ENV"]
            }
        }

        base_pattern = patterns.get(app_type, {
            "ports": [8080],
            "processes": ["app"],
            "health_endpoints": ["/health"],
            "log_files": ["logs/*.log"],
            "performance_metrics": ["cpu_usage", "memory_usage"],
            "environment_variables": ["PORT"]
        })

        # Enhance with project-specific detection
        enhanced_pattern = self._enhance_monitoring_pattern(base_pattern, project_path, package_info, app_type)

        return enhanced_pattern

    def _enhance_monitoring_pattern(self, base_pattern: Dict[str, Any], project_path: Path,
                                   package_info: Dict, app_type: AppType) -> Dict[str, Any]:
        """Enhance monitoring pattern with project-specific analysis"""
        enhanced = base_pattern.copy()

        # Detect custom ports from multiple sources
        detected_ports = self._detect_ports(project_path, package_info)
        for port in detected_ports:
            if port not in enhanced["ports"]:
                enhanced["ports"].append(port)

        # Detect environment files and variables
        env_vars = self._detect_environment_variables(project_path, app_type)
        enhanced["environment_variables"].extend(env_vars)

        # Detect configuration files
        config_files = self._detect_config_files(project_path)
        enhanced["config_files"] = config_files

        # Detect log patterns
        log_patterns = self._detect_log_patterns(project_path, app_type)
        enhanced["log_files"].extend(log_patterns)

        # Detect database connections
        db_info = self._detect_database_usage(project_path, package_info)
        if db_info:
            enhanced["database_monitoring"] = db_info

        # Detect API endpoints
        api_endpoints = self._detect_api_endpoints(project_path, app_type)
        enhanced["api_endpoints"] = api_endpoints

        # Detect dependencies that need monitoring
        service_deps = self._detect_service_dependencies(project_path, package_info)
        enhanced["service_dependencies"] = service_deps

        # Remove duplicates and sort
        enhanced["ports"] = sorted(list(set(enhanced["ports"])))
        enhanced["environment_variables"] = list(set(enhanced["environment_variables"]))

        return enhanced

    def _detect_ports(self, project_path: Path, package_info: Dict) -> List[int]:
        """Detect ports used by the application"""
        ports = []

        # Check package.json scripts
        if package_info:
            scripts = package_info.get("scripts", {})
            for script_cmd in scripts.values():
                port_matches = re.findall(r'(?:--port[=\s]+|PORT[=\s]+|:)(\d+)', script_cmd)
                for match in port_matches:
                    port = int(match)
                    if 1000 <= port <= 65535:
                        ports.append(port)

        # Check environment files
        for env_file in [".env", ".env.local", ".env.development", ".env.production"]:
            env_path = project_path / env_file
            if env_path.exists():
                try:
                    content = env_path.read_text()
                    port_matches = re.findall(r'PORT[=\s]+(\d+)', content)
                    for match in port_matches:
                        port = int(match)
                        if 1000 <= port <= 65535:
                            ports.append(port)
                except Exception:
                    pass

        # Check configuration files
        for config_file in ["config.json", "config.js", "next.config.js", "vite.config.js"]:
            config_path = project_path / config_file
            if config_path.exists():
                try:
                    content = config_path.read_text()
                    port_matches = re.findall(r'(?:port["\']?\s*:\s*|PORT[=\s]+)(\d+)', content)
                    for match in port_matches:
                        port = int(match)
                        if 1000 <= port <= 65535:
                            ports.append(port)
                except Exception:
                    pass

        return list(set(ports))

    def _detect_environment_variables(self, project_path: Path, app_type: AppType) -> List[str]:
        """Detect environment variables used by the application"""
        env_vars = set()

        # App type specific variables
        type_vars = {
            AppType.REACT_SPA: ["REACT_APP_*", "PUBLIC_URL", "GENERATE_SOURCEMAP"],
            AppType.NEXTJS_APP: ["NEXT_PUBLIC_*", "NEXTAUTH_*"],
            AppType.VITE_REACT: ["VITE_*"],
            AppType.EXPRESS_API: ["DB_URL", "JWT_SECRET", "API_KEY"],
            AppType.PYTHON_FLASK: ["FLASK_ENV", "SECRET_KEY", "DATABASE_URL"],
            AppType.PYTHON_FASTAPI: ["DATABASE_URL", "SECRET_KEY", "API_V1_STR"]
        }

        env_vars.update(type_vars.get(app_type, []))

        # Scan environment files
        for env_file in [".env.example", ".env", ".env.local", ".env.development"]:
            env_path = project_path / env_file
            if env_path.exists():
                try:
                    content = env_path.read_text()
                    var_matches = re.findall(r'^([A-Z_][A-Z0-9_]*)', content, re.MULTILINE)
                    env_vars.update(var_matches)
                except Exception:
                    pass

        # Scan source code for process.env usage
        for pattern in ["*.js", "*.ts", "*.jsx", "*.tsx", "*.py"]:
            for file_path in project_path.rglob(pattern):
                if "node_modules" in str(file_path) or ".git" in str(file_path):
                    continue
                try:
                    content = file_path.read_text()
                    # JavaScript/TypeScript
                    js_matches = re.findall(r'process\.env\.([A-Z_][A-Z0-9_]*)', content)
                    # Python
                    py_matches = re.findall(r'os\.environ\.get\(["\']([A-Z_][A-Z0-9_]*)["\']', content)
                    env_vars.update(js_matches)
                    env_vars.update(py_matches)
                except Exception:
                    pass

        return list(env_vars)

    def _detect_config_files(self, project_path: Path) -> List[str]:
        """Detect configuration files that should be monitored"""
        config_files = []

        common_configs = [
            "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
            "tsconfig.json", "jsconfig.json", "babel.config.js", "webpack.config.js",
            "next.config.js", "vite.config.js", "vue.config.js",
            "requirements.txt", "Pipfile", "pyproject.toml",
            "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
            "docker-compose.yml", "Dockerfile", ".dockerignore",
            ".env", ".env.example", ".env.local"
        ]

        for config in common_configs:
            if (project_path / config).exists():
                config_files.append(config)

        return config_files

    def _detect_log_patterns(self, project_path: Path, app_type: AppType) -> List[str]:
        """Detect log file patterns"""
        log_patterns = []

        # App type specific log patterns
        type_patterns = {
            AppType.REACT_SPA: ["build/static/js/*.map", "npm-debug.log"],
            AppType.NEXTJS_APP: [".next/trace", ".next/server/pages/**/*.js.map"],
            AppType.VITE_REACT: ["dist/**/*.map", "vite.log"],
            AppType.EXPRESS_API: ["logs/*.log", "access.log", "error.log"],
            AppType.PYTHON_FLASK: ["logs/*.log", "flask.log", "app.log"],
            AppType.PYTHON_FASTAPI: ["logs/*.log", "uvicorn.log", "app.log"]
        }

        log_patterns.extend(type_patterns.get(app_type, []))

        # Check for existing log directories
        common_log_dirs = ["logs", "log", ".logs", "var/log"]
        for log_dir in common_log_dirs:
            if (project_path / log_dir).exists():
                log_patterns.append(f"{log_dir}/*.log")

        return log_patterns

    def _detect_database_usage(self, project_path: Path, package_info: Dict) -> Dict[str, Any]:
        """Detect database usage and connection patterns"""
        db_info = {}

        if package_info:
            deps = {**package_info.get("dependencies", {}), **package_info.get("devDependencies", {})}

            # Detect database libraries
            db_libs = {
                "mongodb": ["mongodb", "mongoose"],
                "postgresql": ["pg", "postgres", "sequelize", "typeorm"],
                "mysql": ["mysql", "mysql2", "sequelize"],
                "redis": ["redis", "ioredis"],
                "sqlite": ["sqlite3", "better-sqlite3"],
                "prisma": ["prisma", "@prisma/client"]
            }

            detected_dbs = []
            for db_type, libs in db_libs.items():
                if any(lib in deps for lib in libs):
                    detected_dbs.append(db_type)

            if detected_dbs:
                db_info["detected_databases"] = detected_dbs
                db_info["connection_monitoring"] = True
                db_info["health_checks"] = [f"/health/db/{db}" for db in detected_dbs]

        return db_info

    def _detect_api_endpoints(self, project_path: Path, app_type: AppType) -> List[str]:
        """Detect API endpoints for monitoring"""
        endpoints = []

        # App type specific endpoints
        if app_type in [AppType.EXPRESS_API, AppType.NODEJS_API]:
            # Scan for Express routes
            for pattern in ["*.js", "*.ts"]:
                for file_path in project_path.rglob(pattern):
                    if "node_modules" in str(file_path):
                        continue
                    try:
                        content = file_path.read_text()
                        # Express route patterns
                        route_matches = re.findall(r'\.(?:get|post|put|delete|patch)\(["\']([^"\']+)["\']', content)
                        endpoints.extend(route_matches)
                    except Exception:
                        pass

        elif app_type in [AppType.PYTHON_FLASK, AppType.PYTHON_FASTAPI]:
            # Scan for Python routes
            for file_path in project_path.rglob("*.py"):
                try:
                    content = file_path.read_text()
                    # Flask routes
                    flask_matches = re.findall(r'@app\.route\(["\']([^"\']+)["\']', content)
                    # FastAPI routes
                    fastapi_matches = re.findall(r'@app\.(?:get|post|put|delete|patch)\(["\']([^"\']+)["\']', content)
                    endpoints.extend(flask_matches)
                    endpoints.extend(fastapi_matches)
                except Exception:
                    pass

        # Add common endpoints
        common_endpoints = ["/health", "/status", "/ping", "/metrics", "/api/health"]
        endpoints.extend(common_endpoints)

        return list(set(endpoints))

    def _detect_service_dependencies(self, project_path: Path, package_info: Dict) -> List[str]:
        """Detect external service dependencies"""
        services = []

        # Check docker-compose for services
        compose_path = project_path / "docker-compose.yml"
        if compose_path.exists():
            try:
                content = compose_path.read_text()
                service_matches = re.findall(r'^\s+([a-zA-Z][a-zA-Z0-9_-]+):', content, re.MULTILINE)
                services.extend(service_matches)
            except Exception:
                pass

        # Check for common service indicators in code
        if package_info:
            deps = {**package_info.get("dependencies", {}), **package_info.get("devDependencies", {})}

            service_libs = {
                "redis": "redis",
                "elasticsearch": "elasticsearch",
                "rabbitmq": "amqplib",
                "kafka": "kafkajs",
                "aws": "aws-sdk"
            }

            for service, lib in service_libs.items():
                if lib in deps:
                    services.append(service)

        return list(set(services))

    def _generate_generic_monitoring_pattern(self, project_path: Path, package_info: Dict) -> Dict[str, Any]:
        """Generate generic monitoring pattern for unknown app types"""
        return {
            "ports": self._detect_ports(project_path, package_info) or [8080],
            "processes": ["app"],
            "health_endpoints": ["/health", "/status"],
            "log_files": ["logs/*.log", "*.log"],
            "performance_metrics": ["cpu_usage", "memory_usage", "response_time"],
            "environment_variables": self._detect_environment_variables(project_path, AppType.GENERIC),
            "config_files": self._detect_config_files(project_path),
            "api_endpoints": ["/health", "/status"]
        }

    def _find_existing_scripts(self, project_path: Path) -> List[Dict[str, str]]:
        """Find existing launch/build scripts in the project"""
        scripts = []

        # Check package.json scripts
        package_path = project_path / "package.json"
        if package_path.exists():
            package_info = self._parse_package_json(package_path)
            npm_scripts = package_info.get("scripts", {})

            for script_name, script_cmd in npm_scripts.items():
                scripts.append({
                    "name": script_name,
                    "command": f"npm run {script_name}",
                    "description": f"NPM script: {script_cmd}",
                    "type": "npm_script"
                })

        # Check for shell scripts
        for script_file in project_path.glob("*.sh"):
            scripts.append({
                "name": script_file.stem,
                "command": f"./{script_file.name}",
                "description": f"Shell script: {script_file.name}",
                "type": "shell_script"
            })

        # Check for Python scripts
        common_python_files = ["app.py", "main.py", "server.py", "run.py"]
        for py_file in common_python_files:
            if (project_path / py_file).exists():
                scripts.append({
                    "name": Path(py_file).stem,
                    "command": f"python {py_file}",
                    "description": f"Python script: {py_file}",
                    "type": "python_script"
                })

        return scripts

    def _find_environment_files(self, project_path: Path) -> List[str]:
        """Find environment configuration files"""
        env_files = []
        env_patterns = [".env*", "*.env", "config/*.env"]

        for pattern in env_patterns:
            for env_file in project_path.glob(pattern):
                if env_file.is_file():
                    env_files.append(str(env_file.relative_to(project_path)))

        return env_files

    def _generate_config_suggestions(self, app_type: Optional[AppType],
                                   project_path: Path, analysis: Dict) -> List[Dict[str, Any]]:
        """Generate ProcessGuard configuration suggestions"""

        if not app_type:
            return []

        suggestions = []
        package_info = analysis.get("package_info", {})
        monitoring = analysis.get("monitoring_suggestions", {})

        # Development configuration
        dev_config = {
            "name": f"{project_path.name}-dev",
            "command": self._suggest_dev_command(app_type, package_info),
            "working_dir": str(project_path),
            "type": "nodejs" if "nodejs" in app_type.value else app_type.value.split("_")[0],
            "env_vars": {
                "NODE_ENV": "development" if "nodejs" in app_type.value else "development",
                "PORT": str(monitoring.get("ports", [3000])[0])
            },
            "auto_restart": True,
            "max_restarts": 10,
            "restart_delay": 3,
            "redirect_output": True,
            "crash_policy": {
                "max_crashes": 8,
                "time_window_minutes": 5,
                "action_on_threshold": "quarantine",
                "quarantine_duration_minutes": 10
            },
            "monitoring": {
                "ports": monitoring.get("ports", []),
                "health_endpoints": monitoring.get("health_endpoints", []),
                "performance_metrics": monitoring.get("performance_metrics", [])
            }
        }

        # Production configuration
        prod_config = {
            "name": f"{project_path.name}-prod",
            "command": self._suggest_prod_command(app_type, package_info),
            "working_dir": str(project_path),
            "type": "nodejs" if "nodejs" in app_type.value else app_type.value.split("_")[0],
            "env_vars": {
                "NODE_ENV": "production" if "nodejs" in app_type.value else "production",
                "PORT": str(monitoring.get("ports", [3000])[0])
            },
            "auto_restart": True,
            "max_restarts": 3,
            "restart_delay": 10,
            "redirect_output": True,
            "crash_policy": {
                "max_crashes": 3,
                "time_window_minutes": 15,
                "action_on_threshold": "disable",
                "kill_dependencies": False
            },
            "monitoring": {
                "ports": monitoring.get("ports", []),
                "health_endpoints": monitoring.get("health_endpoints", []),
                "performance_metrics": monitoring.get("performance_metrics", [])
            }
        }

        suggestions.extend([
            {"name": "Development", "config": dev_config},
            {"name": "Production", "config": prod_config}
        ])

        return suggestions

    def _suggest_dev_command(self, app_type: AppType, package_info: Dict) -> str:
        """Suggest development command based on app type"""

        scripts = package_info.get("scripts", {})

        # Check for common dev script names
        dev_script_names = ["dev", "start", "serve", "develop"]
        for script_name in dev_script_names:
            if script_name in scripts:
                return f"npm run {script_name}"

        # Fallback based on app type
        fallbacks = {
            AppType.REACT_SPA: "npm start",
            AppType.NEXTJS_APP: "npm run dev",
            AppType.VITE_REACT: "npm run dev",
            AppType.EXPRESS_API: "npm run dev",
            AppType.NODEJS_API: "npm start",
            AppType.PYTHON_FLASK: "python app.py",
            AppType.PYTHON_FASTAPI: "uvicorn main:app --reload",
            AppType.GO_API: "go run main.go",
            AppType.RUST_API: "cargo run"
        }

        return fallbacks.get(app_type, "npm start")

    def _suggest_prod_command(self, app_type: AppType, package_info: Dict) -> str:
        """Suggest production command based on app type"""

        scripts = package_info.get("scripts", {})

        # Check for production script names
        prod_script_names = ["start", "prod", "production", "serve"]
        for script_name in prod_script_names:
            if script_name in scripts:
                return f"npm run {script_name}"

        # Fallback based on app type
        fallbacks = {
            AppType.REACT_SPA: "npx serve -s build",
            AppType.NEXTJS_APP: "npm start",
            AppType.VITE_REACT: "npm run preview",
            AppType.EXPRESS_API: "npm start",
            AppType.NODEJS_API: "node server.js",
            AppType.PYTHON_FLASK: "gunicorn app:app",
            AppType.PYTHON_FASTAPI: "uvicorn main:app --host 0.0.0.0 --port 8000",
            AppType.GO_API: "./main",
            AppType.RUST_API: "./target/release/app"
        }

        return fallbacks.get(app_type, "npm start")

    async def generate_launch_script(self, project_path: str = None, app_type: str = None,
                                    process_name: str = None, environment: str = "development",
                                    custom_command: str = None, custom_env_vars: Dict[str, str] = None,
                                    custom_ports: List[int] = None, config: Dict[str, Any] = None) -> str:
        """Generate intelligent launch script"""
        # Support both new signature and legacy config parameter
        if config is None:
            config = {
                "project_path": project_path,
                "app_type": app_type,
                "name": process_name,
                "environment": environment,
                "custom_command": custom_command,
                "env_vars": custom_env_vars or {},
                "ports": custom_ports or []
            }

        app_type_enum = AppType(config.get("app_type", "generic"))

        script_templates = {
            AppType.NODEJS_API: self._generate_nodejs_launch_script,
            AppType.REACT_SPA: self._generate_react_launch_script,
            AppType.NEXTJS_APP: self._generate_nextjs_launch_script,
            AppType.VITE_REACT: self._generate_vite_launch_script,
            AppType.EXPRESS_API: self._generate_express_launch_script,
            AppType.PYTHON_FLASK: self._generate_python_launch_script,
            AppType.PYTHON_FASTAPI: self._generate_fastapi_launch_script,
            AppType.GO_API: self._generate_go_launch_script,
            AppType.RUST_API: self._generate_rust_launch_script
        }

        generator = script_templates.get(app_type_enum, self._generate_generic_launch_script)
        return generator(config)

    def _generate_nodejs_launch_script(self, config: Dict[str, Any]) -> str:
        """Generate Node.js launch script"""
        return f'''#!/bin/bash
# Auto-generated Node.js launch script for {config.get("name", "app")}

set -e

APP_NAME="{config.get("name", "nodejs-app")}"
PORT=${{PORT:-{config.get("port", 3000)}}}
NODE_ENV=${{NODE_ENV:-{config.get("environment", "development")}}}

log() {{
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$APP_NAME] $1"
}}

log "Starting $APP_NAME on port $PORT in $NODE_ENV mode..."

# Check Node.js
if ! command -v node &> /dev/null; then
    log "ERROR: Node.js not found"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    log "Installing dependencies..."
    npm install
fi

# Set environment
export NODE_ENV=$NODE_ENV
export PORT=$PORT
{self._generate_env_exports(config.get("env_vars", {}))}

# Health check function
health_check() {{
    curl -f http://localhost:$PORT{config.get("health_endpoint", "/health")} >/dev/null 2>&1
}}

# Start application
log "Starting: {config.get("command", "npm start")}"
exec {config.get("command", "npm start")}
'''

    def _generate_react_launch_script(self, config: Dict[str, Any]) -> str:
        """Generate React launch script"""
        return f'''#!/bin/bash
# Auto-generated React launch script for {config.get("name", "app")}

set -e

APP_NAME="{config.get("name", "react-app")}"
PORT=${{PORT:-{config.get("port", 3000)}}}

log() {{
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$APP_NAME] $1"
}}

log "Starting React app $APP_NAME on port $PORT..."

# Check for package.json
if [ ! -f "package.json" ]; then
    log "ERROR: package.json not found"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    log "Installing dependencies..."

    if [ -f "yarn.lock" ]; then
        yarn install
    elif [ -f "pnpm-lock.yaml" ]; then
        pnpm install
    else
        npm install
    fi
fi

# Set React environment variables
export PORT=$PORT
export BROWSER=none
export FAST_REFRESH=true
export GENERATE_SOURCEMAP=true
{self._generate_env_exports(config.get("env_vars", {}))}

# Start development server
log "Starting: {config.get("command", "npm start")}"
exec {config.get("command", "npm start")}
'''

    def _generate_nextjs_launch_script(self, config: Dict[str, Any]) -> str:
        """Generate Next.js launch script"""
        return f'''#!/bin/bash
# Auto-generated Next.js launch script for {config.get("name", "app")}

set -e

APP_NAME="{config.get("name", "nextjs-app")}"
PORT=${{PORT:-{config.get("port", 3000)}}}
NODE_ENV=${{NODE_ENV:-{config.get("environment", "development")}}}

log() {{
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$APP_NAME] $1"
}}

log "Starting Next.js app $APP_NAME on port $PORT..."

# Install dependencies
if [ ! -d "node_modules" ]; then
    log "Installing dependencies..."
    npm install
fi

# Set environment
export PORT=$PORT
export NODE_ENV=$NODE_ENV
{self._generate_env_exports(config.get("env_vars", {}))}

# Build for production if needed
if [ "$NODE_ENV" = "production" ] && [ ! -d ".next" ]; then
    log "Building for production..."
    npm run build
fi

# Start application
log "Starting: {config.get("command", "npm run dev" if config.get("environment") == "development" else "npm start")}"
exec {config.get("command", "npm run dev" if config.get("environment") == "development" else "npm start")}
'''

    def _generate_python_launch_script(self, config: Dict[str, Any]) -> str:
        """Generate Python launch script"""
        return f'''#!/bin/bash
# Auto-generated Python launch script for {config.get("name", "app")}

set -e

APP_NAME="{config.get("name", "python-app")}"
PORT=${{PORT:-{config.get("port", 5000)}}}

log() {{
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$APP_NAME] $1"
}}

log "Starting Python app $APP_NAME on port $PORT..."

# Check Python
if ! command -v python3 &> /dev/null; then
    log "ERROR: Python 3 not found"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    log "Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Install dependencies
if [ -f "requirements.txt" ]; then
    log "Installing dependencies..."
    pip install -r requirements.txt
fi

# Set environment
export PORT=$PORT
{self._generate_env_exports(config.get("env_vars", {}))}

# Start application
log "Starting: {config.get("command", "python app.py")}"
exec {config.get("command", "python app.py")}
'''

    def _generate_go_launch_script(self, config: Dict[str, Any]) -> str:
        """Generate Go launch script"""
        return f'''#!/bin/bash
# Auto-generated Go launch script for {config.get("name", "app")}

set -e

APP_NAME="{config.get("name", "go-app")}"
PORT=${{PORT:-{config.get("port", 8080)}}}

log() {{
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$APP_NAME] $1"
}}

log "Starting Go app $APP_NAME on port $PORT..."

# Check Go
if ! command -v go &> /dev/null; then
    log "ERROR: Go not found"
    exit 1
fi

# Set environment
export PORT=$PORT
{self._generate_env_exports(config.get("env_vars", {}))}

# Build and start
if [ "{config.get("environment", "development")}" = "development" ]; then
    log "Starting: go run ."
    exec go run .
else
    log "Building application..."
    go build -o app .
    log "Starting: ./app"
    exec ./app
fi
'''

    def _generate_generic_launch_script(self, config: Dict[str, Any]) -> str:
        """Generate generic launch script"""
        return f'''#!/bin/bash
# Auto-generated launch script for {config.get("name", "app")}

set -e

APP_NAME="{config.get("name", "app")}"

log() {{
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$APP_NAME] $1"
}}

log "Starting $APP_NAME..."

# Set environment variables
{self._generate_env_exports(config.get("env_vars", {}))}

# Start application
log "Starting: {config.get("command", "./start.sh")}"
exec {config.get("command", "./start.sh")}
'''

    def _generate_vite_launch_script(self, config: Dict[str, Any]) -> str:
        """Generate Vite React launch script"""
        return f'''#!/bin/bash
# Auto-generated Vite React launch script for {config.get("name", "app")}

set -e

APP_NAME="{config.get("name", "vite-app")}"
PORT=${{PORT:-{config.get("port", 5173)}}}

log() {{
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$APP_NAME] $1"
}}

log "Starting Vite app $APP_NAME on port $PORT..."

# Check for package.json
if [ ! -f "package.json" ]; then
    log "ERROR: package.json not found"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    log "Installing dependencies..."

    if [ -f "pnpm-lock.yaml" ]; then
        pnpm install
    elif [ -f "yarn.lock" ]; then
        yarn install
    else
        npm install
    fi
fi

# Set Vite environment variables
export PORT=$PORT
export VITE_HOST=0.0.0.0
export VITE_PORT=$PORT
{self._generate_env_exports(config.get("env_vars", {}))}

# Start Vite dev server
log "Starting: {config.get("command", "npm run dev")}"
exec {config.get("command", "npm run dev")}
'''

    def _generate_express_launch_script(self, config: Dict[str, Any]) -> str:
        """Generate Express.js launch script"""
        return f'''#!/bin/bash
# Auto-generated Express.js launch script for {config.get("name", "app")}

set -e

APP_NAME="{config.get("name", "express-app")}"
PORT=${{PORT:-{config.get("port", 3000)}}}
NODE_ENV=${{NODE_ENV:-{config.get("environment", "development")}}}

log() {{
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$APP_NAME] $1"
}}

log "Starting Express.js app $APP_NAME on port $PORT in $NODE_ENV mode..."

# Check Node.js
if ! command -v node &> /dev/null; then
    log "ERROR: Node.js not found"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    log "Installing dependencies..."
    npm install
fi

# Set environment
export NODE_ENV=$NODE_ENV
export PORT=$PORT
{self._generate_env_exports(config.get("env_vars", {}))}

# Health check function
health_check() {{
    curl -f http://localhost:$PORT{config.get("health_endpoint", "/api/health")} >/dev/null 2>&1
}}

# Pre-flight checks
if [ "$NODE_ENV" = "production" ]; then
    log "Running pre-flight checks..."

    # Check if build exists for production
    if [ -d "dist" ] || [ -d "build" ]; then
        log "Build directory found"
    else
        log "WARNING: No build directory found for production"
    fi
fi

# Start Express application
log "Starting: {config.get("command", "npm start")}"
exec {config.get("command", "npm start")}
'''

    def _generate_fastapi_launch_script(self, config: Dict[str, Any]) -> str:
        """Generate FastAPI launch script"""
        return f'''#!/bin/bash
# Auto-generated FastAPI launch script for {config.get("name", "app")}

set -e

APP_NAME="{config.get("name", "fastapi-app")}"
HOST=${{HOST:-0.0.0.0}}
PORT=${{PORT:-{config.get("port", 8000)}}}
WORKERS=${{WORKERS:-1}}

log() {{
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$APP_NAME] $1"
}}

log "Starting FastAPI app $APP_NAME on $HOST:$PORT..."

# Check Python
if ! command -v python3 &> /dev/null; then
    log "ERROR: Python3 not found"
    exit 1
fi

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ] && [ ! -d "venv" ]; then
    log "Installing dependencies..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set environment
export HOST=$HOST
export PORT=$PORT
{self._generate_env_exports(config.get("env_vars", {}))}

# Health check function
health_check() {{
    curl -f http://$HOST:$PORT{config.get("health_endpoint", "/health")} >/dev/null 2>&1
}}

# Start FastAPI application
if [ "{config.get("environment", "development")}" = "production" ]; then
    log "Starting in production mode with $WORKERS workers"
    exec uvicorn main:app --host $HOST --port $PORT --workers $WORKERS
else
    log "Starting in development mode with auto-reload"
    exec uvicorn main:app --host $HOST --port $PORT --reload
fi
'''

    def _generate_rust_launch_script(self, config: Dict[str, Any]) -> str:
        """Generate Rust launch script"""
        return f'''#!/bin/bash
# Auto-generated Rust launch script for {config.get("name", "app")}

set -e

APP_NAME="{config.get("name", "rust-app")}"
PORT=${{PORT:-{config.get("port", 8080)}}}

log() {{
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$APP_NAME] $1"
}}

log "Starting Rust app $APP_NAME on port $PORT..."

# Check Rust
if ! command -v cargo &> /dev/null; then
    log "ERROR: Rust/Cargo not found"
    exit 1
fi

# Check for Cargo.toml
if [ ! -f "Cargo.toml" ]; then
    log "ERROR: Cargo.toml not found"
    exit 1
fi

# Set environment
export PORT=$PORT
{self._generate_env_exports(config.get("env_vars", {}))}

# Build and run
if [ "{config.get("environment", "development")}" = "production" ]; then
    log "Building for production..."
    cargo build --release
    log "Starting: ./target/release/{config.get("name", "app")}"
    exec ./target/release/{config.get("name", "app")}
else
    log "Starting in development mode with cargo run"
    exec cargo run
fi
'''

    def _generate_env_exports(self, env_vars: Dict[str, str]) -> str:
        """Generate environment variable exports"""
        if not env_vars:
            return ""

        exports = []
        for key, value in env_vars.items():
            exports.append(f'export {key}="{value}"')

        return "\n".join(exports)

    async def generate_kill_script(self, project_path: str = None, app_type: str = None,
                                  process_name: str = None, environment: str = "development",
                                  config: Dict[str, Any] = None) -> str:
        """Generate intelligent kill script"""
        # Support both new signature and legacy config parameter
        if config is None:
            config = {
                "project_path": project_path,
                "app_type": app_type,
                "name": process_name,
                "environment": environment
            }

        monitoring = config.get("monitoring", {})
        ports = monitoring.get("ports", [])
        processes = monitoring.get("processes", [])

        return f'''#!/bin/bash
# Auto-generated kill script for {config.get("name", "app")}

APP_NAME="{config.get("name", "app")}"

log() {{
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$APP_NAME] $1"
}}

log "Stopping $APP_NAME..."

# Kill by port
{self._generate_port_kills(ports)}

# Kill by process name
{self._generate_process_kills(processes)}

# Graceful shutdown with timeout
graceful_shutdown() {{
    local pid=$1
    local timeout=${{2:-30}}

    if kill -TERM "$pid" 2>/dev/null; then
        log "Sent TERM signal to PID $pid, waiting $timeout seconds..."

        for i in $(seq 1 $timeout); do
            if ! kill -0 "$pid" 2>/dev/null; then
                log "Process $pid terminated gracefully"
                return 0
            fi
            sleep 1
        done

        log "Process $pid did not terminate, forcing kill..."
        kill -KILL "$pid" 2>/dev/null || true
    fi
}}

# Wait for processes to stop
sleep 2

log "$APP_NAME stopped"
'''

    def _generate_port_kills(self, ports: List[int]) -> str:
        """Generate port-based kill commands"""
        if not ports:
            return ""

        kills = []
        for port in ports:
            kills.append(f'''
# Kill process on port {port}
PID=$(lsof -ti:{port} 2>/dev/null || true)
if [ ! -z "$PID" ]; then
    log "Killing process on port {port} (PID: $PID)"
    graceful_shutdown $PID
fi''')

        return "\n".join(kills)

    def _generate_process_kills(self, processes: List[str]) -> str:
        """Generate process-name-based kill commands"""
        if not processes:
            return ""

        kills = []
        for process in processes:
            kills.append(f'''
# Kill {process} processes
PIDS=$(pgrep -f "{process}" 2>/dev/null || true)
if [ ! -z "$PIDS" ]; then
    log "Killing {process} processes: $PIDS"
    echo "$PIDS" | xargs -r kill -TERM
fi''')

        return "\n".join(kills)