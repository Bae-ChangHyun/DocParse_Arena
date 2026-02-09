"use client";

import { useEffect, useState } from "react";
import { listDocuments, getApiBase, type DocumentInfo } from "@/lib/api";
import { FileImage } from "lucide-react";

interface SampleDocumentsProps {
  onSelect: (name: string) => void;
  selected: string | null;
}

export default function SampleDocuments({ onSelect, selected }: SampleDocumentsProps) {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);

  useEffect(() => {
    listDocuments().then(setDocs).catch(console.error);
  }, []);

  if (docs.length === 0) {
    return (
      <div className="text-sm text-muted-foreground py-4 text-center">
        No sample documents available. Upload some to the backend/sample_docs/ directory.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
      {docs.map((doc) => (
        <button
          key={doc.name}
          onClick={() => onSelect(doc.name)}
          className={`relative border rounded-lg p-2 hover:border-primary/50 transition-colors overflow-hidden ${
            selected === doc.name ? "border-primary ring-1 ring-primary" : ""
          }`}
        >
          <div className="aspect-[3/4] bg-muted/30 rounded flex items-center justify-center overflow-hidden">
            {[".png", ".jpg", ".jpeg", ".webp", ".bmp"].includes(doc.extension) ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={`${getApiBase()}${doc.path}`}
                alt={doc.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <FileImage className="h-8 w-8 text-muted-foreground" />
            )}
          </div>
          <p className="text-xs mt-1 truncate text-muted-foreground">{doc.name}</p>
        </button>
      ))}
    </div>
  );
}
