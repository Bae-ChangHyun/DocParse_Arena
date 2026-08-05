"use client";

import { ChevronLeft, ChevronRight, Equal, RefreshCw, RotateCcw, Square } from "lucide-react";
import { Button } from "@/components/ui/button";

interface VoteButtonsProps {
  onVote: (winner: "a" | "b" | "tie") => void;
  onEndEarly: () => void;
  onNewBattle: () => void;
  onRetry: () => void;
  isVoting: boolean;
  isEndingEarly: boolean;
  hasVoted: boolean;
  disabled: boolean;
  canEndEarly: boolean;
  canRetry: boolean;
}

export default function VoteButtons({
  onVote,
  onEndEarly,
  onNewBattle,
  onRetry,
  isVoting,
  isEndingEarly,
  hasVoted,
  disabled,
  canEndEarly,
  canRetry,
}: VoteButtonsProps) {
  if (hasVoted) {
    return (
      <div className="flex justify-center border-t bg-background/80 p-4">
        <Button onClick={onNewBattle} className="gap-2">
          <RotateCcw className="h-4 w-4" />
          New Battle
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-center gap-2 border-t bg-background/80 p-4">
      <Button
        onClick={onNewBattle}
        disabled={isVoting || isEndingEarly}
        variant="ghost"
        size="sm"
        className="gap-1.5"
      >
        <RotateCcw className="h-3.5 w-3.5" />
        New Battle
      </Button>
      <Button
        onClick={onRetry}
        disabled={!canRetry || isVoting || isEndingEarly}
        variant="outline"
        size="sm"
        className="gap-1.5"
      >
        <RefreshCw className="h-3.5 w-3.5" />
        Retry
      </Button>
      <Button
        onClick={onEndEarly}
        disabled={!canEndEarly || isVoting || isEndingEarly}
        variant="outline"
        size="sm"
        className="gap-1.5"
      >
        <Square className="h-3.5 w-3.5" />
        Stop & Judge
      </Button>
      <Button
        onClick={() => onVote("a")}
        disabled={disabled || isVoting || isEndingEarly}
        variant="secondary"
        className="gap-2"
      >
        <ChevronLeft className="h-4 w-4" />
        A is better
      </Button>
      <Button
        onClick={() => onVote("tie")}
        disabled={disabled || isVoting || isEndingEarly}
        variant="outline"
        size="sm"
        className="gap-1.5"
      >
        <Equal className="h-3.5 w-3.5" />
        Tie
      </Button>
      <Button
        onClick={() => onVote("b")}
        disabled={disabled || isVoting || isEndingEarly}
        variant="secondary"
        className="gap-2"
      >
        B is better
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  );
}
