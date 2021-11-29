from app.registry import Registry
from app.streaming.agents.base import BaseStreamingAgent

streaming_agents = Registry[BaseStreamingAgent]()
streaming_agents.add("squaremeal", "app.streaming.agents.squaremeal.SquareMeal")
