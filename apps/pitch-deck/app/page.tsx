import Link from "next/link";
import { Button } from "@konqer/ui";

export default async function Page() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4000";

  return (
    <main className="max-w-5xl mx-auto px-6 py-16">
      <div className="mb-8">
        <Link href="http://localhost:3100" className="text-sm text-blue-600 hover:underline">
          ← Back to Konqer
        </Link>
      </div>

      <h1 className="text-4xl font-bold tracking-tight">Startup Pitch Deck Builder</h1>
      <p className="mt-3 text-neutral-700">
        Create investor-ready pitch decks that raise capital. AI-powered storytelling and design.
      </p>

      <div className="mt-10 p-8 bg-white rounded-2xl border border-neutral-200 shadow-soft">
        <h2 className="text-2xl font-semibold mb-4">Service Features</h2>

        <ul className="space-y-3 text-neutral-700">
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">✓</span>
            AI-generated narrative and content
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">✓</span>
            Professional design templates
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">✓</span>
            Market sizing and competitive analysis
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">✓</span>
            Financial projections generation
          </li>
        </ul>

        <div className="mt-8">
          <Button className="w-full">Get Started</Button>
        </div>
      </div>

      <div className="mt-8 text-sm text-neutral-500">
        <a href={`${apiUrl}/services/startup-pitch-deck-builder`} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
          API Documentation →
        </a>
      </div>
    </main>
  );
}
