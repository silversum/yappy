from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from inspect import isclass
from pathlib import Path
from typing import Any, Optional, TypeVar, Union, cast

import click
from pydantic import DirectoryPath, FilePath, fields
from pydantic.typing import NONE_TYPES


SCALAR_TYPES: tuple[type[Any], ...] = (
    int,
    float,
    bool,
    str,
    bytes,
)


CLICK_TYPE_ALIACES: dict[Any, click.types.ParamType] = {
    FilePath: click.Path(exists=True, file_okay=False, path_type=Path),
    DirectoryPath: click.Path(exists=True, dir_okay=False, path_type=Path),
}


def match_click_type_from_field(
    field: fields.ModelField,
    *,
    extra_types: dict[Any, click.types.ParamType] = {},
    case_sensitive_enums: bool = False,
) -> click.types.ParamType:

    types: list[Any]
    kwargs: dict[Any, Any] = {
        "extra_types": extra_types,
        "case_sensitive_enums": case_sensitive_enums,
    }

    if not field.sub_fields:
        if field.shape == fields.SHAPE_TUPLE:
            # empty tuple - no data needed
            return NONE

        if field.type_ is None:
            return NONE

        types = [field.type_]

    elif field.shape in fields.MAPPING_LIKE_SHAPES:
        return build_mapping_type(field, **kwargs)

    else:
        types = [
            match_click_type_from_field(i, **kwargs) for i in field.sub_fields
        ]

    if field.shape == fields.SHAPE_TUPLE:
        return TupleType(types)

    return match_click_type(types, **kwargs)


def match_click_type(
    types: list[Any],
    *,
    extra_types: dict[Any, click.types.ParamType] = {},
    case_sensitive_enums: bool = False,
) -> click.types.ParamType:

    kwargs: dict[Any, Any] = {
        "extra_types": extra_types,
        "case_sensitive_enums": case_sensitive_enums,
    }

    if len(types) > 1:
        return build_click_composite_type(UnionType, types, **kwargs)

    type_ = types[0]

    if type_ in extra_types:
        return extra_types[type_]

    if type_ in NONE_TYPES:
        return NONE

    if type_ in SCALAR_TYPES:
        return click.types.convert_type(type_)

    if isinstance(type_, click.ParamType):
        return type_

    if isclass(type_) and issubclass(type_, Enum):
        type_ = cast("type[Enum]", type_)
        return EnumChoice(type_, case_sensitive=case_sensitive_enums)

    if type_ in CLICK_TYPE_ALIACES:
        return CLICK_TYPE_ALIACES[type_]

    return click.UNPROCESSED


def build_mapping_type(
    field: fields.ModelField,
    extra_types: dict[Any, click.types.ParamType] = {},
    case_sensitive_enums: bool = False,
) -> MappingType:

    kwargs: dict[Any, Any] = {
        "extra_types": extra_types,
        "case_sensitive_enums": case_sensitive_enums,
    }

    key_field = cast("fields.ModelField", field.key_field)
    key_type = match_click_type_from_field(key_field, **kwargs)
    value_type = match_click_type([field.type_], **kwargs)
    return MappingType(key_type, value_type)


_ClidanticCompositeType = TypeVar(
    "_ClidanticCompositeType", bound="Union[TupleType, UnionType]"
)


def build_click_composite_type(
    click_type: type[_ClidanticCompositeType],
    types: Sequence[Any],
    **kwargs: Any,
) -> _ClidanticCompositeType:

    subtypes = [match_click_type([i], **kwargs) for i in types]
    return cast("_ClidanticCompositeType", click_type(subtypes))


class NoneType(click.types.ParamType):
    arity = 0

    name = ""

    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> None:

        return None


NONE = NoneType()


class EnumChoice(click.types.Choice):
    _enum: type[Enum]
    _choices_aliaces: dict[str, Enum]

    def __init__(self, enum: type[Enum], case_sensitive: bool = False) -> None:
        self._enum = enum
        self._choices_aliaces = {str(i.value): i for i in enum}

        choices = tuple(self._choices_aliaces.keys())

        if not case_sensitive:
            case_sensitive = len(set(map(str.lower, choices))) != len(choices)

        super().__init__(choices=choices, case_sensitive=case_sensitive)

    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Any:

        if isinstance(value, self._enum):
            return value

        value = super().convert(value=value, param=param, ctx=ctx)
        return self._choices_aliaces[value]


class TupleType(click.types.CompositeParamType):
    _subtypes: tuple[click.types.ParamType, ...]

    def __init__(self, subtypes: Sequence[click.types.ParamType]):
        self._subtypes = tuple(subtypes)

    @property
    # ignore: incompatible signature
    def name(self) -> str:  # type: ignore
        subtypes = " ".join(t.name for t in self._subtypes)
        return f"<{subtypes}>"

    @property
    # ignore: incompatible signature
    def arity(self) -> int:  # type: ignore
        return sum(i.arity for i in self._subtypes)

    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> tuple[Any, ...]:

        if not isinstance(value, tuple):
            value = (value,)

        remain_values: list[Any] = list(value)
        results: list[Any] = []

        for subtype in self._subtypes:
            if subtype.arity == 1:
                subtype_value = remain_values[0]
            else:
                subtype_value = tuple(remain_values[: subtype.arity])

            results.append(subtype(subtype_value))
            remain_values = remain_values[subtype.arity :]

        return tuple(results)


class MappingType(TupleType):
    def __init__(
        self,
        key_type: click.types.ParamType,
        value_type: click.types.ParamType,
    ) -> None:
        self._subtypes = (key_type, value_type)


class UnionType(click.types.CompositeParamType):
    _subtypes: tuple[click.types.ParamType, ...]

    def __init__(self, subtypes: Sequence[click.types.ParamType]):
        self._subtypes = tuple(subtypes)

        if len(self._subtypes) < 2:
            raise ValueError("at least two subtype are required")

        if len(set(i.arity for i in self._subtypes)) > 1:
            raise TypeError(
                "different subtypes args count is not supported for UnionType"
            )

    @property
    # ignore: incompatible signature
    def name(self) -> str:  # type: ignore
        names = [t.name for t in self._subtypes]
        uniq_names = set(names)
        subtypes = " ".join(sorted(uniq_names, key=lambda x: names.index(x)))
        return f"<ANY: {subtypes}>"

    @property
    # ignore: incompatible signature
    def arity(self) -> int:  # type: ignore
        return self._subtypes[0].arity

    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Any:

        for subtype in self._subtypes:
            try:
                return subtype(value)
            except click.BadParameter as e:
                error = e

        raise error
