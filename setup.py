import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='harmonia',
    version='0.1',
    author='Chris Latham',
    author_email='cl@bink.com',
    description='Transaction Matching',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://git.bink.com/olympus/harmonia',
    classifiers=(
        'Programming Language :: Python :: 3',
    ),
    entry_points={
        'console_scripts': (
            'txmatch_import = app.imports.cli:cli',
            'txmatch_core = app.core.cli:cli',
        ),
    },
)
