"""
Route Planning Module

This module provides functionalities for handling vehicle route planning,
including the creation, analysis, and management of route plans. It integrates
with an external routing service (OSRM) to calculate distances and durations
between various locations. The module is designed to facilitate the solving
of vehicle routing problems using constraints and optimization techniques.

Key Features:
- Define and manage vehicle route plans with associated constraints.
- Analyze route plans to evaluate compliance with defined constraints.
- Communicate with the OSRM API to retrieve distance and duration matrices.
- Support for adding, updating, and deleting route plans dynamically.

Endpoints:
- `POST /route-plans`: Initiate the solving process for a new route plan.
- `PUT /route-plans/analyze`: Analyze an existing route plan for constraints.
- `DELETE /route-plans/{problem_id}`: Stop the solving process for a specific route plan.
- `POST /clear`: Clear all datasets used for route planning.
- `GET /route-plans/{problem_id}/status`: Retrieve the status of a specific route plan.
- `GET /route-plans/{problem_id}`: Get the details of a specific route plan.

Exception Handling:
The module includes error handling for requests to the OSRM API to manage timeouts
and other request-related exceptions gracefully.

Usage:
This module can be imported into a FastAPI application, allowing for the
development of a comprehensive route planning API service.

"""
import uuid
from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, Request
from fastapi.responses import PlainTextResponse
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from timefold.solver import ProblemChange, ProblemChangeDirector

# from api.utils import get_distance_duration_matrix_from_osrm
from src.domain.customer_vehicle import Customer, Depot
from src.domain.location import Location
from src.domain.route_plan import VehicleRoutePlan
from src.enums import StaticValues
from src.score_analysis import ConstraintAnalysisDTO, MatchAnalysisDTO
from src.solver import solver
from test import Solution

# logging.basicConfig(level=logging.INFO)
import math
import logfire

logfire.configure(console=False)
logfire.install_auto_tracing(modules=['app'], min_duration=0.01)

app = FastAPI(docs_url="/api/docs",openapi_url="/api")
logfire.instrument_fastapi(app)
# init_router(app)
data_sets: dict[str, VehicleRoutePlan] = {}


@app.get("/route-plans/{problem_id}/status", response_model_exclude_none=True)
async def get_status(problem_id: str) -> dict:
    """
    Retrieve the status of a route plan by problem ID.

    This endpoint checks if a route plan associated with the given `problem_id` exists in the
    system and returns its current solver status. If no route plan is found, an error message
    is returned.

    :param problem_id: The unique identifier of the route plan problem.
    :type problem_id: str
    :return: A dictionary containing the job ID and message if the route plan is not found, or
                the solver status if it exists.
    :rtype: dict
    """
    if problem_id not in data_sets:
        return {"jobId": problem_id, "message": "No route plan found."}
    return {"solverStatus": "NOT SOLVING" if solver.is_solving() is False else "SOLVING"}


def update_vehicles_departure_and_arrival_time(response):
    vehicles = response['vehicles']
    for i in range(1, len(vehicles)):
        time_diff = vehicles[i]["arrival_time"] - vehicles[i]["departureTime"]
        vehicles[i]["departureTime"] = vehicles[i - 1]["arrival_time"] + timedelta(seconds=60)
        vehicles[i]["arrival_time"] = vehicles[i]["departureTime"] + time_diff

    response['vehicles'] = vehicles
    return response


@app.get("/route-plans/{problem_id}", response_model_exclude_none=True)
async def get_route(problem_id: str) -> dict:
    """
    Retrieve the route plan by problem ID.

    This endpoint retrieves the route plan for the specified `problem_id`. If the route plan
    is not found, an error message is returned. The route plan data is processed to update field
    names for consistency, and various nested attributes such as vehicle and customer data
    are also adjusted accordingly.

    The fields `total_driving_time_seconds`, `total_driving_distance_meters`, and `total_fuel_liter`
    are renamed to match the required format. Similar changes are applied to the vehicle and customer
    data.

    :param problem_id: The unique identifier of the route plan problem.
    :type problem_id: str
    :return: A dictionary containing the processed route plan data including vehicle and customer
                information, or an error message if the route plan is not found.
    :rtype: dict
    """
    if problem_id not in data_sets:
        return {"jobId": problem_id, "message": "No route plan found."}

    route = data_sets[problem_id]
    # print(route)
    route_dict = route.dict(exclude={"constraint_configuration"})

    route_dict.update({"solverStatus": "NOT SOLVING" if solver.is_solving() is False else "SOLVING"})
    route_dict["totalDrivingTimeSeconds"] = route_dict.pop("total_driving_time_seconds")
    route_dict["totalDrivingDistanceMeters"] = route_dict.pop(
        "total_driving_distance_meters"
    )
    route_dict["totalFuelLiter"] = route_dict.pop("total_fuel_liter")

    # for vehicle in route_dict["vehicles"]:
    #     if len(vehicle.get('customers')) == 1:
    #         customer = vehicle.get('customers')[0]
    #         for cust in route_dict['customers']:
    #             if cust.get('id') == customer:
    #                 cust['drivingTimeSecondsToDepot'] = cust['drivingTimeSecondsFromPreviousStandstill'] + 600 #cust['serviceDuration']


    for vehicle in route_dict["vehicles"]:
        vehicle["vehicle_id"] = vehicle.pop("vehicle_id")
        vehicle["vehicleType"] = vehicle.pop("vehicleType")
        vehicle["vehicleNo"] = vehicle.pop("vehicleNo")
        vehicle["departureTime"] = vehicle.pop("departure_time")
        vehicle["totalDemand"] = vehicle.pop("total_demand")
        vehicle["totalDrivingTimeSeconds"] = vehicle.pop("total_driving_time_seconds")
        vehicle["totalDrivingDistanceMeters"] = vehicle.pop(
            "total_driving_distance_meters"
        )
        vehicle["totalFuelLitre"] = vehicle.pop("total_fuel_litre")
        vehicle["depot"] = vehicle["depot"]["id"]
        vehicle["pitStopTime"] = StaticValues.pit_stop_time.value * len(vehicle['customers'])

    for customer in route_dict["customers"]:
        customer["readyTime"] = customer.pop("ready_time")
        customer["dueTime"] = customer.pop("due_time")
        customer["serviceDuration"] = customer.pop("service_duration")
        customer["previousCustomer"] = customer.pop("previous_customer")
        customer["nextCustomer"] = customer.pop("next_customer")
        customer["arrivalTime"] = customer.pop("arrival_time")
        customer["pitStopTime"] = StaticValues.pit_stop_time.value

    # route_dict = remove_customers_if_going_after_end_time(route_dict)
    route_dict = update_vehicles_departure_and_arrival_time(route_dict)
    # logfire.info(str(route_dict), response="RESPONSE")
    return route_dict

def remove_customers_if_going_after_end_time(route):
    customer_to_drop = []

    for customer in route['customers']:
        if customer['arrivalTime'] > route['endDateTime']:
            customer_to_drop.append(customer.get('id'))


    for vehicle in route.get('vehicles'):
        customers_to_remove_indices = []
        time_to_deduct = 0


        for idx, customer_id in enumerate(vehicle.get('customers')):
            if customer_id in customer_to_drop:
                customers_to_remove_indices.append(idx)

                for customer in route['customers']:
                    if customer['id'] == customer_id:
                        time_to_deduct += customer['drivingTimeSecondsFromPreviousStandstill']


        for idx in sorted(customers_to_remove_indices, reverse=True):
            vehicle['customers'].pop(idx)
            vehicle['route'].pop(idx)


        vehicle['arrival_time'] -= timedelta(seconds=time_to_deduct)
        vehicle['totalDrivingTimeSeconds'] -= time_to_deduct
        return route


def update_route(problem_id: str, route: VehicleRoutePlan) -> None:
    """
    Update the route plan for a given problem ID.

    This function updates the route plan associated with the provided `problem_id`
    in the global `data_sets` dictionary. If the route plan exists, it will be
    overwritten with the new `route`.

    :param problem_id: The unique identifier of the route plan problem.
    :type problem_id: str
    :param route: The updated route plan to be associated with the problem ID.
    :type route: VehicleRoutePlan
    :return: None
    :rtype: None
    """
    global data_sets
    data_sets[problem_id] = route


def get_location(id: str, depot_data: list) -> Optional[tuple[str, list]]:
    """
    Retrieve the location for a given depot ID.

    This function searches through the `depot_data` list to find the depot that
    matches the given `id`. If a match is found, it returns a tuple containing the
    depot ID and its associated location data. If no match is found, it returns `None`.

    :param id: The unique identifier of the depot.
    :type id: str
    :param depot_data: A list of dictionaries, where each dictionary contains
                        depot information, including the depot's ID and location.
    :type depot_data: list
    :return: A tuple containing the depot ID and location if found, or `None` if
                no match is found.
    :rtype: Optional[tuple[str, list]]
    """
    for i in depot_data:
        if str(i["id"]) == str(id):
            return id, i.get("location")


def convert_to_datetime_object(datetime_string: str) -> datetime | str:
    """
    Convert an ISO 8601 formatted string to a `datetime` object.

    This function attempts to convert a given ISO 8601 `datetime_string` into a
    Python `datetime` object. If the conversion fails (e.g., due to a `TypeError`),
    it returns the original string.

    The function handles time zone information by replacing the "Z" (representing
    UTC) with `+00:00` before conversion.

    :param datetime_string: The ISO 8601 formatted datetime string to be converted.
    :type datetime_string: str
    :return: A `datetime` object if conversion is successful, otherwise the original string.
    :rtype: datetime | str
    """
    try:
        datetime_obj = datetime.fromisoformat(datetime_string.replace("Z", "+00:00"))
        return datetime_obj
    except TypeError:
        return datetime_string


def convert_to_depot_object(vehicle, depot_data) -> dict:
    """
    Convert the depot ID in a vehicle dictionary to a `Depot` object.

    This function replaces the depot ID in the given `vehicle` dictionary with
    a `Depot` object. The `Depot` object is created by retrieving the depot's
    location from the `depot_data` list using the depot ID from the `vehicle`.

    :param vehicle: A dictionary containing vehicle information, including a depot ID.
    :type vehicle: dict
    :param depot_data: A list of dictionaries containing depot information,
                        including depot IDs and locations.
    :type depot_data: list
    :return: The updated vehicle dictionary with the depot ID replaced by a `Depot` object.
    :rtype: dict
    """
    _id, location = get_location(vehicle["depot"], depot_data=depot_data)
    depot = Depot(id=str(_id), location=location)
    vehicle["depot"] = depot
    return vehicle


def convert_customer_datetime_format(customers) -> Optional[list]:
    """
    Convert date and time fields in a list of customers to appropriate `datetime` or `timedelta` objects.

    This function iterates over a list of customer dictionaries and converts specific
    date and time fields (`readyTime`, `dueTime`, and optionally `bookingDate`) to `datetime`
    objects using the `convert_to_datetime_object` function. It also converts the
    `serviceDuration` field to a `timedelta` object.

    If a `TypeError` occurs during iteration or conversion, the function will return `None`.

    :param customers: A list of dictionaries, where each dictionary represents a customer
                        and contains the fields `readyTime`, `dueTime`, `bookingDate` (optional),
                        and `serviceDuration`.
    :type customers: list
    :return: The updated list of customers with date and time fields converted, or `None` if
                an error occurs.
    :rtype: Optional[list]
    """
    try:
        for customer in customers:
            customer["readyTime"] = convert_to_datetime_object(customer["readyTime"])
            customer["dueTime"] = convert_to_datetime_object(customer["dueTime"])
            if customer.get("bookingDate", None) is not None:
                customer["bookingDate"] = convert_to_datetime_object(
                    customer["bookingDate"]
                )
            try:
                customer["serviceDuration"] = timedelta(
                    seconds=600#customer["serviceDuration"]
                )
            except TypeError:
                pass
        return customers
    except TypeError:
        return None


def convert_vehicle_datetime_format(vehicles) -> list:
    """
    Convert the departure time field in a list of vehicles to `datetime` objects.

    This function iterates over a list of vehicle dictionaries and converts the
    `departureTime` field of each vehicle to a `datetime` object using the
    `convert_to_datetime_object` function.

    :param vehicles: A list of dictionaries, where each dictionary represents a vehicle
                        and contains a `departureTime` field.
    :type vehicles: list
    :return: The updated list of vehicles with `departureTime` fields converted to `datetime` objects.
    :rtype: list
    """
    for vehicle in vehicles:
        vehicle["departureTime"] = convert_to_datetime_object(vehicle["departureTime"])
    return vehicles


def convert_json_to_acceptable_format(json_data: dict) -> dict:
    """
    Convert date and time fields in a JSON object to appropriate formats.

    This function processes a JSON dictionary by converting various fields to
    `datetime` objects or other appropriate formats. Specifically, it:

    - Converts the `departureTime` for all vehicles using `convert_vehicle_datetime_format`.
    - Converts the `readyTime`, `dueTime`, `bookingDate`, and `serviceDuration` for all
        customers using `convert_customer_datetime_format`.
    - Converts the overall `startDateTime` and `endDateTime` fields to `datetime` objects.

    :param json_data: A dictionary containing route plan data with vehicles, customers,
                        and start/end date-time fields.
    :type json_data: dict
    :return: The updated JSON dictionary with properly formatted date and time fields.
    :rtype: dict
    """
    json_data["vehicles"] = convert_vehicle_datetime_format(json_data["vehicles"])
    json_data["customers"] = convert_customer_datetime_format(json_data["customers"])
    json_data["startDateTime"] = convert_to_datetime_object(json_data["startDateTime"])
    json_data["endDateTime"] = convert_to_datetime_object(json_data["endDateTime"])
    return json_data


def mark_extra_locations(locations: list, num_extra: int) -> list:
    """
    Mark the last `num_extra` locations in the list as extra.

    This function updates a list of location dictionaries by adding or modifying an
    `isExtra` field. It sets the `isExtra` field to `True` for the last `num_extra`
    locations and `False` for all other locations. If `num_extra` exceeds the total
    number of locations, it is capped to the length of the locations list.

    :param locations: A list of dictionaries where each dictionary represents a location.
    :type locations: list
    :param num_extra: The number of locations at the end of the list to mark as extra.
    :type num_extra: int
    :return: The updated list of locations with the `isExtra` field marked appropriately.
    :rtype: list
    """
    # Ensure num_extra does not exceed the length of locations
    num_extra = min(num_extra, len(locations))

    # Set isExtra to False for all locations initially
    for location in locations:
        location["isExtra"] = False

    # Mark the last `num_extra` locations as True
    for i in range(len(locations) - num_extra, len(locations)):
        locations[i]["isExtra"] = True

    return locations


def create_location_string_for_distance_and_duration_matrix(json_data: dict) -> str:
    """
    Generate a location string for constructing distance and duration matrices.

    This function extracts the locations from depots and customers in the provided
    `json_data` and formats them into a string suitable for use in calculating
    distance and duration matrices. Depot locations are repeated for each vehicle,
    and all locations are formatted as "latitude,longitude". The locations are
    then joined into a single string with a semicolon (`;`) delimiter.

    :param json_data: A dictionary containing depot and customer data with locations.
                        The depots and customers must have `location` fields in the format
                        `[latitude, longitude]`.
    :type json_data: dict
    :return: A semicolon-separated string of locations in "latitude,longitude" format.
    :rtype: str
    """
    locations = []
    locations.extend(
        [
            f"{depot['location'][0]},{depot['location'][1]}"
            for depot in json_data["depots"]
            for _ in range(len(json_data["vehicles"]))
        ]
    )
    locations.extend(
        [
            f"{customer['location'][0]},{customer['location'][1]}"
            for customer in json_data["customers"]
        ]
    )
    return ";".join(locations)

def increase_vehicle_capacity_as_per_extra_location(input_data: dict) -> tuple[dict, int]:
    """
    Adjust vehicle capacities based on the number of extra locations.

    This function increases the capacity of vehicles in the `input_data` if the
    total capacity of all vehicles is less than the number of extra locations
    (`extraLocationCount`). It evenly distributes the additional capacity needed
    across all vehicles. If the current total capacity is sufficient, no changes
    are made.

    :param input_data: A dictionary containing the vehicle data and the number of
                        extra locations (`extraLocationCount`). Each vehicle should
                        have a `capacity` field.
    :type input_data: dict
    :return: A tuple containing the updated `input_data` and the number of extra locations.
    :rtype: tuple[dict, int]
    """
    extra_location_count = input_data.get(
        "extraLocationCount", 0
    )  # Get the number of extra locations

    # Total number of locations is only the extra locations, not all customers + extra locations
    if extra_location_count > 0:
        total_vehicle_capacity = 0
        vehicles = input_data.get("vehicles", [])

        # Calculate total vehicle capacity
        for vehicle in vehicles:
            total_vehicle_capacity += vehicle.get("capacity", 0)

        # Check if total capacity is less than the number of extra locations
        if total_vehicle_capacity < extra_location_count:
            extra_capacity_needed = extra_location_count - total_vehicle_capacity
            number_of_vehicles = len(vehicles)

            # Calculate the additional capacity needed per vehicle
            if number_of_vehicles > 0:
                additional_capacity_per_vehicle = (
                    extra_capacity_needed / number_of_vehicles
                )

                # Increase each vehicle's capacity equally to accommodate only the extra locations
                for vehicle in vehicles:
                    current_capacity = vehicle.get("capacity", 0)
                    vehicle["capacity"] = (
                        current_capacity + additional_capacity_per_vehicle
                    )
    return input_data, extra_location_count

def increase_vehicle_capacity_unit(json: dict) -> dict:

    for vehicle in json.get('vehicles', {}):
        if 'capacity' in vehicle.keys():
            try:
                if vehicle["additionalCapacityUnit"] == "percent":
                    vehicle["capacity"] += math.ceil(int(vehicle["capacity"] * (10/100)))
                elif vehicle["additionalCapacityUnit"] == "number":
                    vehicle["capacity"] += int(vehicle["additionalCapacityValue"])
            except:
                vehicle["capacity"] += int(math.ceil(vehicle["capacity"] * (10/100)))
        elif 'volumeCapacity' in vehicle.keys():
            vehicle['capacity'] = vehicle.get('volumeCapacity')
            try:
                if vehicle["additionalCapacityUnit"] == "percent":
                    vehicle["capacity"] += math.ceil(int(vehicle["capacity"] * (10/100)))
                elif vehicle["additionalCapacityUnit"] == "number":
                    vehicle["capacity"] += int(vehicle["additionalCapacityValue"])
            except:
                vehicle["capacity"] += int(math.ceil(vehicle["capacity"] * (10/100)))
        elif 'numberCapacity' in vehicle.keys():
            vehicle['capacity'] = vehicle.get('numberCapacity')
            try:
                if vehicle["additionalCapacityUnit"] == "percent":
                    vehicle["capacity"] += math.ceil(int(vehicle["capacity"] * (10/100)))
                elif vehicle["additionalCapacityUnit"] == "number":
                    vehicle["capacity"] += int(vehicle["additionalCapacityValue"])
            except:
                vehicle["capacity"] += int(math.ceil(vehicle["capacity"] * (10/100)))
    return json

def create_matrix_according_to_vehicle_count(matrix: dict, key: str, number_of_vehicles: int) -> dict:
    # Insert the first item of each sublist at the first index
    for sublist in matrix[key]:
        first_item = sublist[0]
        for _ in range(number_of_vehicles - 1):  # Insert 3 times
            sublist.insert(0, first_item)

    # Insert the depot matrix at the start
    depot_matrix = matrix[key][0]
    for _ in range(number_of_vehicles - 1):
        matrix[key].insert(0, depot_matrix)

    return matrix

def increase_durations_by_percentage(duration_response: dict) -> dict:
    try:
        rows = []
        for row in duration_response['durationResponse']["durations"]:
            cols = []
            for i in row:
                if i != 0:
                    cols.append(round(i + (i * 0.8), 1))
                else:
                    cols.append(i)
            rows.append(cols)
        duration_response['durationResponse']["durations"] = rows
        return duration_response
    except Exception as e:
        # logfire.info(e)
        return duration_response

def modify_duration_matrix(json: dict) -> dict:
    for i in range(len(json['durationResponse']['durations'])):
        for j in range(len(json['durationResponse']['durations'][i])):
            if json['durationResponse']['durations'][i][j] < 60 and json['durationResponse']['durations'][i][j] != 0:
                json['durationResponse']['durations'][i][j] = 60.0
    return json

def json_to_vehicle_route_plan(json: dict) -> VehicleRoutePlan:
    """
    Convert a JSON dictionary into a `VehicleRoutePlan` object.

    This function processes the input JSON to extract and format route plan data for
    vehicles and customers. It:

    - Generates a location string for calculating distance and duration matrices.
    - Retrieves the distance and duration matrices from an OSRM service.
    - Converts the JSON fields to proper datetime and object formats.
    - Adjusts vehicle capacities to accommodate extra locations, if necessary.
    - Converts customer and vehicle data into model objects, including assigning depots to vehicles.
    - Marks extra locations among the customers.
    - Validates the final route plan with `VehicleRoutePlan`.

    :param json: A dictionary containing route plan information, including depots, vehicles,
                    and customers.
    :type json: dict
    :return: A `VehicleRoutePlan` object representing the validated vehicle route plan.
    :rtype: VehicleRoutePlan
    """
    # location_string = create_location_string_for_distance_and_duration_matrix(json_data=json)
    # durations, distances = get_distance_duration_matrix_from_osrm(location_string)
    # if durations is not None and distances is not None:
    try:
        json['durationResponse']['durations'] = [[round(value) for value in row] for row in json.get('durationResponse', {}).get('durations')]
    except Exception as e:
        json['durationResponse']['durations'] = json.get('durationResponse', {}).get('durations')
    json['durationResponse']['distances'] = json.get('durationResponse', {}).get('distances')
    json = modify_duration_matrix(json)
    number_of_vehicles = len(json.get('vehicles', {}))
    json['durationResponse'] = create_matrix_according_to_vehicle_count(json['durationResponse'], 'durations', number_of_vehicles)
    json['durationResponse'] = create_matrix_according_to_vehicle_count(json['durationResponse'], 'distances', number_of_vehicles)
    # logfire.info(f"before: {str(json)}")
    json = increase_durations_by_percentage(json)
    # logfire.info(str(json))
    json = convert_json_to_acceptable_format(json)
    extra_location_count = 0
    json = increase_vehicle_capacity_unit(json)
    depot_data = json.get("depots", [])

    customers = {customer["id"]: customer for customer in json.get("customers", [])}
    vehicles = {
        vehicle["id"]: convert_to_depot_object(vehicle, depot_data)
        for vehicle in json.get("vehicles", [])
    }
    for customer in customers.values():
        if "vehicle" in customer:
            del customer["vehicle"]

        if "previousVisit" in customer:
            del customer["previousVisit"]

        if "nextVisit" in customer:
            del customer["nextVisit"]

    json["customers"] = mark_extra_locations(
        json.get("customers", []), extra_location_count
    )

    customers = {
        customer_id: Customer.model_validate(customers[customer_id])
        for customer_id in customers
    }
    json["customers"] = list(customers.values())

    for vehicle in vehicles.values():
        vehicle["customers"] = [
            customers[customer_id] for customer_id in vehicle["customers"]
        ]

    json["vehicles"] = list(vehicles.values())

    return VehicleRoutePlan.model_validate(
        json, context={"customers": customers, "vehicles": vehicles}
    )


def convert_id_to_string(data) -> dict:
    """
    Convert 'id' fields in a dictionary to strings recursively.

    This function takes an input dictionary (or any nested structure) and converts
    the value of any key named "id" to a string. If the input is a dictionary,
    it applies the conversion recursively to all nested dictionaries. Non-dictionary
    elements are returned unchanged.

    :param data: The input data, which can be a dictionary or a nested structure
                    containing dictionaries.
    :type data: dict
    :return: A new dictionary with 'id' fields converted to strings, while other
                elements remain unchanged.
    :rtype: dict
    """
    try:
        for depot in data.get('depots', {}):
            depot['id'] = str(depot.get('id'))

        for vehicle in data.get('vehicles', {}):
            vehicle['id'] = str(vehicle.get('id'))

        for customer in data.get('customers', {}):
            customer['id'] = str(customer.get('id'))

        return data
    except:
        return data

async def setup_context(request: Request) -> VehicleRoutePlan:
    """
    Set up the context for vehicle routing by processing the request data.

    This asynchronous function retrieves JSON input from the provided request,
    converts all 'id' fields to strings, and transforms the input data into a
    `VehicleRoutePlan` object. It is typically used in the context of handling
    routing requests in a web application.

    :param request: The HTTP request object containing the input data in JSON format.
    :type request: Request
    :return: A `VehicleRoutePlan` object created from the input data.
    :rtype: VehicleRoutePlan
    """
    input_data = await request.json()
    # logfire.info(input_data)
    input_data = convert_id_to_string(input_data)
    return json_to_vehicle_route_plan(input_data)

def update_location_matrix(location: Location, new_location: Location) -> None:
    location.driving_distance_meters_map[new_location] = 21544
    location.driving_time_seconds_map[new_location] = 1653
    new_location.driving_distance_meters_map[location] = 21543
    new_location.driving_time_seconds_map[location] = 1652

class AddCustomer(ProblemChange[VehicleRoutePlan]):
    customer: Customer
    def __init__(self, customer: Customer):
        self.customer = customer

    def do_change(self, working_solution: VehicleRoutePlan, problem_change_director: ProblemChangeDirector) -> None:
        problem_change_director.add_entity(self.customer, lambda working_entity: working_solution.customers.append(working_entity))
        for customer in working_solution.customers:
            problem_change_director.change_problem_property(customer,
                lambda working_location: update_location_matrix(working_location.location, self.customer.location))
            for vehicle in working_solution.vehicles:
                problem_change_director.change_problem_property(vehicle,
                    lambda working_depot: update_location_matrix(working_depot.depot.location, self.customer.location))
        problem_change_director.add_problem_fact(self.customer.location, lambda new_location: working_solution.customers.append(self.customer))


@app.post("/route-plans", response_class=PlainTextResponse)
async def solve_route(
    route: Annotated[VehicleRoutePlan, Depends(setup_context)],
) -> str:
    """
    Initiate the vehicle routing solution process.

    This asynchronous function accepts a `VehicleRoutePlan` object as input and
    starts the route-solving process. A unique solver ID is generated for each
    request, and the route plan is stored in a global dataset. The solver manager
    then begins solving the routing problem, and updates the route with each new
    solution received.

    :param route: The vehicle route plan to be solved, provided by the
                    `setup_context` dependency.
    :type route: VehicleRoutePlan
    :return: A unique identifier for the solver process.
    :rtype: str
    """
    solver_id = str(uuid.uuid4())
    # logfire.info(solver_id, solverId="solver id")
    data_sets[solver_id] = route
    # solution = solver_manager.solve_and_listen(
    #     solver_id, route, lambda solution: update_route(solver_id, solution)
    # )
    solution = solver.solve(route)
    print(solver.is_solving(), "status")
    print(solution.json())
    update_route(solver_id, solution)
    import datetime
    cust = Customer(id=100,
        location=Location(latitude=12.9716, longitude=77.5946, id="6"),
        ready_time=datetime.datetime(2022, 1, 1, 0, 0, tzinfo=datetime.timezone.utc), due_time=datetime.datetime(2022, 1, 1, 20, 0, tzinfo=datetime.timezone.utc),
        service_duration=timedelta(seconds=600), demand=1, vehicle=None, previous_customer=None, next_customer=None, arrival_time=None)
    solver_manager.add_problem_change(solver_id, AddCustomer(cust))
    return solver_id
    return solver_id


@app.put("/route-plans/analyze")
async def analyze_route(
    route: Annotated[VehicleRoutePlan, Depends(setup_context)],
) -> dict["str", list[ConstraintAnalysisDTO]]:
    """
    Analyze the given vehicle route plan for constraint compliance.

    This asynchronous function analyzes the provided `VehicleRoutePlan` to evaluate
    how well it complies with defined constraints. It retrieves constraint analyses
    from the `solution_manager`, returning a structured response that includes
    the names, weights, scores, and matching details for each constraint.

    :param route: The vehicle route plan to be analyzed, provided by the
                    `setup_context` dependency.
    :type route: VehicleRoutePlan
    :return: A dictionary containing the constraint analyses, where each constraint
                includes its name, weight, score, and matching details.
    :rtype: dict[str, list[ConstraintAnalysisDTO]]
    """
    return {
        "constraints": [
            ConstraintAnalysisDTO(
                name=constraint.constraint_name,
                weight=constraint.weight,
                score=constraint.score,
                matches=[
                    MatchAnalysisDTO(
                        name=match.constraint_ref.constraint_name,
                        score=match.score,
                        justification=match.justification,
                    )
                    for match in constraint.matches
                ],
            )
            for constraint in solution_manager.analyze(route).constraint_analyses
        ]
    }


@app.delete("/route-plans/{problem_id}")
async def stop_solving(problem_id: str) -> None:
    """
    Stop the solving process for a specific route plan.

    This asynchronous function terminates the solving process associated with the
    provided `problem_id`. It calls the solver manager's `terminate_early` method
    to halt any ongoing computations for the specified route plan.

    :param problem_id: The unique identifier for the route plan whose solving
                        process should be stopped.
    :type problem_id: str
    :return: None
    """
    solver_manager.terminate_early(problem_id)


@app.post("/clear")
async def clear_datasets() -> bool:
    """
    Clear all datasets used for route planning.

    This asynchronous function attempts to clear all entries in the global `data_sets`
    dictionary. It returns `True` if the operation is successful and `False` if
    an exception occurs during the clearing process.

    :return: A boolean indicating the success of the clearing operation.
    :rtype: bool
    """
    try:
        data_sets.clear()
        return True
    except Exception:
        return False
