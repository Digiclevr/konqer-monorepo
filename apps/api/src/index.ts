import Fastify from "fastify";
import cors from "@fastify/cors";
import swagger from "@fastify/swagger";
import * as dotenv from "dotenv";
import { KONQER_SERVICES } from "@konqer/utils";

dotenv.config();

const app = Fastify({ logger: true });

await app.register(cors, { origin: true });
await app.register(swagger, { });

app.get("/health", async () => ({ ok: true, ts: Date.now() }));

app.get("/version", async () => ({
  name: "konqer-api",
  version: "0.1.0"
}));

app.get("/services", async () => ({ services: KONQER_SERVICES }));

app.get("/services/:slug", async (req, reply) => {
  const { slug } = req.params as { slug: string };
  const svc = KONQER_SERVICES.find(s => s.slug === slug);
  if (!svc) return reply.status(404).send({ error: "not_found" });
  return {
    ...svc,
    demo: `This is a placeholder demo payload for ${svc.name}.`
  };
});

const port = Number(process.env.PORT || 4000);
const host = process.env.HOST || "0.0.0.0";

app.listen({ port, host }).then(() => {
  app.log.info(`API listening on http://${host}:${port}`);
});
