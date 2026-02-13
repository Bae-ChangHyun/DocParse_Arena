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
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-muted-foreground mt-1">
            Manage API providers, OCR models, and prompts
          </p>
        </div>

        <div className="flex gap-6">
          <nav className="w-48 shrink-0">
            <div className="sticky top-20 space-y-1">
              {SIDEBAR_ITEMS.map((item) => (
                <button
                  key={item.key}
                  onClick={() => setActiveSection(item.key)}
                  className={cn(
                    "w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-colors text-left",
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
