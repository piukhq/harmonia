from app.exports.agents import BaseAgent
from app.registry import Registry

export_agents = Registry[BaseAgent]()
export_agents.add("harvey-nichols", "app.exports.agents.harvey_nichols.HarveyNichols")
export_agents.add("cooperative", "app.exports.agents.cooperative.Cooperative")
export_agents.add("iceland-bonus-card", "app.exports.agents.iceland.Iceland")
export_agents.add("burger-king-rewards", "app.exports.agents.burger_king.BurgerKing")
export_agents.add("fatface", "app.exports.agents.fatface.FatFace")
export_agents.add("whsmith-rewards", "app.exports.agents.whsmith.WhSmith")
export_agents.add("wasabi-club", "app.exports.agents.wasabi.Wasabi")
export_agents.add("bpl-trenette", "app.exports.agents.trenette.Trenette")
export_agents.add("squaremeal", "app.exports.agents.squaremeal.SquareMeal")
