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
    <div className="flex flex-col items-center gap-6 p-8 max-w-lg mx-auto">
      <div className="text-center mb-2">
        <div className="flex items-center justify-center gap-2 mb-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <FileText className="h-5 w-5 text-primary" />
          </div>
        </div>
        <h2 className="text-xl font-semibold">Start a Battle</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Upload a document and two anonymous models will parse it
        </p>
      </div>

      <div
        className="w-full rounded-xl border-2 border-dashed border-primary/20 bg-primary/[0.02] p-8 text-center cursor-pointer hover:border-primary/40 hover:bg-primary/[0.04] transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
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
        <div className="h-12 w-12 rounded-full bg-accent mx-auto mb-4 flex items-center justify-center">
          <Upload className="h-5 w-5 text-muted-foreground" />
        </div>
        <p className="text-sm font-medium mb-1">
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

      <div className="flex items-center gap-3 w-full text-xs text-muted-foreground">
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
