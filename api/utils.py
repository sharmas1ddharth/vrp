"""
API Utilities files
"""
import requests

def get_distance_duration_matrix_from_osrm(location_string):
    """
    Retrieve distance and duration matrices from the OSRM API.

    This function sends a GET request to the OSRM (Open Source Routing Machine) API to
    obtain the distance and duration matrices for the specified locations. The input
    is a string of comma-separated coordinates, and the function returns the durations
    and distances in matrix format if the request is successful.

    :param location_string: A string containing comma-separated latitude and longitude
                            pairs representing the locations for which to retrieve the
                            distance and duration matrices.
    :type location_string: str
    :return: A tuple containing two lists: the first list represents the duration matrix,
                and the second list represents the distance matrix. Both are in the format
                of lists of lists of floats. If an error occurs during the request,
                both values will be None.
    :rtype: tuple[list[list[float]], list[list[float]] | None]
    """
    url = f"http://20.40.51.151:5000/table/v1/driving/{location_string}?annotations=distance,duration"
    querystring = {"annotations": "distance,duration"}

    headers = {"Content-Type": "application/json", "User-Agent": "insomnia/8.6.0"}
    try:
        response = requests.request("GET", url, headers=headers, params=querystring, timeout=2)
        response.raise_for_status()
        durations = response.json().get('durations', None)
        distances = response.json().get('distances', None)
        return durations, distances
    except requests.Timeout:
        return None, None
    except requests.RequestException:
        return None, None
