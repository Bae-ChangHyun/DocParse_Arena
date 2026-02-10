"use client";

import { useState, lazy, Suspense } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import "katex/dist/katex.min.css";
import "markstream-react/index.tailwind.css";
import { preprocessOcrText } from "@/lib/markdown-utils";
import { Copy, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";

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

  const displayText = text || (isStreaming ? streamingText : null);

  return (
    <div className="flex flex-col h-full border rounded-lg overflow-hidden bg-card">
      <div className="flex items-center justify-between px-3 py-2 border-b bg-accent/50">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center justify-center h-5 w-5 rounded text-[10px] font-bold bg-primary/10 text-primary">{label.slice(-1)}</span>
          <span className="text-sm font-semibold">{modelName || label}</span>
          {isStreaming && (
            <span className="flex items-center gap-1 text-xs text-blue-500">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
              Streaming
            </span>
          )}
          {latencyMs !== null && (
            <span className="text-xs text-muted-foreground">{(latencyMs / 1000).toFixed(1)}s</span>
          )}
          {eloChange !== undefined && (
            <span className={`text-xs font-medium ${eloChange > 0 ? "text-green-600" : eloChange < 0 ? "text-red-600" : "text-muted-foreground"}`}>
              {eloChange > 0 ? `+${eloChange}` : eloChange} ELO
            </span>
          )}
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleCopy} disabled={!displayText} aria-label="Copy result to clipboard">
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
        </Button>
      </div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Processing...</span>
          </div>
        </div>
      ) : error ? (
        <div className="flex-1 flex items-center justify-center p-4">
          <p className="text-sm text-destructive text-center">{error}</p>
        </div>
      ) : isStreaming && streamingText ? (
        <ScrollArea className="flex-1 min-h-0">
          <div className="p-4 prose prose-sm max-w-none dark:prose-invert">
            <Suspense fallback={<pre className="text-xs font-mono whitespace-pre-wrap break-words">{streamingText}</pre>}>
              <NodeRenderer content={streamingText} final={false} />
            </Suspense>
          </div>
        </ScrollArea>
      ) : text ? (
        <Tabs defaultValue="rendered" className="flex-1 flex flex-col min-h-0">
          <TabsList className="mx-2 mt-2 w-fit">
            <TabsTrigger value="rendered">Rendered</TabsTrigger>
            <TabsTrigger value="raw">Raw</TabsTrigger>
          </TabsList>
          <TabsContent value="rendered" className="flex-1 min-h-0 m-0">
            <ScrollArea className="h-full">
              <div className="p-4 prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex, rehypeRaw, [rehypeSanitize, {
                    ...defaultSchema,
                    tagNames: [...(defaultSchema.tagNames || []), "math", "semantics", "mrow", "mi", "mo", "mn", "msup", "msub", "mfrac", "mover", "munder", "mtable", "mtr", "mtd", "annotation"],
                    attributes: {
                      ...defaultSchema.attributes,
                      "*": [...(defaultSchema.attributes?.["*"] || []), "className", "style"],
                      span: [...(defaultSchema.attributes?.["span"] || []), "className", "style"],
                      div: [...(defaultSchema.attributes?.["div"] || []), "className", "style"],
                    },
                  }]]}
                >{preprocessOcrText(text)}</ReactMarkdown>
              </div>
            </ScrollArea>
          </TabsContent>
          <TabsContent value="raw" className="flex-1 min-h-0 m-0">
            <ScrollArea className="h-full">
              <pre className="p-4 text-xs font-mono whitespace-pre-wrap break-words">{text}</pre>
            </ScrollArea>
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
