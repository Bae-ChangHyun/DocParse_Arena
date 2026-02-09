"use client";

import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
import { ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface DocumentViewerProps {
  imageUrl: string;
  documentName?: string;
}

export default function DocumentViewer({ imageUrl, documentName }: DocumentViewerProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-2 border-b bg-muted/30">
        <span className="text-xs font-medium text-muted-foreground truncate px-2">
          {documentName || "Document"}
        </span>
      </div>
      <div className="flex-1 overflow-hidden bg-muted/10">
        <TransformWrapper
          initialScale={1}
          minScale={0.5}
          maxScale={4}
        >
          {({ zoomIn, zoomOut, resetTransform }) => (
            <>
              <div className="absolute top-2 right-2 z-10 flex gap-1">
                <Button variant="secondary" size="icon" className="h-7 w-7" onClick={() => zoomIn()}>
                  <ZoomIn className="h-3.5 w-3.5" />
                </Button>
                <Button variant="secondary" size="icon" className="h-7 w-7" onClick={() => zoomOut()}>
                  <ZoomOut className="h-3.5 w-3.5" />
                </Button>
                <Button variant="secondary" size="icon" className="h-7 w-7" onClick={() => resetTransform()}>
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
      </div>
    </div>
  );
}
