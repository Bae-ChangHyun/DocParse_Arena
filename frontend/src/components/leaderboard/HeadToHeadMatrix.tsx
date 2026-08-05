"use client";

import { useEffect, useState } from "react";
import { getHeadToHead, type HeadToHeadEntry } from "@/lib/api";

export default function HeadToHeadMatrix() {
  const [entries, setEntries] = useState<HeadToHeadEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getHeadToHead()
      .then(setEntries)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="surface-card py-10 text-center text-muted-foreground">Loading head-to-head data...</div>;
  }

  if (entries.length === 0) {
    return (
      <div className="surface-card py-10 text-center text-muted-foreground">
        No head-to-head battles yet. Start battling to see matchup data!
      </div>
    );
  }

  return (
    <div className="surface-panel overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="border-b">
              <th className="p-4 text-left text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">Matchup</th>
              <th className="p-4 text-center text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">Wins A</th>
              <th className="p-4 text-center text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">Wins B</th>
              <th className="p-4 text-center text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">Ties</th>
              <th className="p-4 text-center text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">Total</th>
              <th className="p-4 text-center text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">Win Rate A</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, i) => {
              const winRateA = entry.total > 0 ? ((entry.a_wins / entry.total) * 100).toFixed(0) : "0";
              return (
                <tr key={i} className="border-b transition-colors hover:bg-muted/60">
                  <td className="p-4">
                    <span className="font-medium">{entry.model_a_name}</span>
                    <span className="text-muted-foreground mx-2">vs</span>
                    <span className="font-medium">{entry.model_b_name}</span>
                  </td>
                  <td className="p-4 text-center font-medium text-foreground">{entry.a_wins}</td>
                  <td className="p-4 text-center font-medium text-muted-foreground">{entry.b_wins}</td>
                  <td className="p-4 text-center text-muted-foreground">{entry.ties}</td>
                  <td className="p-4 text-center">{entry.total}</td>
                  <td className="p-4 text-center">
                    <div className="flex items-center gap-2 justify-center">
                      <div className="w-16 h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-primary"
                          style={{ width: `${winRateA}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium">{winRateA}%</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
