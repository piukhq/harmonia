from app.registry import Registry

import_agents = Registry()
import_agents.add("acxetado", "app.imports.agents.aĉetado.AĉetadoAgent")
import_agents.add("kasisto", "app.imports.agents.kasisto.KasistoAgent")
