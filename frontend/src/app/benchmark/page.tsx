"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import AuthGate from "@/components/settings/AuthGate";
import CollectionManager from "@/components/benchmark/CollectionManager";
import ResultMatrix from "@/components/benchmark/ResultMatrix";
import {
  getModels,
  createBatchRun,
  listBatchRuns,
  getBatchRun,
  type OcrModel,
  type BatchRun,
  type BatchRunDetail,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Play, Loader2 } from "lucide-react";

export default function BenchmarkPage() {
  const [models, setModels] = useState<OcrModel[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set());
  const [runs, setRuns] = useState<BatchRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [runDetail, setRunDetail] = useState<BatchRunDetail | null>(null);
  const [starting, setStarting] = useState(false);

  const refreshRuns = useCallback(() => {
    listBatchRuns()
      .then(setRuns)
      .catch((e) => toast.error("Failed to load runs", { description: String(e) }));
  }, []);

  useEffect(() => {
    getModels()
      .then(setModels)
      .catch((e) => toast.error("Failed to load models", { description: String(e) }));
    refreshRuns();
  }, [refreshRuns]);

  // Poll the selected run's detail until it is done
  useEffect(() => {
    if (!selectedRunId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | null = null;
    const fetchDetail = () => {
      getBatchRun(selectedRunId)
        .then((detail) => {
          if (cancelled) return;
          setRunDetail(detail);
          if (detail.status === "done" || detail.status === "failed") {
            if (timer) clearInterval(timer);
            timer = null;
            refreshRuns();
          }
        })
        .catch((e) => toast.error("Failed to load run", { description: String(e) }));
    };
    fetchDetail();
    timer = setInterval(fetchDetail, 2000);
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [selectedRunId, refreshRuns]);

  const toggleModel = (id: string) => {
    setSelectedModels((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleStart = async () => {
    if (!selectedCollection || selectedModels.size === 0) return;
    setStarting(true);
    try {
      const run = await createBatchRun(selectedCollection, Array.from(selectedModels));
      refreshRuns();
      setSelectedRunId(run.id);
      toast.success("Batch run started");
    } catch (e) {
      toast.error("Failed to start run", { description: String(e) });
    }
    setStarting(false);
  };

  return (
    <AuthGate>
      <div className="mx-auto max-w-[1400px] px-4 py-8">
        <div className="mb-8 max-w-3xl">
          <div className="mb-3 inline-flex rounded-full border border-border px-3 py-1 text-xs font-medium tracking-[0.01em] text-muted-foreground">
            Batch evaluation
          </div>
          <h1 className="font-display text-5xl font-medium leading-tight">Benchmark</h1>
          <p className="mt-2 text-muted-foreground">
            Run a document collection against multiple models at once and compare results side-by-side.
          </p>
        </div>

        <div className="flex flex-col gap-6 lg:flex-row">
          {/* Left: collections */}
          <div className="w-full shrink-0 lg:w-80">
            <CollectionManager selectedId={selectedCollection} onSelect={setSelectedCollection} />
          </div>

          {/* Right: run config + results */}
          <div className="flex-1 min-w-0 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Models</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {models.length === 0 && (
                    <p className="text-sm text-muted-foreground">
                      No active models. Enable models in Settings first.
                    </p>
                  )}
                  {models.map((m) => (
                    <button key={m.id} onClick={() => toggleModel(m.id)}>
                      <Badge
                        variant={selectedModels.has(m.id) ? "default" : "outline"}
                        className="cursor-pointer px-3 py-1.5 text-sm"
                      >
                        {m.display_name}
                      </Badge>
                    </button>
                  ))}
                </div>
                <Button
                  onClick={handleStart}
                  disabled={starting || !selectedCollection || selectedModels.size === 0}
                  className="gap-2"
                >
                  {starting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                  Run benchmark
                  {selectedModels.size > 0 && ` (${selectedModels.size} models)`}
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Runs</CardTitle>
              </CardHeader>
              <CardContent>
                {runs.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No runs yet.</p>
                ) : (
                  <div className="space-y-1">
                    {runs.map((r) => (
                      <button
                        key={r.id}
                        onClick={() => setSelectedRunId(r.id)}
                        className={cn(
                          "flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition-colors",
                          selectedRunId === r.id ? "bg-muted" : "hover:bg-muted/60",
                        )}
                      >
                        <span className="flex items-center gap-2">
                          {r.status === "running" && (
                            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                          )}
                          <span className="font-mono text-xs">{r.id.slice(0, 8)}</span>
                          <span className="text-muted-foreground">
                            {new Date(r.created_at).toLocaleString()}
                          </span>
                        </span>
                        <Badge variant={r.status === "done" ? "secondary" : "outline"}>
                          {r.completed}/{r.total} · {r.status}
                        </Badge>
                      </button>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {runDetail && runDetail.id === selectedRunId && runDetail.documents.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-medium text-muted-foreground">
                    Result matrix · {runDetail.completed}/{runDetail.total}
                  </h2>
                  {runDetail.status === "running" && (
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  )}
                </div>
                <ResultMatrix run={runDetail} models={models} />
              </div>
            )}
          </div>
        </div>
      </div>
    </AuthGate>
  );
}
