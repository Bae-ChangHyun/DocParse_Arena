import Link from "next/link";
import { FlaskConical, Swords, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="mx-auto flex min-h-[calc(100dvh-5rem)] max-w-[1200px] flex-col overflow-hidden px-4 py-8 md:py-12">
      <section className="grid flex-1 items-center gap-8 md:grid-cols-[1.05fr_0.95fr]">
        <div className="soft-enter">
          <div className="mb-5 inline-flex items-center rounded-full border border-border px-3 py-1 text-xs font-medium tracking-[0.01em] text-muted-foreground">
            Blind OCR model evaluation
          </div>
          <h1 className="max-w-[350px] font-display text-[2.75rem] leading-[1.08] text-foreground sm:max-w-none sm:text-[3.8rem] lg:text-[4.4rem]">
            Find the parser that reads your documents best.
          </h1>
          <p className="mt-6 max-w-[340px] text-base leading-[1.6] text-muted-foreground sm:max-w-[560px]">
            Run blind side-by-side battles, inspect streamed output, and rank models by real results on your own files.
          </p>
          <div className="mt-8 grid w-full max-w-[350px] grid-cols-1 gap-3 sm:flex sm:max-w-none sm:flex-wrap sm:items-center">
            <Link href="/battle">
              <Button size="lg" className="w-full gap-2 sm:w-auto">
                <Swords className="h-4 w-4" />
                Start Battle
              </Button>
            </Link>
            <Link href="/leaderboard">
              <Button variant="secondary" size="lg" className="w-full gap-2 sm:w-auto">
                <Trophy className="h-4 w-4" />
                Leaderboard
              </Button>
            </Link>
            <Link href="/playground">
              <Button variant="outline" size="lg" className="w-full gap-2 sm:w-auto">
                <FlaskConical className="h-4 w-4" />
                Playground
              </Button>
            </Link>
          </div>
        </div>

        <div className="soft-enter grid w-full max-w-[350px] min-w-0 gap-4 sm:max-w-none md:pt-16" style={{ animationDelay: "120ms" }}>
          <div className="surface-panel overflow-hidden p-4">
            <div className="rounded-[16px] bg-muted p-6">
              <div className="mb-8 flex items-center justify-between">
                <span className="text-sm font-medium">Live battle</span>
                <span className="rounded-full border border-border bg-background px-2.5 py-1 text-xs font-medium text-muted-foreground">streaming</span>
              </div>
              <div className="grid gap-3">
                <div className="rounded-[14px] border border-border bg-background p-4">
                  <div className="mb-3 h-2 w-20 rounded-full bg-foreground" />
                  <div className="space-y-2">
                    <div className="h-2 rounded-full bg-border" />
                    <div className="h-2 w-5/6 rounded-full bg-border" />
                    <div className="h-2 w-2/3 rounded-full bg-border" />
                  </div>
                </div>
                <div className="ml-10 rounded-[14px] border border-border bg-background p-4">
                  <div className="mb-3 h-2 w-16 rounded-full bg-muted-foreground" />
                  <div className="space-y-2">
                    <div className="h-2 rounded-full bg-border" />
                    <div className="h-2 w-4/5 rounded-full bg-border" />
                    <div className="h-2 w-1/2 rounded-full bg-border" />
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="surface-card p-5">
              <div className="font-mono text-2xl font-semibold tracking-normal">1500</div>
              <div className="mt-1 text-sm text-muted-foreground">starting ELO</div>
            </div>
            <div className="surface-card p-5">
              <div className="font-mono text-2xl font-semibold tracking-normal">2</div>
              <div className="mt-1 text-sm text-muted-foreground">anonymous models</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
