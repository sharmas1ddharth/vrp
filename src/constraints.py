"""
Vehicle Routing Constraints Module

This module defines the constraints for solving vehicle routing problems using Timefold's `ConstraintFactory`.
The constraints are divided into two categories: **Hard Constraints** and **Soft Constraints**. Hard constraints must be satisfied,
while soft constraints represent optimization goals that should be minimized but can be violated.

Hard Constraints:
- **Vehicle Capacity**: Ensure that a vehicle's load does not exceed its capacity.
- **Service Finished After Max End Time**: Penalize when the service is finished after the customer's latest acceptable time.
- **Prioritize Older Dates**: Prioritize customers with older service requests.

Soft Constraints:
- **Minimize Travel Distance**: Minimize the total travel distance of all vehicles.
- **Minimize Travel Time**: Minimize the total travel time of all vehicles.

The `define_constraints` function acts as the main entry point for the constraint provider, integrating all constraints defined below.

Functions:
----------
- `define_constraints`: Provides the list of constraints used for vehicle routing.
- `vehicle_capacity`: Ensures that vehicle load does not exceed its capacity.
- `service_finished_after_max_end_time`: Penalizes when service is completed after the customer’s acceptable end time.
- `prioritize_older_dates`: Penalizes lower-priority customers in favor of older service requests.
- `minimize_travel_distance`: Minimizes the total travel distance for all vehicles.
- `minimize_travel_time`: Minimizes the total travel time for all vehicles.
"""

from timefold.solver.score import ConstraintFactory, HardMediumSoftScore, constraint_provider

from src.domain.customer_vehicle import Customer, Vehicle

VEHICLE_CAPACITY = "vehicleCapacity"
MINIMIZE_TRAVEL_TIME = "minimizeTravelTime"
SERVICE_FINISHED_AFTER_MAX_END_TIME = "serviceFinishedAfterMaxEndTime"
PRIORITIZE_OLDER_DATES = "prioritize_older_dates"
MINIMIZE_TRAVEL_DISTANCE = "minimizeTravelDistance"
UNASSIGNED_CUSTOMER = "UnassignedCustomer"


@constraint_provider
def define_constraints(factory: ConstraintFactory):
    return [
        # Hard constraints
        vehicle_capacity(factory),
        # service_finished_after_max_end_time(factory),
        # prioritize_older_dates(factory),
        # minimize_travel_distance(factory),
        # Soft constraints
        # minimize_travel_time(factory),
        unassigned_order(factory)
    ]


##############################################
# Hard constraints
##############################################


def vehicle_capacity(factory: ConstraintFactory):
    return (
        factory.for_each(Vehicle)
        .filter(lambda vehicle: vehicle.calculate_total_demand() > vehicle.capacity)
        .penalize(
            HardMediumSoftScore.of_hard(5),
            lambda vehicle: vehicle.calculate_total_demand() - vehicle.capacity,
        )
        .as_constraint(VEHICLE_CAPACITY)
    )


# def service_finished_after_max_end_time(factory: ConstraintFactory):
#     return (
#         factory.for_each(Customer)
#         .filter(lambda customer: customer.is_service_finished_after_due_time())
#         .penalize(
#             HardMediumSoftScore.of_hard(1),
#             lambda customer: customer.get_service_finished_delay_in_minutes(),
#         )
#         .as_constraint(SERVICE_FINISHED_AFTER_MAX_END_TIME)
#     )


# def prioritize_older_dates(factory: ConstraintFactory):
#     return (
#         factory.for_each(Customer)
#         .filter(lambda customer: customer.get_days_since_request() < customer.days)
#         .penalize(
#             HardMediumSoftScore.of_hard(1), lambda customer: customer.get_days_since_request()
#         )
#         .as_constraint(PRIORITIZE_OLDER_DATES)
#     )


# def minimize_travel_distance(factory: ConstraintFactory):
#     return (
#         factory.for_each(Vehicle)
#         .penalize(
#             HardMediumSoftScore.of_soft(5),
#             lambda vehicle: vehicle.calculate_total_driving_distance_meters(),
#         )
#         .as_constraint(MINIMIZE_TRAVEL_DISTANCE)
#     )


# def minimize_travel_time(factory: ConstraintFactory):
#     return (
#         factory.for_each(Vehicle)
#         .penalize(
#             HardMediumSoftScore.of_soft(1),
#             lambda vehicle: vehicle.calculate_total_driving_time_seconds(),
#         )
#         .as_constraint(MINIMIZE_TRAVEL_TIME)
#     )

def unassigned_order(constraint_factory: ConstraintFactory):
    return (constraint_factory.for_each_including_unassigned(Customer)
                                                  .filter(lambda customer: customer.vehicle is None)
                                                  .penalize(HardMediumSoftScore.ONE_MEDIUM)
                                                  .as_constraint(UNASSIGNED_CUSTOMER)
    )
