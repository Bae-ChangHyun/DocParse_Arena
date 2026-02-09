import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AboutPage() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <h1 className="text-2xl font-bold mb-6">About OCR Arena</h1>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>What is OCR Arena?</CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <p>
              OCR Arena is a self-hosted blind comparison platform for OCR (Optical Character Recognition) models,
              inspired by <a href="https://www.ocrarena.ai" target="_blank" rel="noopener noreferrer" className="underline">ocrarena.ai</a>.
            </p>
            <p>
              Upload a document, and two randomly selected AI models will compete to convert it into markdown text.
              You vote for the better result without knowing which model produced it.
            </p>
            <p>
              This project was built to connect your own OCR models and evaluate them with your own datasets
              in a fair, unbiased manner through blind human evaluation with ELO ranking.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>How does ELO Rating work?</CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <p>
              We use the ELO rating system (the same system used in chess) to rank OCR models.
              Each model starts with a rating of <strong>1500</strong>.
            </p>
            <p>The rating update formula is:</p>
            <ul>
              <li><strong>Expected Score:</strong> E = 1 / (1 + 10<sup>(R<sub>opponent</sub> - R<sub>self</sub>) / 400</sup>)</li>
              <li><strong>New Rating:</strong> R&apos; = R + K &times; (S - E)</li>
              <li><strong>K-factor:</strong> 20 (determines how much each battle affects the rating)</li>
            </ul>
            <p>
              When a higher-rated model loses to a lower-rated one, the rating change is larger,
              and vice versa. Ties give each model 0.5 points.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Supported Models</CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <ul>
              <li><strong>Claude (Anthropic)</strong> - Claude Sonnet 4, Claude Haiku 3.5</li>
              <li><strong>GPT (OpenAI)</strong> - GPT-4o, GPT-4o Mini</li>
              <li><strong>Gemini (Google)</strong> - Gemini 2.0 Flash, Gemini 2.0 Flash Lite</li>
              <li><strong>Mistral</strong> - Mistral Small</li>
              <li><strong>Ollama</strong> - LLaVA and other local models</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Fair Matchmaking</CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <p>
              To ensure fair evaluation, model selection uses <strong>weighted random sampling</strong> based on battle count.
              Models with fewer battles receive higher selection probability, so all models get roughly equal evaluation opportunities.
            </p>
            <p>
              The weight formula is: <code>weight = max_battles - model_battles + 1</code>.
              A brand-new model will be selected more often until its battle count catches up with others.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Features</CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <ul>
              <li><strong>Battle Mode:</strong> Blind side-by-side comparison of two random models</li>
              <li><strong>Playground:</strong> Test individual models on any document</li>
              <li><strong>Leaderboard:</strong> Global ELO rankings and head-to-head statistics</li>
              <li><strong>Settings:</strong> Manage providers, models, prompts, and extra API parameters</li>
              <li><strong>Document Support:</strong> PDF, JPEG, PNG, WebP, TIFF, BMP</li>
              <li><strong>Custom Providers:</strong> Connect any OpenAI-compatible endpoint (vLLM, LiteLLM, etc.)</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
