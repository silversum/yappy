from pathlib import Path

import click
import pytest

from yappy.types import (
    NONE,
    EnumChoice,
    MappingType,
    TupleType,
    UnionType,
    match_click_type_from_field,
)

from .models import CaseSensitiveEnum, IntEnum, StrEnum, TypesTestModel


def compare_click_types(result, expected):
    assert result.__class__ is expected.__class__
    assert result.is_composite == expected.is_composite
    assert result.arity == expected.arity
    assert result.name == expected.name
    assert result.envvar_list_splitter == expected.envvar_list_splitter

    if result.__class__ is EnumChoice:
        assert result._enum == expected._enum
        assert result._choices_aliaces == expected._choices_aliaces
        assert result.choices == expected.choices
        assert result.case_sensitive == expected.case_sensitive

    if hasattr(expected, "_subtypes"):
        for _result, _expected in zip(result._subtypes, expected._subtypes):
            compare_click_types(_result, _expected)


@pytest.mark.parametrize(
    "field_name, extra_types, case_sensitive_enums, expected",
    (
        ("empty_tuple", {}, False, NONE),
        ("none", {}, False, NONE),
        ("scalar", {}, False, click.INT),
        ("mapping", {}, False, MappingType(click.STRING, click.STRING)),
        ("tuple_", {}, False, TupleType([click.INT, click.INT])),
        ("tuple_none", {}, False, TupleType([NONE])),
        ("union", {}, False, UnionType([click.INT, click.STRING])),
        ("enum", {}, False, EnumChoice(StrEnum)),
        ("cs_enum", {}, False, EnumChoice(CaseSensitiveEnum)),
        ("enum", {}, True, EnumChoice(StrEnum, True)),
        ("scalar", {int: click.STRING}, False, click.STRING),
        ("any_", {}, False, click.UNPROCESSED),
        (
            "file_path",
            {},
            False,
            click.Path(exists=True, file_okay=False, path_type=Path),
        ),
        (
            "dir_path",
            {},
            False,
            click.Path(exists=True, dir_okay=False, path_type=Path),
        ),
    ),
)
def test_match_click_type_from_field(
    field_name,
    extra_types,
    case_sensitive_enums,
    expected,
):
    result = match_click_type_from_field(
        TypesTestModel.__fields__[field_name],
        extra_types=extra_types,
        case_sensitive_enums=case_sensitive_enums,
    )

    compare_click_types(result, expected)


def test_none_type():
    assert NONE.convert("some value", param=None, ctx=None) is None


def test_enum_choice_convert_value_type():
    enum_choice = EnumChoice(IntEnum)

    assert enum_choice._enum is IntEnum
    assert enum_choice.choices == ("1", "2")
    assert enum_choice.case_sensitive is False

    result = enum_choice.convert("1", param=None, ctx=None)
    assert result is IntEnum.FIRST

    result = enum_choice.convert(IntEnum.SECOND, param=None, ctx=None)
    assert result is IntEnum.SECOND

    match_msg = "'0' is not one of '1', '2'."
    with pytest.raises(click.BadParameter, match=match_msg):
        enum_choice.convert("0", param=None, ctx=None)


def test_enum_choice_case_isensitive():
    enum_choice = EnumChoice(StrEnum)

    assert enum_choice._enum is StrEnum
    assert enum_choice.choices == ("foo", "bar", "1", "2")
    assert enum_choice.case_sensitive is False

    result = enum_choice.convert("Foo", param=None, ctx=None)
    assert result is StrEnum.FOO

    match_msg = "'Fooo' is not one of 'foo', 'bar', '1', '2'."
    with pytest.raises(click.BadParameter, match=match_msg):
        enum_choice.convert("Fooo", param=None, ctx=None)


def test_enum_choice_case_sensitive():
    enum_choice = EnumChoice(StrEnum, case_sensitive=True)

    assert enum_choice._enum is StrEnum
    assert enum_choice.choices == ("foo", "bar", "1", "2")
    assert enum_choice.case_sensitive is True

    result = enum_choice.convert("foo", param=None, ctx=None)
    assert result is StrEnum.FOO

    match_msg = "'Foo' is not one of 'foo', 'bar', '1', '2'."
    with pytest.raises(click.BadParameter, match=match_msg):
        enum_choice.convert("Foo", param=None, ctx=None)


def test_enum_choice_case_sensitive_auto():
    enum_choice = EnumChoice(CaseSensitiveEnum)

    assert enum_choice._enum is CaseSensitiveEnum
    assert enum_choice.choices == ("Value", "value", "VALUE")
    assert enum_choice.case_sensitive is True

    result = enum_choice.convert("VALUE", param=None, ctx=None)
    assert result is CaseSensitiveEnum.VAL3

    match_msg = "'VAlue' is not one of 'Value', 'value', 'VALUE'."
    with pytest.raises(click.BadParameter, match=match_msg):
        enum_choice.convert("VAlue", param=None, ctx=None)


def test_tuple_type():
    subtypes = (click.INT, TupleType([click.STRING, click.STRING]))

    tuple_type = TupleType(subtypes)

    assert tuple_type._subtypes == subtypes
    assert tuple_type.name == "<integer <text text>>"
    assert tuple_type.arity == 3

    result = tuple_type.convert(("1", "2", "3"), param=None, ctx=None)
    assert result == (1, ("2", "3"))

    match_msg = "'a' is not a valid integer."
    with pytest.raises(click.BadParameter, match=match_msg):
        tuple_type.convert(("a", "b", "c"), param=None, ctx=None)

    tuple_type = TupleType([click.INT, NONE])
    assert (1, None) == tuple_type.convert("1", param=None, ctx=None)


def test_mapping_type():
    key_type = click.INT
    value_type = TupleType([click.STRING, click.STRING])

    tuple_type = MappingType(key_type, value_type)

    assert tuple_type._subtypes == (key_type, value_type)
    assert tuple_type.name == "<integer <text text>>"
    assert tuple_type.arity == 3

    result = tuple_type.convert(("1", "2", "3"), param=None, ctx=None)
    assert result == (1, ("2", "3"))

    match_msg = "'a' is not a valid integer."
    with pytest.raises(click.BadParameter, match=match_msg):
        tuple_type.convert(("a", "b", "c"), param=None, ctx=None)


def test_union_type():
    subtypes = (
        TupleType([click.BOOL, click.BOOL]),
        TupleType([click.INT, click.INT]),
    )

    union_type = UnionType(subtypes)

    assert union_type._subtypes == subtypes
    assert union_type.name == "<ANY: <boolean boolean> <integer integer>>"
    assert union_type.arity == 2

    result = union_type.convert(("1", "2"), param=None, ctx=None)
    assert result[0] == 1 and result[0] is not True
    assert result[1] == 2

    result = union_type.convert(("1", "0"), param=None, ctx=None)
    assert result[0] is True
    assert result[1] is False

    match_msg = "'a' is not a valid integer."
    with pytest.raises(click.BadParameter, match=match_msg):
        union_type.convert(("a", "b"), param=None, ctx=None)

    with pytest.raises(ValueError, match="at least two subtype are required"):
        UnionType([click.BOOL])

    match_msg = "different subtypes args count is not supported for UnionType"
    with pytest.raises(TypeError, match=match_msg):
        UnionType([click.BOOL, TupleType([click.INT, click.INT])])
