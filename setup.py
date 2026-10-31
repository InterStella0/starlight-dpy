import re

from setuptools import setup

version_re = re.compile(r"^__version__ *= *('|\")((?:[0-9]+\.)*[0-9]+(?:\.?([0-z]+)(?:\.?[0-9])?)?)\1$", re.MULTILINE)
with open(r'starlight/__init__.py') as r:
    ver = version_re.search(r.read())
    version = ver.group(2)

packages = [
    "starlight",
    "starlight.star_commands",
    "starlight.star_commands.help_command",
    "starlight.star_commands.views",
    "starlight.utils",
]

with open('README.md', encoding="utf8") as f:
    # relative image paths don't render on PyPI
    readme = f.read().replace(
        '](docs/images/', '](https://raw.githubusercontent.com/InterStella0/starlight-dpy/main/docs/images/'
    )

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

extras_require = {
    'docs': [
        'sphinx_rtd_dark_mode >= 1.2.4',
    ],
}


setup(
    name='starlight-dpy',
    author='InterStella0',
    url='https://github.com/InterStella0/starlight-dpy',
    project_urls={
      "Issue tracker": "https://github.com/InterStella0/starlight-dpy/issues",
    },
    version=version,
    packages=packages,
    license='MIT',
    description='A Utility library for discord.py',
    long_description=readme,
    long_description_content_type='text/markdown',
    include_package_data=True,
    install_requires=requirements,
    extras_require=extras_require,
    python_requires='>=3.8.0',
    classifiers=[
      'Development Status :: 2 - Pre-Alpha',
      'License :: OSI Approved :: MIT License',
      'Intended Audience :: Developers',
      'Natural Language :: English',
      'Operating System :: OS Independent',
      'Programming Language :: Python :: 3.8',
      'Programming Language :: Python :: 3.9',
      'Programming Language :: Python :: 3.10',
      'Programming Language :: Python :: 3.11',
      'Programming Language :: Python :: 3.12',
      'Topic :: Internet',
      'Topic :: Software Development :: Libraries',
      'Topic :: Software Development :: Libraries :: Python Modules',
      'Topic :: Utilities',
      'Typing :: Typed',
    ]
)
