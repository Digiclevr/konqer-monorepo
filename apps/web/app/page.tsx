import Link from "next/link";
import { KONQER_SERVICES } from "@konqer/utils";
import { Button } from "@konqer/ui";

export default async function Page() {
  const getServiceUrl = (slug: string) => {
    const subdomain = slug.replace(/-/g, '-');
    return process.env.NODE_ENV === 'production'
      ? `https://${subdomain}.konqer.app`
      : `http://localhost:${getServicePort(slug)}`;
  };

  const getServicePort = (slug: string) => {
    const ports: Record<string, number> = {
      'cold-dm-personalizer': 3101,
      'outbound-battlecards-ai': 3102,
      'sales-objection-crusher': 3103,
      'community-finder-pro': 3104,
      'linkedin-carousel-forge': 3105,
      'ai-cold-email-writer': 3106,
      'startup-pitch-deck-builder': 3107,
      'ai-whitepaper-generator': 3108,
      'vc-deck-heatmap': 3109,
      'webinar-demand-scanner': 3110,
      'email-warmranker': 3111,
      'calendar-no-show-shield': 3112,
    };
    return ports[slug] || 3000;
  };

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4000";

  return (
    <main className="max-w-5xl mx-auto px-6 py-16">
      <h1 className="text-4xl font-bold tracking-tight">Konqer</h1>
      <p className="mt-3 text-neutral-700">
        Productized services for outbound, enablement and viral content — built for B2B.
      </p>

      <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {KONQER_SERVICES.map((s) => (
          <Link key={s.slug} href={getServiceUrl(s.slug)}>
            <div className="rounded-2xl border border-neutral-200 p-5 shadow-soft hover:shadow-md transition-shadow cursor-pointer">
              <h3 className="font-semibold">{s.name}</h3>
              <p className="text-xs text-neutral-500 mt-1">Type: {s.type}</p>
              <div className="mt-4 text-sm text-blue-600 font-medium">
                Explore →
              </div>
            </div>
          </Link>
        ))}
      </div>

      <div className="mt-12 flex items-center gap-3">
        <Link href="/">
          <Button variant="secondary">Home</Button>
        </Link>
        <a href={`${apiUrl}/health`} target="_blank" rel="noreferrer">
          <Button>API Health</Button>
        </a>
      </div>
    </main>
  );
}
