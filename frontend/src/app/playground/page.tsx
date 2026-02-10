"use client";

import { useState, useEffect, useRef } from "react";
import { Upload, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import ModelSelector from "@/components/playground/ModelSelector";
import SampleDocuments from "@/components/playground/SampleDocuments";
import PlaygroundResult from "@/components/playground/PlaygroundResult";
import {
  getModels,
  runPlaygroundOcr,
  getResolvedPrompt,
  type OcrModel,
  type PlaygroundResponse,
} from "@/lib/api";

const SOURCE_LABELS: Record<string, { label: string; variant: "default" | "secondary" | "outline" }> = {
  model: { label: "Model-specific", variant: "default" },
  default: { label: "Default", variant: "secondary" },
  builtin: { label: "Built-in", variant: "outline" },
};

export default function PlaygroundPage() {
  const [models, setModels] = useState<OcrModel[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [result, setResult] = useState<PlaygroundResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Prompt & Temperature state
  const [prompt, setPrompt] = useState("");
  const [promptSource, setPromptSource] = useState<string>("builtin");
  const [loadingPrompt, setLoadingPrompt] = useState(false);
  const [temperature, setTemperature] = useState<string>("");

  useEffect(() => {
    getModels().then((m) => {
      setModels(m);
      if (m.length > 0) setSelectedModel(m[0].id);
    });
  }, []);

  // Fetch resolved prompt when model changes
  useEffect(() => {
    if (!selectedModel) return;
    setLoadingPrompt(true);
    getResolvedPrompt(selectedModel)
      .then((data) => {
        setPrompt(data.prompt);
        setPromptSource(data.source);
      })
      .catch(() => {
        setPrompt("");
        setPromptSource("builtin");
      })
      .finally(() => setLoadingPrompt(false));
  }, [selectedModel]);

  const handleRun = async () => {
    if (!selectedModel) return;
    if (!selectedDoc && !uploadedFile) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const tempValue = temperature !== "" ? parseFloat(temperature) : undefined;
      const res = await runPlaygroundOcr(
        selectedModel,
        uploadedFile || undefined,
        !uploadedFile ? selectedDoc || undefined : undefined,
        prompt || undefined,
        tempValue,
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "OCR failed");
    } finally {
      setIsLoading(false);
    }
  };

  const sourceInfo = SOURCE_LABELS[promptSource] || SOURCE_LABELS.builtin;

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Playground</h1>
        <p className="text-muted-foreground mt-1">
          Test individual parsing models on any document
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Model</CardTitle>
            </CardHeader>
            <CardContent>
              <ModelSelector
                models={models}
                selectedId={selectedModel}
                onSelect={setSelectedModel}
                label="OCR Model"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Parameters</CardTitle>
                {loadingPrompt && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Prompt</Label>
                  <Badge variant={sourceInfo.variant} className="text-[10px]">
                    {sourceInfo.label}
                  </Badge>
                </div>
                <Textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="OCR prompt..."
                  rows={5}
                  className="font-mono text-xs resize-y"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs">Temperature</Label>
                <Input
                  type="number"
                  min={0}
                  max={2}
                  step={0.1}
                  value={temperature}
                  onChange={(e) => setTemperature(e.target.value)}
                  placeholder="default"
                  className="font-mono text-sm"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Document</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Button
                  variant="outline"
                  className="w-full gap-2"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="h-4 w-4" />
                  {uploadedFile ? uploadedFile.name : "Upload a file"}
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept=".pdf,.jpg,.jpeg,.png,.webp,.tiff,.bmp"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setUploadedFile(file);
                      setSelectedDoc(null);
                    }
                  }}
                />
              </div>

              <div className="text-xs text-muted-foreground text-center">or select a sample</div>

              <SampleDocuments
                onSelect={(name) => {
                  setSelectedDoc(name);
                  setUploadedFile(null);
                }}
                selected={selectedDoc}
              />
            </CardContent>
          </Card>

          <Button
            className="w-full"
            onClick={handleRun}
            disabled={!selectedModel || (!selectedDoc && !uploadedFile) || isLoading}
          >
            Run OCR
          </Button>
        </div>

        <div className="lg:col-span-2">
          <PlaygroundResult result={result} isLoading={isLoading} error={error} />
        </div>
      </div>
    </div>
  );
}
