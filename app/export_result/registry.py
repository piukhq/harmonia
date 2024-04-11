from app.export_result.agents.bases.base import BaseAgent
from app.registry import Registry

export_result_agents = Registry[BaseAgent]()
export_result_agents.add("stonegate", "app.export_result.agents.stonegate.Stonegate")
