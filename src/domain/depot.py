from typing import Annotated, Optional

from pydantic import BeforeValidator

from src.domain.location import Location
from src.json_serialization import JsonDomainBase, LocationSerializer


def location_validator(location):
    if isinstance(location, Location):
        return location
    elif isinstance(location, Depot):
        return location.location
    else:
        print(location)
        return Location(longitude=location[1], latitude=location[0])


LocationValidator = BeforeValidator(lambda location: location_validator(location))


class Depot(JsonDomainBase):
    id: int
    location: Annotated[Location, LocationSerializer, LocationValidator]
    address: Optional[str] = None
