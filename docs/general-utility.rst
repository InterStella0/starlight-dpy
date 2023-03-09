.. currentmodule:: starlight

General Utility
================

Search
-------
This is an expanded version of :func:`~discord.utils.get`. However, it returns an iterable by filtering
relevant predicate.

.. autofunction:: search

Filters
--------
This are supported utility classes that can be used along side :func:`search`.

SearchFilter
~~~~~~~~~~~~
.. autoclass:: SearchFilter
    :members:

ContainsFilter
~~~~~~~~~~~~~~~
.. autoclass:: ContainsFilter
    :members:
    :show-inheritance:

FuzzyFilter
~~~~~~~~~~~~
.. autoclass:: FuzzyFilter
    :members:
    :show-inheritance:

RegexFilter
~~~~~~~~~~~~
.. autoclass:: RegexFilter
    :members:
    :show-inheritance:


get_app_signature
------------------
.. autofunction:: get_app_signature


Iterables
---------
recursive_unpack
~~~~~~~~~~~~~~~~
.. autofunction:: recursive_unpack

flatten
~~~~~~~
.. autofunction:: flatten