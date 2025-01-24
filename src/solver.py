"""
**Solver Configuration Module**

This module initializes the solver configuration, solver manager, and solution manager.
It sets up the necessary components to manage and solve vehicle routing plans effectively.

Key Components:

- **SolverConfig**: Configures the optimization solver with the specified solution class, entity classes, and termination conditions.
- **SolverManager**: Manages the lifecycle and execution of the solver.
- **SolutionManager**: Handles the results and analysis of the solutions produced by the solver.

Core Functionality:

1. **Solver Configuration**: The module defines a solver configuration that includes:

   - The solution class (`VehicleRoutePlan`) representing the overall routing solution.
   - Entity classes (`Vehicle` and `Customer`) that represent the components of the solution.
   - A score director factory configuration that specifies the constraints for the optimization problem.
   - Termination conditions that dictate when the solver should stop, based on time spent and feasibility of the best score.

2. **Constraint Definition**: The module imports and utilizes a function (`define_constraints`) to establish the rules and restrictions that the solver must adhere to while searching for optimal solutions.
:ivar
"""
from timefold.solver import SolutionManager, SolverManager, SolverFactory
from timefold.solver.config import (
    Duration,
    ScoreDirectorFactoryConfig,
    SolverConfig,
    TerminationConfig,
)

from src.constraints import define_constraints
from src.domain.customer_vehicle import Customer, Vehicle
from src.domain.route_plan import VehicleRoutePlan

solver_config = SolverConfig(
    solution_class=VehicleRoutePlan,
    entity_class_list=[Vehicle, Customer],
    score_director_factory_config=ScoreDirectorFactoryConfig(
        constraint_provider_function=define_constraints
    ),
    termination_config=TerminationConfig(
        spent_limit=Duration(seconds=30),
        best_score_feasible=True
    ),
)
"""
Configures the optimization solver with the specified solution class, entity classes, and termination conditions.
"""

# solver_manager = SolverManager.create(solver_config)
solver = SolverFactory.create(solver_config).build_solver()

"""
Manages the lifecycle and execution of the solver.
"""

# solution_manager = SolutionManager.create(solver_manager)
"""
Handles the results and analysis of the solutions produced by the solver.
"""
