"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getProviders,
  updateProvider,
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
  type ProviderSetting,
  type OcrModelAdmin,
  type OcrModelCreate,
  type PromptSetting,
  type PromptSettingCreate,
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
} from "lucide-react";
import { cn } from "@/lib/utils";

const PROVIDER_OPTIONS = [
  { value: "claude", label: "Anthropic Claude" },
  { value: "openai", label: "OpenAI" },
  { value: "gemini", label: "Google Gemini" },
  { value: "mistral", label: "Mistral AI" },
  { value: "ollama", label: "Ollama (Local)" },
  { value: "custom", label: "Custom (OpenAI-compatible)" },
];

type SettingsSection = "providers" | "models" | "prompts";

const SIDEBAR_ITEMS: { key: SettingsSection; label: string; icon: React.ReactNode }[] = [
  { key: "providers", label: "API Providers", icon: <KeyRound className="h-4 w-4" /> },
  { key: "models", label: "Models", icon: <Bot className="h-4 w-4" /> },
  { key: "prompts", label: "Prompts", icon: <MessageSquareText className="h-4 w-4" /> },
];

// ── Provider Settings Section ────────────────────────────

function ProviderSettings() {
  const [providers, setProviders] = useState<ProviderSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [edits, setEdits] = useState<Record<string, Partial<ProviderSetting>>>({});

  useEffect(() => {
    getProviders()
      .then(setProviders)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

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

  if (loading) return <div className="text-center py-8 text-muted-foreground">Loading providers...</div>;

  return (
    <div className="space-y-4">
      <div className="mb-2">
        <h2 className="text-lg font-semibold">API Providers</h2>
        <p className="text-sm text-muted-foreground">Configure API keys and endpoints for each provider</p>
      </div>
      {providers.map((provider) => (
        <Card key={provider.id}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">{provider.display_name}</CardTitle>
                <CardDescription className="text-xs font-mono">{provider.id}</CardDescription>
              </div>
              <Switch
                checked={getValue(provider, "is_enabled") as boolean}
                onCheckedChange={(v) => setEdit(provider.id, "is_enabled", v)}
              />
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
                    placeholder={provider.id === "ollama" ? "(not required)" : "Enter API key..."}
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
                    {showKeys[provider.id] ? (
                      <EyeOff className="h-3.5 w-3.5" />
                    ) : (
                      <Eye className="h-3.5 w-3.5" />
                    )}
                  </Button>
                </div>
              </div>
            </div>

            {(provider.id === "ollama" || provider.id === "custom") && (
              <div className="space-y-1.5">
                <Label className="text-xs">Base URL</Label>
                <Input
                  value={(getValue(provider, "base_url") as string) || ""}
                  onChange={(e) => setEdit(provider.id, "base_url", e.target.value)}
                  placeholder={provider.id === "ollama" ? "http://localhost:11434" : "https://your-endpoint.com/v1"}
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
                  {saving === provider.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Save className="h-3.5 w-3.5" />
                  )}
                  Save
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Model Management Section ────────────────────────────

const EMPTY_FORM: OcrModelCreate = {
  name: "",
  display_name: "",
  icon: "\u{1F916}",
  provider: "openai",
  model_id: "",
  api_key: "",
  base_url: "",
  is_active: true,
};

function ModelManagement() {
  const [models, setModels] = useState<OcrModelAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<OcrModelCreate>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  const loadModels = useCallback(() => {
    getAdminModels()
      .then(setModels)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadModels(); }, [loadModels]);

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (model: OcrModelAdmin) => {
    setEditingId(model.id);
    setForm({
      name: model.name,
      display_name: model.display_name,
      icon: model.icon,
      provider: model.provider,
      model_id: model.model_id,
      api_key: model.api_key,
      base_url: model.base_url,
      is_active: model.is_active,
    });
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      if (editingId) {
        await updateModel(editingId, form);
      } else {
        await createModel(form);
      }
      setDialogOpen(false);
      loadModels();
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
                  <Badge variant="secondary" className="text-xs">{model.provider}</Badge>
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

      {/* Add / Edit Dialog */}
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
                disabled={!!editingId}
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Provider</Label>
              <Select value={form.provider} onValueChange={(v) => setForm({ ...form, provider: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PROVIDER_OPTIONS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Model ID</Label>
              <Input
                value={form.model_id}
                onChange={(e) => setForm({ ...form, model_id: e.target.value })}
                placeholder="gpt-4o / claude-sonnet-4-20250514 / ..."
                className="font-mono"
              />
              <p className="text-[11px] text-muted-foreground">
                The actual model identifier sent to the API
              </p>
            </div>

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

              {(form.provider === "ollama" || form.provider === "custom") && (
                <div className="space-y-1.5">
                  <Label className="text-xs">Base URL (optional)</Label>
                  <Input
                    value={form.base_url}
                    onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                    placeholder="https://your-endpoint.com/v1"
                    className="font-mono text-sm"
                  />
                </div>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={submitting || !form.name || !form.display_name || !form.model_id}>
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
        {/* Default Prompt */}
        {defaultPrompt && (
          <Card className="border-primary/30">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Star className="h-4 w-4 text-primary fill-primary" />
                  <CardTitle className="text-base">{defaultPrompt.name}</CardTitle>
                  <Badge variant="default" className="text-xs">Default</Badge>
                </div>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(defaultPrompt)}>
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <pre className="text-xs bg-muted p-3 rounded-md whitespace-pre-wrap font-mono max-h-32 overflow-y-auto">
                {defaultPrompt.prompt_text}
              </pre>
            </CardContent>
          </Card>
        )}

        {/* Model-specific Prompts */}
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
                        <Badge variant="secondary" className="text-xs">
                          {getModelName(prompt.model_id)}
                        </Badge>
                      </div>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(prompt)}>
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost" size="icon" className="h-7 w-7 text-destructive"
                          onClick={() => handleDelete(prompt.id, prompt.name)}
                        >
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

        {/* Other Prompts */}
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
                        <Button
                          variant="ghost" size="icon" className="h-7 w-7 text-destructive"
                          onClick={() => handleDelete(prompt.id, prompt.name)}
                        >
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
        <DialogContent className="max-w-2xl">
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
                className="font-mono text-sm"
              />
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Switch
                  id="is-default"
                  checked={form.is_default}
                  onCheckedChange={(v) => setForm({ ...form, is_default: v, model_id: v ? null : form.model_id })}
                />
                <Label htmlFor="is-default" className="text-sm">Set as default prompt</Label>
              </div>
            </div>

            {!form.is_default && (
              <div className="space-y-1.5">
                <Label className="text-xs">Assign to Model (optional)</Label>
                <Select
                  value={form.model_id || "_none"}
                  onValueChange={(v) => setForm({ ...form, model_id: v === "_none" ? null : v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="No specific model (standalone prompt)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_none">No specific model</SelectItem>
                    {models.map((m) => (
                      <SelectItem key={m.id} value={m.id}>
                        {m.icon} {m.display_name}
                      </SelectItem>
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
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
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

// ── Main Settings Page with Sidebar ────────────────────────────

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState<SettingsSection>("providers");

  return (
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
                    ? "bg-primary text-primary-foreground font-medium"
                    : "hover:bg-muted text-muted-foreground hover:text-foreground"
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
        </div>
      </div>
    </div>
  );
}
