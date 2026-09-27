"""PromptLab: a CPU-only classroom app for learning prompt design.

The application intentionally makes no model calls. Students can build and
inspect prompts locally, then paste outputs produced by any model for a fair,
side-by-side evaluation. This keeps the Space public, inexpensive, and usable
without secrets or a database.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import re
import secrets
import tempfile

import gradio as gr
from openai import OpenAI


APP_TITLE = "PromptLab"
DEFAULT_MODEL = "gpt-5.6-luna"
REASONING_EFFORT = "medium"
MAX_PROMPT_CHARS = 20_000
MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "6000"))


TEMPLATES = {
    "Start from scratch": {
        "task": "",
        "context": "",
        "audience": "",
        "input_data": "",
        "constraints": "",
        "output_format": "",
        "examples": "",
        "evidence": "",
        "uncertainty": "",
        "criteria": "",
    },
    "Business decision": {
        "task": "Recommend whether the company should launch the proposed service.",
        "context": "A mid-sized retailer is considering a subscription delivery service. Management needs a decision, not a generic market overview.",
        "audience": "Executive committee with limited technical knowledge.",
        "input_data": "Use only the supplied customer, cost, and competitor information. Clearly distinguish supplied facts from assumptions.",
        "constraints": "Consider value, feasibility, strategic fit, implementation risk, and opportunity cost. Keep the main answer under 700 words.",
        "output_format": "Executive summary; evidence table; recommendation; three next actions.",
        "examples": "A useful recommendation states what to do, why, under which assumptions, and what evidence could reverse it.",
        "evidence": "For every major claim, cite the relevant supplied fact or label it as an inference.",
        "uncertainty": "Give confidence as low, medium, or high and identify the two uncertainties that most affect the decision.",
        "criteria": "Decision usefulness, numerical consistency, traceability to evidence, and explicit trade-offs.",
    },
    "Scientific exploration": {
        "task": "Evaluate the proposed hypothesis and design a discriminating experiment.",
        "context": "The goal is exploration, not confirmation. Avoid treating conceptual consistency as empirical support.",
        "audience": "Researchers familiar with the field but not with this specific framework.",
        "input_data": "Use the hypothesis, observations, and papers supplied below. Do not invent references or results.",
        "constraints": "Separate definitions, assumptions, predictions, and evidence. Include at least two plausible rival explanations.",
        "output_format": "Hypothesis map; strongest argument; strongest objection; experiment table; conclusion.",
        "examples": "A strong experiment predicts meaningfully different observations under the focal and rival hypotheses.",
        "evidence": "Attach each empirical claim to a supplied source. Mark unsupported statements as hypotheses requiring verification.",
        "uncertainty": "Use calibrated verbal confidence and state what new result would change the conclusion.",
        "criteria": "Falsifiability, non-circularity, rival hypotheses, measurement validity, and informational value of the experiment.",
    },
    "Data analysis": {
        "task": "Analyse the dataset to answer the stated business question.",
        "context": "The analysis will inform an operational decision. Descriptive patterns must not be presented as causal effects.",
        "audience": "Product owner and data analyst.",
        "input_data": "Inspect the schema, sample size, missingness, units, and target definition before modelling.",
        "constraints": "Do not silently drop rows or impute values. Avoid data leakage. Use a simple baseline before complex methods.",
        "output_format": "Data-quality findings; method; results table; limitations; recommended next step.",
        "examples": "Report absolute values as well as percentages, and compare performance with an explicit baseline.",
        "evidence": "Every numerical conclusion must be reproducible from the supplied data or code output.",
        "uncertainty": "Report sampling or model uncertainty where appropriate and distinguish absence of evidence from evidence of absence.",
        "criteria": "Correctness, leakage prevention, reproducibility, appropriate baseline, and decision relevance.",
    },
    "Critical review": {
        "task": "Critically review the argument without defaulting to agreement or disagreement.",
        "context": "The author wants to find weaknesses early and improve the argument before publication.",
        "audience": "A demanding but constructive expert reader.",
        "input_data": "Evaluate only the text and sources supplied. Do not attribute claims that are not present.",
        "constraints": "Identify hidden assumptions, circular reasoning, unfalsifiable claims, missing alternatives, and scope errors.",
        "output_format": "Thesis reconstruction; strongest contribution; major concerns ranked by severity; revisions; verdict.",
        "examples": "For each criticism, quote or precisely paraphrase the relevant claim and explain why it matters.",
        "evidence": "Distinguish textual evidence, external fact, and your own inference.",
        "uncertainty": "State when a criticism depends on an interpretation and offer the strongest alternative reading.",
        "criteria": "Charitable reconstruction, specificity, logical validity, evidential support, and actionable revision advice.",
    },
    "Coding task": {
        "task": "Implement the requested feature and verify that it works.",
        "context": "Preserve existing behaviour unless the requirement explicitly changes it.",
        "audience": "A maintainer who will review and extend the code.",
        "input_data": "Use the supplied repository structure, interfaces, tests, and runtime constraints.",
        "constraints": "Make the smallest coherent change. Do not add dependencies without justification. Do not expose secrets.",
        "output_format": "Implementation; tests run; assumptions; remaining limitations.",
        "examples": "A complete answer includes edge cases and evidence from tests, not only a code listing.",
        "evidence": "Base claims about behaviour on inspected code or executed tests. Label anything not verified.",
        "uncertainty": "List untested paths and conditions that could invalidate the solution.",
        "criteria": "Correctness, maintainability, security, test coverage, and compatibility.",
    },
}


EXAMPLES = {
    "Customer segmentation": {
        "weak": "Analyse our customer data and find useful segments.",
        "issues": [
            "The decision and intended user are unspecified.",
            "There is no definition of a useful segment.",
            "Variables, constraints, and output format are missing.",
            "The model may invent columns, causal explanations, or business actions.",
        ],
        "strong": """Act as a customer analytics consultant. Using only the attached customer table, propose 3–5 actionable segments based on recency, purchase frequency, average order value, discount usage, and engagement. First inspect missing values and variable ranges. Explain the segmentation method and justify the number of segments against a simple baseline. For each segment, provide size, defining features, business interpretation, one recommended action, and one risk. Do not infer causality from correlations. Return: (1) data-quality notes, (2) segment comparison table, (3) recommended actions, and (4) limitations. Flag any conclusion not supported by the supplied data.""",
    },
    "Scientific hypothesis": {
        "weak": "Prove that my theory of curiosity is correct.",
        "issues": [
            "It requests confirmation rather than a test.",
            "No theory, evidence, or rival explanation is supplied.",
            "The word “prove” is usually inappropriate for empirical work.",
            "It invites sycophancy and confirmation bias.",
        ],
        "strong": """Evaluate the following curiosity hypothesis as a critical collaborator: [HYPOTHESIS]. Reconstruct its assumptions and derive three risky predictions. Generate at least two rival explanations that fit the current observations. Design one experiment in which the focal hypothesis and its strongest rival predict different outcomes. For each measurement, state the operational definition and likely confounds. Conclude with calibrated confidence and specify what result would falsify or substantially weaken the hypothesis. Do not treat internal consistency as empirical evidence; use [NEEDS VERIFICATION] when evidence is unavailable.""",
    },
    "Executive recommendation": {
        "weak": "Should we use AI in customer service? Give pros and cons.",
        "issues": [
            "The workflow, organization, and decision threshold are undefined.",
            "A generic pros-and-cons list does not support a decision.",
            "No information is given about volume, cost, risk, or data.",
            "There is no request for assumptions or a pilot design.",
        ],
        "strong": """Advise a mid-sized online retailer on whether to pilot an AI assistant for order-status and return-policy enquiries. Use the supplied ticket volumes, handling times, error costs, and satisfaction data. Compare three options: no change, agent-assist, and partially automated service. Evaluate expected value, feasibility, customer risk, employee impact, and reversibility. State assumptions explicitly and show a sensitivity table for adoption and error rate. Recommend one option, define go/no-go metrics for a six-week pilot, and identify the evidence that would reverse your recommendation. Keep the executive summary under 200 words.""",
    },
    "Misleading summary": {
        "weak": "Summarise this report and explain why the project succeeded.",
        "issues": [
            "It embeds the unverified premise that the project succeeded.",
            "The model is pushed to select confirming evidence.",
            "Success criteria and audience are undefined.",
            "Contradictory evidence may be omitted.",
        ],
        "strong": """Summarise the attached report for the steering committee. First identify the project’s stated success criteria. For each criterion, classify the available evidence as met, partly met, not met, or insufficient. Include evidence that supports and challenges a positive conclusion. Separate reported facts from your interpretation. End with a neutral assessment of whether the project succeeded, your confidence, and the missing information most likely to change that assessment.""",
    },
    "Humorous constraint failure": {
        "weak": "Write a short email that is detailed, exhaustive, poetic, legally precise, funny, serious, exactly 30 words, and includes all 17 policy clauses.",
        "issues": [
            "The constraints are mutually incompatible.",
            "No priority is given when requirements conflict.",
            "Thirty words cannot reliably contain all requested content.",
            "The model may quietly violate constraints while sounding confident.",
        ],
        "strong": """Draft an email announcing the updated policy. Priority order: (1) legal accuracy, (2) the three actions employees must take, (3) clarity, and (4) a lightly humorous closing. The body may use up to 180 words. Link to the full 17-clause policy rather than reproducing it. If the legal summary cannot be both accurate and concise, flag the conflict and favour accuracy.""",
    },
}


CHALLENGES = {
    "1 · The agreeable analyst": {
        "brief": "Repair a prompt that invites the model to endorse the user’s preferred strategy.",
        "bad": "Our CEO thinks entering the German market is obviously the best move. Analyse the data and explain convincingly why she is right.",
        "checks": ["neutral framing", "alternatives", "decision criteria", "disconfirming evidence", "uncertainty"],
        "solution": """Evaluate whether entering the German market is preferable to the two strongest alternatives, using the supplied market, cost, and capability data. Define decision criteria before comparing options. Present the strongest evidence for and against each option, identify assumptions, and run a sensitivity analysis on the variables most likely to change the ranking. Make a recommendation only after the comparison, state confidence, and specify what evidence would reverse it.""",
    },
    "2 · The impossible research request": {
        "brief": "Make the task scientifically defensible and explicit about unavailable evidence.",
        "bad": "Read every paper ever written about consciousness, find the true theory, and prove it with no uncertainty.",
        "checks": ["bounded scope", "source policy", "comparison criteria", "uncertainty", "verification"],
        "solution": """Using the papers supplied and a clearly documented literature-search protocol, compare leading theories of consciousness published within the stated scope. Define evaluation criteria such as empirical specificity, falsifiability, explanatory reach, and evidential support. Identify where evidence discriminates among theories and where it does not. Do not select a uniquely true theory unless the evidence warrants it. Mark missing or unverified sources, report uncertainty, and propose the experiment with the highest expected discriminatory value.""",
    },
    "3 · The magical data scientist": {
        "brief": "Prevent invented data, leakage, and causal overclaiming.",
        "bad": "Use our spreadsheet to predict which customers will leave, explain why they leave, and guarantee 95% accuracy.",
        "checks": ["target definition", "data audit", "baseline", "leakage", "causal caution", "metric"],
        "solution": """Using the supplied spreadsheet, first define the churn target and prediction horizon, then audit sample size, missingness, class balance, and possible leakage. Build a simple baseline before testing more complex models. Evaluate with metrics appropriate to the business cost, using a held-out set. Treat feature importance as predictive association, not proof of why customers leave. Report uncertainty and limitations; do not promise a performance threshold before inspecting the data.""",
    },
    "4 · The contradiction machine": {
        "brief": "Resolve competing requirements by declaring priorities and feasible limits.",
        "bad": "Write a complete but very short technical report. Explain everything to beginners but assume expert knowledge. Use no jargon but retain every technical term.",
        "checks": ["audience", "priority", "length", "technical terms", "conflict rule"],
        "solution": """Write a two-page technical briefing for readers with general scientific literacy but no specialist knowledge of this topic. Preserve essential technical terms, define each at first use, and omit implementation detail that is not necessary for the central argument. Priority order: conceptual accuracy, clarity, then brevity. If a concept cannot be explained accurately within the limit, name it and link it to an appendix rather than oversimplifying it.""",
    },
    "5 · The confident historian": {
        "brief": "Add evidence boundaries and a safe response to uncertain facts.",
        "bad": "Tell me the exact private conversation that caused the minister to resign and include realistic quotations.",
        "checks": ["available evidence", "no fabrication", "source distinction", "uncertainty", "alternative explanation"],
        "solution": """Using reliable public sources, summarise the documented events and stated reasons surrounding the minister’s resignation. Distinguish direct evidence, contemporary reporting, later interpretation, and unresolved speculation. Do not invent private conversations or quotations. Where motives are uncertain, present the leading supported explanations and describe the evidence for each. Use [UNKNOWN] when the public record does not establish a fact.""",
    },
}


CRITERIA = [
    "Task completion",
    "Accuracy",
    "Relevance",
    "Clarity",
    "Evidence",
    "Uncertainty",
    "Format compliance",
    "Safety & fairness",
]


CSS = """
:root { --pl-ink: #172033; --pl-navy: #14213d; --pl-blue: #2f6fed; --pl-mint: #14b8a6; }
.gradio-container { max-width: 1240px !important; margin: 0 auto !important; }
.hero { background: linear-gradient(125deg, #14213d 0%, #203768 58%, #176b75 100%);
        color: white; padding: 28px 32px; border-radius: 18px; margin: 8px 0 18px; }
.hero h1 { color: white !important; font-size: 2.25rem !important; margin: 0 0 5px !important; }
.hero p { color: #dbeafe !important; font-size: 1.03rem; margin: 0 !important; max-width: 850px; }
.step { background: #f7f9fc; border-left: 4px solid #2f6fed; padding: 12px 16px; border-radius: 8px; }
.card-note { background: #ecfeff; border: 1px solid #a5f3fc; padding: 10px 14px; border-radius: 10px; }
.footer { text-align: center; color: #64748b; font-size: .88rem; padding: 18px; }
textarea { line-height: 1.42 !important; }
"""


def clean(value: str | None) -> str:
    """Normalize a text-field value without changing its meaning."""
    return (value or "").strip()


def api_configuration_status() -> str:
    """Return a safe, user-facing summary without exposing secret values."""
    has_key = bool(os.getenv("OPENAI_API_KEY"))
    has_code = bool(os.getenv("CLASS_ACCESS_CODE"))
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    if has_key and has_code:
        return f"🟢 Live testing available · `{model}` · reasoning `{REASONING_EFFORT}`"
    missing = []
    if not has_key:
        missing.append("OPENAI_API_KEY")
    if not has_code:
        missing.append("CLASS_ACCESS_CODE")
    return "🟠 Paste-only mode · instructor must configure: " + ", ".join(missing)


def call_luna(prompt: str, access_code: str):
    """Call OpenAI Responses API using a server-side key and guarded access."""
    prompt = clean(prompt)
    expected_code = os.getenv("CLASS_ACCESS_CODE", "")
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

    if not api_key:
        return "", "API unavailable: the instructor has not configured `OPENAI_API_KEY`."
    if not expected_code:
        return "", "API locked: set `CLASS_ACCESS_CODE` in the Space secrets before enabling live calls."
    if not secrets.compare_digest(clean(access_code), expected_code):
        return "", "Access denied: check the class access code."
    if not prompt:
        return "", "Add a prompt before running the model."
    if len(prompt) > MAX_PROMPT_CHARS:
        return "", f"Prompt too long: maximum {MAX_PROMPT_CHARS:,} characters."

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            reasoning={"effort": REASONING_EFFORT},
            input=[{"role": "user", "content": prompt}],
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        answer = response.output_text or ""
        status = f"Completed with `{model}` · reasoning `{REASONING_EFFORT}`"
        if getattr(response, "status", None) == "incomplete":
            reason = getattr(getattr(response, "incomplete_details", None), "reason", "unknown")
            status = f"Incomplete response ({reason}). The visible partial answer is shown."
        usage = getattr(response, "usage", None)
        if usage:
            input_tokens = getattr(usage, "input_tokens", None)
            output_tokens = getattr(usage, "output_tokens", None)
            if input_tokens is not None and output_tokens is not None:
                status += f" · {input_tokens:,} input / {output_tokens:,} output tokens"
        return answer, status
    except Exception as exc:  # API/network failures must not crash the classroom app.
        return "", f"The model request failed ({type(exc).__name__}). Ask the instructor to check the Space logs and API configuration."


def call_luna_pair(prompt_a: str, prompt_b: str, access_code: str):
    """Run two prompts under identical model settings for a controlled comparison."""
    answer_a, status_a = call_luna(prompt_a, access_code)
    if not answer_a:
        return "", "", f"**A:** {status_a}"
    answer_b, status_b = call_luna(prompt_b, access_code)
    return answer_a, answer_b, f"**A:** {status_a}\n\n**B:** {status_b}"


def load_template(name: str):
    item = TEMPLATES.get(name, TEMPLATES["Start from scratch"])
    return tuple(item[key] for key in (
        "task", "context", "audience", "input_data", "constraints",
        "output_format", "examples", "evidence", "uncertainty", "criteria",
    ))


def build_prompt(
    task, context, audience, input_data, constraints, output_format,
    examples, evidence, uncertainty, criteria, compact=False,
):
    values = {
        "TASK": clean(task),
        "CONTEXT": clean(context),
        "AUDIENCE": clean(audience),
        "INPUTS AND DATA BOUNDARY": clean(input_data),
        "METHOD AND CONSTRAINTS": clean(constraints),
        "OUTPUT FORMAT": clean(output_format),
        "EXAMPLE OR QUALITY ANCHOR": clean(examples),
        "EVIDENCE AND VERIFICATION": clean(evidence),
        "UNCERTAINTY POLICY": clean(uncertainty),
        "SUCCESS CRITERIA": clean(criteria),
    }

    if not values["TASK"]:
        return "Add a task before generating the prompt.", prompt_diagnostics("")

    if compact:
        pieces = []
        for label, value in values.items():
            if value:
                pieces.append(f"{label.title()}: {value}")
        prompt = "\n".join(pieces)
    else:
        pieces = [
            "You are a careful collaborator. Follow the task and boundaries below. "
            "Do not silently invent missing facts or ignore conflicting requirements."
        ]
        for label, value in values.items():
            if value:
                pieces.append(f"## {label}\n{value}")
        pieces.append(
            "## FINAL CHECK\nBefore answering, verify that the response follows the requested "
            "format, separates facts from assumptions, and flags material uncertainty."
        )
        prompt = "\n\n".join(pieces)

    return prompt, prompt_diagnostics(prompt)


def prompt_diagnostics(prompt: str) -> str:
    text = clean(prompt).lower()
    if not text:
        return "### Prompt check\nAdd or generate a prompt to see the diagnostic."

    checks = [
        ("Clear task", any(x in text for x in ["task", "analyse", "analyze", "evaluate", "write", "recommend", "implement", "summarise", "summarize"])),
        ("Context or audience", any(x in text for x in ["context", "audience", "committee", "reader", "customer", "researcher", "maintainer"])),
        ("Constraints or boundaries", any(x in text for x in ["constraint", "only", "must", "do not", "under ", "limit", "boundary"])),
        ("Output structure", any(x in text for x in ["output", "return", "table", "format", "sections", "json"])),
        ("Evidence or verification", any(x in text for x in ["evidence", "source", "cite", "verify", "reproduc", "supplied data"])),
        ("Uncertainty handling", any(x in text for x in ["uncertain", "confidence", "assumption", "unknown", "limitation", "flag"])),
        ("Quality criteria", any(x in text for x in ["criteria", "successful", "quality", "accuracy", "correctness", "falsifi"])),
    ]
    count = sum(ok for _, ok in checks)
    rows = [f"- {'✅' if ok else '○'} {label}" for label, ok in checks]
    caution = ""
    if len(text.split()) > 450:
        caution = "\n\n> The prompt is long. Remove repetition before removing useful constraints."
    if any(term in text for term in ["prove that", "obviously", "guarantee", "tell me why i am right"]):
        caution += "\n\n> Possible leading or impossible requirement detected. Reframe it as a comparison or test."
    return f"### Prompt check: {count}/{len(checks)} signals present\n" + "\n".join(rows) + caution


def load_example(name: str):
    item = EXAMPLES[name]
    issues = "### Why the weak prompt fails\n" + "\n".join(f"- {x}" for x in item["issues"])
    return item["weak"], issues, item["strong"]


def load_challenge(name: str):
    item = CHALLENGES[name]
    checks = ", ".join(item["checks"])
    brief = f"**Your task:** {item['brief']}\n\n**Try to include:** {checks}."
    return brief, item["bad"], "", "Write your repair, then select **Check my repair**."


def check_repair(name: str, revision: str):
    item = CHALLENGES[name]
    text = clean(revision).lower()
    if len(text.split()) < 18:
        return "### Not enough to evaluate\nWrite a complete revised prompt of at least a few sentences."

    signal_groups = {
        "neutral framing": ["evaluate", "compare", "whether", "for and against"],
        "alternatives": ["alternative", "option", "rival"],
        "decision criteria": ["criteria", "value", "feasibility", "compare"],
        "disconfirming evidence": ["against", "reverse", "weaken", "disconfirm"],
        "uncertainty": ["uncertain", "confidence", "assumption", "limitation"],
        "bounded scope": ["supplied", "scope", "selected", "published", "search protocol"],
        "source policy": ["source", "paper", "cite", "reference"],
        "comparison criteria": ["criteria", "compare", "falsifi", "evidence"],
        "verification": ["verify", "unverified", "check", "source"],
        "target definition": ["target", "churn", "horizon", "define"],
        "data audit": ["missing", "sample", "balance", "audit", "schema"],
        "baseline": ["baseline"],
        "leakage": ["leakage", "held-out", "test set"],
        "causal caution": ["causal", "association", "correlation", "not proof"],
        "metric": ["metric", "precision", "recall", "auc", "cost"],
        "audience": ["audience", "reader", "beginner", "scientific literacy"],
        "priority": ["priority", "priorit"],
        "length": ["word", "page", "length"],
        "technical terms": ["technical term", "define", "jargon"],
        "conflict rule": ["if", "conflict", "favour", "favor"],
        "available evidence": ["public", "documented", "available", "reliable"],
        "no fabrication": ["do not invent", "do not fabricate", "unknown", "no invented"],
        "source distinction": ["distinguish", "direct evidence", "reporting", "interpretation"],
        "alternative explanation": ["explanation", "motive", "alternative"],
    }
    outcomes = []
    hits = 0
    for requirement in item["checks"]:
        terms = signal_groups.get(requirement, requirement.split())
        present = any(term in text for term in terms)
        hits += int(present)
        outcomes.append(f"- {'✅' if present else '○'} {requirement.title()}")

    general = []
    if any(x in text for x in ["obviously", "prove that", "guarantee"]):
        general.append("- The revision still contains leading or impossible language.")
    if not any(x in text for x in ["table", "sections", "return", "output", "conclude", "summary"]):
        general.append("- Consider specifying the expected output structure.")
    if not general:
        general.append("- The prompt has no obvious leading or impossible requirement.")

    return (
        f"### Repair check: {hits}/{len(item['checks'])} challenge signals detected\n"
        + "\n".join(outcomes)
        + "\n\n### General feedback\n"
        + "\n".join(general)
        + "\n\n*This is a transparent keyword-based teaching aid, not an AI grade. Defend choices that the checker misses.*"
    )


def reveal_solution(name: str):
    item = CHALLENGES[name]
    return f"### Example repair — not the only correct answer\n\n{item['solution']}"


def analyse_pair(prompt_a: str, prompt_b: str):
    return (
        "## Prompt A\n" + prompt_diagnostics(prompt_a)
        + "\n\n---\n\n## Prompt B\n" + prompt_diagnostics(prompt_b)
        + "\n\n> Structural signals do not guarantee a good prompt. Use the model outputs and rubric to test whether the changes matter."
    )


def weighted_total(scores, critical):
    total = sum(scores)
    # A critical factual/safety failure limits an otherwise polished response.
    adjusted = min(total, 20) if critical else total
    return total, adjusted


def evaluation_report(
    student, case_title, prompt_a, prompt_b, output_a, output_b,
    scores_a, scores_b, critical_a, critical_b, preferred, justification,
):
    raw_a, total_a = weighted_total(scores_a, critical_a)
    raw_b, total_b = weighted_total(scores_b, critical_b)
    winner = preferred
    if preferred == "Let the rubric decide":
        winner = "A" if total_a > total_b else "B" if total_b > total_a else "Tie"

    result = f"""### Evaluation result

| Response | Raw score | Adjusted score | Critical error |
|---|---:|---:|:---:|
| A | {raw_a}/40 | **{total_a}/40** | {'Yes' if critical_a else 'No'} |
| B | {raw_b}/40 | **{total_b}/40** | {'Yes' if critical_b else 'No'} |

**Selected result:** {winner}

Scores organize judgment; they do not replace it. A critical error caps the adjusted score at 20/40.
"""

    rows = "\n".join(
        f"| {criterion} | {a} | {b} |"
        for criterion, a, b in zip(CRITERIA, scores_a, scores_b)
    )
    report = f"""# PromptLab Evaluation Report

- **Student/team:** {clean(student) or 'Not specified'}
- **Case:** {clean(case_title) or 'Untitled comparison'}
- **Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
- **Selected result:** {winner}

## Rubric

| Criterion | A | B |
|---|---:|---:|
{rows}
| **Raw total** | **{raw_a}/40** | **{raw_b}/40** |
| **Adjusted total** | **{total_a}/40** | **{total_b}/40** |

- Critical error in A: {'Yes' if critical_a else 'No'}
- Critical error in B: {'Yes' if critical_b else 'No'}

## Justification

{clean(justification) or 'No justification supplied.'}

## Prompt A

{clean(prompt_a) or '[Not supplied]'}

## Output A

{clean(output_a) or '[Not supplied]'}

## Prompt B

{clean(prompt_b) or '[Not supplied]'}

## Output B

{clean(output_b) or '[Not supplied]'}

---
Generated by PromptLab. Scores reflect the evaluator's judgment, not an automated truth assessment.
"""
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", clean(case_title))[:40].strip("_") or "comparison"
    temp_dir = Path(tempfile.mkdtemp(prefix="promptlab_"))
    report_path = temp_dir / f"promptlab_{safe_stem}.md"
    report_path.write_text(report, encoding="utf-8")
    return result, str(report_path)


def run_evaluation(
    student, case_title, prompt_a, prompt_b, output_a, output_b,
    *rubric_values,
):
    scores_a = list(rubric_values[:8])
    scores_b = list(rubric_values[8:16])
    critical_a, critical_b, preferred, justification = rubric_values[16:20]
    return evaluation_report(
        student, case_title, prompt_a, prompt_b, output_a, output_b,
        scores_a, scores_b, critical_a, critical_b, preferred, justification,
    )


theme = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="teal",
    neutral_hue="slate",
    radius_size="lg",
    font=[gr.themes.GoogleFont("Inter"), "Arial", "sans-serif"],
)


with gr.Blocks(title=f"{APP_TITLE} · Learn Prompting") as demo:
    gr.HTML(
        """<section class="hero"><h1>PromptLab</h1>
        <p>Build, repair, test, and evaluate prompts. The goal is not to discover magic words—it is to design a clearer task and test whether the result improves.</p></section>"""
    )
    with gr.Row():
        api_status = gr.Markdown(api_configuration_status())
        class_access_code = gr.Textbox(
            label="Class access code",
            type="password",
            placeholder="Provided by the instructor",
            max_lines=1,
        )

    with gr.Tabs():
        with gr.Tab("1 · Build"):
            gr.Markdown(
                """<div class="step"><b>FRAME in practice:</b> define the function and task, provide relevant context, specify a method and boundaries, then state how the answer will be evaluated.</div>"""
            )
            with gr.Row():
                with gr.Column(scale=5):
                    template = gr.Dropdown(list(TEMPLATES), value="Business decision", label="Load a template")
                    task = gr.Textbox(label="Task · What should the model accomplish?", lines=2)
                    context = gr.Textbox(label="Context · What situation matters?", lines=3)
                    audience = gr.Textbox(label="Audience · Who will use the answer?", lines=2)
                    input_data = gr.Textbox(label="Inputs and data boundary", lines=3)
                    constraints = gr.Textbox(label="Method and constraints", lines=3)
                with gr.Column(scale=5):
                    output_format = gr.Textbox(label="Output format", lines=3)
                    examples = gr.Textbox(label="Example or quality anchor", lines=3)
                    evidence = gr.Textbox(label="Evidence and verification policy", lines=3)
                    uncertainty = gr.Textbox(label="Uncertainty policy", lines=3)
                    criteria = gr.Textbox(label="Success criteria", lines=3)

            with gr.Row():
                generate = gr.Button("Generate structured prompt", variant="primary")
                compact = gr.Button("Generate compact prompt")
                run_built = gr.Button("Run with Luna · medium")
            with gr.Row():
                built_prompt = gr.Textbox(label="Generated prompt", lines=18, buttons=["copy"])
                diagnostics = gr.Markdown("### Prompt check\nGenerate a prompt to see the diagnostic.")
            built_answer = gr.Textbox(label="Luna response", lines=14, buttons=["copy"])
            built_status = gr.Markdown()

            fields = [task, context, audience, input_data, constraints, output_format, examples, evidence, uncertainty, criteria]
            template.change(load_template, template, fields)
            generate.click(build_prompt, fields, [built_prompt, diagnostics])
            compact.click(lambda *x: build_prompt(*x, compact=True), fields, [built_prompt, diagnostics])
            run_built.click(
                call_luna,
                [built_prompt, class_access_code],
                [built_answer, built_status],
                concurrency_limit=2,
            )
            demo.load(load_template, gr.State("Business decision"), fields)

        with gr.Tab("2 · Examples"):
            gr.Markdown("Compare prompts by the behaviours they invite—not by length or sophistication of vocabulary.")
            example_name = gr.Dropdown(list(EXAMPLES), value="Customer segmentation", label="Example")
            with gr.Row():
                weak_prompt = gr.Textbox(label="Weak prompt", lines=12, interactive=True, buttons=["copy"])
                strong_prompt = gr.Textbox(label="Improved prompt", lines=12, interactive=True, buttons=["copy"])
            example_issues = gr.Markdown()
            gr.Markdown(
                """<div class="card-note"><b>Mini-experiment:</b> run both prompts with the same model, input, and settings. Then evaluate the outputs in Tab 4. Change one design choice at a time if you want to know what caused the difference.</div>"""
            )
            run_example_pair = gr.Button("Run both with Luna · medium", variant="primary")
            with gr.Row():
                weak_answer = gr.Textbox(label="Output from weak prompt", lines=12)
                strong_answer = gr.Textbox(label="Output from improved prompt", lines=12)
            example_api_status = gr.Markdown()
            example_name.change(load_example, example_name, [weak_prompt, example_issues, strong_prompt])
            run_example_pair.click(
                call_luna_pair,
                [weak_prompt, strong_prompt, class_access_code],
                [weak_answer, strong_answer, example_api_status],
                concurrency_limit=1,
            )
            demo.load(lambda: load_example("Customer segmentation"), outputs=[weak_prompt, example_issues, strong_prompt])

        with gr.Tab("3 · Repair"):
            gr.Markdown("Repair the failure mode before seeing the example answer. The checker is deliberately simple and transparent.")
            challenge_name = gr.Dropdown(list(CHALLENGES), value="1 · The agreeable analyst", label="Challenge")
            challenge_brief = gr.Markdown()
            bad_prompt = gr.Textbox(label="Prompt to repair", lines=5, interactive=False)
            student_repair = gr.Textbox(label="Your revised prompt", lines=10, placeholder="Rewrite the prompt here…")
            with gr.Row():
                check_button = gr.Button("Check my repair", variant="primary")
                reveal_button = gr.Button("Reveal example repair")
            repair_feedback = gr.Markdown()
            challenge_name.change(load_challenge, challenge_name, [challenge_brief, bad_prompt, student_repair, repair_feedback])
            check_button.click(check_repair, [challenge_name, student_repair], repair_feedback)
            reveal_button.click(reveal_solution, challenge_name, repair_feedback)
            demo.load(lambda: load_challenge("1 · The agreeable analyst"), outputs=[challenge_brief, bad_prompt, student_repair, repair_feedback])

        with gr.Tab("4 · Test & Evaluate"):
            gr.Markdown(
                """Test two prompts under comparable conditions. Paste outputs from any model, score them independently, and justify the conclusion. Do not paste confidential or personal data into public AI services."""
            )
            with gr.Row():
                student = gr.Textbox(label="Student or team")
                case_title = gr.Textbox(label="Case title", value="Prompt comparison")
            with gr.Row():
                prompt_a = gr.Textbox(label="Prompt A", lines=8)
                prompt_b = gr.Textbox(label="Prompt B", lines=8)
            inspect_pair = gr.Button("Inspect prompt structure")
            pair_diagnostic = gr.Markdown()
            inspect_pair.click(analyse_pair, [prompt_a, prompt_b], pair_diagnostic)
            with gr.Row():
                output_a = gr.Textbox(label="Model output A", lines=14, placeholder="Paste the response produced with Prompt A…")
                output_b = gr.Textbox(label="Model output B", lines=14, placeholder="Paste the response produced with Prompt B…")
            run_test_pair = gr.Button("Run both prompts with Luna · medium", variant="primary")
            test_api_status = gr.Markdown()
            run_test_pair.click(
                call_luna_pair,
                [prompt_a, prompt_b, class_access_code],
                [output_a, output_b, test_api_status],
                concurrency_limit=1,
            )

            gr.Markdown("### Evaluation rubric · 1 = poor, 5 = excellent")
            sliders_a = []
            sliders_b = []
            for criterion_name in CRITERIA:
                with gr.Row():
                    gr.Markdown(f"**{criterion_name}**")
                    sa = gr.Slider(1, 5, value=3, step=1, label="A")
                    sb = gr.Slider(1, 5, value=3, step=1, label="B")
                sliders_a.append(sa)
                sliders_b.append(sb)

            with gr.Row():
                critical_a = gr.Checkbox(label="A contains a critical factual, logical, or safety error")
                critical_b = gr.Checkbox(label="B contains a critical factual, logical, or safety error")
            with gr.Row():
                preferred = gr.Radio(
                    ["Let the rubric decide", "A", "B", "Tie"],
                    value="Let the rubric decide",
                    label="Final judgment",
                )
                justification = gr.Textbox(
                    label="Justification",
                    lines=5,
                    placeholder="Which concrete differences mattered? Did a better score reflect a genuinely better answer?",
                )
            evaluate_button = gr.Button("Calculate and create report", variant="primary")
            evaluation_result = gr.Markdown()
            report_file = gr.File(label="Download evaluation report")
            evaluate_inputs = [
                student, case_title, prompt_a, prompt_b, output_a, output_b,
                *sliders_a, *sliders_b, critical_a, critical_b, preferred, justification,
            ]
            evaluate_button.click(run_evaluation, evaluate_inputs, [evaluation_result, report_file])

    gr.HTML(
        """<div class="footer">PromptLab · OpenAI Responses API · Luna with medium reasoning · No database or GPU required</div>"""
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=16).launch(theme=theme, css=CSS)
