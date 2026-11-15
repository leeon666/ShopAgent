# Evaluation Results

JSON files in this directory are produced by:

```powershell
docker compose -f docker-compose.dev.yml exec -T app `
  shopagent_v2 cmd eval-after-sales `
  --mode llm_only --mode llm_rag --mode full_agent
```

Each report includes aggregate metrics and per-case outputs. Model outputs are
kept verbatim so low scores and failure modes can be audited instead of edited
after the fact.

Important: results depend on the current model, prompt version, policy corpus,
demo data, network latency, and DeepSeek account limits. Compare reports with
the same dataset and prompt version.
