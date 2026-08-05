"use client";

import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
import { ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface DocumentViewerProps {
  imageUrl: string;
  documentName?: string;
}

function isPdf(url: string, name?: string): boolean {
  if (name?.toLowerCase().endsWith(".pdf")) return true;
  try {
    const u = new URL(url, window.location.origin);
    return u.pathname.toLowerCase().endsWith(".pdf");
  } catch {
    return false;
  }
}

export default function DocumentViewer({ imageUrl, documentName }: DocumentViewerProps) {
  const pdf = isPdf(imageUrl, documentName);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <span className="truncate text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
          {documentName || "Document"}
        </span>
      </div>
      <div className="relative flex-1 overflow-hidden bg-muted">
        {pdf ? (
          <iframe
            src={imageUrl}
            title="PDF Document"
            className="w-full h-full border-0"
          />
        ) : (
          <TransformWrapper
            initialScale={1}
            minScale={0.5}
            maxScale={4}
          >
            {({ zoomIn, zoomOut, resetTransform }) => (
              <>
                <div className="absolute right-3 top-3 z-10 flex gap-1">
                  <Button variant="secondary" size="icon" className="h-8 w-8" onClick={() => zoomIn()}>
                    <ZoomIn className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="secondary" size="icon" className="h-8 w-8" onClick={() => zoomOut()}>
                    <ZoomOut className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="secondary" size="icon" className="h-8 w-8" onClick={() => resetTransform()}>
                    <RotateCcw className="h-3.5 w-3.5" />
                  </Button>
                </div>
                <TransformComponent wrapperClass="!w-full !h-full" contentClass="!w-full !h-full flex items-center justify-center">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={imageUrl}
                    alt="Document"
                    className="max-w-full max-h-full object-contain"
                  />
                </TransformComponent>
              </>
            )}
          </TransformWrapper>
        )}
      </div>
    </div>
  );
}
