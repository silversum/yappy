from collections import defaultdict, deque
from unittest.mock import MagicMock, call, patch, sentinel

import click
import pytest
from pydantic import fields
from pydantic.error_wrappers import ErrorWrapper

from yappy import main, types

from . import models


@patch.object(main, "option_from_model_field")
@patch.object(
    main,
    "calculate_fields",
    return_value=[sentinel.field_name_1, sentinel.field_name_2],
)
def test_options_from_model(calculate_fields, option_from_model_field):
    option_func = MagicMock(side_effect=lambda x: x)
    option_from_model_field.side_effect = [option_func, option_func]

    model = models.MainTestModel

    func = MagicMock()

    option_decorator = main.options_from_model(
        model,
        include=sentinel.include,
        exclude=sentinel.exclude,
        to_kwarg=sentinel.to_kwarg,
        apply_model_validators=sentinel.apply_model_validators,
        apply_env_vars=sentinel.apply_env_vars,
        bool_as_flag=sentinel.bool_as_flag,
        case_sensitive_enums=sentinel.case_sensitive_enums,
        option_kwarg_1=sentinel.option_kwarg_1,
        option_kwarg_2=sentinel.option_kwarg_2,
    )

    option_decorator(func)

    calculate_fields.assert_called_once_with(
        model, include=sentinel.include, exclude=sentinel.exclude
    )

    assert option_from_model_field.call_count == 2
    option_from_model_field.assert_has_calls(
        (
            call(
                sentinel.field_name_2,
                model,
                apply_model_validators=sentinel.apply_model_validators,
                apply_env_vars=sentinel.apply_env_vars,
                bool_as_flag=sentinel.bool_as_flag,
                case_sensitive_enums=sentinel.case_sensitive_enums,
                option_kwarg_1=sentinel.option_kwarg_1,
                option_kwarg_2=sentinel.option_kwarg_2,
            ),
            call(
                sentinel.field_name_1,
                model,
                apply_model_validators=sentinel.apply_model_validators,
                apply_env_vars=sentinel.apply_env_vars,
                bool_as_flag=sentinel.bool_as_flag,
                case_sensitive_enums=sentinel.case_sensitive_enums,
                option_kwarg_1=sentinel.option_kwarg_1,
                option_kwarg_2=sentinel.option_kwarg_2,
            ),
        )
    )

    assert option_func.call_count == 2
    option_func.assert_has_calls(
        (
            call(func),
            call(func),
        )
    )

    func.assert_not_called()


@patch.object(
    main,
    "option_from_model_field",
    return_value=MagicMock(side_effect=lambda x: x),
)
@patch.object(
    main,
    "calculate_fields",
    return_value=[sentinel.field_name_1],
)
def test_options_from_model_model_instance(
    calculate_fields,
    option_from_model_field,
):

    model = models.MainTestModel
    model_instance = model(float_val=1, list_val=[])
    func = MagicMock()
    option_decorator = main.options_from_model(model_instance)
    option_decorator(func)

    assert calculate_fields.call_args.args[0] is model
    assert option_from_model_field.call_args.args[1] is model


@patch.object(
    main,
    "option_from_model_field",
    return_value=MagicMock(side_effect=lambda x: x),
)
@patch.object(main, "calculate_fields")
def test_options_from_model_call(
    calculate_fields,
    option_from_model_field,
):

    calculate_fields.return_value = ["field_name_1", "field_name_2"]

    model = models.MainTestModel
    func = MagicMock(return_value=sentinel.func_return_value)
    option_decorator = main.options_from_model(model)
    cli = option_decorator(func)

    result = cli(
        sentinel.arg1,
        sentinel.arg2,
        field_name_1=sentinel.kwarg1,
        field_name_2=sentinel.kwarg2,
    )

    func.assert_called_once_with(
        sentinel.arg1,
        sentinel.arg2,
        field_name_1=sentinel.kwarg1,
        field_name_2=sentinel.kwarg2,
    )

    assert result is sentinel.func_return_value


@patch.object(
    main,
    "option_from_model_field",
    return_value=MagicMock(side_effect=lambda x: x),
)
@patch.object(main, "calculate_fields")
def test_options_from_model_call_to_kwarg(
    calculate_fields,
    option_from_model_field,
):

    calculate_fields.return_value = ["field_name_1", "field_name_2"]

    model = models.MainTestModel
    func = MagicMock(return_value=sentinel.func_return_value)
    option_decorator = main.options_from_model(model, to_kwarg="kwarg_name")
    cli = option_decorator(func)

    result = cli(
        sentinel.arg1,
        sentinel.arg2,
        field_name_1=sentinel.kwarg1,
        field_name_2=sentinel.kwarg2,
    )

    func.assert_called_once_with(
        sentinel.arg1,
        sentinel.arg2,
        kwarg_name={
            "field_name_1": sentinel.kwarg1,
            "field_name_2": sentinel.kwarg2,
        },
    )

    assert result is sentinel.func_return_value


@patch.object(
    main,
    "option_from_model_field",
    return_value=MagicMock(side_effect=lambda x: x),
)
@patch.object(main, "calculate_fields")
def test_options_from_model_call_to_kwarg_warning(
    calculate_fields,
    option_from_model_field,
):

    calculate_fields.return_value = ["field_name_1", "field_name_2"]

    model = models.MainTestModel
    func = MagicMock(
        return_value=sentinel.func_return_value,
    )
    option_decorator = main.options_from_model(model, to_kwarg="kwarg_name")
    cli = option_decorator(func)

    with pytest.warns(UserWarning) as warn_records:
        result = cli(
            sentinel.arg1,
            sentinel.arg2,
            kwarg_name=sentinel.kwarg0,
            field_name_1=sentinel.kwarg1,
            field_name_2=sentinel.kwarg2,
        )

    assert len(warn_records) == 1
    assert warn_records[0].message.args[0] == "kwarg_name already in kwargs"

    func.assert_called_once_with(
        sentinel.arg1,
        sentinel.arg2,
        kwarg_name={
            "field_name_1": sentinel.kwarg1,
            "field_name_2": sentinel.kwarg2,
        },
    )

    assert result is sentinel.func_return_value


@pytest.mark.parametrize(
    "field_name, return_values, result_kwargs",
    (
        (
            "bool_val",
            {},
            {
                "default": sentinel.convert_default,
                "show_default": True,
                "required": False,
                "type": sentinel.match_click_type_from_field,
                "envvar": sentinel.get_envvar,
                "callback": sentinel.create_field_validator,
            },
        ),
        (
            "list_val",
            {
                "match_click_type_from_field": types.NONE,
                "convert_default": None,
                "get_envvar": None,
            },
            {
                "is_flag": True,
                "multiple": True,
                "required": True,
                "type": types.NONE,
                "help": "Field description",
                "callback": sentinel.create_field_validator,
            },
        ),
    ),
)
@patch.object(click, "option", return_value=sentinel.option_decorator)
@patch.object(main, "create_field_validator")
@patch.object(main, "get_envvar")
@patch.object(main, "convert_default")
@patch.object(main, "make_option_key")
@patch.object(main, "match_click_type_from_field")
def test_option_from_model_field(
    match_click_type_from_field,
    make_option_key,
    convert_default,
    get_envvar,
    create_field_validator,
    click_option,
    field_name,
    return_values,
    result_kwargs,
):
    model = models.MainTestModel
    field = model.__fields__[field_name]

    match_click_type_from_field.return_value = return_values.get(
        "match_click_type_from_field", sentinel.match_click_type_from_field
    )
    make_option_key.return_value = return_values.get(
        "make_option_key", sentinel.make_option_key
    )
    convert_default.return_value = return_values.get(
        "convert_default", sentinel.convert_default
    )
    get_envvar.return_value = return_values.get(
        "get_envvar", sentinel.get_envvar
    )
    create_field_validator.return_value = return_values.get(
        "create_field_validator", sentinel.create_field_validator
    )

    result = main.option_from_model_field(
        field_name,
        model,
        apply_model_validators=sentinel.apply_model_validators,
        apply_env_vars=sentinel.apply_env_vars,
        bool_as_flag=sentinel.bool_as_flag,
        case_sensitive_enums=sentinel.case_sensitive_enums,
        extra_types=sentinel.extra_types,
        option_kwarg_1=sentinel.option_kwarg_1,
        option_kwarg_2=sentinel.option_kwarg_2,
    )

    match_click_type_from_field.assert_called_once_with(
        field,
        case_sensitive_enums=sentinel.case_sensitive_enums,
        extra_types=sentinel.extra_types,
    )

    make_option_key.assert_called_once_with(
        field_name,
        match_click_type_from_field.return_value,
        sentinel.bool_as_flag,
    )

    convert_default.assert_called_once_with(field.default)
    get_envvar.assert_called_once_with(field, sentinel.apply_env_vars)

    create_field_validator.assert_called_once_with(
        field,
        model,
        apply_model_validators=sentinel.apply_model_validators,
    )

    click_option.assert_called_once_with(
        make_option_key.return_value,
        field_name,
        option_kwarg_1=sentinel.option_kwarg_1,
        option_kwarg_2=sentinel.option_kwarg_2,
        **result_kwargs,
    )

    assert result is sentinel.option_decorator


@patch.object(main, "run_model_validator")
@patch.object(main, "convert_to_shape_type")
def test_create_field_validator(convert_to_shape_type, run_model_validator):
    convert_to_shape_type.return_value = sentinel.convert_to_shape_type
    run_model_validator.return_value = sentinel.run_model_validator

    validator = main.create_field_validator(
        sentinel.model_field,
        sentinel.model,
    )
    result = validator(
        ctx=sentinel.ctx,
        param=sentinel.param,
        value=sentinel.value,
    )

    convert_to_shape_type.assert_called_once_with(
        sentinel.value,
        sentinel.model_field,
    )
    run_model_validator.assert_called_once_with(
        sentinel.convert_to_shape_type,
        sentinel.model_field,
        sentinel.model,
    )
    assert result is sentinel.run_model_validator


@patch.object(main, "run_model_validator")
@patch.object(main, "convert_to_shape_type")
def test_create_field_validator_no_apply_field_validator(
    convert_to_shape_type,
    run_model_validator,
):
    convert_to_shape_type.return_value = sentinel.convert_to_shape_type

    validator = main.create_field_validator(
        sentinel.model_field,
        sentinel.model,
        apply_model_validators=False,
    )
    result = validator(
        ctx=sentinel.ctx,
        param=sentinel.param,
        value=sentinel.value,
    )

    convert_to_shape_type.assert_called_once_with(
        sentinel.value,
        sentinel.model_field,
    )
    run_model_validator.assert_not_called()
    assert result is sentinel.convert_to_shape_type


@pytest.mark.parametrize(
    "shape, value, expected",
    (
        (-1, "value", "value"),  # unexpected shape
        (fields.SHAPE_LIST, (1, 2, 3), [1, 2, 3]),
        (fields.SHAPE_SET, (1, 2, 3), {1, 2, 3}),
        (fields.SHAPE_MAPPING, (("a", 1), ("b", 2)), {"a": 1, "b": 2}),
        (fields.SHAPE_FROZENSET, (1, 2, 3), frozenset((1, 2, 3))),
        (fields.SHAPE_DEQUE, (1, 2, 3), deque((1, 2, 3))),
        (fields.SHAPE_DICT, (("a", 1), ("b", 2)), {"a": 1, "b": 2}),
        (
            fields.SHAPE_DEFAULTDICT,
            (("a", 1), ("b", 2)),
            defaultdict(int, {"a": 1, "b": 2}),
        ),
    ),
)
def test_convert_to_shape_type(shape, value, expected):
    field = MagicMock(spec=fields.ModelField)
    field.shape = shape
    field.type_ = int

    result = main.convert_to_shape_type(value, field)

    assert result == expected


def test_convert_to_shape_type_iter():
    field = MagicMock(spec=fields.ModelField)
    field.shape = fields.SHAPE_ITERABLE
    value = (1, 2, 3)

    result = main.convert_to_shape_type(value, field)

    assert repr(result).startswith("<tuple_iterator object at ")
    assert tuple(result) == value


def test_run_model_validator():
    field = MagicMock(spec=fields.ModelField)
    field.validate.return_value = (sentinel.validated_value, [])
    field.name = sentinel.field_name

    result = main.run_model_validator(sentinel.value, field, sentinel.model)

    assert result is sentinel.validated_value
    field.validate.assert_called_once_with(
        sentinel.value, values={}, loc=sentinel.field_name, cls=sentinel.model
    )


def test_run_model_validator_error():
    field = MagicMock(spec=fields.ModelField)
    field.validate.return_value = (
        None,
        [ErrorWrapper(ValueError("some error"), "field_name")],
    )
    field.name = "field_name"

    with pytest.raises(click.BadParameter) as exc_info:
        main.run_model_validator(sentinel.value, field, models.MainTestModel)

    assert exc_info.value.args[0] == "some error"

    field.validate.assert_called_once_with(
        sentinel.value,
        values={},
        loc="field_name",
        cls=models.MainTestModel,
    )


@pytest.mark.parametrize(
    "value, expected",
    (
        (None, None),
        ("str value", "str value"),
        (models.StrEnum.FOO, "foo"),
        ([1, "a", models.StrEnum.BAR], [1, "a", "bar"]),
    ),
)
def test_convert_default(value, expected):
    result = main.convert_default(value)
    assert repr(result) == repr(expected)


@pytest.mark.parametrize(
    "env_names, apply_env_vars, expected",
    (
        (None, False, None),
        (None, True, None),
        (["env1"], True, "env1"),
        (["env1"], False, None),
        (["env1", "env2"], True, "env1"),
    ),
)
def test_get_envvar(env_names, apply_env_vars, expected):
    field = MagicMock(spec=fields.ModelField)
    field.field_info.extra.get.return_value = env_names

    result = main.get_envvar(field, apply_env_vars)

    assert result == expected

    if apply_env_vars:
        field.field_info.extra.get.assert_called_once_with("env_names")


@pytest.mark.parametrize(
    "field_name, click_type, bool_as_flag, expected",
    (
        ("Foo", click.types.STRING, False, "--foo"),
        ("foo_bar", click.types.STRING, False, "--foo-bar"),
        ("foo_bar", click.types.BOOL, False, "--foo-bar"),
        ("foo_bar", click.types.BOOL, True, "--foo-bar/--no-foo-bar"),
    ),
)
def test_make_option_key(field_name, click_type, bool_as_flag, expected):
    result = main.make_option_key(field_name, click_type, bool_as_flag)
    assert result == expected


@pytest.mark.parametrize(
    "include, exclude, expected",
    (
        (None, None, ("bool_val", "int_val", "float_val", "list_val")),
        ({"bool_val", "int_val"}, None, ("bool_val", "int_val")),
        (None, {"bool_val", "int_val"}, ("float_val", "list_val")),
        ({"bool_val", "int_val"}, {"int_val", "float_val"}, ("bool_val",)),
    ),
)
def test_calculate_fields(include, exclude, expected):
    result = main.calculate_fields(
        models.MainTestModel,
        include=include,
        exclude=exclude,
    )
    assert result == expected
