"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { toast } from "sonner";
import {
  getProviders,
  getAdminModels,
  createModel,
  updateModel,
  toggleModel,
  deleteModel,
  resetModelElo,
  getProviderModels,
  createPrompt,
  matchRegistry,
  type ProviderSetting,
  type OcrModelAdmin,
  type OcrModelCreate,
  type RegistryEntry,
} from "@/lib/api";
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
  Plus,
  Pencil,
  Trash2,
  RotateCcw,
  Check,
  Loader2,
  WifiOff,
  Zap,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";

const BUILTIN_IDS = new Set(["claude", "openai", "gemini", "mistral", "ollama"]);

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

export default function ModelManagement() {
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
      toast.error("Failed to load models", { description: String(e) });
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

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
    setUseRegistryPostprocessor(!!cfg.postprocessor);
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    let parsedConfig: Record<string, unknown> = {};
    try {
      parsedConfig = JSON.parse(configText);
      if (typeof parsedConfig !== "object" || Array.isArray(parsedConfig)) {
        toast.error("Extra kwargs must be a JSON object");
        return;
      }
    } catch {
      toast.error("Invalid JSON in extra kwargs");
      return;
    }

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

      if (!editingId && useRegistryPrompt && registryMatch && modelId) {
        try {
          await createPrompt({
            name: `${registryMatch.display_name} (recommended)`,
            prompt_text: registryMatch.recommended_prompt,
            is_default: false,
            model_id: modelId,
          });
        } catch {
          // Non-critical
        }
      }

      setDialogOpen(false);
      await loadData();
      toast.success(editingId ? "Model updated" : "Model created");
    } catch (e) {
      toast.error("Failed to save model", { description: e instanceof Error ? e.message : "Unknown error" });
    }
    setSubmitting(false);
  };

  const handleToggle = async (id: string) => {
    try {
      const updated = await toggleModel(id);
      setModels((prev) => prev.map((m) => (m.id === id ? updated : m)));
    } catch (e) {
      toast.error("Failed to toggle model", { description: String(e) });
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete model "${name}"?`)) return;
    try {
      await deleteModel(id);
      setModels((prev) => prev.filter((m) => m.id !== id));
      toast.success(`Model "${name}" deleted`);
    } catch (e) {
      toast.error("Failed to delete", { description: e instanceof Error ? e.message : "Unknown error" });
    }
  };

  const handleResetElo = async (id: string, name: string) => {
    if (!confirm(`Reset ELO for "${name}"? This will clear all win/loss stats.`)) return;
    try {
      const updated = await resetModelElo(id);
      setModels((prev) => prev.map((m) => (m.id === id ? updated : m)));
      toast.success(`ELO reset for "${name}"`);
    } catch (e) {
      toast.error("Failed to reset ELO", { description: String(e) });
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
