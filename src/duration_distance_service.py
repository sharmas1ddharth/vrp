"""
Duration and Distance Services for Location Routing

This module provides utilities for managing the duration and distance matrices between a set of locations.
It includes classes and methods for updating locations with driving times and distances, based on
a response object (`DurationDistanceResponse`) that contains precomputed values.

Classes:
--------
- **DurationDistanceResponse**: Holds the duration and distance matrices between locations.
- **DurationDistanceService**: Provides static methods to update location objects with driving durations
  and distances using the data from `DurationDistanceResponse`.

"""

from typing import List

from src.domain.location import Location
from src.json_serialization import JsonDomainBase


class DurationDistanceResponse(JsonDomainBase):
    """
    Represents the response containing duration and distance matrices.

    This class holds the driving durations and distances between multiple locations in the form of matrices.
    The rows and columns represent the locations, and the values in the matrices represent the time in seconds
    and distance in meters between pairs of locations.

    Attributes:
    -----------
    """
    durations: List[List[float]]
    """A matrix representing the driving durations between locations in seconds."""

    distances: List[List[float]]
    """A matrix representing the driving distances between locations in meters."""

    def get_durations(self):
        """
        Returns the matrix of driving durations between locations.

        The durations are stored in a 2D list where each row corresponds to a location,
        and each element in the row corresponds to the duration to another location in seconds.

        Returns:
        --------
        List[List[float]]: A 2D list of driving durations in seconds.
        """
        return self.durations

    def get_distances(self):
        """
        Returns the matrix of driving distances between locations.

        The distances are stored in a 2D list where each row corresponds to a location,
        and each element in the row corresponds to the distance to another location in meters.

        Returns:
        --------
        List[List[float]]: A 2D list of driving distances in meters.
        """
        return self.distances


class DurationDistanceService(JsonDomainBase):
    """
    Provides services to update locations with driving durations and distances.

    This service contains static methods to update `Location` objects with driving time and distance matrices
    from a `DurationDistanceResponse` object. The methods map the distances and durations from the response
    to the locations by iterating through the locations and applying the values.

    Methods:
    --------
    update_locations_with_durations(locations: List[Location], duration_response: DurationDistanceResponse):
        Updates the driving time matrices for each location with values from the provided `DurationDistanceResponse`.

    update_locations_with_distance(locations: List[Location], duration_response: DurationDistanceResponse):
        Updates the driving distance matrices for each location with values from the provided `DurationDistanceResponse`.
    """
    @staticmethod
    def update_locations_with_durations(
        locations: List[Location], duration_response: DurationDistanceResponse
    ):
        """
        Updates the driving time matrices of each location with values from the provided duration response.

        This method iterates over the list of locations and updates each location's driving time matrix with
        the durations from the `DurationDistanceResponse` object. If a duration is not available, the method
        sets the value to 0 for that location pair.

        Parameters:
        -----------
        locations : List[Location]
            A list of `Location` objects whose driving time matrices will be updated.

        duration_response : DurationDistanceResponse
            A response object containing the driving durations between the locations.

        Returns:
        --------
        None
        """
        for i, location1 in enumerate(locations):
            driving_time_seconds_map = {}
            for j, location2 in enumerate(locations):
                if (
                    duration_response
                    and i < len(duration_response.get_durations())
                    and j < len(duration_response.get_durations()[i])
                ):
                    duration_value = duration_response.get_durations()[i][j]
                else:
                    duration_value = 0
                driving_time_seconds_map[location2] = duration_value
            location1.set_driving_time_matrix(driving_time_seconds_map)

    @staticmethod
    def update_locations_with_distance(
        locations: List[Location], duration_response: DurationDistanceResponse
    ):
        """
        Updates the driving distance matrices of each location with values from the provided distance response.

        This method iterates over the list of locations and updates each location's driving distance matrix
        with the distances from the `DurationDistanceResponse` object. If a distance is not available, the method
        sets the value to 0 for that location pair.

        Parameters:
        -----------
        locations : List[Location]
            A list of `Location` objects whose driving distance matrices will be updated.

        duration_response : DurationDistanceResponse
            A response object containing the driving distances between the locations.

        Returns:
        --------
        None
        """
        for i, location1 in enumerate(locations):
            driving_distance_meters_map = {}
            for j, location2 in enumerate(locations):
                if (
                    duration_response
                    and i < len(duration_response.get_distances())
                    and j < len(duration_response.get_distances()[i])
                ):
                    distance_value = duration_response.get_distances()[i][j]
                else:
                    distance_value = 0
                driving_distance_meters_map[location2] = distance_value
            location1.set_driving_distance_matrix(driving_distance_meters_map)
