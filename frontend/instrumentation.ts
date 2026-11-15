
import { registerOTel } from "@vercel/otel";

export function register() {
  registerOTel({
    serviceName: "shopagent_v2-frontend",
  });
}
