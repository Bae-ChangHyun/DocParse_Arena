"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { toast } from "sonner";
import DocumentUpload from "./DocumentUpload";
import DocumentViewer from "./DocumentViewer";
import ModelResult from "./ModelResult";
import VoteButtons from "./VoteButtons";
import {
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
};

export default function BattleArena() {
  const [state, setState] = useState<BattleState>(initialState);
  const eventSourceRef = useRef<EventSource | null>(null);
  const documentUrlRef = useRef<string | null>(null);

  // Keep ref in sync with state
  useEffect(() => {
    documentUrlRef.current = state.documentUrl;
  }, [state.documentUrl]);

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
      // Revoke blob URL on unmount
      if (documentUrlRef.current?.startsWith("blob:")) {
        URL.revokeObjectURL(documentUrlRef.current);
      }
    };
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

      eventSourceRef.current?.close();
      eventSourceRef.current = streamBattle(response.battle_id, (event, data: unknown) => {
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
              modelAText: prev.modelAStreamText || null,
              modelALatency: d.latency_ms || null,
              modelAError: d.error || null,
              modelAStreaming: false,
              modelALoading: false,
            }));
            break;
          case "model_b_done":
            setState((prev) => ({
              ...prev,
              modelBText: prev.modelBStreamText || null,
              modelBLatency: d.latency_ms || null,
              modelBError: d.error || null,
              modelBStreaming: false,
              modelBLoading: false,
            }));
            break;
          case "model_a_replace":
            setState((prev) => ({
              ...prev,
              modelAStreamText: d.text || prev.modelAStreamText,
              modelAText: prev.modelAText ? (d.text || prev.modelAText) : prev.modelAText,
            }));
            break;
          case "model_b_replace":
            setState((prev) => ({
              ...prev,
              modelBStreamText: d.text || prev.modelBStreamText,
              modelBText: prev.modelBText ? (d.text || prev.modelBText) : prev.modelBText,
            }));
            break;
          case "model_a_result":
            setState((prev) => ({
              ...prev,
              modelAText: d.text || null,
              modelALatency: d.latency_ms || null,
              modelAError: d.error || null,
              modelALoading: false,
            }));
            break;
          case "model_b_result":
            setState((prev) => ({
              ...prev,
              modelBText: d.text || null,
              modelBLatency: d.latency_ms || null,
              modelBError: d.error || null,
              modelBLoading: false,
            }));
            break;
        }
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start battle";
      setState((prev) => ({
        ...prev,
        isStarting: false,
        modelAError: message,
        modelBError: message,
      }));
    }
  }, []);

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

  const handleNewBattle = useCallback(() => {
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
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <DocumentUpload
          onFileSelect={handleFileSelect}
          onRandomDoc={handleRandomDoc}
          isLoading={state.isStarting}
        />
      </div>
    );
  }

  const resultsReady =
    !state.modelALoading && !state.modelBLoading &&
    !state.modelAStreaming && !state.modelBStreaming &&
    (state.modelAText || state.modelAError) &&
    (state.modelBText || state.modelBError);

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-2 p-2 min-h-0">
        <div className="relative min-h-[200px] lg:min-h-0 border rounded-lg overflow-hidden">
          {state.documentUrl ? (
            <DocumentViewer imageUrl={state.documentUrl} documentName={state.documentName || undefined} />
          ) : (
            <div className="flex items-center justify-center h-full">
              <span className="text-sm text-muted-foreground">Loading document...</span>
            </div>
          )}
        </div>

        <div className="min-h-[300px] lg:min-h-0">
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
        </div>

        <div className="min-h-[300px] lg:min-h-0">
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
        </div>
      </div>

      <VoteButtons
        onVote={handleVote}
        onNewBattle={handleNewBattle}
        isVoting={state.isVoting}
        hasVoted={!!state.voteResult}
        disabled={!resultsReady}
      />
    </div>
  );
}
