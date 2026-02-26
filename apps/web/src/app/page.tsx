import { Button } from "@scr/ui";
import { ArrowRight, BarChart3, Shield, TrendingUp } from "lucide-react";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="mx-auto max-w-4xl text-center">
        <h1 className="text-4xl font-bold tracking-tight text-primary-800 sm:text-6xl">
          SCR Platform
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Investment intelligence connecting impact project developers with
          professional investors.
        </p>

        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          <div className="rounded-lg border p-6">
            <TrendingUp className="mx-auto h-8 w-8 text-secondary-500" />
            <h3 className="mt-3 font-semibold text-primary-800">
              Deal Pipeline
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Track investments from prospecting to deployment.
            </p>
          </div>
          <div className="rounded-lg border p-6">
            <Shield className="mx-auto h-8 w-8 text-accent-500" />
            <h3 className="mt-3 font-semibold text-primary-800">
              ESG Scoring
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              AI-powered environmental, social, and governance analysis.
            </p>
          </div>
          <div className="rounded-lg border p-6">
            <BarChart3 className="mx-auto h-8 w-8 text-primary-500" />
            <h3 className="mt-3 font-semibold text-primary-800">
              Analytics
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Real-time portfolio and market intelligence dashboards.
            </p>
          </div>
        </div>

        <div className="mt-10 flex justify-center gap-4">
          <Button size="lg">
            Get Started
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
          <Button variant="outline" size="lg">
            Learn More
          </Button>
        </div>
      </div>
    </main>
  );
}
