The bottleneck is no longer the model. It is **context**: what agents can see, what they are allowed to write back, and who is accountable when they do. Most firms already run agents; far fewer have wired them to trusted internal content or set rules for how generated work re-enters the organization.

Treat information flow as infrastructure, not as “better search.”

## What broke

Classic org design assumed humans were the scarce channel. Email, meetings, and slide decks throttled volume.

Agents invert that:

- **Volume explodes.** Drafts, summaries, tickets, code, and “research” appear faster than anyone can read.
- **Truth fragments.** Every team’s agent builds a slightly different picture of the customer, the policy, and last week’s decision.
- **Write-back is the new risk.** An agent that only *reads* Slack is a nuisance. An agent that *updates* CRM, ships code, or emails a customer is a system of record.
- **Human-only knowledge stays trapped.** Tariffs, political risk, “don’t pitch this account,” the real reason a deal stalled — agents cannot see it unless you design a path for it.
- **Sprawl is the default.** Gartner’s warning is agent population growing by orders of magnitude without identity, owners, or retirement.

If you do not design the flow, you get a second, unofficial company made of model context windows.

## The rule

**Separate four kinds of information, and never let them mix without a gate.**

| Layer | What it is | Who may write | Agents may |
|---|---|---|---|
| **System of record** | Contracts, ledger, inventory, HRIS, source code main branch | Named humans or tightly scoped services | Read widely; write only with a commit boundary |
| **System of decision** | Approved policy, pricing rules, legal positions, “how we interpret X” | Domain owners | Read as law; propose edits, never silently overwrite |
| **System of work** | Tickets, drafts, meeting notes, agent traces | Humans and agents | Write freely, but labeled as provisional |
| **System of memory** | What an agent “remembers” across sessions | Agent + owner | Isolated, time-boxed, provenance-tagged |

Most chaos is an agent treating layer 3 as layer 1.

## An operating model that actually moves information

### 1. One governed context layer
Do not give every agent raw Drive + Slack + ten SaaS apps. Build a **knowledge platform** in front of them: ingest, score freshness, attach permissions, cite version, serve retrieval. Raw → refined → integrated → serving.

Agents are only as good as the messiest document they can reach. Forty to sixty percent of corporate content is typically ROT (redundant, outdated, trivial). Clean that before you scale autonomy.

Practical standard: every agent answer carries **source, version, last-verified date, and permission scope**. No citation, no action.

### 2. Positions, not piles of docs
Meta’s useful pattern: a domain “second brain” with **position files** — the organization’s official stance, constraints, and routing rules — plus a reasoning layer, plus a loop that turns expert corrections into regression-tested knowledge *without* retraining the model.

That is how you stop twenty agents inventing twenty privacy policies.

### 3. Orchestrate across silos; do not clone chatbots
HBR’s field pattern from firms such as Walmart: **connector agents** move structured task outputs between functions; a **master orchestrator** pulls in human-only facts and frames decisions; humans keep authority. You automate routing and synthesis, not the enterprise decision.

Train people to inject the fact only they have — not to re-litigate the analysis the system already did.

### 4. Identity and leases for every agent
Persistent agents are machine actors, not sessions. Give each one:

- unique ID, owner, purpose  
- tools it may call  
- whether it may spawn sub-agents  
- **time-bound authority** (a lease, not permanent admin)  
- memory namespaces with provenance  

Identity can persist. Authority should expire. Delegation from human → agent → sub-agent must be reconstructable.

### 5. Commit boundaries, not “human in every loop”
Human-in-the-loop does not scale to thousands of agents. Use **human-on-the-loop** with explicit gates:

- **Copilot:** human clicks send  
- **Draft-and-propose:** agent prepares; human commits  
- **Bounded act:** agent executes inside money / data / customer limits  
- **Halt and escalate:** low confidence, novel case, or policy miss  

Match autonomy to irreversibility. A research brief is cheap to check. A wire, a production deploy, or an external email is not.

### 6. Make managers into agent managers
The new scarce skill is briefing, verification, and exception handling — not doing every intermediate step. Redesign roles around **delegation + review + extension**. Put agent capacity next to headcount on the org chart so work has an owner when the agent fails.

## Information hygiene (the unglamorous half)

- **Write once, reuse many.** Ingest a fact into the context layer; do not let five agents scrape five copies.  
- **Freshness SLAs.** Policies and prices older than N days are not retrievable for action, only for history.  
- **Permission inheritance.** SharePoint and Salesforce ACLs must survive retrieval. An agent running as “the company” is how you leak M&A folders.
- **Label synthetic text.** Drafts from agents should be stamped so they cannot be cited later as primary evidence.  
- **Close the loop.** When a human corrects an agent, that correction becomes a tested position, not a Slack shrug.  
- **Retire agents.** No owner, no use in 30 days, no tools — off. Sprawl is an information-quality problem as much as an IT one.

## A 90-day sequence

**Days 1–30 — See the flow**  
Inventory agents, tools, and write destinations. Map three critical workflows end to end (e.g. quote-to-cash, incident response, hiring). Mark where information dies in a silo or gets rewritten by a model.

**Days 31–60 — Install the spine**  
Stand up the context layer for one domain. Publish ten position files. Register every agent. Put commit boundaries on anything external or financial. Ban unregistered connectors.

**Days 61–90 — Run one orchestrated loop**  
One cross-functional flow with connector agents + human-only intake + an owner who reviews exceptions. Measure cycle time, error rate, and how often humans had to inject knowledge the system lacked. Only then clone the pattern.

## What good looks like

Leaders who capture value are the ones **redesigning workflows**, not sprinkling chat on old processes. The information system of an agentic company is: a shared context graph, a small set of official positions, agents with leased authority, humans on the loop for irreversible acts, and a written trail from question → sources → action.

Do that and AI increases the organization’s bandwidth. Skip it and you have just automated the rumor mill.