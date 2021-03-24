from setuptools import setup

setup(
    name='europeana',
    version='0.1.1',
    py_modules=['europeana'],
    install_requires=[
        'rdflib',
        'requests',
    ],
    entry_points='''
        [console_scripts]
        europeana=europeana:europeana
    ''',
)