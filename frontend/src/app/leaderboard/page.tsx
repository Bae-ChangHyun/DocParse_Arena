"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import RankingTable from "@/components/leaderboard/RankingTable";
import HeadToHeadMatrix from "@/components/leaderboard/HeadToHeadMatrix";

export default function LeaderboardPage() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Leaderboard</h1>
        <p className="text-muted-foreground mt-1">
          OCR model rankings based on ELO rating from blind battles
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
