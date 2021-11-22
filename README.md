# yappy

Yet another way to turn your [pydantic](https://github.com/samuelcolvin/pydantic) model into [click](https://github.com/pallets/click/) console application.


## What in the box?
- [union fields](https://pydantic-docs.helpmanual.io/usage/types/#unions) support (with some limitations - see [unions](#unions) section)
- [sequence](#sequences)- and [mapping](#mappings)-like fields
- [enum](https://docs.python.org/3/library/enum.html) values as [choices](https://click.palletsprojects.com/en/8.0.x/options/#choice-options)
- running [fields validators](https://pydantic-docs.helpmanual.io/usage/validators/) for values


## Installation

`pip install yappy`


## Usage

```python
# content of newuser.py

import enum

import click
from yappy import options_from_model
from pydantic import BaseModel, Field


class UserRole(str, enum.Enum):
    PLAIN = "plain"
    ADMIN = "admin"


class NewUserModel(BaseModel):
    name: str = Field(..., description="New user name")
    role: UserRole = UserRole.PLAIN
    blocked: bool = True


@click.command()
@options_from_model(NewUserModel)
def create_new_user(name: str, role: UserRole, blocked: bool):
    """Trying to create new user."""
    click.echo(f"Create new {'inactive' if blocked else 'active'} user...")
    click.echo(f"With username {name} and {role} role...")
    click.echo(f"Fail.")


if __name__ == '__main__':
    create_new_user()
```

```
$ python newuser.py --name Pancake --role admin --no-blocked
Create new active user...
With username Pancake and admin role...
Fail.
```

```
$ python newuser.py --help
Usage: newuser.py [OPTIONS]

  Trying to create new user.

Options:
  --name TEXT               New user name  [required]
  --role [plain|admin]      [default: plain]
  --blocked / --no-blocked  [default: no-blocked]
  --help                    Show this message and exit.
```


## Sequences

Tuple fields with fixed elements count turns into [multi value options](https://click.palletsprojects.com/en/8.0.x/options/#tuples-as-multi-value-options).

All other sequences (except `str`, of course) turns into [multiple options](https://click.palletsprojects.com/en/8.0.x/options/#multiple-options).


## Mappings

For now mappings turns into mix of [multi value](https://click.palletsprojects.com/en/8.0.x/options/#tuples-as-multi-value-options) and [multiple](https://click.palletsprojects.com/en/8.0.x/options/#multiple-options) options - every option contains key and value pair and can repeat.
Example:
```
$ python cli.py --dict-field key1 value1 --dict-field key2 value2
```
produce dict:
```python
{
    "key1": "value1",
    "key2": "value2",
}
```


## Unions

`Union` supports only same elements count, e.g. `Union[tuple[str, bool], tuple[str, int]]` are valid type, but `Union[tuple[str, bool], tuple[str]]` are not.
