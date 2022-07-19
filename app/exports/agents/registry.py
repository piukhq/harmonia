from app.exports.agents import BaseAgent
from app.registry import Registry

export_agents = Registry[BaseAgent]()
export_agents.add("harvey-nichols", "app.exports.agents.harvey_nichols.HarveyNichols")
export_agents.add("cooperative", "app.exports.agents.cooperative.Cooperative")
export_agents.add("iceland-bonus-card", "app.exports.agents.iceland.Iceland")
export_agents.add("wasabi-club", "app.exports.agents.wasabi.Wasabi")
export_agents.add("bpl-trenette", "app.exports.agents.bpl.Trenette")
export_agents.add("squaremeal", "app.exports.agents.squaremeal.SquareMeal")
export_agents.add("bpl-asos", "app.exports.agents.bpl.Asos")
export_agents.add("bpl-viator", "app.exports.agents.bpl.Viator")
export_agents.add("bpl-cortado", "app.exports.agents.bpl.Cortado")
