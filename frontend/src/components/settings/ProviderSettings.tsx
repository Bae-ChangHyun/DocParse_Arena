"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import {
  getProviders,
  createProvider,
  updateProvider,
  deleteProvider,
  testProvider,
  testAllProviders,
  type ProviderSetting,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Eye,
  EyeOff,
  Save,
  Plus,
  Trash2,
  Loader2,
  Wifi,
  WifiOff,
  Zap,
} from "lucide-react";

const BUILTIN_IDS = new Set(["claude", "openai", "gemini", "mistral", "ollama"]);

export default function ProviderSettings() {
  const [providers, setProviders] = useState<ProviderSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [edits, setEdits] = useState<Record<string, Partial<ProviderSetting>>>({});
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; message: string }>>({});
  const [testingAll, setTestingAll] = useState(false);

  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [newProvider, setNewProvider] = useState({ display_name: "", base_url: "", api_key: "" });
  const [addingProvider, setAddingProvider] = useState(false);

  const loadProviders = useCallback(() => {
    getProviders()
      .then(setProviders)
      .catch((e) => toast.error("Failed to load providers", { description: String(e) }))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadProviders(); }, [loadProviders]);

  const handleSave = async (id: string) => {
    const changes = edits[id];
    if (!changes) return;
    setSaving(id);
    try {
      const updated = await updateProvider(id, changes);
      setProviders((prev) => prev.map((p) => (p.id === id ? updated : p)));
      setEdits((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      toast.success("Provider saved");
    } catch (e) {
      toast.error("Failed to save provider", { description: String(e) });
    }
    setSaving(null);
  };

  const setEdit = (id: string, field: string, value: string | boolean) => {
    setEdits((prev) => ({
      ...prev,
      [id]: { ...prev[id], [field]: value },
    }));
  };

  const getValue = (provider: ProviderSetting, field: keyof ProviderSetting) => {
    const edit = edits[provider.id];
    if (edit && field in edit) return edit[field as keyof typeof edit];
    return provider[field];
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      const result = await testProvider(id);
      setTestResults((prev) => ({ ...prev, [id]: { ok: result.ok, message: result.message } }));
      if (result.disabled_models.length > 0) {
        toast.warning(`Disabled models: ${result.disabled_models.join(", ")}`);
      }
    } catch {
      setTestResults((prev) => ({ ...prev, [id]: { ok: false, message: "Test failed" } }));
    }
    setTesting(null);
  };

  const handleTestAll = async () => {
    setTestingAll(true);
    try {
      const result = await testAllProviders();
      const newResults: Record<string, { ok: boolean; message: string }> = {};
      for (const r of result.results) {
        newResults[r.provider_id] = { ok: r.ok, message: r.message };
      }
      setTestResults(newResults);
      if (result.total_disabled.length > 0) {
        toast.warning(`Disabled models:\n${result.total_disabled.join(", ")}`);
      }
    } catch (e) {
      toast.error("Test all failed", { description: String(e) });
    }
    setTestingAll(false);
  };

  const handleAddCustom = async () => {
    setAddingProvider(true);
    try {
      await createProvider({
        display_name: newProvider.display_name,
        provider_type: "custom",
        base_url: newProvider.base_url,
        api_key: newProvider.api_key,
        is_enabled: true,
      });
      setAddDialogOpen(false);
      setNewProvider({ display_name: "", base_url: "", api_key: "" });
      loadProviders();
      toast.success("Custom provider created");
    } catch (e) {
      toast.error("Failed to create provider", { description: e instanceof Error ? e.message : "Unknown error" });
    }
    setAddingProvider(false);
  };

  const handleDeleteProvider = async (id: string, name: string) => {
    if (!confirm(`Delete provider "${name}"? Models using this provider must be removed first.`)) return;
    try {
      await deleteProvider(id);
      setProviders((prev) => prev.filter((p) => p.id !== id));
      toast.success(`Provider "${name}" deleted`);
    } catch (e) {
      toast.error("Failed to delete", { description: e instanceof Error ? e.message : "Unknown error" });
    }
  };

  const isUrlBased = (p: ProviderSetting) =>
    p.provider_type === "ollama" || p.provider_type === "custom";

  if (loading) return <div className="text-center py-8 text-muted-foreground">Loading providers...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h2 className="text-lg font-semibold">API Providers</h2>
          <p className="text-sm text-muted-foreground">Configure API keys and endpoints</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleTestAll} disabled={testingAll} className="gap-1.5">
            {testingAll ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
            Test All
          </Button>
          <Button size="sm" onClick={() => setAddDialogOpen(true)} className="gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            Add Custom
          </Button>
        </div>
      </div>

      {providers.map((provider) => (
        <Card key={provider.id} className={testResults[provider.id] ? (testResults[provider.id].ok ? "border-green-500/30" : "border-red-500/30") : ""}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                {BUILTIN_IDS.has(provider.id) ? (
                  <>
                    <CardTitle className="text-base">{provider.display_name}</CardTitle>
                    <CardDescription className="text-xs font-mono">{provider.id}</CardDescription>
                  </>
                ) : (
                  <>
                    <div className="flex items-center gap-2">
                      <Input
                        value={(getValue(provider, "display_name") as string) || ""}
                        onChange={(e) => setEdit(provider.id, "display_name", e.target.value)}
                        className="h-7 text-sm font-semibold w-48"
                      />
                      <Badge variant="outline" className="text-[10px]">custom</Badge>
                    </div>
                    <CardDescription className="text-xs font-mono mt-0.5">{provider.id.slice(0, 8)}...</CardDescription>
                  </>
                )}
              </div>
              <div className="flex items-center gap-2">
                {testResults[provider.id] && (
                  <Badge variant={testResults[provider.id].ok ? "default" : "destructive"} className="text-[10px] gap-1 shrink-0">
                    {testResults[provider.id].ok ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
                    {testResults[provider.id].message}
                  </Badge>
                )}
                <Button variant="ghost" size="sm" onClick={() => handleTest(provider.id)} disabled={testing === provider.id} className="gap-1 h-7 px-2 text-xs shrink-0">
                  {testing === provider.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Wifi className="h-3 w-3" />}
                  Test
                </Button>
                {!BUILTIN_IDS.has(provider.id) && (
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive shrink-0" onClick={() => handleDeleteProvider(provider.id, provider.display_name)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                )}
                <Switch
                  checked={getValue(provider, "is_enabled") as boolean}
                  onCheckedChange={(v) => setEdit(provider.id, "is_enabled", v)}
                />
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label className="text-xs">API Key</Label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Input
                    type={showKeys[provider.id] ? "text" : "password"}
                    value={(getValue(provider, "api_key") as string) || ""}
                    onChange={(e) => setEdit(provider.id, "api_key", e.target.value)}
                    placeholder={provider.provider_type === "ollama" ? "(not required)" : "Enter API key..."}
                    className="pr-10 font-mono text-sm"
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full w-9"
                    onClick={() =>
                      setShowKeys((prev) => ({ ...prev, [provider.id]: !prev[provider.id] }))
                    }
                  >
                    {showKeys[provider.id] ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  </Button>
                </div>
              </div>
            </div>

            {isUrlBased(provider) && (
              <div className="space-y-1.5">
                <Label className="text-xs">Base URL</Label>
                <Input
                  value={(getValue(provider, "base_url") as string) || ""}
                  onChange={(e) => setEdit(provider.id, "base_url", e.target.value)}
                  placeholder={provider.provider_type === "ollama" ? "http://localhost:11434" : "https://your-endpoint.com/v1"}
                  className="font-mono text-sm"
                />
              </div>
            )}

            {edits[provider.id] && (
              <div className="flex justify-end">
                <Button
                  size="sm"
                  onClick={() => handleSave(provider.id)}
                  disabled={saving === provider.id}
                  className="gap-1.5"
                >
                  {saving === provider.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                  Save
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      ))}

      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add Custom Provider</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label className="text-xs">Provider Name</Label>
              <Input
                value={newProvider.display_name}
                onChange={(e) => setNewProvider({ ...newProvider, display_name: e.target.value })}
                placeholder="e.g., My vLLM Server, LiteLLM Gateway"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Base URL</Label>
              <Input
                value={newProvider.base_url}
                onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })}
                placeholder="https://your-endpoint.com/v1"
                className="font-mono text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">API Key (optional)</Label>
              <Input
                type="password"
                value={newProvider.api_key}
                onChange={(e) => setNewProvider({ ...newProvider, api_key: e.target.value })}
                placeholder="Leave empty if not required"
                className="font-mono text-sm"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleAddCustom} disabled={addingProvider || !newProvider.display_name || !newProvider.base_url}>
              {addingProvider ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
