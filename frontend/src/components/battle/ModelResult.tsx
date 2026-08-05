"use client";

import { useState, lazy, Suspense } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import { sanitizeSchema } from "@/lib/markdown-config";
import "katex/dist/katex.min.css";
import "markstream-react/index.tailwind.css";
import { preprocessOcrText, stripThinking } from "@/lib/markdown-utils";
import { Copy, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const NodeRenderer = lazy(() => import("markstream-react").then((m) => ({ default: m.NodeRenderer })));

interface ModelResultProps {
  label: string;
  text: string | null;
  latencyMs: number | null;
  isLoading: boolean;
  isStreaming?: boolean;
  streamingText?: string;
  error?: string | null;
  modelName?: string;
  eloChange?: number;
}

export default function ModelResult({
  label,
  text,
  latencyMs,
  isLoading,
  isStreaming,
  streamingText,
  error,
  modelName,
  eloChange,
}: ModelResultProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const copyText = text || streamingText;
    if (!copyText) return;
    await navigator.clipboard.writeText(copyText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const hasFinalText = text !== null;
  const displayText = hasFinalText ? text : (isStreaming ? streamingText : null);

  return (
    <div className="surface-card flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground">{label.slice(-1)}</span>
          <span className="text-sm font-semibold tracking-[-0.01em]">{modelName || label}</span>
          {isStreaming && (
            <span className="flex items-center gap-1 rounded-full border border-border bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-foreground" />
              Streaming
            </span>
          )}
          {latencyMs !== null && (
            <span className="text-xs text-muted-foreground">{(latencyMs / 1000).toFixed(1)}s</span>
          )}
          {eloChange !== undefined && (
            <span className={`text-xs font-medium ${eloChange > 0 ? "text-foreground" : "text-muted-foreground"}`}>
              {eloChange > 0 ? `+${eloChange}` : eloChange} ELO
            </span>
          )}
        </div>
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleCopy} disabled={!displayText} aria-label="Copy result to clipboard">
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
        </Button>
      </div>

      {isLoading ? (
        <div className="flex flex-1 items-center justify-center p-6">
          <div className="w-full max-w-sm space-y-3">
            <div className="h-3 w-24 rounded-full bg-foreground" />
            <div className="h-2 rounded-full bg-muted" />
            <div className="h-2 w-5/6 rounded-full bg-muted" />
            <div className="h-2 w-2/3 rounded-full bg-muted" />
            <div className="flex items-center gap-2 pt-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Processing...
            </div>
          </div>
        </div>
      ) : error ? (
        <div className="flex flex-1 items-center justify-center p-6">
          <p className="rounded-[16px] border border-destructive/20 bg-card px-4 py-3 text-center text-sm text-destructive">{error}</p>
        </div>
      ) : isStreaming && streamingText ? (
        <div className="flex-1 min-h-0 overflow-auto">
          <div className="p-4 prose prose-sm max-w-none dark:prose-invert">
            <Suspense fallback={<pre className="text-xs font-mono whitespace-pre-wrap break-words">{stripThinking(streamingText)}</pre>}>
              <NodeRenderer content={stripThinking(streamingText)} final={false} />
            </Suspense>
          </div>
        </div>
      ) : hasFinalText ? (
        <Tabs defaultValue="rendered" className="flex-1 flex flex-col min-h-0">
          <TabsList className="mx-2 mt-2 w-fit">
            <TabsTrigger value="rendered">Rendered</TabsTrigger>
            <TabsTrigger value="raw">Raw</TabsTrigger>
          </TabsList>
          <TabsContent value="rendered" className="flex-1 min-h-0 m-0">
            <div className="h-full overflow-auto">
              <div className="p-4 prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex, rehypeRaw, [rehypeSanitize, sanitizeSchema]]}
                >{text ? preprocessOcrText(stripThinking(text)) : "No text extracted."}</ReactMarkdown>
              </div>
            </div>
          </TabsContent>
          <TabsContent value="raw" className="flex-1 min-h-0 m-0">
            <div className="h-full overflow-auto">
              <pre className="p-4 text-xs font-mono whitespace-pre-wrap break-words">{text || "No text extracted."}</pre>
            </div>
          </TabsContent>
        </Tabs>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <span className="text-sm text-muted-foreground">Waiting for results...</span>
        </div>
      )}
    </div>
  );
}
