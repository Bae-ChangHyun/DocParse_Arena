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
    listDocuments().then(setDocs).catch(() => {});
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
          className={`relative overflow-hidden rounded-[16px] border bg-card p-2 text-left transition-all duration-300 ease-out hover:-translate-y-0.5 hover:border-foreground/40 ${
            selected === doc.name ? "border-foreground ring-2 ring-foreground/15" : ""
          }`}
        >
          <div className="flex aspect-[3/4] items-center justify-center overflow-hidden rounded-[12px] bg-muted">
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
          <p className="mt-1 truncate text-xs text-muted-foreground">{doc.name}</p>
        </button>
      ))}
    </div>
  );
}
