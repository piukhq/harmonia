from app.exports.agents import BaseAgent
from app.registry import Registry

export_agents = Registry[BaseAgent]()
export_agents.add("iceland-bonus-card", "app.exports.agents.iceland.Iceland")
export_agents.add("wasabi-club", "app.exports.agents.wasabi.Wasabi")
export_agents.add("bpl-trenette", "app.exports.agents.bpl.Trenette")
export_agents.add("squaremeal", "app.exports.agents.squaremeal.SquareMeal")
export_agents.add("bpl-viator", "app.exports.agents.bpl.Viator")
export_agents.add("bpl-cortado", "app.exports.agents.bpl.Cortado")
export_agents.add("costa", "app.exports.agents.costa.Costa")
export_agents.add("the-works", "app.exports.agents.the_works.TheWorks")
export_agents.add("itsu", "app.exports.agents.itsu.Itsu")
export_agents.add("slim-chickens", "app.exports.agents.slim_chickens.SlimChickens")
export_agents.add("stonegate", "app.exports.agents.stonegate.Stonegate")
