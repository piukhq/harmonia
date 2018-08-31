from setuptools import setup, find_packages

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='harmonia',
    version='0.1',
    author='Chris Latham',
    author_email='cl@bink.com',
    description='Transaction Matching',
    packages=['.'] + find_packages(),
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://git.bink.com/olympus/harmonia',
    classifiers=('Programming Language :: Python :: 3', ),
    entry_points={
        'console_scripts': (
            'tximport = app.imports.cli:cli',
            'txcore = app.core.cli:cli',
        ),
    },
)
