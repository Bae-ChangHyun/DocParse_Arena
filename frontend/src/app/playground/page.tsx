"use client";

import { useState, useEffect, useRef } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import ModelSelector from "@/components/playground/ModelSelector";
import SampleDocuments from "@/components/playground/SampleDocuments";
import PlaygroundResult from "@/components/playground/PlaygroundResult";
import { getModels, runPlaygroundOcr, type OcrModel, type PlaygroundResponse } from "@/lib/api";

export default function PlaygroundPage() {
  const [models, setModels] = useState<OcrModel[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [result, setResult] = useState<PlaygroundResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getModels().then((m) => {
      setModels(m);
      if (m.length > 0) setSelectedModel(m[0].id);
    });
  }, []);

  const handleRun = async () => {
    if (!selectedModel) return;
    if (!selectedDoc && !uploadedFile) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await runPlaygroundOcr(
        selectedModel,
        uploadedFile || undefined,
        !uploadedFile ? selectedDoc || undefined : undefined
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "OCR failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Playground</h1>
        <p className="text-muted-foreground mt-1">
          Test individual OCR models on any document
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
