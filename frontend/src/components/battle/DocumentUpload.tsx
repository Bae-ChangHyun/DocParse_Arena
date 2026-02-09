"use client";

import { useCallback, useRef } from "react";
import { Upload, Shuffle } from "lucide-react";
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
    <div className="flex flex-col items-center gap-4 p-8">
      <div
        className="w-full max-w-md border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
        <p className="text-sm text-muted-foreground mb-2">
          Drag & drop a document here, or click to select
        </p>
        <p className="text-xs text-muted-foreground">
          Supports: PDF, JPEG, PNG, WebP, TIFF, BMP
        </p>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept=".pdf,.jpg,.jpeg,.png,.webp,.tiff,.bmp"
          onChange={handleChange}
        />
      </div>

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <div className="h-px w-12 bg-border" />
        or
        <div className="h-px w-12 bg-border" />
      </div>

      <Button variant="outline" onClick={onRandomDoc} disabled={isLoading} className="gap-2">
        <Shuffle className="h-4 w-4" />
        Get a random document
      </Button>
    </div>
  );
}
