#!/usr/bin/env python3
"""
BRANE Backend Setup Validation
Checks that all components are properly configured before first run
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Verify Python version is 3.11+"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor} detected")
        print("      Requires Python 3.11 or higher")
        return False

def check_imports():
    """Verify all critical imports work"""
    print("\n📦 Checking imports...")

    imports_to_check = [
        ("fastapi", "FastAPI"),
        ("sqlalchemy", "SQLAlchemy"),
        ("pydantic", "Pydantic"),
        ("asyncpg", "AsyncPG"),
        ("sentence_transformers", "Sentence Transformers"),
        ("faiss", "FAISS"),
        ("cryptography", "Cryptography"),
        ("redis", "Redis"),
        ("aiofiles", "AioFiles"),
        ("yaml", "PyYAML"),
    ]

    all_good = True
    for module_name, display_name in imports_to_check:
        try:
            __import__(module_name)
            print(f"   ✅ {display_name}")
        except ImportError:
            print(f"   ❌ {display_name} - Not installed")
            all_good = False

    return all_good

def check_project_structure():
    """Verify project structure is correct"""
    print("\n📁 Checking project structure...")

    required_files = [
        "main.py",
        "requirements.txt",
        ".env.example",
        "alembic.ini",
        "db/models.py",
        "db/database.py",
        "api/auth.py",
        "api/neurons.py",
        "api/chat.py",
        "api/rag.py",
        "api/admin.py",
        "core/neuron/neuron.py",
        "core/neuron/neuron_manager.py",
        "core/llm/broker.py",
        "core/axon/axon.py",
        "core/synapse/synapse.py",
        "core/config/settings.py",
        "core/security/audit.py",
    ]

    all_good = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} - Missing!")
            all_good = False

    return all_good

def check_env_file():
    """Check .env configuration"""
    print("\n⚙️  Checking environment configuration...")

    if not Path(".env").exists():
        print("   ⚠️  .env file not found")
        print("      Copy .env.example to .env and configure it")
        return False

    # Check critical env vars
    try:
        from core.config import get_settings
        settings = get_settings()

        checks = [
            ("DATABASE_URL", settings.DATABASE_URL != ""),
            ("JWT_SECRET_KEY", len(settings.JWT_SECRET_KEY) >= 32),
            ("ENCRYPTION_KEY", len(settings.ENCRYPTION_KEY) >= 32),
        ]

        all_good = True
        for key, passed in checks:
            if passed:
                print(f"   ✅ {key} configured")
            else:
                print(f"   ❌ {key} - Invalid or too short")
                all_good = False

        return all_good

    except Exception as e:
        print(f"   ❌ Error loading settings: {e}")
        return False

def check_database_models():
    """Verify database models can be imported"""
    print("\n🗄️  Checking database models...")

    try:
        from db.models import User, Neuron, ChatSession, Message, AuditLog, Document
        from db.models import UserRole, PrivacyTier

        models = [
            User, Neuron, ChatSession, Message, AuditLog, Document
        ]

        print(f"   ✅ All {len(models)} models imported successfully")
        print(f"   ✅ Enums: UserRole, PrivacyTier")
        return True

    except Exception as e:
        print(f"   ❌ Error importing models: {e}")
        return False

def check_core_components():
    """Verify core components can be imported"""
    print("\n🧩 Checking core components...")

    components = [
        ("core.neuron.neuron", "Neuron"),
        ("core.neuron.neuron_manager", "NeuronManager"),
        ("core.llm.broker", "LLMBroker"),
        ("core.axon.axon", "Axon"),
        ("core.synapse.synapse", "Synapse"),
        ("core.config.settings", "Settings"),
        ("core.security.audit", "Audit"),
    ]

    all_good = True
    for module_path, component_name in components:
        try:
            __import__(module_path)
            print(f"   ✅ {component_name}")
        except Exception as e:
            print(f"   ❌ {component_name} - Error: {e}")
            all_good = False

    return all_good

def check_api_routes():
    """Verify API routes can be imported"""
    print("\n🌐 Checking API routes...")

    try:
        from api import auth, neurons, chat, rag, admin

        routers = [
            ("Auth", auth.router),
            ("Neurons", neurons.router),
            ("Chat", chat.router),
            ("RAG", rag.router),
            ("Admin", admin.router),
        ]

        all_good = True
        for name, router in routers:
            route_count = len(router.routes)
            print(f"   ✅ {name} ({route_count} routes)")

        return all_good

    except Exception as e:
        print(f"   ❌ Error importing API routes: {e}")
        return False

def main():
    """Run all validation checks"""
    print("=" * 60)
    print("BRANE Backend Setup Validation")
    print("=" * 60)

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_imports),
        ("Project Structure", check_project_structure),
        ("Environment Config", check_env_file),
        ("Database Models", check_database_models),
        ("Core Components", check_core_components),
        ("API Routes", check_api_routes),
    ]

    results = []
    for name, check_func in checks:
        try:
            passed = check_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n   💥 Unexpected error in {name}: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    print("\n" + "-" * 60)
    print(f"Result: {passed_count}/{total_count} checks passed")

    if passed_count == total_count:
        print("\n🎉 All validations passed! Ready to start BRANE backend.")
        print("\nNext steps:")
        print("  1. Start PostgreSQL: brew services start postgresql@14")
        print("  2. Run migrations: alembic upgrade head")
        print("  3. Start server: python main.py")
        print("  4. Run tests: python test_server.py")
        return 0
    else:
        print("\n⚠️  Some validations failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Configure .env: cp .env.example .env && vim .env")
        print("  - Create virtual env: python3 -m venv venv && source venv/bin/activate")
        return 1

if __name__ == "__main__":
    sys.exit(main())
