from __future__ import annotations

import warnings
from collections import defaultdict, deque
from collections.abc import Callable, Sequence, Set
from enum import Enum
from functools import wraps
from typing import Any, Optional, TypeVar, Union, cast

import click
from pydantic import BaseModel, fields
from pydantic.error_wrappers import ValidationError

from .types import SCALAR_TYPES, NoneType, match_click_type_from_field


Func = TypeVar("Func", bound=Callable[..., Any])


__all__ = ()


MULTIPLE_VALUES_SHAPES: set[int] = {
    fields.SHAPE_LIST,
    fields.SHAPE_SET,
    fields.SHAPE_TUPLE_ELLIPSIS,
    fields.SHAPE_SEQUENCE,
    fields.SHAPE_FROZENSET,
    fields.SHAPE_ITERABLE,
    fields.SHAPE_DEQUE,
    *fields.MAPPING_LIKE_SHAPES,
}


def options_from_model(
    model: Union[type[BaseModel], BaseModel],
    *,
    include: Optional[set[str]] = None,
    exclude: Optional[set[str]] = None,
    to_kwarg: Optional[str] = None,
    apply_model_validators: bool = True,
    apply_env_vars: bool = True,
    bool_as_flag: bool = True,
    case_sensitive_enums: bool = False,
    **options_kwargs: Any,
) -> Callable[[Func], Func]:
    """
    Args:
        model: ...
        include:
        exclude:
        to_kwarg:
        apply_model_validators:
        apply_env_vars:
        bool_as_flag:
            use boolean flags feature for boolean fields (like --foo/--no-foo)
        case_sensitive_enums:
        **options_kwargs:
    """

    if isinstance(model, BaseModel):
        model_ = model.__class__
    else:
        model_ = model

    def decorator(func: Func) -> Func:
        field_names = calculate_fields(
            model_, include=include, exclude=exclude
        )

        for field_name in reversed(field_names):
            option = option_from_model_field(
                field_name,
                model_,
                apply_model_validators=apply_model_validators,
                apply_env_vars=apply_env_vars,
                bool_as_flag=bool_as_flag,
                case_sensitive_enums=case_sensitive_enums,
                **options_kwargs,
            )

            func = cast("Func", option(func))

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if to_kwarg is not None:
                model_data: dict[str, Any] = {
                    key: value
                    for key, value in kwargs.items()
                    if key in field_names
                }

                kwargs = {
                    key: value
                    for key, value in kwargs.items()
                    if key not in model_data
                }

                if to_kwarg in kwargs:
                    warnings.warn(f"{to_kwarg} already in kwargs")

                kwargs[to_kwarg] = model_data

            return func(*args, **kwargs)

        return cast("Func", wrapper)

    return decorator


def option_from_model_field(
    field_name: str,
    model: type[BaseModel],
    *,
    apply_model_validators: bool = True,
    apply_env_vars: bool = True,
    bool_as_flag: bool = True,
    case_sensitive_enums: bool = False,
    extra_types: dict[Any, Any] = {},
    **option_kwargs: Any,
) -> Callable[[click.decorators.FC], click.decorators.FC]:

    field = model.__fields__[field_name]

    click_type = match_click_type_from_field(
        field,
        case_sensitive_enums=case_sensitive_enums,
        extra_types=extra_types,
    )

    key = make_option_key(field_name, click_type, bool_as_flag)

    if isinstance(click_type, NoneType):
        option_kwargs.setdefault("is_flag", True)

    if field.shape in MULTIPLE_VALUES_SHAPES:
        option_kwargs.setdefault("multiple", True)

    default = convert_default(field.default)
    if default is not None:
        option_kwargs.setdefault("default", default)
        option_kwargs.setdefault("show_default", True)

    option_kwargs.setdefault("required", field.required)
    option_kwargs.setdefault("type", click_type)

    if field.field_info.description:
        option_kwargs.setdefault("help", field.field_info.description)

    envvar = get_envvar(field, apply_env_vars)
    if envvar is not None:
        option_kwargs.setdefault("envvar", envvar)

    validator = create_field_validator(
        field, model, apply_model_validators=apply_model_validators
    )
    option_kwargs.setdefault("callback", validator)

    return click.option(
        key,
        field_name,
        **option_kwargs,
    )


def create_field_validator(
    field: fields.ModelField,
    model: type[BaseModel],
    *,
    apply_model_validators: bool = True,
) -> Callable[[click.Context, click.Parameter, Any], Any]:
    def field_validator(
        ctx: click.Context, param: click.Parameter, value: Any
    ) -> Any:

        value = convert_to_shape_type(value, field)

        if apply_model_validators:
            value = run_model_validator(value, field, model)

        return value

    return field_validator


SHAPE_TO_TYPE_MAP: dict[int, Callable[[Any], Any]] = {
    fields.SHAPE_LIST: list,
    fields.SHAPE_SET: set,
    fields.SHAPE_MAPPING: dict,
    fields.SHAPE_FROZENSET: frozenset,
    fields.SHAPE_ITERABLE: iter,
    fields.SHAPE_DEQUE: deque,
    fields.SHAPE_DICT: dict,
}


def convert_to_shape_type(value: Any, field: fields.ModelField) -> Any:
    if field.shape in SHAPE_TO_TYPE_MAP:
        value = SHAPE_TO_TYPE_MAP[field.shape](value)
    elif field.shape == fields.SHAPE_DEFAULTDICT:
        value = defaultdict(field.type_, value)

    return value


def run_model_validator(
    value: Any,
    field: fields.ModelField,
    model: type[BaseModel],
) -> Any:
    value, errors = field.validate(value, values={}, loc=field.name, cls=model)

    if errors:
        validation_error = ValidationError([errors], model=model)
        raise click.BadParameter(validation_error.errors()[0]["msg"])

    return value


def convert_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value

    if isinstance(value, SCALAR_TYPES):
        return value

    if isinstance(value, Sequence):
        return [convert_default(i) for i in value]

    return value


def get_envvar(
    field: fields.ModelField,
    apply_env_vars: bool = True,
) -> Optional[str]:

    if apply_env_vars:
        env_names = field.field_info.extra.get("env_names") or []

        if env_names:
            return cast(str, list(env_names)[0])

    return None


def make_option_key(
    field_name: str,
    click_type: click.types.ParamType,
    bool_as_flag: bool,
) -> str:
    key = field_name.replace("_", "-").lower()

    if isinstance(click_type, click.types.BoolParamType) and bool_as_flag:
        key = f"{key}/--no-{key}"

    return f"--{key}"


def calculate_fields(
    model: type[BaseModel],
    *,
    include: Optional[set[str]] = None,
    exclude: Optional[set[str]] = None,
) -> tuple[str, ...]:
    keys: Set[str] = model.__fields__.keys()

    if include is not None:
        keys &= include

    if exclude is not None:
        keys -= exclude

    return tuple(key for key in model.__fields__.keys() if key in keys)
