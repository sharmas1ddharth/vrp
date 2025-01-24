"""
Solver Analysis Data Transfer Objects (DTOs)

This module defines data transfer objects (DTOs) used for analyzing the results of vehicle routing solver runs.
It includes classes to represent individual matches and constraint analyses, and ensures that scores
are properly serialized and deserialized.

Classes:
---------
- **MatchAnalysisDTO**: Contains information about a single match within the optimization process.
- **ConstraintAnalysisDTO**: Aggregates multiple match analyses and provides overall score and weight information for a specific constraint.

Serialization:
---------------
Fields that use `HardSoftScore` are serialized with the `ScoreSerializer`, ensuring compatibility with JSON serialization.
This is particularly useful for transferring data between systems or storing results for later analysis.
"""

from dataclasses import dataclass
from typing import Annotated

from src.json_serialization import *


@dataclass
class MatchAnalysisDTO:
    """
    Data Transfer Object (DTO) for representing the analysis of a single match in the vehicle routing problem.

    Attributes:
    -----------
    """
    name: str
    """The name of the match or scenario being analyzed."""

    score: Annotated[HardSoftScore, ScoreSerializer]
    """The score of the match, serialized using `ScoreSerializer` to convert the score into a JSON-compatible format."""

    justification: object
    """A general object that justifies or explains the reason behind the score or result for this match.
    This could include details such as violated constraints, customer demands, or vehicle capacities."""


@dataclass
class ConstraintAnalysisDTO:
    """
    Data Transfer Object (DTO) for representing the analysis of a constraint within the optimization problem.
    This class aggregates multiple match analyses and provides overall score and weight information.

    Attributes:
    -----------
    """
    name: str
    """The name of the constraint being analyzed (e.g., "vehicle capacity", "delivery time windows")."""
    weight: Annotated[HardSoftScore, ScoreSerializer]
    """The weight or importance of this constraint in the optimization problem, serialized using `ScoreSerializer`."""
    matches: list[MatchAnalysisDTO]
    """A list of `MatchAnalysisDTO` objects, each representing the analysis of a specific match related to this constraint."""
    score: Annotated[HardSoftScore, ScoreSerializer]
    """The overall score of this constraint, serialized using `ScoreSerializer`, representing how well the constraint was respected
    or violated across all matches."""
