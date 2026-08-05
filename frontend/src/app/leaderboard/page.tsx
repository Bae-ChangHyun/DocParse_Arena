"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import RankingTable from "@/components/leaderboard/RankingTable";
import HeadToHeadMatrix from "@/components/leaderboard/HeadToHeadMatrix";

export default function LeaderboardPage() {
  return (
    <div className="mx-auto max-w-[1200px] px-4 py-8">
      <div className="mb-8 max-w-3xl">
        <div className="mb-3 inline-flex rounded-full border border-border px-3 py-1 text-xs font-medium tracking-[0.01em] text-muted-foreground">
          Arena results
        </div>
        <h1 className="font-display text-5xl font-medium leading-tight">Leaderboard</h1>
        <p className="mt-2 text-muted-foreground">
          Model rankings based on ELO rating from blind document parsing battles
        </p>
      </div>

      <Tabs defaultValue="ranking">
        <TabsList>
          <TabsTrigger value="ranking">Ranking</TabsTrigger>
          <TabsTrigger value="head-to-head">Head-to-Head</TabsTrigger>
        </TabsList>
        <TabsContent value="ranking" className="mt-4">
          <RankingTable />
        </TabsContent>
        <TabsContent value="head-to-head" className="mt-4">
          <HeadToHeadMatrix />
        </TabsContent>
      </Tabs>
    </div>
  );
}
