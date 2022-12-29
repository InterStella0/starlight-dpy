from __future__ import annotations

import difflib

from operator import attrgetter
from typing import (
    overload,
    TYPE_CHECKING,
    TypeVar,
    Generic,
)

T = TypeVar('T')

if TYPE_CHECKING:
    from typing import (
        List,
        Dict,
        Tuple,
        Any,
        AsyncIterable,
        Callable,
        Coroutine,
        Iterable,
        Union,
    )

    Coro = Coroutine[Any, Any, T]
    _Iter = Union[Iterable[T], AsyncIterable[T]]

__all__ = (
    'SearchFilter',
    'ContainsFilter',
    'FuzzyFilter',
    'Contains',
    'Fuzzy',
    'search',
)


class SearchFilter(Generic[T]):
    """Base class for filtering with :func:`search`.

    Parameters
    ------------
    query: Any
        The query value to filter by.
    """
    def __init__(self, query: T):
        self.query: T = query

    def filter(self, value: Any, /) -> Any:
        """Filters the value from the iterable. The return value will be included
        if it is truthy or excluded if it is falsy. The return value is used to sort
        the item.

        Subclasses should override this method.

        Parameters
        ------------
        value: Any
            The value of the attribute from the item in iterable.

        Returns
        --------
        Any
            The value to sort this item by.

        """
        raise NotImplementedError


class ContainsFilter(SearchFilter[Any]):
    """Basic filter that checks if ``query`` is in the attribute value.

    Parameters
    ------------
    query: Any
        The query value to filter by.
    """
    def filter(self, value: Any, /) -> bool:
        """Filters the value from the iterable. The return value will be included
        if it is truthy or excluded if it is falsy. The return value is used to sort
        the item.

        Parameters
        ------------
        value: Any
            The value of the attribute from the item in iterable.

        Returns
        --------
        Any
            The value to sort this item by.
        """
        return self.query in value

Contains = ContainsFilter


class FuzzyFilter(SearchFilter[str]):
    """Basic fuzzy filter using difflib that filters based on the distance
    between two strings.

    Parameters
    ------------
    query: :class: `str`
        The query value to filter by.
    cutoff_ratio: :class:`float`
        The minimum ratio the input must be to be included. Default is ``0.6``.
    quick: :class:`bool`
        Whether to use ``quick_ratio`` or slower ``ratio`` for getting the fuzzy ratio.
        Defaults to ``True`` to use ``quick_ratio``.
    """
    def __init__(self, query: str, /, *, cutoff_ratio: float = 0.6, quick: bool = True):
        super().__init__(query)
        self.cutoff_ratio = cutoff_ratio
        self.quick = quick

    def get_ratio(self, query: str, value: str) -> float:
        """Uses difflib to get the ratio between ``query`` and ``value``.

        Parameters
        ------------
        query: :class:`str`
            The value to use as ``a`` for difflib ratio/quick_ratio.
        value: :class:`str`
            The value to use as ``b`` for difflib ratio/quick_ratio.

        Returns
        --------
        :class:`float`
            The ratio between the two input strings.
        """
        matcher = difflib.SequenceMatcher(a=query, b=value)
        ratio = (matcher.quick_ratio if self.quick else matcher.ratio)()
        contains = self.query in value
        return (ratio + 0.5 * contains) if ratio >= self.cutoff_ratio or contains else 0.0

    def filter(self, value: Any, /) -> float:
        """Filters the value from the iterable. The return value will be included
        if it is truthy or excluded if it is falsy. The return value is used to sort
        the item.

        Parameters
        ------------
        value: Any
            The value of the attribute from the item in iterable. It is cast to
            :class:`str` before

        Returns
        --------
        :class:`float`
            The value to sort this item by.
        """
        return self.get_ratio(self.query, str(value))

Fuzzy = FuzzyFilter


def _eq_predicate(query: Any) -> Callable[[Any], bool]:

    def _predicate(value: Any) -> bool:
        return value == query

    return _predicate


def _get_score(item: Any, attr: str, predicate: Callable[[Any], Any], /) -> Any:
    return predicate(attrgetter(attr.replace('__', '.'))(item))


def _search(
    iterable: Iterable[T],
    /,
    *,
    _check_any: bool,
    _sort: bool,
    attrs: Dict[str, Any],
) -> List[T]:
    # global -> local
    _check = any if _check_any else all

    unsorted_items: List[Tuple[T, Any]]

    # sepcial case single attribute
    if len(attrs) == 1:
        k, v = attrs.popitem()
        predicate = v.filter if isinstance(v, SearchFilter) else _eq_predicate(v)
        unsorted_items_gen = ((item, _get_score(item, k, predicate)) for item in iterable)
        unsorted_items = [t for t in unsorted_items_gen if t[1]]
        if _sort:
            unsorted_items.sort(key=lambda t: t[1], reverse=True)
        items = [t[0] for t in unsorted_items]
    else:
        predicates = {k: v.filter if isinstance(v, SearchFilter) else _eq_predicate(v) for k, v in attrs.items()}
        unsorted_items = []

        if _sort:
            if _check_any:
                # any, sorted
                items_gen = (
                    (item, [_get_score(item, k, pred) for k, pred in predicates.items()])
                    for item in iterable
                )
                unsorted_items = [t for t in items_gen if _check(t[1])]
            else:
                # need the scores to sort, but try to short circuit if it fails
                num_predicates = len(predicates)
                # all, sorted
                for item in iterable:
                    scores = []
                    for k, pred in predicates.items():
                        score = _get_score(item, k, pred)
                        if not score:
                            break
                        scores.append(score)
                    if len(scores) == num_predicates:
                        unsorted_items.append((item, scores))

            unsorted_items.sort(key=lambda t: t[1])
            items = [t[0] for t in unsorted_items]
        else:
            # not sorted, don't need the score
            items = [
                item
                for item in iterable
                if _check(_get_score(item, k, pred) for k, pred in predicates.items())
            ]

    return items


async def _asearch(
    iterable: AsyncIterable[T],
    /,
    *,
    _check_any: bool,
    _sort: bool,
    attrs: Dict[str, Union[str, SearchFilter]],
) -> List[T]:
    # global -> local
    _check = any if _check_any else all

    unsorted_items: List[Tuple[T, Any]]

    # sepcial case single attribute
    if len(attrs) == 1:
        k, v = attrs.popitem()
        predicate = v.filter if isinstance(v, SearchFilter) else _eq_predicate(v)
        unsorted_items_gen = ((item, _get_score(item, k, predicate)) async for item in iterable)
        unsorted_items = [t async for t in unsorted_items_gen if t[1]]
        if _sort:
            unsorted_items.sort(key=lambda t: t[1], reverse=True)
        items = [t[0] for t in unsorted_items]
    else:
        predicates = {k: v.filter if isinstance(v, SearchFilter) else _eq_predicate(v) for k, v in attrs.items()}
        unsorted_items = []

        if _sort:
            if _check_any:
                # any, sorted
                items_gen = (
                    (item, [_get_score(item, k, pred) for k, pred in predicates.items()])
                    async for item in iterable
                )
                unsorted_items = [t async for t in items_gen if _check(t[1])]
            else:
                # need the scores to sort, but try to short circuit if it fails
                num_predicates = len(predicates)
                # all, sorted
                async for item in iterable:
                    scores = []
                    for k, pred in predicates.items():
                        score = _get_score(item, k, pred)
                        if not score:
                            break
                        scores.append(score)
                    if len(scores) == num_predicates:
                        unsorted_items.append((item, scores))

            unsorted_items.sort(key=lambda t: t[1])
            items = [t[0] for t in unsorted_items]
        else:
            # not sorted, don't need the score
            items = [
                item
                async for item in iterable
                if _check(_get_score(item, k, pred) for k, pred in predicates.items())
            ]
    return items


@overload
def search(iterable: AsyncIterable[T], /, *, check_any: bool = False, sort: bool = False,  **attrs: Any) -> Coro[List[T]]:
    ...

@overload
def search(iterable: Iterable[T], /, *, check_any: bool = False, sort: bool = False,  **attrs: Any) -> List[T]:
    ...

def search(
    iterable: _Iter[T], /, *, check_any: bool = False, sort: bool = False, **attrs: Any
) -> Union[List[T], Coro[List[T]]]:
    r"""A helper that returns all elements in the iterable that meet all or any
    of the traits passed in ``attrs`` depending on ``check_any``.
    To have a nested attribute search (i.e. search by ``x.y``) then
    pass in ``x__y`` as the keyword argument.
    If nothing is found that matches the attributes passed, then
    an empty list is returned.

    Examples
    ---------
    Using :class:`SearchFilter`:
    .. code-block:: python3
        cmds_by_name_and_desc = await starlight.search(bot.commands, name=FuzzyFilter('user'), description=ContainsFilter('user'))
    Sorting output based on fuzzy ratio:
    .. code-block:: python3
        sorted_cmds_by_fuzzy_name = await starlight.search(bot.commands, sort=True, name=FuzzyFilter('user'))
    Turn attribute matching to logical OR:
    .. code-block:: python3
        cmds_by_name_or_desc = await starlight.search(bot.commands, check_any=True, name=FuzzyFilter('user'), description=ContainsFilter('user'))

    Parameters
    -----------
    iterable: Union[:class:`collections.abc.Iterable`, :class:`collections.abc.AsyncIterable`]
        The iterable to search through. Using a :class:`collections.abc.AsyncIterable`,
        makes this function return a :term:`coroutine`.
    check_any: class:`bool`
        When multiple attributes are specified, determines whether they are checked
        using logical AND or logical OR. when this value is ``False``, logical AND
        is used meaning they have to meet every attribute passed in and not one of them.
        Default is ``False``.
    sort: class:`bool`
        Whether to sort the output based on the scoring values. Default is ``False``.
        The order of attributes determines their weighting for sorting with the first
        having the most weight and last the least weight.
    \*\*attrs
        Keyword arguments that denote attributes to search with.

    Returns
    --------
    List[Any]
        List of values that match the filters passed in through attrs.
    """
    return (
        _asearch(iterable, _check_any=check_any, _sort=sort, attrs=attrs)  # type: ignore
        if hasattr(iterable, '__aiter__')  # isinstance(iterable, collections.abc.AsyncIterable) is too slow
        else _search(iterable, _check_any=check_any, _sort=sort, attrs=attrs)  # type: ignore

    )