from setuptools import setup

setup(
    name='gtd',
    version='1.0',
    packages=['gtd'],
    entry_points={
        'console_scripts': [
            'gtd = gtd.__main__:main'
        ]
    },
    install_requires=[
        "jira",
        "pandas",
        "requests",
        "odfpy"
    ],
    author="Stefan Nožinić",
    author_email='stefan@lugons.org',
    description='GTD tool which uses JIRA as a backend and allows you to manage your tasks in a GTD way',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
