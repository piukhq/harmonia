from app.registry import Registry

export_agents = Registry()
export_agents.add("acxetado", "app.exports.agents.aĉetado.AĉetadoAgent")
export_agents.add("batch-example", "app.exports.agents.batch_example.BatchExampleAgent")
