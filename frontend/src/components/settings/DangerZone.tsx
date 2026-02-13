"use client";

import { useState } from "react";
import { toast } from "sonner";
import { resetBattles, resetAll } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, AlertTriangle } from "lucide-react";

export default function DangerZone() {
  const [confirmText, setConfirmText] = useState("");
  const [resetting, setResetting] = useState(false);
  const [factoryConfirmText, setFactoryConfirmText] = useState("");
  const [factoryResetting, setFactoryResetting] = useState(false);

  const handleResetBattles = async () => {
    if (confirmText !== "RESET") return;
    setResetting(true);
    try {
      await resetBattles();
      setConfirmText("");
      toast.success("All battle records have been deleted and ELO ratings reset.");
    } catch (e) {
      toast.error("Reset failed", { description: e instanceof Error ? e.message : "Unknown error" });
    }
    setResetting(false);
  };

  const handleFactoryReset = async () => {
    if (factoryConfirmText !== "FACTORY RESET") return;
    setFactoryResetting(true);
    try {
      await resetAll();
      setFactoryConfirmText("");
      toast.success("Factory reset complete. All battles, prompts deleted and ELO reset.");
    } catch (e) {
      toast.error("Reset failed", { description: e instanceof Error ? e.message : "Unknown error" });
    }
    setFactoryResetting(false);
  };

  return (
    <div className="space-y-6">
      <div className="mb-2">
        <h2 className="text-lg font-semibold text-destructive">Danger Zone</h2>
        <p className="text-sm text-muted-foreground">
          Irreversible operations. Proceed with caution.
        </p>
      </div>

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-base">Reset Battle Records</CardTitle>
          <CardDescription>
            Delete all battle history and reset ELO ratings for all models back to 1500.
            Models and their configurations will be preserved.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">
              Type <span className="font-mono font-bold text-foreground">RESET</span> to confirm
            </Label>
            <div className="flex gap-2">
              <Input
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="RESET"
                className="font-mono max-w-[200px]"
              />
              <Button
                variant="destructive"
                onClick={handleResetBattles}
                disabled={confirmText !== "RESET" || resetting}
              >
                {resetting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                Reset Battles
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="text-base text-destructive">Factory Reset</CardTitle>
          <CardDescription>
            Delete all battles, all custom prompts, and reset ELO ratings.
            Models and provider settings will be preserved, but all statistics and prompts are lost.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            <div className="flex gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>This action cannot be undone. All battle data and custom prompts will be permanently deleted.</span>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">
              Type <span className="font-mono font-bold text-foreground">FACTORY RESET</span> to confirm
            </Label>
            <div className="flex gap-2">
              <Input
                value={factoryConfirmText}
                onChange={(e) => setFactoryConfirmText(e.target.value)}
                placeholder="FACTORY RESET"
                className="font-mono max-w-[200px]"
              />
              <Button
                variant="destructive"
                onClick={handleFactoryReset}
                disabled={factoryConfirmText !== "FACTORY RESET" || factoryResetting}
              >
                {factoryResetting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                Factory Reset
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
