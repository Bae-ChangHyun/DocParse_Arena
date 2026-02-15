import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Server, Eye, Puzzle, ShieldCheck, Wrench, Github } from "lucide-react";

export default function AboutPage() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <h1 className="text-2xl font-bold mb-6">About DocParse Arena</h1>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Why DocParse Arena?</CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <p>
              DocParse Arena is a <strong>self-hosted</strong> blind comparison platform for document parsing models.
              Unlike cloud-based services, your documents never leave your infrastructure.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 not-prose mt-4">
              <div className="flex flex-col items-center gap-2 p-4 rounded-lg bg-accent/50 text-center">
                <Server className="h-6 w-6 text-primary" />
                <span className="text-sm font-semibold">Self-Hosted</span>
                <span className="text-xs text-muted-foreground">Runs on your own server. No data leaves your network.</span>
              </div>
              <div className="flex flex-col items-center gap-2 p-4 rounded-lg bg-accent/50 text-center">
                <ShieldCheck className="h-6 w-6 text-primary" />
                <span className="text-sm font-semibold">Privacy-First</span>
                <span className="text-xs text-muted-foreground">Evaluate sensitive documents safely. Optionally disable result storage.</span>
              </div>
              <div className="flex flex-col items-center gap-2 p-4 rounded-lg bg-accent/50 text-center">
                <Puzzle className="h-6 w-6 text-primary" />
                <span className="text-sm font-semibold">Customizable</span>
                <span className="text-xs text-muted-foreground">Add your own models, providers, and prompts via Settings.</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>How It Works</CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <div className="not-prose grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
              <div className="flex flex-col items-center gap-2 p-4 rounded-lg border text-center">
                <span className="text-2xl font-bold text-primary">1</span>
                <span className="text-sm font-semibold">Upload</span>
                <span className="text-xs text-muted-foreground">Upload a document or pick a random sample from the pool.</span>
              </div>
              <div className="flex flex-col items-center gap-2 p-4 rounded-lg border text-center">
                <span className="text-2xl font-bold text-primary">2</span>
                <span className="text-sm font-semibold">Compare</span>
                <span className="text-xs text-muted-foreground">Two anonymous models parse the document side-by-side in real time.</span>
              </div>
              <div className="flex flex-col items-center gap-2 p-4 rounded-lg border text-center">
                <span className="text-2xl font-bold text-primary">3</span>
                <span className="text-sm font-semibold">Vote</span>
                <span className="text-xs text-muted-foreground">Pick the better result. ELO ratings update automatically.</span>
              </div>
            </div>
            <p>
              Models are ranked using the <strong>ELO rating system</strong> (K=20, starting at 1500) &mdash; the same
              approach used in chess and <a href="https://lmsys.org/blog/2023-05-03-arena/" target="_blank" rel="noopener noreferrer" className="underline">LMSYS Chatbot Arena</a>.
              Fair matchmaking ensures all models get roughly equal battle opportunities through weighted random sampling.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Key Differences
              <Badge variant="secondary">vs Cloud Services</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <ul>
              <li>
                <strong>Self-Hosted:</strong> Not a cloud service &mdash; deploy on your own infrastructure with full control.
              </li>
              <li>
                <strong>VLM Registry:</strong> Each model has its own optimized prompt and post-processing pipeline, automatically applied during battles.
              </li>
              <li>
                <strong>Custom Providers:</strong> Connect any OpenAI-compatible endpoint &mdash; vLLM, LiteLLM, Ollama, or your own API.
              </li>
              <li>
                <strong>Privacy Controls:</strong> Set <code>STORE_OCR_RESULTS=false</code> to prevent storing parsed results. Documents stay ephemeral.
              </li>
              <li>
                <strong>Full Admin Control:</strong> Manage providers, models, prompts, and system parameters through the built-in Settings page.
              </li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Built-in Providers
            </CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <p>DocParse Arena ships with 5 providers out of the box. Add your own via <strong>Settings &rarr; API Providers</strong>.</p>
            <div className="not-prose flex flex-wrap gap-2 mt-2">
              <Badge variant="outline">Claude (Anthropic)</Badge>
              <Badge variant="outline">GPT (OpenAI)</Badge>
              <Badge variant="outline">Gemini (Google)</Badge>
              <Badge variant="outline">Mistral</Badge>
              <Badge variant="outline">Ollama</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wrench className="h-5 w-5" />
              Features
            </CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <ul>
              <li><strong>Battle Mode:</strong> Blind side-by-side comparison with real-time SSE streaming</li>
              <li><strong>Playground:</strong> Test individual models with custom prompts and parameters</li>
              <li><strong>Leaderboard:</strong> ELO rankings and head-to-head matchup statistics</li>
              <li><strong>Document Support:</strong> PDF, JPEG, PNG, WebP, TIFF, BMP</li>
              <li><strong>Settings Dashboard:</strong> Full CRUD for providers, models, prompts, and extra API params</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Github className="h-5 w-5" />
              Open Source
            </CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <p>
              DocParse Arena is open source under the <strong>MIT License</strong>.
              Contributions, bug reports, and feature requests are welcome.
            </p>
            <p>
              <a href="https://github.com/scout-partners/docparse-arena" target="_blank" rel="noopener noreferrer" className="underline">
                GitHub Repository
              </a>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
