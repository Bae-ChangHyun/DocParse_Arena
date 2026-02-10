"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import "katex/dist/katex.min.css";
import { Copy, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { PlaygroundResponse } from "@/lib/api";
import { preprocessOcrText } from "@/lib/markdown-utils";

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
      <div className="flex items-center justify-center h-[calc(100vh-16rem)] border rounded-lg">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Running OCR...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-16rem)] border rounded-lg">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-16rem)] border rounded-lg">
        <span className="text-sm text-muted-foreground">
          Select a model and document, then click &quot;Run OCR&quot;
        </span>
      </div>
    );
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="flex items-center justify-between p-3 border-b bg-muted/30">
        <div className="flex items-center gap-3">
          <span className="font-medium">{result.model_name}</span>
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
          <ScrollArea className="h-[calc(100vh-16rem)]">
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
              >{preprocessOcrText(result.result)}</ReactMarkdown>
            </div>
          </ScrollArea>
        </TabsContent>
        <TabsContent value="raw">
          <ScrollArea className="h-[calc(100vh-16rem)]">
            <pre className="p-4 text-xs font-mono whitespace-pre-wrap break-words">{result.result}</pre>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  );
}
