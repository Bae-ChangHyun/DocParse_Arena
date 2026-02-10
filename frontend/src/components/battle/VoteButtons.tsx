"use client";

import { ChevronLeft, ChevronRight, Equal, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface VoteButtonsProps {
  onVote: (winner: "a" | "b" | "tie") => void;
  onNewBattle: () => void;
  isVoting: boolean;
  hasVoted: boolean;
  disabled: boolean;
}

export default function VoteButtons({ onVote, onNewBattle, isVoting, hasVoted, disabled }: VoteButtonsProps) {
  if (hasVoted) {
    return (
      <div className="flex justify-center p-4 border-t bg-card/50">
        <Button onClick={onNewBattle} className="gap-2">
          <RotateCcw className="h-4 w-4" />
          New Battle
        </Button>
      </div>
    );
  }

  return (
    <div className="flex justify-center items-center gap-3 p-4 border-t bg-card/50">
      <Button
        onClick={() => onVote("a")}
        disabled={disabled || isVoting}
        variant="secondary"
        className="gap-2"
      >
        <ChevronLeft className="h-4 w-4" />
        A is better
      </Button>
      <Button
        onClick={() => onVote("tie")}
        disabled={disabled || isVoting}
        variant="outline"
        size="sm"
        className="gap-1.5"
      >
        <Equal className="h-3.5 w-3.5" />
        Tie
      </Button>
      <Button
        onClick={() => onVote("b")}
        disabled={disabled || isVoting}
        variant="secondary"
        className="gap-2"
      >
        B is better
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  );
}
