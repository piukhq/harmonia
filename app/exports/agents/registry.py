from app.registry import Registry
from app.exports.agents import BaseAgent

export_agents = Registry[BaseAgent]()
export_agents.add("bink-loyalty", "app.exports.agents.bink_loyalty.BinkLoyalty")
export_agents.add("harvey-nichols", "app.exports.agents.harvey_nichols.HarveyNichols")
export_agents.add("cooperative", "app.exports.agents.cooperative.Cooperative")
