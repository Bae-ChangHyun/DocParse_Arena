"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  getProviders,
  createProvider,
  updateProvider,
  deleteProvider,
  testProvider,
  testAllProviders,
  getProviderModels,
  getAdminModels,
  createModel,
  updateModel,
  toggleModel,
  deleteModel,
  resetModelElo,
  getPrompts,
  createPrompt,
  updatePrompt,
  deletePrompt,
  getAuthStatus,
  adminLogin,
  setAdminToken,
  clearAdminToken,
  resetBattles,
  resetAll,
  matchRegistry,
  type ProviderSetting,
  type OcrModelAdmin,
  type OcrModelCreate,
  type PromptSetting,
  type PromptSettingCreate,
  type RegistryEntry,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Eye,
  EyeOff,
  Save,
  Plus,
  Pencil,
  Trash2,
  RotateCcw,
  Check,
  Loader2,
  KeyRound,
  Bot,
  MessageSquareText,
  Star,
  Wifi,
  WifiOff,
  Zap,
  X,
  Lock,
  AlertTriangle,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";

const BUILTIN_IDS = new Set(["claude", "openai", "gemini", "mistral", "ollama"]);

type SettingsSection = "providers" | "models" | "prompts" | "dangerous";

const SIDEBAR_ITEMS: { key: SettingsSection; label: string; icon: React.ReactNode; className?: string }[] = [
  { key: "providers", label: "API Providers", icon: <KeyRound className="h-4 w-4" /> },
  { key: "models", label: "Models", icon: <Bot className="h-4 w-4" /> },
  { key: "prompts", label: "Prompts", icon: <MessageSquareText className="h-4 w-4" /> },
  { key: "dangerous", label: "Danger Zone", icon: <AlertTriangle className="h-4 w-4" />, className: "text-destructive" },
];

// ── Provider Settings Section ────────────────────────────

function ProviderSettings() {
  const [providers, setProviders] = useState<ProviderSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [edits, setEdits] = useState<Record<string, Partial<ProviderSetting>>>({});
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; message: string }>>({});
  const [testingAll, setTestingAll] = useState(false);

  // Add custom provider dialog
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [newProvider, setNewProvider] = useState({ display_name: "", base_url: "", api_key: "" });
  const [addingProvider, setAddingProvider] = useState(false);

  const loadProviders = useCallback(() => {
    getProviders()
      .then(setProviders)
      .catch(console.error)
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
    } catch (e) {
      console.error(e);
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
        alert(`Connection failed. Disabled models: ${result.disabled_models.join(", ")}`);
      }
    } catch (e) {
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
        alert(`Disabled models due to connection failure:\n${result.total_disabled.join(", ")}`);
      }
    } catch (e) {
      console.error(e);
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
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed");
    }
    setAddingProvider(false);
  };

  const handleDeleteProvider = async (id: string, name: string) => {
    if (!confirm(`Delete provider "${name}"? Models using this provider must be removed first.`)) return;
    try {
      await deleteProvider(id);
      setProviders((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to delete");
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

      {/* Add Custom Provider Dialog */}
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

// ── Model Management Section ────────────────────────────

const EMPTY_FORM: OcrModelCreate & { config: Record<string, unknown> } = {
  name: "",
  display_name: "",
  icon: "\u{1F916}",
  provider: "",
  model_id: "",
  api_key: "",
  base_url: "",
  config: {},
  is_active: false,
};

function ModelManagement() {
  const [models, setModels] = useState<OcrModelAdmin[]>([]);
  const [providers, setProviders] = useState<ProviderSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<OcrModelCreate & { config: Record<string, unknown> }>(EMPTY_FORM);
  const [configText, setConfigText] = useState("{}");
  const [configError, setConfigError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [registryMatch, setRegistryMatch] = useState<RegistryEntry | null>(null);
  const [useRegistryPrompt, setUseRegistryPrompt] = useState(false);
  const [useRegistryPostprocessor, setUseRegistryPostprocessor] = useState(false);
  const registryDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [m, p] = await Promise.all([getAdminModels(), getProviders()]);
      setModels(m);
      setProviders(p);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // Debounce registry match check when model_id changes
  useEffect(() => {
    if (registryDebounceRef.current) clearTimeout(registryDebounceRef.current);
    if (!form.model_id || form.model_id.length < 3) {
      setRegistryMatch(null);
      return;
    }
    registryDebounceRef.current = setTimeout(() => {
      matchRegistry(form.model_id)
        .then((entry) => {
          setRegistryMatch(entry);
          if (entry) {
            setUseRegistryPrompt(true);
            setUseRegistryPostprocessor(!!entry.postprocessor);
          }
        })
        .catch(() => setRegistryMatch(null));
    }, 400);
    return () => {
      if (registryDebounceRef.current) clearTimeout(registryDebounceRef.current);
    };
  }, [form.model_id]);

  const applyRegistryConfig = () => {
    if (!registryMatch) return;
    const cfg: Record<string, unknown> = { ...(registryMatch.recommended_config || {}) };
    if (useRegistryPostprocessor && registryMatch.postprocessor) {
      cfg.postprocessor = registryMatch.postprocessor;
    }
    setConfigText(Object.keys(cfg).length > 0 ? JSON.stringify(cfg, null, 2) : "{}");
  };

  const fetchProviderModels = useCallback(async (providerId: string) => {
    if (!providerId) return;
    setLoadingModels(true);
    try {
      const modelIds = await getProviderModels(providerId);
      setAvailableModels(modelIds);
    } catch {
      setAvailableModels([]);
    }
    setLoadingModels(false);
  }, []);

  const openCreate = () => {
    setEditingId(null);
    const firstProvider = providers[0]?.id || "";
    setForm({ ...EMPTY_FORM, provider: firstProvider });
    setConfigText("{}");
    setConfigError("");
    setAvailableModels([]);
    setRegistryMatch(null);
    setUseRegistryPrompt(false);
    setUseRegistryPostprocessor(false);
    if (firstProvider) fetchProviderModels(firstProvider);
    setDialogOpen(true);
  };

  const openEdit = (model: OcrModelAdmin) => {
    setEditingId(model.id);
    const cfg = model.config || {};
    setForm({
      name: model.name,
      display_name: model.display_name,
      icon: model.icon,
      provider: model.provider,
      model_id: model.model_id,
      api_key: model.api_key,
      base_url: model.base_url,
      config: cfg,
      is_active: model.is_active,
    });
    setConfigText(Object.keys(cfg).length > 0 ? JSON.stringify(cfg, null, 2) : "{}");
    setConfigError("");
    setRegistryMatch(null);
    // Pre-set postprocessor toggle based on existing config
    setUseRegistryPostprocessor(!!cfg.postprocessor);
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    // Validate JSON config
    let parsedConfig: Record<string, unknown> = {};
    try {
      parsedConfig = JSON.parse(configText);
      if (typeof parsedConfig !== "object" || Array.isArray(parsedConfig)) {
        alert("Extra kwargs must be a JSON object");
        return;
      }
    } catch {
      alert("Invalid JSON in extra kwargs");
      return;
    }

    // Manage postprocessor in config based on registry toggle
    if (registryMatch?.postprocessor) {
      if (useRegistryPostprocessor) {
        parsedConfig.postprocessor = registryMatch.postprocessor;
      } else {
        delete parsedConfig.postprocessor;
      }
    }

    setSubmitting(true);
    try {
      const payload = { ...form, config: parsedConfig };
      let modelId = editingId;
      if (editingId) {
        await updateModel(editingId, payload);
      } else {
        const created = await createModel(payload);
        modelId = created.id;
      }

      // Create recommended prompt if user opted in (new model only)
      if (!editingId && useRegistryPrompt && registryMatch && modelId) {
        try {
          await createPrompt({
            name: `${registryMatch.display_name} (recommended)`,
            prompt_text: registryMatch.recommended_prompt,
            is_default: false,
            model_id: modelId,
          });
        } catch {
          // Non-critical: prompt creation failure shouldn't block model creation
        }
      }

      setDialogOpen(false);
      await loadData();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed");
    }
    setSubmitting(false);
  };

  const handleToggle = async (id: string) => {
    try {
      const updated = await toggleModel(id);
      setModels((prev) => prev.map((m) => (m.id === id ? updated : m)));
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete model "${name}"?`)) return;
    try {
      await deleteModel(id);
      setModels((prev) => prev.filter((m) => m.id !== id));
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to delete");
    }
  };

  const handleResetElo = async (id: string, name: string) => {
    if (!confirm(`Reset ELO for "${name}"? This will clear all win/loss stats.`)) return;
    try {
      const updated = await resetModelElo(id);
      setModels((prev) => prev.map((m) => (m.id === id ? updated : m)));
    } catch (e) {
      console.error(e);
    }
  };

  const getProviderName = (providerId: string) => {
    const p = providers.find((pr) => pr.id === providerId);
    return p?.display_name || providerId;
  };

  const selectedProvider = providers.find((p) => p.id === form.provider);
  const isUrlBasedProvider = selectedProvider && (selectedProvider.provider_type === "ollama" || selectedProvider.provider_type === "custom");

  if (loading) return <div className="text-center py-8 text-muted-foreground">Loading models...</div>;

  return (
    <>
      <div className="mb-2">
        <h2 className="text-lg font-semibold">Models</h2>
        <p className="text-sm text-muted-foreground">Manage OCR models for battle arena</p>
      </div>

      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-muted-foreground">
          {models.filter((m) => m.is_active).length} active / {models.length} total models.
          Only active models are used in battle.
        </p>
        <Button onClick={openCreate} className="gap-1.5">
          <Plus className="h-4 w-4" />
          Add Model
        </Button>
      </div>

      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">Active</TableHead>
              <TableHead>Model</TableHead>
              <TableHead>Provider</TableHead>
              <TableHead>Model ID</TableHead>
              <TableHead className="text-center">API Key</TableHead>
              <TableHead className="text-right">ELO</TableHead>
              <TableHead className="text-right">Battles</TableHead>
              <TableHead className="w-32">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {models.map((model) => (
              <TableRow key={model.id} className={!model.is_active ? "opacity-50" : ""}>
                <TableCell>
                  <Switch
                    checked={model.is_active}
                    onCheckedChange={() => handleToggle(model.id)}
                  />
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span>{model.icon}</span>
                    <div>
                      <div className="font-medium text-sm">{model.display_name}</div>
                      <div className="text-xs text-muted-foreground font-mono">{model.name}</div>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    <Badge variant="secondary" className="text-xs">{getProviderName(model.provider)}</Badge>
                    {model.provider_ok === false && (
                      <Badge variant="destructive" className="text-[10px] gap-0.5">
                        <WifiOff className="h-2.5 w-2.5" />
                        No Key
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell className="font-mono text-xs max-w-[200px] truncate">{model.model_id}</TableCell>
                <TableCell className="text-center">
                  {model.api_key ? (
                    <Check className="h-4 w-4 text-green-600 mx-auto" />
                  ) : (
                    <span className="text-xs text-muted-foreground">provider</span>
                  )}
                </TableCell>
                <TableCell className="text-right font-mono">{model.elo}</TableCell>
                <TableCell className="text-right">{model.total_battles}</TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(model)}>
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleResetElo(model.id, model.display_name)}>
                      <RotateCcw className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive"
                      onClick={() => handleDelete(model.id, model.display_name)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Add / Edit Model Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Model" : "Add New Model"}</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="grid grid-cols-[60px_1fr] gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Icon</Label>
                <Input
                  value={form.icon}
                  onChange={(e) => setForm({ ...form, icon: e.target.value })}
                  className="text-center text-lg"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Display Name</Label>
                <Input
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                  placeholder="GPT-4o Vision"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Unique Name (slug)</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="gpt-4o-vision"
                className="font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Provider</Label>
              <Select value={form.provider} onValueChange={(v) => {
                setForm({ ...form, provider: v, model_id: "" });
                fetchProviderModels(v);
              }}>
                <SelectTrigger>
                  <SelectValue placeholder="Select provider" />
                </SelectTrigger>
                <SelectContent>
                  {providers.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.display_name}
                      {!BUILTIN_IDS.has(p.id) && <span className="ml-1 text-muted-foreground">(custom)</span>}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs flex items-center gap-2">
                Model ID
                {loadingModels && <Loader2 className="h-3 w-3 animate-spin" />}
              </Label>
              {availableModels.length > 0 ? (
                <div className="space-y-1.5">
                  <Select value={form.model_id} onValueChange={(v) => setForm({ ...form, model_id: v })}>
                    <SelectTrigger className="font-mono">
                      <SelectValue placeholder="Select model" />
                    </SelectTrigger>
                    <SelectContent className="max-h-60">
                      {availableModels.map((m) => (
                        <SelectItem key={m} value={m} className="font-mono text-xs">
                          {m}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    value={form.model_id}
                    onChange={(e) => setForm({ ...form, model_id: e.target.value })}
                    placeholder="Or type manually..."
                    className="font-mono text-xs"
                  />
                </div>
              ) : (
                <Input
                  value={form.model_id}
                  onChange={(e) => setForm({ ...form, model_id: e.target.value })}
                  placeholder="gpt-4o / claude-sonnet-4-20250514 / ..."
                  className="font-mono"
                />
              )}
              <p className="text-[11px] text-muted-foreground">
                {availableModels.length > 0
                  ? `${availableModels.length} models found from provider API`
                  : "The actual model identifier sent to the API"}
              </p>
            </div>

            {registryMatch && (
              <div className="rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30 p-3 space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium text-blue-700 dark:text-blue-300">
                  <Info className="h-4 w-4 shrink-0" />
                  Registry: {registryMatch.display_name}
                </div>
                <p className="text-xs text-blue-600 dark:text-blue-400">
                  {registryMatch.notes}
                </p>

                <div className="space-y-2 pt-1">
                  {!editingId ? (
                    <div className="flex items-center gap-2">
                      <Switch
                        id="use-registry-prompt"
                        checked={useRegistryPrompt}
                        onCheckedChange={setUseRegistryPrompt}
                      />
                      <Label htmlFor="use-registry-prompt" className="text-xs text-blue-700 dark:text-blue-300">
                        Use recommended prompt
                      </Label>
                    </div>
                  ) : (
                    <p className="text-[11px] text-blue-600 dark:text-blue-400 italic">
                      Prompt can be managed in the Prompts tab
                    </p>
                  )}

                  {registryMatch.postprocessor && (
                    <div className="flex items-center gap-2">
                      <Switch
                        id="use-registry-postprocessor"
                        checked={useRegistryPostprocessor}
                        onCheckedChange={setUseRegistryPostprocessor}
                      />
                      <Label htmlFor="use-registry-postprocessor" className="text-xs text-blue-700 dark:text-blue-300">
                        Enable post-processing ({registryMatch.postprocessor})
                      </Label>
                    </div>
                  )}

                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="gap-1.5 text-xs border-blue-300 dark:border-blue-700"
                    onClick={applyRegistryConfig}
                  >
                    <Zap className="h-3 w-3" />
                    Apply recommended config
                  </Button>
                </div>
              </div>
            )}

            <div className="border-t pt-3 space-y-3">
              <p className="text-xs font-medium text-muted-foreground">
                Override credentials (leave empty to use provider-level settings)
              </p>
              <div className="space-y-1.5">
                <Label className="text-xs">API Key (optional)</Label>
                <Input
                  type="password"
                  value={form.api_key}
                  onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                  placeholder="Uses provider API key if empty"
                  className="font-mono text-sm"
                />
              </div>

              {isUrlBasedProvider && (
                <div className="space-y-1.5">
                  <Label className="text-xs">Base URL (optional)</Label>
                  <Input
                    value={form.base_url}
                    onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                    placeholder="Uses provider base URL if empty"
                    className="font-mono text-sm"
                  />
                </div>
              )}
            </div>

            <div className="border-t pt-3 space-y-1.5">
              <Label className="text-xs">Extra kwargs (JSON)</Label>
              <Textarea
                value={configText}
                onChange={(e) => {
                  setConfigText(e.target.value);
                  try {
                    JSON.parse(e.target.value);
                    setConfigError("");
                  } catch {
                    setConfigError("Invalid JSON");
                  }
                }}
                placeholder='{"max_completion_tokens": 4096, "temperature": 0.2}'
                rows={3}
                className={cn("font-mono text-xs", configError && "border-destructive")}
              />
              {configError && <p className="text-[11px] text-destructive">{configError}</p>}
              <p className="text-[11px] text-muted-foreground">
                Additional API call parameters as JSON. e.g. max_completion_tokens, temperature
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={submitting || !form.name || !form.display_name || !form.model_id || !form.provider}>
              {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              {editingId ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ── Prompt Management Section ────────────────────────────

function PromptManagement() {
  const [prompts, setPrompts] = useState<PromptSetting[]>([]);
  const [models, setModels] = useState<OcrModelAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<PromptSettingCreate>({
    name: "",
    prompt_text: "",
    is_default: false,
    model_id: null,
  });
  const [submitting, setSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [p, m] = await Promise.all([getPrompts(), getAdminModels()]);
      setPrompts(p);
      setModels(m);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const openCreate = () => {
    setEditingId(null);
    setForm({ name: "", prompt_text: "", is_default: false, model_id: null });
    setDialogOpen(true);
  };

  const openEdit = (prompt: PromptSetting) => {
    setEditingId(prompt.id);
    setForm({
      name: prompt.name,
      prompt_text: prompt.prompt_text,
      is_default: prompt.is_default,
      model_id: prompt.model_id,
    });
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      if (editingId) {
        await updatePrompt(editingId, form);
      } else {
        await createPrompt(form);
      }
      setDialogOpen(false);
      loadData();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed");
    }
    setSubmitting(false);
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete prompt "${name}"?`)) return;
    try {
      await deletePrompt(id);
      setPrompts((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to delete");
    }
  };

  const getModelName = (modelId: string | null) => {
    if (!modelId) return null;
    const model = models.find((m) => m.id === modelId);
    return model ? `${model.icon} ${model.display_name}` : modelId;
  };

  if (loading) return <div className="text-center py-8 text-muted-foreground">Loading prompts...</div>;

  const defaultPrompt = prompts.find((p) => p.is_default);
  const modelPrompts = prompts.filter((p) => p.model_id);
  const otherPrompts = prompts.filter((p) => !p.is_default && !p.model_id);

  return (
    <>
      <div className="mb-2">
        <h2 className="text-lg font-semibold">Prompts</h2>
        <p className="text-sm text-muted-foreground">
          Manage OCR prompts. Model-specific prompts override the default prompt.
        </p>
      </div>

      <div className="flex justify-end mb-4">
        <Button onClick={openCreate} className="gap-1.5">
          <Plus className="h-4 w-4" />
          Add Prompt
        </Button>
      </div>

      <div className="space-y-4">
        {defaultPrompt && (
          <Card className="border-primary/30">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Star className="h-4 w-4 text-primary fill-primary" />
                  <CardTitle className="text-base">{defaultPrompt.name}</CardTitle>
                  <Badge variant="default" className="text-xs">Default</Badge>
                </div>
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(defaultPrompt)}>
                  <Pencil className="h-3.5 w-3.5" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <pre className="text-xs bg-muted p-3 rounded-md whitespace-pre-wrap font-mono max-h-32 overflow-y-auto">
                {defaultPrompt.prompt_text}
              </pre>
            </CardContent>
          </Card>
        )}

        {modelPrompts.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Model-Specific Prompts</h3>
            <div className="space-y-3">
              {modelPrompts.map((prompt) => (
                <Card key={prompt.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-base">{prompt.name}</CardTitle>
                        <Badge variant="secondary" className="text-xs">{getModelName(prompt.model_id)}</Badge>
                      </div>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(prompt)}>
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => handleDelete(prompt.id, prompt.name)}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <pre className="text-xs bg-muted p-3 rounded-md whitespace-pre-wrap font-mono max-h-24 overflow-y-auto">
                      {prompt.prompt_text}
                    </pre>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {otherPrompts.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Other Prompts</h3>
            <div className="space-y-3">
              {otherPrompts.map((prompt) => (
                <Card key={prompt.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">{prompt.name}</CardTitle>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(prompt)}>
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => handleDelete(prompt.id, prompt.name)}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <pre className="text-xs bg-muted p-3 rounded-md whitespace-pre-wrap font-mono max-h-24 overflow-y-auto">
                      {prompt.prompt_text}
                    </pre>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {prompts.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No prompts configured. Add one to customize OCR behavior.
          </div>
        )}
      </div>

      {/* Add / Edit Prompt Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Prompt" : "Add New Prompt"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label className="text-xs">Name</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g., Default OCR Prompt, Claude Detailed Prompt"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Prompt Text</Label>
              <Textarea
                value={form.prompt_text}
                onChange={(e) => setForm({ ...form, prompt_text: e.target.value })}
                placeholder="You are a document OCR assistant..."
                rows={8}
                className="font-mono text-sm max-h-64 overflow-y-auto"
              />
            </div>
            <div className="flex items-center gap-2">
              <Switch
                id="is-default"
                checked={form.is_default}
                onCheckedChange={(v) => setForm({ ...form, is_default: v, model_id: v ? null : form.model_id })}
              />
              <Label htmlFor="is-default" className="text-sm">Set as default prompt</Label>
            </div>
            {!form.is_default && (
              <div className="space-y-1.5">
                <Label className="text-xs">Assign to Model (optional)</Label>
                <Select
                  value={form.model_id || "_none"}
                  onValueChange={(v) => setForm({ ...form, model_id: v === "_none" ? null : v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="No specific model" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_none">No specific model</SelectItem>
                    {models.map((m) => (
                      <SelectItem key={m.id} value={m.id}>{m.icon} {m.display_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-[11px] text-muted-foreground">
                  When assigned, this prompt overrides the default for that model
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={submitting || !form.name || !form.prompt_text}>
              {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              {editingId ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ── Danger Zone Section ────────────────────────────

function DangerZone() {
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
      alert("All battle records have been deleted and ELO ratings reset.");
    } catch (e) {
      alert(e instanceof Error ? e.message : "Reset failed");
    }
    setResetting(false);
  };

  const handleFactoryReset = async () => {
    if (factoryConfirmText !== "FACTORY RESET") return;
    setFactoryResetting(true);
    try {
      await resetAll();
      setFactoryConfirmText("");
      alert("Factory reset complete. All battles, prompts deleted and ELO reset.");
    } catch (e) {
      alert(e instanceof Error ? e.message : "Reset failed");
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

// ── Auth Gate ────────────────────────────

function AuthGate({ children }: { children: React.ReactNode }) {
  const [checking, setChecking] = useState(true);
  const [authRequired, setAuthRequired] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loggingIn, setLoggingIn] = useState(false);

  useEffect(() => {
    getAuthStatus()
      .then(({ auth_required }) => {
        setAuthRequired(auth_required);
        if (!auth_required) setAuthenticated(true);
      })
      .catch(console.error)
      .finally(() => setChecking(false));
  }, []);

  const handleLogin = async () => {
    setLoggingIn(true);
    setLoginError("");
    try {
      const { token } = await adminLogin(password);
      setAdminToken(token);
      setAuthenticated(true);
    } catch {
      setLoginError("Invalid password");
    }
    setLoggingIn(false);
  };

  if (checking) {
    return (
      <div className="container mx-auto px-4 py-20 max-w-md text-center">
        <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
      </div>
    );
  }

  if (authRequired && !authenticated) {
    return (
      <div className="container mx-auto px-4 py-20 max-w-md">
        <Card>
          <CardHeader className="text-center">
            <div className="mx-auto mb-2 h-12 w-12 rounded-full bg-muted flex items-center justify-center">
              <Lock className="h-6 w-6 text-muted-foreground" />
            </div>
            <CardTitle>Admin Authentication</CardTitle>
            <CardDescription>Enter the admin password to access settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleLogin()}
                autoFocus
              />
              {loginError && (
                <p className="text-sm text-destructive">{loginError}</p>
              )}
            </div>
            <Button className="w-full" onClick={handleLogin} disabled={loggingIn || !password}>
              {loggingIn ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Sign In
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
}

// ── Main Settings Page with Sidebar ────────────────────────────

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
          {/* Sidebar */}
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

          {/* Content */}
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
