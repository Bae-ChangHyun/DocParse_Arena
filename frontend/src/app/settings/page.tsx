"use client";

import { useState } from "react";
import AuthGate from "@/components/settings/AuthGate";
import ProviderSettings from "@/components/settings/ProviderSettings";
import ModelManagement from "@/components/settings/ModelManagement";
import PromptManagement from "@/components/settings/PromptManagement";
import DangerZone from "@/components/settings/DangerZone";
import { KeyRound, Bot, MessageSquareText, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

type SettingsSection = "providers" | "models" | "prompts" | "dangerous";

const SIDEBAR_ITEMS: { key: SettingsSection; label: string; icon: React.ReactNode; className?: string }[] = [
  { key: "providers", label: "API Providers", icon: <KeyRound className="h-4 w-4" /> },
  { key: "models", label: "Models", icon: <Bot className="h-4 w-4" /> },
  { key: "prompts", label: "Prompts", icon: <MessageSquareText className="h-4 w-4" /> },
  { key: "dangerous", label: "Danger Zone", icon: <AlertTriangle className="h-4 w-4" />, className: "text-destructive" },
];

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState<SettingsSection>("providers");

  return (
    <AuthGate>
      <div className="mx-auto max-w-[1200px] px-4 py-8">
        <div className="mb-8 max-w-3xl">
          <div className="mb-3 inline-flex rounded-full border border-border px-3 py-1 text-xs font-medium tracking-[0.01em] text-muted-foreground">
            Control room
          </div>
          <h1 className="font-display text-5xl font-medium leading-tight">Settings</h1>
          <p className="mt-2 text-muted-foreground">
            Manage API providers, OCR models, and prompts
          </p>
        </div>

        <div className="flex flex-col gap-6 md:flex-row">
          <nav className="w-full shrink-0 md:w-56">
            <div className="surface-card grid grid-cols-2 gap-1 p-2 md:sticky md:top-24 md:block md:space-y-1">
              {SIDEBAR_ITEMS.map((item) => (
                <button
                  key={item.key}
                  onClick={() => setActiveSection(item.key)}
                  className={cn(
                    "w-full flex items-center gap-2 rounded-[10px] px-3 py-2.5 text-sm transition-colors text-left",
                    activeSection === item.key
                      ? item.key === "dangerous"
                        ? "bg-destructive text-destructive-foreground font-medium"
                        : "bg-primary text-primary-foreground font-medium"
                      : item.className || "hover:bg-muted text-muted-foreground hover:text-foreground"
                  )}
                >
                  {item.icon}
                  {item.label}
                </button>
              ))}
            </div>
          </nav>

          <div className="flex-1 min-w-0">
            {activeSection === "providers" && <ProviderSettings />}
            {activeSection === "models" && <ModelManagement />}
            {activeSection === "prompts" && <PromptManagement />}
            {activeSection === "dangerous" && <DangerZone />}
          </div>
        </div>
      </div>
    </AuthGate>
  );
}
