from typing import Any, Dict, Optional, Annotated

from src.json_serialization import JsonDomainBase
from timefold.solver.domain import PlanningId

class Location(JsonDomainBase):
    # id: Annotated[str, PlanningId]
    longitude: Optional[float]
    latitude: Optional[float]
    driving_time_seconds_map: Optional[dict] = {}
    driving_distance_meters_map: Optional[dict] = {}

    def __init__(self, /, **data: Any):
        super().__init__(**data)
        if (
            not hasattr(self, "driving_time_seconds_map")
            or self.driving_time_seconds_map is None
        ):
            self.driving_time_seconds_map = {}
        if (
            not hasattr(self, "driving_distance_meters_map")
            or self.driving_distance_meters_map is None
        ):
            self.driving_distance_meters_map = {}

    def get_latitude(self):
        return self.latitude

    def get_longitude(self):
        return self.longitude

    def get_driving_time_seconds_map(self):
        return self.driving_time_seconds_map

    def driving_time_to(self, other: "Location") -> int:
        return round(self.driving_time_seconds_map[(other.longitude, other.latitude)])

    def driving_distance_to(self, other: "Location") -> int:
        return round(
            self.driving_distance_meters_map[(other.longitude, other.latitude)]
        )

    def set_driving_time_matrix(self, matrix: Dict["Location", float]):
        for key, val in matrix.items():
            self.driving_time_seconds_map[(key.longitude, key.latitude)] = val

    def set_driving_distance_matrix(self, matrix: Dict["Location", float]):
        for key, val in matrix.items():
            self.driving_distance_meters_map[
                (
                    key.longitude,
                    key.latitude,
                )
            ] = val

    def __str__(self):
        return f"[{self.longitude}, {self.latitude}]"

    def __repr__(self):
        return f"Location({self.longitude}, {self.latitude})"

    def __eq__(self, other):
        if isinstance(other, Location):
            return self.longitude == other.longitude and self.latitude == other.latitude
        return False

    def __hash__(self):
        return hash((self.longitude, self.latitude))
