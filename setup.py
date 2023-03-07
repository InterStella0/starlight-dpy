import re

from setuptools import setup

version_re = re.compile(r"^__version__ *= *('|\")((?:[0-9]+\.)*[0-9]+(?:\.?([0-z]+)(?:\.?[0-9])?)?)\1$", re.MULTILINE)
with open(r'starlight/__init__.py') as r:
    ver = version_re.search(r.read())
    version = ver.group(2)

packages = [
    "starlight",
    "starlight.star_commands",
    "starlight.utils",
]

with open('README.md', encoding="utf8") as f:
    readme = f.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()


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
    include_package_data=True,
    install_requires=requirements,
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
      'Topic :: Internet',
      'Topic :: Software Development :: Libraries',
      'Topic :: Software Development :: Libraries :: Python Modules',
      'Topic :: Utilities',
      'Typing :: Typed',
    ]
)
