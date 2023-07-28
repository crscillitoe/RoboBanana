import enum
from quart import Request


class SchemaValueType(enum.Enum):
    Integer = 0
    String = 1
    List = 2


async def parse_body(request: Request, schema: dict[str, SchemaValueType]):
    """Parse body of request according to provided schema

    Args:
        request (Request): Quart request to parse body of
        schema (dict[str, SchemaValueType]): Mapping of key name to its type

    Returns:
        dict[str, int | str]: Body with only the fields provided in schema
    """
    request_json = await request.get_json()
    parsed_body = dict()
    for key, value_type in schema.items():
        value = (
            int(request_json[key])
            if value_type == SchemaValueType.Integer
            else request_json[key]
        )
        parsed_body[key] = value
    return parsed_body
