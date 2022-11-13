from setuptools import find_packages, setup

# read requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='kurator',
    version='0.0.1',
    description='Kurator',
    author='Parth Thakkar',
    packages=find_packages(),
    package_dir={'kurator': 'kurator'},
    install_requires=requirements,
)
