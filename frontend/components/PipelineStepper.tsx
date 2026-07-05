"use client";

export type StageState = "idle" | "active" | "done";

export const STAGES = [
  { role: "Guionista", sub: "decide el evento del día y escribe el guion" },
  { role: "Director de Producción", sub: "arma el prompt de video · Wan / HappyHorse" },
  { role: "Control de Calidad", sub: "aprueba o pide regenerar" },
  { role: "Empaquetador", sub: "título, thumbnail y descripción" },
];

export function PipelineStepper({
  current,
  regens,
}: {
  current: number; // -1 idle, 0..3 active index, 4 = all done
  regens: number;
}) {
  return (
    <div className="panel">
      <h2>El estudio</h2>
      <p className="sub">4 agentes autónomos · un episodio de punta a punta</p>
      <div className="steps">
        {STAGES.map((s, i) => {
          const state: StageState =
            current > i ? "done" : current === i ? "active" : "idle";
          const icon = state === "done" ? "✓" : state === "active" ? "●" : "○";
          return (
            <div className="step" data-state={state} key={s.role}>
              <div className="num">{i + 1}</div>
              <div className="role">
                {s.role}
                <small>{s.sub}</small>
              </div>
              <div className="state">{icon}</div>
            </div>
          );
        })}
      </div>
      {regens > 0 && (
        <span className="regen-badge">
          ↻ QA pidió regenerar {regens} {regens === 1 ? "vez" : "veces"} — presupuesto protegido
        </span>
      )}
    </div>
  );
}
