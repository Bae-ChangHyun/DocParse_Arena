"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { toast } from "sonner";
import DocumentUpload from "./DocumentUpload";
import DocumentViewer from "./DocumentViewer";
import ModelResult from "./ModelResult";
import VoteButtons from "./VoteButtons";
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable";
import {
  abortBattle,
  startBattle,
  streamBattle,
  voteBattle,
  getApiBase,
  type VoteResponse,
} from "@/lib/api";

interface BattleState {
  battleId: string | null;
  documentUrl: string | null;
  documentName: string | null;
  modelAText: string | null;
  modelBText: string | null;
  modelALatency: number | null;
  modelBLatency: number | null;
  modelAError: string | null;
  modelBError: string | null;
  modelALoading: boolean;
  modelBLoading: boolean;
  modelAStreaming: boolean;
  modelBStreaming: boolean;
  modelAStreamText: string;
  modelBStreamText: string;
  voteResult: VoteResponse | null;
  isStarting: boolean;
  isVoting: boolean;
  isEndingEarly: boolean;
}

const initialState: BattleState = {
  battleId: null,
  documentUrl: null,
  documentName: null,
  modelAText: null,
  modelBText: null,
  modelALatency: null,
  modelBLatency: null,
  modelAError: null,
  modelBError: null,
  modelALoading: false,
  modelBLoading: false,
  modelAStreaming: false,
  modelBStreaming: false,
  modelAStreamText: "",
  modelBStreamText: "",
  voteResult: null,
  isStarting: false,
  isVoting: false,
  isEndingEarly: false,
};

export default function BattleArena() {
  const [state, setState] = useState<BattleState>(initialState);
  const [isCompact, setIsCompact] = useState(() =>
    typeof window !== "undefined"
      ? window.matchMedia("(max-width: 767px)").matches
      : false
  );
  const eventSourceRef = useRef<EventSource | null>(null);
  const activeBattleIdRef = useRef<string | null>(null);
  const documentUrlRef = useRef<string | null>(null);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 767px)");
    const handleChange = () => setIsCompact(mediaQuery.matches);
    handleChange();
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  // Keep ref in sync with state
  useEffect(() => {
    documentUrlRef.current = state.documentUrl;
  }, [state.documentUrl]);

  useEffect(() => {
    return () => {
      activeBattleIdRef.current = null;
      eventSourceRef.current?.close();
      // Revoke blob URL on unmount
      if (documentUrlRef.current?.startsWith("blob:")) {
        URL.revokeObjectURL(documentUrlRef.current);
      }
    };
  }, []);

  const connectBattleStream = useCallback((battleId: string) => {
    activeBattleIdRef.current = battleId;
    eventSourceRef.current?.close();
    eventSourceRef.current = streamBattle(battleId, (event, data: unknown) => {
      if (activeBattleIdRef.current !== battleId) return;

      const d = data as { text?: string; token?: string; latency_ms?: number; error?: string };

      switch (event) {
        case "model_a_token":
          setState((prev) => ({
            ...prev,
            modelALoading: false,
            modelAStreaming: true,
            modelAStreamText: prev.modelAStreamText + (d.token || ""),
          }));
          break;
        case "model_b_token":
          setState((prev) => ({
            ...prev,
            modelBLoading: false,
            modelBStreaming: true,
            modelBStreamText: prev.modelBStreamText + (d.token || ""),
          }));
          break;
        case "model_a_done":
          setState((prev) => ({
            ...prev,
            modelAText: d.error ? (prev.modelAStreamText || null) : prev.modelAStreamText,
            modelALatency: d.latency_ms ?? null,
            modelAError: d.error || null,
            modelAStreaming: false,
            modelALoading: false,
          }));
          break;
        case "model_b_done":
          setState((prev) => ({
            ...prev,
            modelBText: d.error ? (prev.modelBStreamText || null) : prev.modelBStreamText,
            modelBLatency: d.latency_ms ?? null,
            modelBError: d.error || null,
            modelBStreaming: false,
            modelBLoading: false,
          }));
          break;
        case "model_a_replace":
          setState((prev) => ({
            ...prev,
            modelAStreamText: d.text ?? prev.modelAStreamText,
            modelAText: prev.modelAText !== null ? (d.text ?? prev.modelAText) : prev.modelAText,
          }));
          break;
        case "model_b_replace":
          setState((prev) => ({
            ...prev,
            modelBStreamText: d.text ?? prev.modelBStreamText,
            modelBText: prev.modelBText !== null ? (d.text ?? prev.modelBText) : prev.modelBText,
          }));
          break;
        case "model_a_result":
          setState((prev) => ({
            ...prev,
            modelAText: d.text ?? "",
            modelALatency: d.latency_ms ?? null,
            modelAError: d.error || null,
            modelALoading: false,
          }));
          break;
        case "model_b_result":
          setState((prev) => ({
            ...prev,
            modelBText: d.text ?? "",
            modelBLatency: d.latency_ms ?? null,
            modelBError: d.error || null,
            modelBLoading: false,
          }));
          break;
        case "stream_error": {
          const message = d.error || "Stream failed";
          toast.error("Battle stream failed", { description: message });
          activeBattleIdRef.current = null;
          eventSourceRef.current = null;
          setState((prev) => ({
            ...prev,
            modelALoading: false,
            modelBLoading: false,
            modelAStreaming: false,
            modelBStreaming: false,
            modelAError: prev.modelAText !== null || prev.modelAError ? prev.modelAError : message,
            modelBError: prev.modelBText !== null || prev.modelBError ? prev.modelBError : message,
            isEndingEarly: true,
          }));
          void abortBattle(battleId)
            .then((result) => {
              setState((prev) => {
                const retryStarted =
                  prev.modelALoading || prev.modelBLoading || prev.modelAStreaming || prev.modelBStreaming;
                if (prev.battleId !== battleId || retryStarted) return prev;
                return {
                  ...prev,
                  modelALatency: prev.modelALatency ?? result.model_a_latency_ms,
                  modelBLatency: prev.modelBLatency ?? result.model_b_latency_ms,
                  isEndingEarly: false,
                };
              });
            })
            .catch((err) => {
              toast.error("Failed to finalize failed battle", {
                description: err instanceof Error ? err.message : undefined,
              });
              setState((prev) => {
                const retryStarted =
                  prev.modelALoading || prev.modelBLoading || prev.modelAStreaming || prev.modelBStreaming;
                return prev.battleId === battleId && !retryStarted ? { ...prev, isEndingEarly: false } : prev;
              });
            });
          break;
        }
        case "done":
          activeBattleIdRef.current = null;
          eventSourceRef.current?.close();
          eventSourceRef.current = null;
          break;
      }
    });
  }, []);

  const handleStartBattle = useCallback(async (file?: File, documentName?: string) => {
    setState({ ...initialState, isStarting: true });

    try {
      const response = await startBattle(file, documentName);

      // Use local blob URL — files are NOT stored on the server
      const docUrl = file
        ? URL.createObjectURL(file)
        : `${getApiBase()}${response.document_url}`;

      setState((prev) => ({
        ...prev,
        battleId: response.battle_id,
        documentUrl: docUrl,
        documentName: documentName || file?.name || "Uploaded document",
        isStarting: false,
        modelALoading: true,
        modelBLoading: true,
      }));

      connectBattleStream(response.battle_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start battle";
      setState((prev) => ({
        ...prev,
        isStarting: false,
        modelAError: message,
        modelBError: message,
      }));
    }
  }, [connectBattleStream]);

  const handleFileSelect = useCallback(
    (file: File) => handleStartBattle(file),
    [handleStartBattle]
  );

  const handleRandomDoc = useCallback(async () => {
    setState((prev) => ({ ...prev, isStarting: true }));
    try {
      const res = await fetch(`${getApiBase()}/api/documents/random`);
      if (!res.ok) {
        throw new Error(
          res.status === 404
            ? "No sample documents available. Upload a file instead."
            : `Server error (${res.status})`
        );
      }
      const name = res.headers.get("X-Document-Name") || "random.png";
      const blob = await res.blob();
      const file = new File([blob], name, { type: blob.type });
      await handleStartBattle(file);
    } catch (err) {
      toast.error("Failed to fetch random document", { description: err instanceof Error ? err.message : undefined });
      setState((prev) => ({ ...prev, isStarting: false }));
    }
  }, [handleStartBattle]);

  const handleVote = useCallback(async (winner: "a" | "b" | "tie") => {
    if (!state.battleId) return;
    setState((prev) => ({ ...prev, isVoting: true }));
    try {
      const result = await voteBattle(state.battleId, winner);
      setState((prev) => ({ ...prev, voteResult: result, isVoting: false }));
    } catch (err) {
      toast.error("Vote failed", { description: err instanceof Error ? err.message : undefined });
      setState((prev) => ({ ...prev, isVoting: false }));
    }
  }, [state.battleId]);

  const handleRetry = useCallback(() => {
    if (!state.battleId) return;
    setState((prev) => ({
      ...prev,
      modelAText: null,
      modelBText: null,
      modelALatency: null,
      modelBLatency: null,
      modelAError: null,
      modelBError: null,
      modelALoading: true,
      modelBLoading: true,
      modelAStreaming: false,
      modelBStreaming: false,
      modelAStreamText: "",
      modelBStreamText: "",
      isEndingEarly: false,
      voteResult: null,
    }));
    connectBattleStream(state.battleId);
  }, [connectBattleStream, state.battleId]);

  const handleEndEarly = useCallback(async () => {
    if (!state.battleId) return;

    const battleId = state.battleId;
    const stoppedMessage = "Stopped before completion";
    activeBattleIdRef.current = null;
    eventSourceRef.current?.close();
    eventSourceRef.current = null;

    setState((prev) => {
      const modelAText = prev.modelAText ?? (prev.modelAStreamText ? prev.modelAStreamText : null);
      const modelBText = prev.modelBText ?? (prev.modelBStreamText ? prev.modelBStreamText : null);

      return {
        ...prev,
        modelAText,
        modelBText,
        modelALoading: false,
        modelBLoading: false,
        modelAStreaming: false,
        modelBStreaming: false,
        modelAError: modelAText !== null || prev.modelAError ? prev.modelAError : stoppedMessage,
        modelBError: modelBText !== null || prev.modelBError ? prev.modelBError : stoppedMessage,
        isEndingEarly: true,
      };
    });

    try {
      const result = await abortBattle(battleId);
      setState((prev) => {
        if (prev.battleId !== battleId) return prev;
        return {
          ...prev,
          modelALatency: prev.modelALatency ?? result.model_a_latency_ms,
          modelBLatency: prev.modelBLatency ?? result.model_b_latency_ms,
          isEndingEarly: false,
        };
      });
      toast.info("Battle stopped", { description: "You can vote with the available output or retry." });
    } catch (err) {
      toast.error("Failed to stop battle", { description: err instanceof Error ? err.message : undefined });
      setState((prev) => (prev.battleId === battleId ? { ...prev, isEndingEarly: false } : prev));
    }
  }, [state.battleId]);

  const handleNewBattle = useCallback(() => {
    activeBattleIdRef.current = null;
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    // Revoke blob URL to prevent memory leak
    if (state.documentUrl?.startsWith("blob:")) {
      URL.revokeObjectURL(state.documentUrl);
    }
    setState(initialState);
  }, [state.documentUrl]);

  if (!state.battleId && !state.isStarting) {
    return (
      <div className="flex min-h-[calc(100dvh-3.5rem)] items-center justify-center px-4">
        <DocumentUpload
          onFileSelect={handleFileSelect}
          onRandomDoc={handleRandomDoc}
          isLoading={state.isStarting}
        />
      </div>
    );
  }

  const modelAReady = state.modelAText !== null || state.modelAError !== null;
  const modelBReady = state.modelBText !== null || state.modelBError !== null;
  const resultsReady =
    !state.modelALoading && !state.modelBLoading &&
    !state.modelAStreaming && !state.modelBStreaming &&
    modelAReady && modelBReady;
  const hasPendingResult =
    state.modelALoading || state.modelBLoading || state.modelAStreaming || state.modelBStreaming;
  const hasErrorResult = state.modelAError !== null || state.modelBError !== null;
  const canEndEarly = !!state.battleId && !state.voteResult && hasPendingResult;
  const canRetry = !!state.battleId && !state.voteResult && !state.isStarting && (hasPendingResult || hasErrorResult);

  const documentPane = (
    <div className="surface-card relative h-full overflow-hidden">
      {state.documentUrl ? (
        <DocumentViewer imageUrl={state.documentUrl} documentName={state.documentName || undefined} />
      ) : (
        <div className="flex items-center justify-center h-full">
          <span className="text-sm text-muted-foreground">Loading document...</span>
        </div>
      )}
    </div>
  );

  const modelAResult = (
    <ModelResult
      label="Model A"
      text={state.modelAText}
      latencyMs={state.modelALatency}
      isLoading={state.modelALoading}
      isStreaming={state.modelAStreaming}
      streamingText={state.modelAStreamText}
      error={state.modelAError}
      modelName={state.voteResult?.model_a.display_name}
      eloChange={state.voteResult?.model_a_elo_change}
    />
  );

  const modelBResult = (
    <ModelResult
      label="Model B"
      text={state.modelBText}
      latencyMs={state.modelBLatency}
      isLoading={state.modelBLoading}
      isStreaming={state.modelBStreaming}
      streamingText={state.modelBStreamText}
      error={state.modelBError}
      modelName={state.voteResult?.model_b.display_name}
      eloChange={state.voteResult?.model_b_elo_change}
    />
  );

  return (
    <div className="flex h-[calc(100dvh-3.5rem)] flex-col">
      {isCompact ? (
        <div className="flex-1 min-h-0 overflow-y-auto p-2 space-y-2">
          <div className="h-[42dvh] min-h-[280px]">{documentPane}</div>
          <div className="h-[55dvh] min-h-[360px]">{modelAResult}</div>
          <div className="h-[55dvh] min-h-[360px]">{modelBResult}</div>
        </div>
      ) : (
        <ResizablePanelGroup orientation="horizontal" className="flex-1 min-h-0 p-4">
          <ResizablePanel defaultSize={33} minSize={15}>
            {documentPane}
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel defaultSize={34} minSize={15}>
            <div className="h-full px-1">{modelAResult}</div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel defaultSize={33} minSize={15}>
            <div className="h-full">{modelBResult}</div>
          </ResizablePanel>
        </ResizablePanelGroup>
      )}

      <VoteButtons
        onVote={handleVote}
        onEndEarly={handleEndEarly}
        onNewBattle={handleNewBattle}
        onRetry={handleRetry}
        isVoting={state.isVoting}
        isEndingEarly={state.isEndingEarly}
        hasVoted={!!state.voteResult}
        disabled={!resultsReady}
        canEndEarly={canEndEarly}
        canRetry={canRetry}
      />
    </div>
  );
}
