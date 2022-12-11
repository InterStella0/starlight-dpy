from setuptools import setup

version = '0.0.1'
packages = [
    "starlight"
]

with open('README.md') as f:
    readme = f.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()


setup(name='starlight',
      author='InterStella0',
      url='https://github.com/InterStella0/starlight',
      project_urls={
        "Issue tracker": "https://github.com/InterStella0/starlight/issues",
      },
      version=version,
      packages=packages,
      license='MIT',
      description='A Utility library for discord.py',
      include_package_data=True,
      install_requires=requirements,
      python_requires='>=3.8.0',
      classifiers=[
        'Development Status :: 1 - Planning',
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