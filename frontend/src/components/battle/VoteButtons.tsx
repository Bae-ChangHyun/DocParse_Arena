"use client";

import { ThumbsUp, Equal, RotateCcw } from "lucide-react";
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
      <div className="flex justify-center p-4">
        <Button onClick={onNewBattle} className="gap-2">
          <RotateCcw className="h-4 w-4" />
          New Battle
        </Button>
      </div>
    );
  }

  return (
    <div className="flex justify-center items-center gap-3 p-4">
      <Button
        onClick={() => onVote("a")}
        disabled={disabled || isVoting}
        variant="outline"
        className="gap-2"
      >
        <ThumbsUp className="h-4 w-4" />
        Model A is better
      </Button>
      <Button
        onClick={() => onVote("tie")}
        disabled={disabled || isVoting}
        variant="outline"
        className="gap-2"
      >
        <Equal className="h-4 w-4" />
        Tie
      </Button>
      <Button
        onClick={() => onVote("b")}
        disabled={disabled || isVoting}
        variant="outline"
        className="gap-2"
      >
        <ThumbsUp className="h-4 w-4 scale-x-[-1]" />
        Model B is better
      </Button>
    </div>
  );
}
