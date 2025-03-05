from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="rufus",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool for intelligent web data extraction for LLMs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sabdulrahman/rufus",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Text Processing :: Markup :: HTML"
    ],
    python_requires=">=3.8",
    install_requires=[
        "beautifulsoup4>=4.9.0",
        "requests>=2.25.0",
        "aiohttp>=3.7.0",
        "openai>=0.27.0"
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "black>=21.5b2",
            "isort>=5.8.0",
            "mypy>=0.812",
            "flake8>=3.9.1"
        ],
        "browser": [
            "playwright>=1.20.0",
            "selenium>=4.0.0",
            "webdriver-manager>=3.5.2"
        ]
    }
)