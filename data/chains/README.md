# Blast Radius Visualizer — scenario data

These JSON files drive the [Blast Radius Visualizer](https://csoh.org/blast-radius.html), a
D3 force-directed graph of each breach kill chain. The visualizer loads
`chains-index.json` at runtime and builds its scenario picker from it — **adding a new
chain requires no changes to the visualizer code**, just two things:

1. A scenario file in this directory (e.g. `my-breach.json`)
2. An entry in `chains-index.json` pointing at it

The scenario `id` should match the breach page filename in `/breaches/` so the
"Visualize blast radius" deep link (`/blast-radius.html?scenario=<id>`) works.

## `chains-index.json`

```json
{
  "scenarios": [
    {
      "id": "capital-one",                       // unique slug, used in ?scenario=
      "title": "Capital One (2019)",             // shown in the scenario picker
      "subtitle": "SSRF → IMDSv1 → …",           // one-line chain summary
      "provider": "AWS",                         // provider chip text
      "year": "2019",                            // used for picker ordering
      "file": "data/chains/capital-one.json",    // scenario file, site-root relative
      "page": "breaches/capital-one.html"        // full kill chain write-up
    }
  ]
}
```

## Scenario file schema

```json
{
  "id": "capital-one",
  "title": "Capital One (2019)",
  "description": "One-paragraph summary shown above the graph.",
  "defaultOrigin": "attacker",       // node id BFS starts from on load (optional,
                                     // falls back to the first node)
  "nodes": [
    { "id": "attacker", "label": "Attacker (Paige Thompson)", "type": "attacker" }
  ],
  "links": [
    {
      "source": "attacker",          // node id
      "target": "waf",               // node id
      "tech": "T1190 – Exploit Public-Facing Application"   // MITRE ATT&CK technique
    }
  ]
}
```

Links are **directed** — they point in the direction the attack propagates. Selecting
any node in the visualizer runs a breadth-first search along link direction from that
node and colours everything reachable by hop distance: the blast radius if that asset
is compromised.

### Node `type` values

| type         | use for                                                   |
|--------------|-----------------------------------------------------------|
| `attacker`   | threat actor / entry point of the chain                   |
| `identity`   | people, user accounts, roles                              |
| `endpoint`   | laptops, workstations, phones                             |
| `credential` | passwords, keys, tokens, secrets                          |
| `service`    | SaaS apps, APIs, managed services                         |
| `compute`    | VMs, build systems, hypervisors, clusters                 |
| `network`    | VPNs, network segments, C2 channels                       |
| `storage`    | buckets, vaults, repos, file shares                       |
| `data`       | records, source code, email, anything exfiltratable       |
| `impact`     | the terminal blast — ransomware, extortion, exposure      |

An unknown type still renders (neutral grey) but prefer the vocabulary above so the
legend stays truthful.

Keep graphs between roughly 7 and 15 nodes — enough to show branching, small enough to
read. Every claim should be sourced from the corresponding kill chain page, which is
itself sourced from post-mortems (see `CONTRIBUTING_KILL_CHAINS.md`).
