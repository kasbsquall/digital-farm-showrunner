# Pipeline LangGraph

Grafo real generado por LangGraph (`pipeline/orchestrator.py`). Las aristas
punteadas desde `qa` son la arista condicional: aprueba → `packager`; rechaza y
queda presupuesto → `director` (loop de regeneración, hasta `MAX_REGEN` veces).

```mermaid
graph TD;
	__start__([__start__]):::first
	scriptwriter(scriptwriter)
	director(director)
	video(video)
	qa(qa)
	packager(packager)
	__end__([__end__]):::last
	__start__ --> scriptwriter;
	scriptwriter --> director;
	director --> video;
	video --> qa;
	qa -.-> director;
	qa -.-> packager;
	packager --> __end__;
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```
