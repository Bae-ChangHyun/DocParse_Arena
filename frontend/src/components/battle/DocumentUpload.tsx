"use client";

import { useCallback, useRef } from "react";
import { Upload, Shuffle, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

interface DocumentUploadProps {
  onFileSelect: (file: File) => void;
  onRandomDoc: () => void;
  isLoading: boolean;
}

export default function DocumentUpload({ onFileSelect, onRandomDoc, isLoading }: DocumentUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) onFileSelect(file);
    },
    [onFileSelect]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFileSelect(file);
    },
    [onFileSelect]
  );

  return (
    <div className="mx-auto flex max-w-lg flex-col items-center gap-6 p-8">
      <div className="mb-2 text-center">
        <div className="mb-3 flex items-center justify-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-muted">
            <FileText className="h-5 w-5 text-foreground" />
          </div>
        </div>
        <h2 className="text-xl font-semibold">Start a Battle</h2>
        <p className="mx-auto mt-1 max-w-[30ch] text-sm text-muted-foreground sm:max-w-none">
          Upload a document and two anonymous models will parse it
        </p>
      </div>

      <div
        className="w-full cursor-pointer rounded-xl border-2 border-dashed border-border bg-muted/30 p-8 text-center transition-all hover:border-muted-foreground hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        role="button"
        tabIndex={0}
        aria-label="Upload a document by dropping or clicking"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
      >
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <Upload className="h-5 w-5 text-muted-foreground" />
        </div>
        <p className="mb-1 text-sm font-medium">
          Drag & drop a document here
        </p>
        <p className="text-xs text-muted-foreground">
          PDF, JPEG, PNG, WebP, TIFF, BMP
        </p>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept=".pdf,.jpg,.jpeg,.png,.webp,.tiff,.bmp"
          onChange={handleChange}
        />
      </div>

      <div className="flex w-full items-center gap-3 text-xs text-muted-foreground">
        <div className="h-px flex-1 bg-border" />
        or try a sample
        <div className="h-px flex-1 bg-border" />
      </div>

      <Button variant="secondary" onClick={onRandomDoc} disabled={isLoading} className="gap-2">
        <Shuffle className="h-4 w-4" />
        Random Document
      </Button>
    </div>
  );
}
