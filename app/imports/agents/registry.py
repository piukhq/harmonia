from app.registry import Registry

import_agents = Registry()
import_agents.add("aĉetado", "app.imports.agents.aĉetado.AĉetadoAgent")
import_agents.add("kasisto", "app.imports.agents.kasisto.KasistoAgent")
