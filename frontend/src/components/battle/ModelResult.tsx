"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeRaw from "rehype-raw";
import "katex/dist/katex.min.css";
import { Copy, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";

interface ModelResultProps {
  label: string;
  text: string | null;
  latencyMs: number | null;
  isLoading: boolean;
  error?: string | null;
  modelName?: string;
  eloChange?: number;
}

export default function ModelResult({
  label,
  text,
  latencyMs,
  isLoading,
  error,
  modelName,
  eloChange,
}: ModelResultProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col h-full border rounded-lg overflow-hidden">
      <div className="flex items-center justify-between p-2 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">{modelName || label}</span>
          {latencyMs !== null && (
            <span className="text-xs text-muted-foreground">{(latencyMs / 1000).toFixed(1)}s</span>
          )}
          {eloChange !== undefined && (
            <span className={`text-xs font-medium ${eloChange > 0 ? "text-green-600" : eloChange < 0 ? "text-red-600" : "text-muted-foreground"}`}>
              {eloChange > 0 ? `+${eloChange}` : eloChange} ELO
            </span>
          )}
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleCopy} disabled={!text}>
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
                  rehypePlugins={[rehypeKatex, rehypeRaw]}
                >{text}</ReactMarkdown>
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
