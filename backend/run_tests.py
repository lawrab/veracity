#!/usr/bin/env python
"""Test runner script with proper setup and teardown."""

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class TestRunner:
    """Manages test execution with proper setup and teardown."""

    def __init__(self):
        self.backend_dir = Path(__file__).parent
        self.test_db_created = False

    async def setup_test_database(self) -> bool:
        """Create test database if it doesn't exist."""
        try:
            # Create test database
            import asyncpg

            # Parse connection details from settings
            conn_params = {
                "host": "localhost",
                "port": 5432,
                "user": "veracity_user",
                "password": "veracity_password",
                "database": "postgres",  # Connect to default db to create test db
            }

            conn = await asyncpg.connect(**conn_params)

            # Check if test database exists
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = 'test_veracity'"
            )

            if not exists:
                await conn.execute("CREATE DATABASE test_veracity")
                logger.info("✓ Created test database: test_veracity")
                self.test_db_created = True
            else:
                logger.info("✓ Test database already exists")

            await conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to setup test database: {e}")
            return False

    def check_services(self) -> bool:
        """Check if required services are running."""
        try:
            result = subprocess.run(
                ["podman", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=True,
            )

            running_services = result.stdout.strip().split("\n")
            required = ["veracity-postgres", "veracity-mongodb", "veracity-redis"]

            missing = [s for s in required if s not in running_services]

            if missing:
                logger.error(f"Missing required services: {missing}")
                logger.info("Run 'podman-compose up -d' to start services")
                return False

            logger.info("✓ All required services are running")
            return True

        except subprocess.CalledProcessError:
            logger.error("Failed to check podman services")
            return False

    def run_tests(self, test_type: Optional[str] = None) -> int:
        """Run pytest with specified test type."""
        cmd = ["pytest", "-v", "--tb=short"]

        if test_type == "unit":
            cmd.extend(["tests/unit/", "-m", "unit"])
        elif test_type == "integration":
            cmd.extend(["tests/integration/", "-m", "integration"])
        elif test_type == "e2e":
            cmd.extend(["tests/e2e/", "-m", "e2e"])
        elif test_type == "coverage":
            cmd.extend(
                [
                    "tests/",
                    "--cov=app",
                    "--cov-report=term-missing",
                    "--cov-report=html",
                    "--cov-fail-under=80",
                ]
            )
        else:
            cmd.append("tests/")

        logger.info(f"Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, check=False, cwd=self.backend_dir)
        return result.returncode

    def run_linters(self) -> int:
        """Run code quality checks."""
        checks = [
            (["black", "--check", "app/", "tests/"], "Code formatting (black)"),
            (["isort", "--check-only", "app/", "tests/"], "Import sorting (isort)"),
            (["flake8", "app/", "tests/"], "Linting (flake8)"),
        ]

        failed = []
        for cmd, name in checks:
            logger.info(f"Running {name}...")
            result = subprocess.run(
                cmd, check=False, cwd=self.backend_dir, capture_output=True
            )
            if result.returncode != 0:
                failed.append(name)
                logger.error(f"✗ {name} failed")
            else:
                logger.info(f"✓ {name} passed")

        if failed:
            logger.error(f"\nFailed checks: {', '.join(failed)}")
            logger.info("Run 'make format' to fix formatting issues")
            return 1

        return 0

    async def cleanup(self):
        """Clean up test artifacts."""
        # Clean test database if we created it
        if self.test_db_created:
            try:
                import asyncpg

                conn = await asyncpg.connect(
                    host="localhost",
                    port=5432,
                    user="veracity_user",
                    password="veracity_password",
                    database="postgres",
                )
                await conn.execute("DROP DATABASE IF EXISTS test_veracity")
                await conn.close()
                logger.info("✓ Cleaned up test database")
            except Exception as e:
                logger.error(f"Failed to cleanup test database: {e}")


async def main():
    """Main test runner entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Veracity test runner")
    parser.add_argument(
        "type",
        nargs="?",
        choices=["all", "unit", "integration", "e2e", "coverage", "lint"],
        default="all",
        help="Type of tests to run",
    )
    parser.add_argument(
        "--no-services-check",
        action="store_true",
        help="Skip checking for running services",
    )

    args = parser.parse_args()

    runner = TestRunner()

    # Check services
    if not args.no_services_check and args.type in ["integration", "e2e", "all"]:
        if not runner.check_services():
            return 1

    # Setup test database for integration/e2e tests
    if args.type in ["integration", "e2e", "all", "coverage"]:
        if not await runner.setup_test_database():
            return 1

    # Run linters if requested
    if args.type == "lint":
        return runner.run_linters()

    # Run tests
    if args.type == "all":
        # Run all test types in sequence
        for test_type in ["unit", "integration", "e2e"]:
            logger.info(f"\n{'=' * 50}")
            logger.info(f"Running {test_type} tests")
            logger.info("=" * 50)

            returncode = runner.run_tests(test_type)
            if returncode != 0:
                logger.error(f"{test_type} tests failed")
                await runner.cleanup()
                return returncode
    else:
        returncode = runner.run_tests(args.type if args.type != "all" else None)

    # Cleanup
    await runner.cleanup()

    if returncode == 0:
        logger.info("\n✅ All tests passed successfully!")
    else:
        logger.error("\n❌ Some tests failed")

    return returncode


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
