#coding=utf8

from setuptools import setup, find_packages

def readme():
    with open('README.rst') as f:
        return f.read()

setup(
    name = "kaleidoscope",
    version = "0.1.0",
    packages = find_packages(),
    include_package_data = True,
    description = "A helper to publish Android project",
    long_description = readme(),

    author = "gouki0123",
    author_email = "gouki0123@gmail.com",
    url = "https://github.com/konakonall",
    classifiers= 'MIT License',
    keywords = ("Android", "Bintray", "JCenter"),

    scripts=['bin/kal'],  
    install_requires=['GitPython', 'cos-python-sdk-v5', 'pyyaml', 'requests']
)
