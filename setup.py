from setuptools import setup, find_packages

setup(
    name="md2adf",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["mistune>=3.0,<4.0"],
    python_requires=">=3.9",
)
