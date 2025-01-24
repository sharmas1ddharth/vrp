"""
Domain Validators and Serializers for Vehicle Routing Optimization

This module defines a set of utility functions and classes for handling JSON serialization and validation
of domain objects like locations, vehicles, customers, and optimization scores.

The module utilizes `Pydantic` for data validation and serialization, providing custom validators for working
with ID lookups and score objects. Additionally, it includes serializers for transforming complex objects
(such as `HardSoftScore`, locations, and durations) into JSON-compatible formats.

Key Components:
---------------
- **JsonDomainBase**: Base model for domain objects that customizes field aliasing and population.
- **Custom Validators**: Functions that validate IDs and map them to actual objects based on a given context.
- **Custom Serializers**: Functions that serialize complex objects (e.g., locations, scores, durations) into simple JSON-friendly formats.
"""

from datetime import timedelta
from typing import Any

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    PlainSerializer,
    ValidationInfo,
)
from pydantic.alias_generators import to_camel
from timefold.solver.score import HardSoftScore


class JsonDomainBase(BaseModel):
    """
    Base model for JSON domain objects.

    This model configures how domain objects are serialized into JSON. Specifically, it ensures that:

    - Field names are serialized using `camelCase`.
    - Fields can be populated using either their attribute names or aliases.
    - Fields can be populated from object attributes during model initialization.

    Attributes:
    -----------
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    """A configuration object for alias generation and field population behavior."""


def make_id_item_validator(key: str):
    """
    Creates a validator for fetching an item by its ID from a given context.

    This validator looks up an object from the context using a string ID.
    If the ID is found in the context dictionary under the provided key,
    it returns the corresponding object; otherwise, it returns the original value.

    Parameters:
    -----------
    key : str
        The key in the context dictionary that maps IDs to actual objects (e.g., 'customers' or 'vehicles').

    Returns:
    --------
    validator : BeforeValidator
        A Pydantic `BeforeValidator` function for validating and resolving the item by its ID.
    """
    def validator(v: Any, info: ValidationInfo) -> Any:
        if v is None:
            return None

        if not isinstance(v, str) or not info.context:
            return v

        return info.context.get(key)[v]

    return BeforeValidator(validator)


def make_id_list_item_validator(key: str):
    """
    Creates a validator for fetching a list of items by their IDs from a given context.

    This validator processes a list of string IDs and maps each ID to an object in the
    context based on the provided key. If the ID is found in the context, it returns
    a list of the corresponding objects.

    Parameters:
    -----------
    key : str
        The key in the context dictionary that maps IDs to actual objects (e.g., 'customers' or 'vehicles').

    Returns:
    --------
    validator : BeforeValidator
        A Pydantic `BeforeValidator` function for validating and resolving the list of items by their IDs.
    """
    def validator(v: Any, info: ValidationInfo) -> Any:
        if v is None:
            return None

        if isinstance(v, (list, tuple)):
            out = []
            for item in v:
                if not isinstance(v, str) or not info.context:
                    return v
                out.append(info.context.get(key)[item])
            return out

        return v

    return BeforeValidator(validator)


LocationSerializer = PlainSerializer(
    lambda location: [
        location.latitude,
        location.longitude,
    ],
    return_type=list[float],
)

# LocationSerializer = PlainSerializer(
#     lambda location: {
#         "location": [
#             location.latitude,
#             location.longitude,
#         ],
#         "id": location.id,
#     },
#     return_type=dict,
# )

"""
Serializer for converting a location object to a list of floats.

This serializer converts a `location` object into a list containing the latitude and
longitude as floats, making it easy to serialize location data in a JSON-friendly format.

Return Type:
------------
list[float]: A list with two elements: latitude and longitude.
"""

ScoreSerializer = PlainSerializer(lambda score: str(score), return_type=str)
"""
Serializer for converting a HardSoftScore object to a string.

This serializer converts a `HardSoftScore` object into a string representation,
making it suitable for serialization into JSON or other formats where a string
representation of the score is needed.

Return Type:
------------
str: The string representation of the score.
"""

IdSerializer = PlainSerializer(
    lambda item: item.id if item is not None else None, return_type=str | None
)
"""
Serializer for extracting the ID from an object.

This serializer extracts the `id` attribute from an object. If the object is `None`,
it returns `None`. Useful for serializing objects where the `id` is a key attribute.

Return Type:
------------
str | None: The ID of the object or `None` if the object is `None`.
"""

IdListSerializer = PlainSerializer(
    lambda items: [item.id for item in items], return_type=list
)
"""
Serializer for extracting IDs from a list of objects.

This serializer processes a list of objects and extracts the `id` attribute
from each object. It returns a list of IDs, which is useful for serializing
collections of objects.

Return Type:
------------
list[str]: A list of IDs from the objects.
"""

DurationSerializer = PlainSerializer(
    lambda duration: duration // timedelta(seconds=1), return_type=int
)
"""
Serializer for converting a timedelta object to an integer representing seconds.

This serializer converts a `timedelta` object into the number of seconds it represents,
allowing for easy serialization of durations in a simple integer format.

Return Type:
------------
int: The duration in seconds.
"""

CustomerListValidator = make_id_list_item_validator("customers")
"""
Validator for resolving a list of customer IDs into customer objects.

This validator maps a list of customer IDs from the input data to actual
customer objects based on the context provided. It uses the key 'customers'
to look up the corresponding objects.
"""

CustomerValidator = make_id_item_validator("customers")
"""
Validator for resolving a single customer ID into a customer object.

This validator maps a single customer ID from the input data to the actual
customer object based on the context provided. It uses the key 'customers'
to look up the corresponding object.
"""

VehicleValidator = make_id_item_validator("vehicles")
"""
Validator for resolving a single vehicle ID into a vehicle object.

This validator maps a single vehicle ID from the input data to the actual
vehicle object based on the context provided. It uses the key 'vehicles'
to look up the corresponding object.
"""


def validate_score(v: Any, info: ValidationInfo) -> Any:
    """
    Validates and parses a score value as a HardSoftScore.

    This validator checks whether the value is already a `HardSoftScore` object or a
    valid string representation. If it's a string, it attempts to parse it into a
    `HardSoftScore`. If it's neither a valid string nor a `HardSoftScore`, it raises an error.

    Parameters:
    -----------
    v : Any
        The value to be validated, either a string or `HardSoftScore` object.

    info : ValidationInfo
        Additional information provided by Pydantic's validation context.

    Returns:
    --------
    HardSoftScore: The parsed or original `HardSoftScore` object.

    Raises:
    -------
    ValueError: If the value is not a valid string or `HardSoftScore`.
    """
    if isinstance(v, HardSoftScore) or v is None:
        return v
    if isinstance(v, str):
        return HardSoftScore.parse(v)
    raise ValueError('"score" should be a string')


ScoreValidator = BeforeValidator(validate_score)
"""
Validator for HardSoftScore fields.

This validator uses the `BeforeValidator` mechanism from `Pydantic` to ensure that any field representing a `HardSoftScore`
is properly validated and parsed before assignment. It checks if the input value is already an instance of `HardSoftScore` or,
if it is a string, attempts to parse it into a valid `HardSoftScore` object. """
