from dataclasses import field
from typing import Annotated

from pydantic import validator
from timefold.solver.domain import ConstraintWeight, constraint_configuration
from timefold.solver.score import HardSoftScore

from src.json_serialization import JsonDomainBase


@constraint_configuration
class VehicleRoutingConstraintConfiguration(JsonDomainBase):
    service_finished_after_due_time: Annotated[
        HardSoftScore, ConstraintWeight("service_finished_after_due_time")
    ] = field(default=HardSoftScore.ONE_HARD)
    vehicle_capacity: Annotated[HardSoftScore, ConstraintWeight("vehicle_capacity")] = (
        field(default=HardSoftScore.ONE_HARD)
    )
    minimize_travel_time: Annotated[
        HardSoftScore, ConstraintWeight("vehicle_capacity")
    ] = field(default=HardSoftScore.ONE_SOFT)
    minimize_travel_distance: Annotated[
        HardSoftScore, ConstraintWeight("vehicle_capacity")
    ] = field(default=HardSoftScore.ONE_SOFT)

    @validator('service_finished_after_due_time', 'vehicle_capacity', 'minimize_travel_time',
               'minimize_travel_distance')
    def validate_scores(cls, v):
        if v.hard_score < 0 and v.soft_score < 0 :
            raise ValueError("Manas Score must be greater than zero.")
        return v

    @classmethod
    def create(cls, service_finished_after_duetime_score: int, vehicle_capacity_score: int,
               minimize_travel_time_score: int, minimize_travel_distance_score: int):
        if service_finished_after_duetime_score < 1:
            raise ValueError("ServiceFinishedAfterDuetime Score must be greater than zero.")
        if vehicle_capacity_score < 1:
            raise ValueError("VehicleCapacity Score must be greater than zero.")
        if minimize_travel_time_score < 1:
            raise ValueError("MinimizeTravelTime Score must be greater than zero.")
        if minimize_travel_distance_score < 1:
            raise ValueError("MinimizeTravelDistance Score must be greater than zero.")

        return cls(
            service_finished_after_due_time=HardSoftScore.of(hard_score=service_finished_after_duetime_score,
                                                             soft_score=1),
            vehicle_capacity=HardSoftScore.of(hard_score=vehicle_capacity_score, soft_score=1),
            minimize_travel_time=HardSoftScore.of(hard_score=1, soft_score=minimize_travel_time_score),
            minimize_travel_distance=HardSoftScore.of(hard_score=1, soft_score=minimize_travel_distance_score)
        )
