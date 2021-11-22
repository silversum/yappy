import enum
from typing import Any, Literal, Tuple, Union

from pydantic import BaseModel, DirectoryPath, Field, FilePath


class MainTestModel(BaseModel):
    bool_val: bool = True
    int_val: int = 0
    float_val: float
    list_val: list[int] = Field(description="Field description")


class StrEnum(str, enum.Enum):
    FOO = "foo"
    BAR = "bar"
    ONE = "1"
    TWO = "2"


class IntEnum(int, enum.Enum):
    FIRST = enum.auto()
    SECOND = enum.auto()


class CaseSensitiveEnum(str, enum.Enum):
    VAL1 = "Value"
    VAL2 = "value"
    VAL3 = "VALUE"


class TypesTestModel(BaseModel):
    empty_tuple: Tuple[()]
    none: None
    scalar: int
    mapping: dict[str, str]
    tuple_: tuple[int, int]
    tuple_none: tuple[Literal[None]]
    union: Union[int, str]
    enum: StrEnum
    cs_enum: CaseSensitiveEnum
    any_: Any
    file_path: FilePath
    dir_path: DirectoryPath
