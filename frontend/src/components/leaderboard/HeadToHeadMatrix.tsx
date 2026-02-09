"use client";

import { useEffect, useState } from "react";
import { getHeadToHead, type HeadToHeadEntry } from "@/lib/api";

export default function HeadToHeadMatrix() {
  const [entries, setEntries] = useState<HeadToHeadEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getHeadToHead()
      .then(setEntries)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-center py-8 text-muted-foreground">Loading head-to-head data...</div>;
  }

  if (entries.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No head-to-head battles yet. Start battling to see matchup data!
      </div>
    );
  }

  return (
    <div className="rounded-lg border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/30">
              <th className="p-3 text-left font-medium">Matchup</th>
              <th className="p-3 text-center font-medium">Wins A</th>
              <th className="p-3 text-center font-medium">Wins B</th>
              <th className="p-3 text-center font-medium">Ties</th>
              <th className="p-3 text-center font-medium">Total</th>
              <th className="p-3 text-center font-medium">Win Rate A</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, i) => {
              const winRateA = entry.total > 0 ? ((entry.a_wins / entry.total) * 100).toFixed(0) : "0";
              return (
                <tr key={i} className="border-b">
                  <td className="p-3">
                    <span className="font-medium">{entry.model_a_name}</span>
                    <span className="text-muted-foreground mx-2">vs</span>
                    <span className="font-medium">{entry.model_b_name}</span>
                  </td>
                  <td className="p-3 text-center text-green-600 font-medium">{entry.a_wins}</td>
                  <td className="p-3 text-center text-blue-600 font-medium">{entry.b_wins}</td>
                  <td className="p-3 text-center text-muted-foreground">{entry.ties}</td>
                  <td className="p-3 text-center">{entry.total}</td>
                  <td className="p-3 text-center">
                    <div className="flex items-center gap-2 justify-center">
                      <div className="w-16 h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full bg-green-500 rounded-full"
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
