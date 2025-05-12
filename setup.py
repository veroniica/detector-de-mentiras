#!/usr/bin/env python3
"""
Setup script for the Audio Interview Analysis System.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="audio-interview-analysis",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A system for analyzing audio interviews in criminal cases",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/audio-interview-analysis",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "audio-analysis=audio_analysis.main:main",
        ],
    },
)