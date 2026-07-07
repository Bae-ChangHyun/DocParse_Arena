"use client";

import { useState } from "react";
import type { BatchRunDetail, BatchRunItem, OcrModel } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import ModelResult from "@/components/battle/ModelResult";
import { cn } from "@/lib/utils";
import { CheckCircle2, XCircle, Loader2, Clock } from "lucide-react";

interface ResultMatrixProps {
  run: BatchRunDetail;
  models: OcrModel[];
}

function statusIcon(status: string) {
  switch (status) {
    case "done":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case "error":
      return <XCircle className="h-4 w-4 text-destructive" />;
    case "running":
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
}

// ── Official scoreboard column definitions ──────────────────
type ScoreCol = { key: string; label: string; pct?: boolean; lowerBetter?: boolean };

const OLMOCR_COLS: ScoreCol[] = [
  { key: "overall", label: "Overall", pct: true },
  { key: "present", label: "Present", pct: true },
  { key: "absent", label: "Absent", pct: true },
  { key: "order", label: "Order", pct: true },
  { key: "table", label: "Table", pct: true },
  { key: "math", label: "Math", pct: true },
  { key: "baseline", label: "Baseline", pct: true },
];

const OMNI_COLS: ScoreCol[] = [
  { key: "overall_edit", label: "Overall edit", lowerBetter: true },
  { key: "text_edit", label: "Text edit", lowerBetter: true },
  { key: "formula_edit", label: "Formula edit", lowerBetter: true },
  { key: "formula_cdm", label: "Formula CDM", pct: true },
  { key: "table_teds", label: "Table TEDS", pct: true },
  { key: "table_edit", label: "Table edit", lowerBetter: true },
  { key: "reading_order_edit", label: "Reading order edit", lowerBetter: true },
];

function fmt(v: unknown, col: ScoreCol): string {
  if (typeof v !== "number") return "—";
  return col.pct ? `${(v * 100).toFixed(1)}%` : v.toFixed(3);
}

// Pull a metric value out of a per-model score object (shape differs by benchmark)
function scoreValue(modelScore: Record<string, unknown>, kind: string, key: string): unknown {
  if (kind === "olmocr_bench") {
    if (key === "overall") return modelScore.overall;
    const byType = (modelScore.by_type ?? {}) as Record<string, unknown>;
    return byType[key];
  }
  if (key === "overall_edit") return modelScore.overall_edit;
  const metrics = (modelScore.metrics ?? {}) as Record<string, unknown>;
  return metrics[key];
}

export default function ResultMatrix({ run, models }: ResultMatrixProps) {
  const [selected, setSelected] = useState<BatchRunItem | null>(null);

  const modelName = (id: string) =>
    models.find((m) => m.id === id)?.display_name ?? id.slice(0, 8);

  const scores = run.summary_scores ?? {};
  const hasScores = run.benchmark_kind != null && Object.keys(scores).length > 0;
  const cols = run.benchmark_kind === "olmocr_bench" ? OLMOCR_COLS : OMNI_COLS;

  // index items by document_id|model_id
  const cell = (docId: string, modelId: string) =>
    run.items.find((i) => i.document_id === docId && i.model_id === modelId) ?? null;

  const docName = (id: string) =>
    run.documents.find((d) => d.id === id)?.original_name ?? id.slice(0, 8);

  return (
    <>
      {hasScores && (
        <div className="surface-card overflow-x-auto">
          <div className="flex items-center gap-2 px-3 pt-3">
            <h3 className="text-sm font-semibold">Official scores</h3>
            <span className="text-xs text-muted-foreground">
              {run.benchmark_kind === "olmocr_bench"
                ? "olmOCR-Bench · pass-rate, higher is better"
                : "OmniDocBench · edit distance lower is better, CDM/TEDS higher is better"}
            </span>
          </div>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="sticky left-0 z-10 bg-background px-3 py-2 text-left font-medium">
                  Model
                </th>
                {cols.map((c) => (
                  <th key={c.key} className="px-3 py-2 text-right font-medium whitespace-nowrap">
                    {c.label}
                    {c.lowerBetter ? " ↓" : c.pct ? " ↑" : ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {run.model_ids
                .filter((mid) => scores[mid])
                .map((mid) => {
                  const ms = scores[mid] as Record<string, unknown>;
                  return (
                    <tr key={mid} className="border-b border-border/50">
                      <td className="sticky left-0 z-10 bg-background px-3 py-2 font-medium whitespace-nowrap">
                        {modelName(mid)}
                      </td>
                      {cols.map((c) => (
                        <td key={c.key} className="px-3 py-2 text-right tabular-nums">
                          {fmt(scoreValue(ms, run.benchmark_kind!, c.key), c)}
                        </td>
                      ))}
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      )}

      <div className="surface-card overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="sticky left-0 z-10 bg-background px-3 py-2 text-left font-medium">
                Document
              </th>
              {run.model_ids.map((mid) => (
                <th key={mid} className="px-3 py-2 text-left font-medium whitespace-nowrap">
                  {modelName(mid)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {run.documents.map((doc) => (
              <tr key={doc.id} className="border-b border-border/50">
                <td className="sticky left-0 z-10 bg-background px-3 py-2 max-w-[200px] truncate font-medium">
                  {doc.original_name}
                </td>
                {run.model_ids.map((mid) => {
                  const c = cell(doc.id, mid);
                  const clickable = c && (c.status === "done" || c.status === "error");
                  return (
                    <td key={mid} className="px-3 py-2">
                      <button
                        disabled={!clickable}
                        onClick={() => c && setSelected(c)}
                        className={cn(
                          "flex items-center gap-2 rounded-md px-2 py-1 transition-colors",
                          clickable ? "hover:bg-muted cursor-pointer" : "cursor-default",
                        )}
                      >
                        {statusIcon(c?.status ?? "pending")}
                        <span className="text-xs text-muted-foreground">
                          {c?.status === "done" && c.latency_ms != null
                            ? `${(c.latency_ms / 1000).toFixed(1)}s`
                            : c?.status === "error"
                              ? "error"
                              : c?.status ?? "pending"}
                        </span>
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Dialog open={selected !== null} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="truncate">
              {selected && `${docName(selected.document_id)} · ${modelName(selected.model_id)}`}
            </DialogTitle>
          </DialogHeader>
          {selected && (
            <div className="overflow-auto">
              <ModelResult
                label={modelName(selected.model_id)}
                modelName={modelName(selected.model_id)}
                text={selected.result_text}
                latencyMs={selected.latency_ms}
                isLoading={false}
                error={selected.error}
              />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
