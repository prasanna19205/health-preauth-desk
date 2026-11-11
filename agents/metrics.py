
from collections import defaultdict
from time import perf_counter


class AgentMetrics:
    """Tracks execution metrics for individual agents."""

    def __init__(self):
        self.data = defaultdict(
            lambda: {
                "calls": 0,
                "successes": 0,
                "failures": 0,
                "total_time_seconds": 0.0,
            }
        )

    def record(self, agent_name, duration, success=True):
        metrics = self.data[agent_name]

        metrics["calls"] += 1
        metrics["total_time_seconds"] += duration

        if success:
            metrics["successes"] += 1
        else:
            metrics["failures"] += 1

    def get_metrics(self):
        result = {}

        for agent_name, metrics in self.data.items():
            calls = metrics["calls"]

            result[agent_name] = {
                **metrics,
                "average_time_seconds": (
                    metrics["total_time_seconds"] / calls
                    if calls else 0.0
                ),
            }

        return result


# Shared metrics instance
agent_metrics = AgentMetrics()
