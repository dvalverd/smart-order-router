from setuptools import setup, Extension
import pybind11
import sys

ext = Extension(
    "pricer",
    sources=["cpp/pricer.cpp", "cpp/bindings.cpp"],
    include_dirs=[pybind11.get_include(), "cpp/"],
    language="c++",
    extra_compile_args=[
        "-std=c++17",
        "-O3",
        "-ffast-math",
    ] if sys.platform != "win32" else ["/std:c++17", "/O2"],
)

setup(
    name="pricer",
    version="0.1.0",
    ext_modules=[ext],
)
