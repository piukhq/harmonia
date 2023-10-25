from app.registry import Registry
from app.streaming.agents.base import BaseStreamingAgent

streaming_agents = Registry[BaseStreamingAgent]()
streaming_agents.add("squaremeal", "app.streaming.agents.squaremeal.SquareMeal")
streaming_agents.add("bpl-viator", "app.streaming.agents.bpl.Bpl")
streaming_agents.add("bpl-trenette", "app.streaming.agents.bpl.Bpl")
streaming_agents.add("bpl-cortado", "app.streaming.agents.bpl.Bpl")
streaming_agents.add("the-works", "app.streaming.agents.the_works.TheWorks")
