"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import { sanitizeSchema } from "@/lib/markdown-config";
import "katex/dist/katex.min.css";
import { Copy, Check, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { PlaygroundResponse } from "@/lib/api";
import { preprocessOcrText, stripThinking } from "@/lib/markdown-utils";

interface PlaygroundResultProps {
  result: PlaygroundResponse | null;
  isLoading: boolean;
  error: string | null;
}

export default function PlaygroundResult({ result, isLoading, error }: PlaygroundResultProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(result.result);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="surface-panel flex min-h-[360px] h-[calc(100dvh-18rem)] items-center justify-center p-8">
        <div className="w-full max-w-md space-y-3">
          <div className="h-3 w-24 rounded-full bg-foreground" />
          <div className="h-2 rounded-full bg-muted" />
          <div className="h-2 w-5/6 rounded-full bg-muted" />
          <div className="h-2 w-2/3 rounded-full bg-muted" />
          <div className="flex items-center gap-2 pt-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Running OCR...
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="surface-panel flex min-h-[360px] h-[calc(100dvh-18rem)] items-center justify-center p-8">
        <p className="rounded-[16px] border border-destructive/20 bg-card px-4 py-3 text-sm text-destructive">{error}</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="surface-panel flex min-h-[360px] h-[calc(100dvh-18rem)] items-center justify-center p-8">
        <div className="max-w-sm text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-border bg-muted">
            <FileText className="h-5 w-5 text-muted-foreground" />
          </div>
          <span className="text-sm text-muted-foreground">
            Select a model and document, then click &quot;Run OCR&quot;
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="surface-panel overflow-hidden">
      <div className="flex items-center justify-between border-b px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="font-semibold tracking-[-0.01em]">{result.model_name}</span>
          <span className="text-xs text-muted-foreground">{(result.latency_ms / 1000).toFixed(1)}s</span>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleCopy} aria-label="Copy result to clipboard">
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
        </Button>
      </div>

      <Tabs defaultValue="rendered">
        <TabsList className="mx-3 mt-2">
          <TabsTrigger value="rendered">Rendered</TabsTrigger>
          <TabsTrigger value="raw">Raw</TabsTrigger>
        </TabsList>
        <TabsContent value="rendered">
          <ScrollArea className="min-h-[360px] h-[calc(100dvh-18rem)]">
            <div className="p-6 prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex, rehypeRaw, [rehypeSanitize, sanitizeSchema]]}
              >{preprocessOcrText(stripThinking(result.result))}</ReactMarkdown>
            </div>
          </ScrollArea>
        </TabsContent>
        <TabsContent value="raw">
          <ScrollArea className="min-h-[360px] h-[calc(100dvh-18rem)]">
            <pre className="p-6 text-xs font-mono whitespace-pre-wrap break-words">{result.result}</pre>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  );
}
