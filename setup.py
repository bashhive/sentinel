"""Setup configuration for Aspasia."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="aspasia",
    version="0.1.0",
    author="Aspasia Team",
    author_email="team@aspasia.ai",
    description="Autonomous AI Agent Bot with Telegram and Web Integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/aspasia",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Communications :: Chat",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "anthropic>=0.21.0",
        "fastapi>=0.109.0",
        "uvicorn[standard]>=0.27.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "python-telegram-bot>=20.7",
        "python-dotenv>=1.0.0",
        "sqlalchemy>=2.0.0",
        "alembic>=1.13.0",
        "redis>=5.0.0",
        "aiohttp>=3.9.0",
        "httpx>=0.25.0",
        "structlog>=24.1.0",
    ],
    entry_points={
        "console_scripts": [
            "aspasia=aspasia.main:run",
        ],
    },
    include_package_data=True,
)
