"""Unit tests for _sort_bases_for_mro in class_stub."""

from __future__ import annotations

import pytest
from chaquopy_stubgen._stubgen.class_stub import _sort_bases_for_mro
from chaquopy_stubgen._stubgen.types import TypeStr

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _names(types: list[TypeStr]) -> list[str]:
    return [t.name for t in types]


def _make(names: list[str]) -> list[TypeStr]:
    return [TypeStr(n) for n in names]


# ---------------------------------------------------------------------------
# A realistic subset of java.util's inheritance graph (dotted names).
# ---------------------------------------------------------------------------

JAVA_UTIL_LOOKUP: dict[str, list[str]] = {
    "java.lang.Object": [],
    "java.lang.Iterable": ["java.lang.Object"],
    "java.lang.Cloneable": ["java.lang.Object"],
    "java.io.Serializable": ["java.lang.Object"],
    "java.util.Collection": ["java.lang.Object", "java.lang.Iterable"],
    "java.util.SequencedCollection": ["java.lang.Object", "java.util.Collection"],
    "java.util.List": [
        "java.lang.Object",
        "java.util.Collection",
        "java.util.SequencedCollection",
    ],
    "java.util.Set": ["java.lang.Object", "java.util.Collection"],
    "java.util.SequencedSet": [
        "java.lang.Object",
        "java.util.Set",
        "java.util.SequencedCollection",
    ],
    "java.util.Map": ["java.lang.Object"],
    "java.util.SequencedMap": ["java.lang.Object", "java.util.Map"],
    "java.util.RandomAccess": ["java.lang.Object"],
    "java.util.AbstractCollection": ["java.lang.Object", "java.util.Collection"],
    "java.util.AbstractList": [
        "java.util.AbstractCollection",
        "java.util.List",
    ],
    "java.util.AbstractSet": [
        "java.util.AbstractCollection",
        "java.util.Set",
    ],
    "java.util.AbstractMap": ["java.lang.Object", "java.util.Map"],
    "java.util.Deque": [
        "java.lang.Object",
        "java.util.Queue",
        "java.util.SequencedCollection",
    ],
    "java.util.Queue": ["java.lang.Object", "java.util.Collection"],
    "java.util.AbstractSequentialList": ["java.util.AbstractList"],
    "java.util.Dictionary": ["java.lang.Object"],
    "java.util.HashMap": ["java.util.AbstractMap", "java.util.Map"],
    "java.util.HashSet": ["java.util.AbstractSet", "java.util.Set"],
    "java.util.Hashtable": [
        "java.util.Dictionary",
        "java.util.Map",
    ],
    "java.util.LinkedHashMap": [
        "java.util.HashMap",
        "java.util.SequencedMap",
        "java.util.Map",
    ],
    "java.util.LinkedHashSet": [
        "java.util.HashSet",
        "java.util.SequencedSet",
        "java.util.Set",
    ],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_single_base_unchanged():
    bases = _make(["java.lang.Object"])
    result = _sort_bases_for_mro(bases, JAVA_UTIL_LOOKUP)
    assert _names(result) == ["java.lang.Object"]


def test_empty_list():
    result = _sort_bases_for_mro([], JAVA_UTIL_LOOKUP)
    assert result == []


def test_unrelated_bases_sorted_alphabetically():
    """Cloneable and Serializable have no inheritance relationship — alphabetical."""
    bases = _make(["java.lang.Cloneable", "java.io.Serializable"])
    result = _sort_bases_for_mro(bases, JAVA_UTIL_LOOKUP)
    assert _names(result) == ["java.io.Serializable", "java.lang.Cloneable"]


def test_unrelated_bases_sorted_alphabetically_reversed():
    bases = _make(["java.io.Serializable", "java.lang.Cloneable"])
    result = _sort_bases_for_mro(bases, JAVA_UTIL_LOOKUP)
    assert _names(result) == ["java.io.Serializable", "java.lang.Cloneable"]


# -- The core bug: Collection listed before SequencedCollection ----------


def test_collection_before_sequenced_collection_is_reordered():
    """API 36 List declares (Collection, SequencedCollection).
    SequencedCollection extends Collection, so it must come first."""
    bases = _make(["java.util.Collection", "java.util.SequencedCollection"])
    result = _sort_bases_for_mro(bases, JAVA_UTIL_LOOKUP)
    assert _names(result) == [
        "java.util.SequencedCollection",
        "java.util.Collection",
    ]


def test_sequenced_collection_before_collection_stays():
    """API 35 order is already correct."""
    bases = _make(["java.util.SequencedCollection", "java.util.Collection"])
    result = _sort_bases_for_mro(bases, JAVA_UTIL_LOOKUP)
    assert _names(result) == [
        "java.util.SequencedCollection",
        "java.util.Collection",
    ]


# -- Full class declarations from API 36 --------------------------------


@pytest.mark.parametrize(
    "input_bases",
    [
        # API 36 order (wrong for Python):
        ["java.util.Collection", "java.util.SequencedCollection"],
        # API 35 order (already correct):
        ["java.util.SequencedCollection", "java.util.Collection"],
    ],
)
def test_list_bases(input_bases: list[str]):
    result = _sort_bases_for_mro(_make(input_bases), JAVA_UTIL_LOOKUP)
    names = _names(result)
    assert names.index("java.util.SequencedCollection") < names.index(
        "java.util.Collection"
    )


def test_arraylist_api36_order():
    """ArrayList(AbstractList, Cloneable, List, RandomAccess, Serializable)
    — AbstractList transitively inherits from List, so AbstractList must
    come before List."""
    bases = _make(
        [
            "java.util.AbstractList",
            "java.lang.Cloneable",
            "java.util.List",
            "java.util.RandomAccess",
            "java.io.Serializable",
        ]
    )
    result = _sort_bases_for_mro(bases, JAVA_UTIL_LOOKUP)
    names = _names(result)
    assert names.index("java.util.AbstractList") < names.index("java.util.List")


def test_linkedlist_api36_order():
    """LinkedList(AbstractSequentialList, Cloneable, Deque, List, Serializable).
    Order must be deterministic regardless of bytecode order."""
    bases = _make(
        [
            "java.util.AbstractSequentialList",
            "java.lang.Cloneable",
            "java.util.Deque",
            "java.util.List",
            "java.io.Serializable",
        ]
    )
    result = _sort_bases_for_mro(bases, JAVA_UTIL_LOOKUP)
    names = _names(result)
    assert names.index("java.util.AbstractSequentialList") < names.index(
        "java.util.List"
    )
    assert names.index("java.util.AbstractSequentialList") < names.index(
        "java.util.Deque"
    )


def test_linkedlist_deterministic_across_api_versions():
    """LinkedList bases must produce the same order regardless of bytecode order.

    API 35 bytecode order: ASL, List, Deque, Cloneable, Serializable
    API 36 bytecode order: ASL, Cloneable, Deque, List, Serializable
    """
    api35_bases = _make(
        [
            "java.util.AbstractSequentialList",
            "java.util.List",
            "java.util.Deque",
            "java.lang.Cloneable",
            "java.io.Serializable",
        ]
    )
    api36_bases = _make(
        [
            "java.util.AbstractSequentialList",
            "java.lang.Cloneable",
            "java.util.Deque",
            "java.util.List",
            "java.io.Serializable",
        ]
    )
    result35 = _names(_sort_bases_for_mro(api35_bases, JAVA_UTIL_LOOKUP))
    result36 = _names(_sort_bases_for_mro(api36_bases, JAVA_UTIL_LOOKUP))
    assert result35 == result36


def test_linked_hashmap_api36_order():
    """LinkedHashMap(HashMap, Map, SequencedMap) — HashMap inherits Map,
    SequencedMap inherits Map."""
    bases = _make(
        [
            "java.util.HashMap",
            "java.util.Map",
            "java.util.SequencedMap",
        ]
    )
    result = _sort_bases_for_mro(bases, JAVA_UTIL_LOOKUP)
    names = _names(result)
    assert names.index("java.util.HashMap") < names.index("java.util.Map")
    assert names.index("java.util.SequencedMap") < names.index("java.util.Map")


def test_linked_hashset_api36_order():
    """LinkedHashSet(HashSet, Cloneable, SequencedSet, Serializable, Set)."""
    bases = _make(
        [
            "java.util.HashSet",
            "java.lang.Cloneable",
            "java.util.SequencedSet",
            "java.io.Serializable",
            "java.util.Set",
        ]
    )
    result = _sort_bases_for_mro(bases, JAVA_UTIL_LOOKUP)
    names = _names(result)
    assert names.index("java.util.HashSet") < names.index("java.util.Set")
    assert names.index("java.util.SequencedSet") < names.index("java.util.Set")


def test_hashtable_api36_order():
    """Hashtable(Dictionary, Cloneable, Map, Serializable)
    — Dictionary and Map are unrelated, order should be preserved."""
    bases = _make(
        [
            "java.util.Dictionary",
            "java.lang.Cloneable",
            "java.util.Map",
            "java.io.Serializable",
        ]
    )
    result = _sort_bases_for_mro(bases, JAVA_UTIL_LOOKUP)
    names = _names(result)
    # Dictionary and Map are unrelated; alphabetical order
    assert names.index("java.util.Dictionary") < names.index("java.util.Map")


# -- Edge cases ----------------------------------------------------------


def test_unknown_types_sorted_alphabetically():
    """Types not in the lookup have no known ancestors; sorted alphabetically."""
    bases = _make(["com.unknown.Foo", "com.unknown.Bar"])
    result = _sort_bases_for_mro(bases, JAVA_UTIL_LOOKUP)
    assert _names(result) == ["com.unknown.Bar", "com.unknown.Foo"]


def test_empty_lookup():
    """With no inheritance info, alphabetical order is returned."""
    bases = _make(["java.util.Collection", "java.util.SequencedCollection"])
    result = _sort_bases_for_mro(bases, {})
    assert _names(result) == [
        "java.util.Collection",
        "java.util.SequencedCollection",
    ]


def test_returns_same_typestr_objects():
    """The returned list should contain the same TypeStr objects, not copies."""
    bases = _make(["java.util.SequencedCollection", "java.util.Collection"])
    result = _sort_bases_for_mro(bases, JAVA_UTIL_LOOKUP)
    for orig in bases:
        assert any(r is orig for r in result)
