from datetime import datetime
from typing import Annotated, Any, List, Optional

from pydantic import Field, computed_field
from timefold.solver import SolverStatus
from timefold.solver.domain import (
    PlanningEntityCollectionProperty,
    PlanningScore,
    ValueRangeProvider,
    planning_solution,
)
from timefold.solver.score import ScoreExplanation, HardMediumSoftScore

from src.constraint_configuration import VehicleRoutingConstraintConfiguration
from src.domain.customer_vehicle import Customer, Vehicle
from src.domain.depot import Depot
from src.domain.location import Location
from src.duration_distance_service import (
    DurationDistanceResponse,
    DurationDistanceService,
)
from src.json_serialization import (
    BeforeValidator,
    JsonDomainBase,
    LocationSerializer,
    ScoreSerializer,
    ScoreValidator,
)


def location_validator(location):
    if isinstance(location, Location):
        return location
    elif isinstance(location, Depot):
        return location.location
    else:
        print(location)
        return Location(longitude=location[1], latitude=location[0])


LocationValidator = BeforeValidator(lambda location: location_validator(location))


@planning_solution
class VehicleRoutePlan(JsonDomainBase):
    name: str
    depots: List[Depot]
    southWestCorner: Annotated[Location, LocationSerializer, LocationValidator]
    northEastCorner: Annotated[Location, LocationSerializer, LocationValidator]
    vehicles: Annotated[list[Vehicle], PlanningEntityCollectionProperty]
    customers: Annotated[
        list[Customer], PlanningEntityCollectionProperty, ValueRangeProvider
    ]
    score: Annotated[
        Optional[HardMediumSoftScore],
        PlanningScore,
        ScoreSerializer,
        ScoreValidator,
        Field(default=None),
    ]
    durationResponse: DurationDistanceResponse
    startDateTime: Optional[datetime] = None
    endDateTime: Optional[datetime] = None
    extraLocationCount: Optional[int] = 0

    def __init__(self, /, **data: Any):
        super().__init__(**data)
        if self.customers:
            locations = [vehicle.depot.location for vehicle in self.vehicles] + [
                customer.location for customer in self.customers
            ]
            duration_service = DurationDistanceService()
            duration_service.update_locations_with_durations(
                locations, self.durationResponse
            )
            duration_service.update_locations_with_distance(
                locations, self.durationResponse
            )

    @computed_field
    @property
    def total_driving_time_seconds(self) -> int:
        # print("solving")
        out = 0
        for vehicle in self.vehicles:
            out += vehicle.total_driving_time_seconds

        for customer in self.customers:
            out += customer.service_duration.seconds

        return out

    @computed_field
    @property
    def total_driving_distance_meters(self) -> int:
        out = 0
        for vehicle in self.vehicles:
            out += vehicle.total_driving_distance_meters
        return out

    @computed_field
    @property
    def total_fuel_liter(self) -> float:
        out = 0
        for vehicle in self.vehicles:
            out += vehicle.total_fuel_litre
        return out

    def __str__(self):
        return f"VehicleRoutePlan(name={self.name}, vehicles={self.vehicles}, customers={self.customers}),\
        southWestCorner={self.southWestCorner}, extraLocationCount={self.extraLocationCount}"
