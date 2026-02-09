"use client";

import { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { getLeaderboard, type LeaderboardEntry } from "@/lib/api";

export default function RankingTable() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getLeaderboard()
      .then(setEntries)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-center py-8 text-muted-foreground">Loading leaderboard...</div>;
  }

  if (entries.length === 0) {
    return <div className="text-center py-8 text-muted-foreground">No models registered yet.</div>;
  }

  return (
    <div className="rounded-lg border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12 text-center">#</TableHead>
            <TableHead>Model</TableHead>
            <TableHead className="text-center">Provider</TableHead>
            <TableHead className="text-right">ELO</TableHead>
            <TableHead className="text-right">Win Rate</TableHead>
            <TableHead className="text-right">W / L</TableHead>
            <TableHead className="text-right">Battles</TableHead>
            <TableHead className="text-right">Avg Latency</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map((entry) => (
            <TableRow key={entry.id}>
              <TableCell className="text-center font-medium">
                {entry.rank <= 3 ? ["🥇", "🥈", "🥉"][entry.rank - 1] : entry.rank}
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <span>{entry.icon}</span>
                  <span className="font-medium">{entry.display_name}</span>
                </div>
              </TableCell>
              <TableCell className="text-center">
                <Badge variant="secondary" className="text-xs">{entry.provider}</Badge>
              </TableCell>
              <TableCell className="text-right font-mono font-semibold">{entry.elo}</TableCell>
              <TableCell className="text-right">{entry.win_rate}%</TableCell>
              <TableCell className="text-right text-sm">
                <span className="text-green-600">{entry.wins}</span>
                {" / "}
                <span className="text-red-600">{entry.losses}</span>
              </TableCell>
              <TableCell className="text-right">{entry.total_battles}</TableCell>
              <TableCell className="text-right">
                {entry.avg_latency_ms > 0 ? `${(entry.avg_latency_ms / 1000).toFixed(1)}s` : "-"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
