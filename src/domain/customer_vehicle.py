from datetime import datetime, timedelta
from typing import Annotated, Any, Optional

import logfire
from pydantic import BeforeValidator, Field, computed_field
from timefold.solver.domain import (
    CascadingUpdateShadowVariable,
    InverseRelationShadowVariable,
    NextElementShadowVariable,
    PlanningId,
    PlanningListVariable,
    PreviousElementShadowVariable,
    planning_entity,
)

from src.domain.depot import Depot
from src.domain.location import Location
from src.json_serialization import (
    CustomerValidator,
    DurationSerializer,
    IdListSerializer,
    IdSerializer,
    JsonDomainBase,
    LocationSerializer,
    VehicleValidator,
)

logfire.configure()

shadow_variable_exception_message = "This method must not be called when the shadow variables are not initialized yet."

def location_validator(location):
    if isinstance(location, Location):
        return location
    elif isinstance(location, Depot):
        return location.location
    else:
        print(location)
        return Location(longitude=location[1], latitude=location[0])


LocationValidator = BeforeValidator(lambda location: location_validator(location))


@planning_entity
class Customer(JsonDomainBase):
    id: Annotated[int, PlanningId]
    name: Optional[str] = None
    location: Annotated[Location, LocationSerializer, LocationValidator]
    ready_time: datetime
    due_time: datetime
    service_duration: Annotated[timedelta, DurationSerializer]
    demand: int
    isExtra: Optional[bool] = False
    booking_date: Optional[datetime] = None
    days: Optional[int] = 1
    vehicle: Annotated[
        Optional["Vehicle"],
        InverseRelationShadowVariable(source_variable_name="customers"),
        IdSerializer,
        VehicleValidator,
        Field(default=None),
    ]
    previous_customer: Annotated[
        Optional["Customer"],
        PreviousElementShadowVariable(source_variable_name="customers"),
        IdSerializer,
        CustomerValidator,
        Field(default=None),
    ]
    next_customer: Annotated[
        Optional["Customer"],
        NextElementShadowVariable(source_variable_name="customers"),
        IdSerializer,
        CustomerValidator,
        Field(default=None),
    ]
    arrival_time: Annotated[
        Optional[datetime],
        CascadingUpdateShadowVariable(target_method_name="update_arrival_time"),
        Field(default=None),
    ]

    def update_arrival_time(self) -> None:
        if self.vehicle is None or (
            self.previous_customer is not None
            and self.previous_customer.arrival_time is None
        ):
            self.arrival_time = None
        elif self.previous_customer is None:
            self.arrival_time = self.vehicle.departure_time + timedelta(
                seconds=self.vehicle.depot.location.driving_time_to(self.location)
            )
        else:
            self.arrival_time = self.previous_customer.departure_time() + timedelta(
                seconds=self.previous_customer.location.driving_time_to(self.location)
            ) + timedelta(seconds=self.previous_customer.service_duration.seconds)

    @computed_field
    @property
    def departureTime(self) -> Optional[datetime]:
        return self.departure_time()

    @computed_field
    @property
    def startServiceTime(self) -> Optional[datetime]:
        if self.arrival_time is None:
            return None

        return max(self.ready_time, self.arrival_time)

    @computed_field
    @property
    def drivingTimeSecondsFromPreviousStandstill(self) -> Optional[int]:
        if self.vehicle is None:
            return None
        return self.driving_time_seconds_from_previous_standstill_or_none()

    @computed_field
    @property
    def drivingTimeSecondsToDepot(self) -> Optional[int]:
        if self.vehicle is None:
            return None
        return self.driving_time_seconds_to_depot()

    def departure_time(self) -> Optional[datetime]:
        if self.arrival_time is None:
            return None
        return self.arrival_time + self.service_duration

    def is_service_finished_after_due_time(self) -> bool:
        return self.arrival_time is not None and self.departure_time() > self.due_time

    def get_service_finished_delay_in_minutes(self) -> float:
        if self.arrival_time is None:
            return float(0)
        return float(
            -((self.departure_time() - self.due_time) // timedelta(minutes=-1))
        )

    def driving_time_seconds_to_depot(self) -> int:
        if self.vehicle is None:
            raise ValueError(
                shadow_variable_exception_message
            )
        return self.location.driving_time_to(self.vehicle.depot.location) #+ 600


    def driving_time_seconds_from_previous_standstill_or_none(self) -> int:
        if self.vehicle is None:
            raise ValueError(
                shadow_variable_exception_message
            )

        if self.previous_customer is None:
            return self.vehicle.depot.location.driving_time_to(self.location)
        else:
            # customer_time = (
            #     self.previous_customer.location.driving_time_to(self.location)
            #     + self.previous_customer.service_duration.seconds
            # )
            customer_time = (
                self.previous_customer.location.driving_time_to(self.location)
            )
            return customer_time

    def get_days_since_request(self) -> int:
        if self.booking_date is not None:
            today = datetime.today()
            difference_in_days = (today - self.booking_date).days
            self.days = difference_in_days
            return difference_in_days
        else:
            return 1

    def get_location(self):
        return [self.location.longitude, self.location.latitude]

    def __str__(self):
        return self.id

    def __repr__(self):
        return f"Customer({self.id})"


@planning_entity
class Vehicle(JsonDomainBase):
    id: Annotated[str, PlanningId]
    vehicle_id: Optional[str] = None
    vehicleType: Optional[str] = None
    vehicleNo: Optional[str] = None
    capacity: int
    mileage: Optional[int] = 1
    departure_time: datetime
    depot: Depot
    customers: Annotated[
        list[Customer],
        PlanningListVariable(allows_unassigned_values=True),
        IdListSerializer,
        CustomerValidator,
        Field(default_factory=list),
    ]

    @computed_field
    @property
    def arrival_time(self) -> datetime:
        if len(self.customers) == 0:
            return self.departure_time

        last_customer = self.customers[-1]
        return last_customer.departureTime + timedelta(
            seconds=last_customer.location.driving_time_to(self.depot.location)
        )

    @computed_field
    @property
    def total_demand(self) -> int:
        return self.calculate_total_demand()

    @computed_field
    @property
    def total_driving_time_seconds(self) -> int:
        return self.calculate_total_driving_time_seconds()

    @computed_field
    @property
    def total_driving_time_seconds_without_pitstop(self) -> int:
        return self.calculate_total_driving_time_seconds_without_pitstop()

    @computed_field
    @property
    def total_driving_distance_meters(self) -> int:
        return self.calculate_total_driving_distance_meters()

    def calculate_total_demand(self) -> int:
        total_demand = 0

        for visit in self.customers:
            total_demand += visit.demand
        return total_demand

    def calculate_total_driving_time_seconds_without_pitstop(self) -> int:
        if len(self.customers) == 0:
            return 0
        total_driving_time_seconds = 0
        previous_location = self.depot.location

        for visit in self.customers:
            total_driving_time_seconds += previous_location.driving_time_to(
                visit.location
            )
            total_driving_time_seconds += visit.service_duration.seconds
            previous_location = visit.location

        total_driving_time_seconds += previous_location.driving_time_to(
            self.depot.location
        )

        return total_driving_time_seconds

    def calculate_total_driving_time_seconds(self) -> int:
        if len(self.customers) == 0:
            return 0
        total_driving_time_seconds = 0
        previous_location = self.depot.location

        for visit in self.customers:
            total_driving_time_seconds += previous_location.driving_time_to(
                visit.location
            )
            total_driving_time_seconds += visit.service_duration.seconds
            previous_location = visit.location

            total_driving_time_seconds += 60 # Added 1 minute per order

        total_driving_time_seconds += previous_location.driving_time_to(
            self.depot.location
        )

        return total_driving_time_seconds

    def calculate_total_driving_distance_meters(self) -> int:
        if len(self.customers) == 0:
            return 0
        total_driving_distance_meters = 0
        previous_location = self.depot.location

        for visit in self.customers:
            total_driving_distance_meters += previous_location.driving_distance_to(
                visit.location
            )
            previous_location = visit.location

        total_driving_distance_meters += previous_location.driving_distance_to(
            self.depot.location
        )
        return total_driving_distance_meters

    @computed_field
    @property
    def route(self) -> list[Any] | list[list[float | None] | Location]:
        if not self.customers:
            return []

        route = [[self.depot.location.longitude, self.depot.location.latitude]]
        for customer in self.customers:
            route.append(customer.get_location())
        route.append([self.depot.location.longitude, self.depot.location.latitude])
        return route

    @computed_field
    @property
    def total_fuel_litre(self) -> int:
        return int(self.calculate_total_driving_distance_meters() / self.mileage)

    def __str__(self):
        return self.id

    def __repr__(self):
        return f"Vehicle({self.id}), departureTime={self.departure_time}"
