from .model import Model
from pathlib import Path
from .solver import Solver

if __name__ == "__main__":
    parent = Path(__file__).parent
    model = Model.from_json(parent / "../examples/one.json")
    solver = Solver(model)

    timetable = solver.solve()
    output = parent / "solution/one.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    timetable.write_csv(output)
