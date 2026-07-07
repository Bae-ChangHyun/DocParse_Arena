"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import {
  getPrompts,
  getAdminModels,
  createPrompt,
  updatePrompt,
  deletePrompt,
  type OcrModelAdmin,
  type PromptSetting,
  type PromptSettingCreate,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  Plus,
  Pencil,
  Trash2,
  Loader2,
  Star,
} from "lucide-react";

export default function PromptManagement() {
  const [prompts, setPrompts] = useState<PromptSetting[]>([]);
  const [models, setModels] = useState<OcrModelAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<PromptSettingCreate>({
    name: "",
    prompt_text: "",
    user_prompt_text: "",
    is_default: false,
    model_id: null,
    benchmark: null,
  });
  const [submitting, setSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [p, m] = await Promise.all([getPrompts(), getAdminModels()]);
      setPrompts(p);
      setModels(m);
    } catch (e) {
      toast.error("Failed to load prompts", { description: String(e) });
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void Promise.resolve().then(loadData);
  }, [loadData]);

  const openCreate = () => {
    setEditingId(null);
    setForm({ name: "", prompt_text: "", user_prompt_text: "", is_default: false, model_id: null, benchmark: null });
    setDialogOpen(true);
  };

  const openEdit = (prompt: PromptSetting) => {
    setEditingId(prompt.id);
    setForm({
      name: prompt.name,
      prompt_text: prompt.prompt_text,
      user_prompt_text: prompt.user_prompt_text ?? "",
      is_default: prompt.is_default,
      model_id: prompt.model_id,
      benchmark: prompt.benchmark ?? null,
    });
    setDialogOpen(true);
  };

  const benchmarkLabel = (b: string | null) =>
    b === "omnidocbench" ? "OmniDocBench" : b === "olmocr_bench" ? "olmOCR-Bench" : null;

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
      toast.success(editingId ? "Prompt updated" : "Prompt created");
    } catch (e) {
      toast.error("Failed to save prompt", { description: e instanceof Error ? e.message : "Unknown error" });
    }
    setSubmitting(false);
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete prompt "${name}"?`)) return;
    try {
      await deletePrompt(id);
      setPrompts((prev) => prev.filter((p) => p.id !== id));
      toast.success(`Prompt "${name}" deleted`);
    } catch (e) {
      toast.error("Failed to delete", { description: e instanceof Error ? e.message : "Unknown error" });
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
          <Card className="border-foreground/20">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Star className="h-4 w-4 fill-foreground text-foreground" />
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
                        {prompt.benchmark && (
                          <Badge variant="outline" className="text-xs">{benchmarkLabel(prompt.benchmark)}</Badge>
                        )}
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
                  <CardContent className="space-y-2">
                    {prompt.prompt_text && (
                      <div>
                        <p className="text-[11px] text-muted-foreground mb-1">System</p>
                        <pre className="text-xs bg-muted p-3 rounded-md whitespace-pre-wrap font-mono max-h-24 overflow-y-auto">
                          {prompt.prompt_text}
                        </pre>
                      </div>
                    )}
                    {prompt.user_prompt_text && (
                      <div>
                        <p className="text-[11px] text-muted-foreground mb-1">User</p>
                        <pre className="text-xs bg-muted p-3 rounded-md whitespace-pre-wrap font-mono max-h-24 overflow-y-auto">
                          {prompt.user_prompt_text}
                        </pre>
                      </div>
                    )}
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
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-base">{prompt.name}</CardTitle>
                        {prompt.benchmark && (
                          <Badge variant="outline" className="text-xs">{benchmarkLabel(prompt.benchmark)}</Badge>
                        )}
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

        {prompts.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No prompts configured. Add one to customize OCR behavior.
          </div>
        )}
      </div>

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
              <Label className="text-xs">System Prompt</Label>
              <Textarea
                value={form.prompt_text}
                onChange={(e) => setForm({ ...form, prompt_text: e.target.value })}
                placeholder="You are a document OCR assistant..."
                rows={8}
                className="font-mono text-sm max-h-64 overflow-y-auto"
              />
              <p className="text-[11px] text-muted-foreground">
                Sent as the system message. Leave empty to send no system message
                (some models like PaddleOCR-VL expect no system prompt).
              </p>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">User Prompt (optional)</Label>
              <Textarea
                value={form.user_prompt_text ?? ""}
                onChange={(e) => setForm({ ...form, user_prompt_text: e.target.value })}
                placeholder="e.g., OCR:  (PaddleOCR-VL official prompt). Empty = provider default ('Convert this document to markdown.')"
                rows={3}
                className="font-mono text-sm max-h-40 overflow-y-auto"
              />
              <p className="text-[11px] text-muted-foreground">
                Text placed in the user turn next to the image.
              </p>
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
            {!form.is_default && (
              <div className="space-y-1.5">
                <Label className="text-xs">Scope to Benchmark (optional)</Label>
                <Select
                  value={form.benchmark || "_none"}
                  onValueChange={(v) => setForm({ ...form, benchmark: v === "_none" ? null : v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="All runs" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_none">All runs (not benchmark-specific)</SelectItem>
                    <SelectItem value="omnidocbench">OmniDocBench</SelectItem>
                    <SelectItem value="olmocr_bench">olmOCR-Bench</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-[11px] text-muted-foreground">
                  Used only when running that official benchmark. Combine with a model to set a
                  per-model prompt for that benchmark; leave the model empty for a benchmark-wide default.
                </p>
                {form.benchmark === "omnidocbench" && (
                  <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-2.5 text-[11px] leading-relaxed">
                    <p className="font-medium">Required output format — OmniDocBench</p>
                    <ul className="mt-1 list-disc space-y-0.5 pl-4 text-muted-foreground">
                      <li>Output one page as <b>Markdown</b> (no explanations, no code fences).</li>
                      <li>Tables as <b>HTML &lt;table&gt;</b> — TEDS scoring parses this.</li>
                      <li>Formulas as <b>LaTeX</b> (<code>$...$</code> / <code>$$...$$</code>) — CDM scoring depends on it.</li>
                      <li>Preserve <b>reading order</b>, headings, lists.</li>
                    </ul>
                    <p className="mt-1 text-muted-foreground">
                      Scored by edit distance / TEDS / CDM — deviating from this format lowers scores.
                    </p>
                  </div>
                )}
                {form.benchmark === "olmocr_bench" && (
                  <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-2.5 text-[11px] leading-relaxed">
                    <p className="font-medium">Required output format — olmOCR-Bench</p>
                    <ul className="mt-1 list-disc space-y-0.5 pl-4 text-muted-foreground">
                      <li>Output <b>Markdown / plain text</b> in natural <b>reading order</b>.</li>
                      <li>Transcribe body text <b>verbatim</b> — pass/fail unit tests look for exact strings.</li>
                      <li>Do <b>not</b> repeat running headers/footers.</li>
                      <li>Formulas as LaTeX; tables as Markdown or HTML.</li>
                    </ul>
                    <p className="mt-1 text-muted-foreground">
                      Scored by deterministic unit tests (pass-rate) — missing/altered text fails tests.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={submitting || !form.name || (!form.prompt_text && !form.user_prompt_text)}>
              {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              {editingId ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
