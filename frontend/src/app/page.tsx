import Link from "next/link";
import { Swords, Trophy, FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center h-[calc(100vh-3.5rem)] px-4">
      <div className="text-center max-w-xl">
        <div className="flex items-center justify-center gap-3 mb-6">
          <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <Swords className="h-6 w-6 text-primary" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">DocParse Arena</h1>
        </div>
        <p className="text-muted-foreground mb-8 text-base leading-relaxed">
          Self-hosted blind comparison for document parsing models.
          <br />
          Upload your documents, vote for the best result, and discover which model works best for you.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link href="/battle">
            <Button size="lg" className="gap-2">
              <Swords className="h-4 w-4" />
              Start Battle
            </Button>
          </Link>
          <Link href="/leaderboard">
            <Button variant="secondary" size="lg" className="gap-2">
              <Trophy className="h-4 w-4" />
              Leaderboard
            </Button>
          </Link>
          <Link href="/playground">
            <Button variant="outline" size="lg" className="gap-2">
              <FlaskConical className="h-4 w-4" />
              Playground
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
