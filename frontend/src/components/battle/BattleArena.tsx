"use client";

import { useState, useCallback } from "react";
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
  voteResult: null,
  isStarting: false,
  isVoting: false,
};

export default function BattleArena() {
  const [state, setState] = useState<BattleState>(initialState);

  const handleStartBattle = useCallback(async (file?: File, documentName?: string) => {
    setState({ ...initialState, isStarting: true });

    try {
      const response = await startBattle(file, documentName);

      const docUrl = `${getApiBase()}${response.document_url}`;

      setState((prev) => ({
        ...prev,
        battleId: response.battle_id,
        documentUrl: docUrl,
        documentName: documentName || file?.name || "Uploaded document",
        isStarting: false,
        modelALoading: true,
        modelBLoading: true,
      }));

      streamBattle(response.battle_id, (event, data: unknown) => {
        const d = data as { text?: string; latency_ms?: number; error?: string };
        if (event === "model_a_result") {
          setState((prev) => ({
            ...prev,
            modelAText: d.text || null,
            modelALatency: d.latency_ms || null,
            modelAError: d.error || null,
            modelALoading: false,
          }));
        } else if (event === "model_b_result") {
          setState((prev) => ({
            ...prev,
            modelBText: d.text || null,
            modelBLatency: d.latency_ms || null,
            modelBError: d.error || null,
            modelBLoading: false,
          }));
        }
      });
    } catch {
      setState((prev) => ({
        ...prev,
        isStarting: false,
        modelAError: "Failed to start battle",
        modelBError: "Failed to start battle",
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
      const name = res.headers.get("X-Document-Name") || "random.png";
      const blob = await res.blob();
      const file = new File([blob], name, { type: blob.type });
      await handleStartBattle(file);
    } catch {
      setState((prev) => ({ ...prev, isStarting: false }));
    }
  }, [handleStartBattle]);

  const handleVote = useCallback(async (winner: "a" | "b" | "tie") => {
    if (!state.battleId) return;
    setState((prev) => ({ ...prev, isVoting: true }));
    try {
      const result = await voteBattle(state.battleId, winner);
      setState((prev) => ({ ...prev, voteResult: result, isVoting: false }));
    } catch {
      setState((prev) => ({ ...prev, isVoting: false }));
    }
  }, [state.battleId]);

  const handleNewBattle = useCallback(() => {
    setState(initialState);
  }, []);

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

  const resultsReady = !state.modelALoading && !state.modelBLoading && (state.modelAText || state.modelAError) && (state.modelBText || state.modelBError);

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
