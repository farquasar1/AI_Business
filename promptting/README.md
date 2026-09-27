---
title: PromptLab
emoji: 🧪
colorFrom: blue
colorTo: teal
sdk: gradio
sdk_version: 6.28.0
app_file: app.py
pinned: false
license: mit
suggested_hardware: cpu-basic
short_description: Learn prompting with live Luna comparisons and evaluation
---

# PromptLab

PromptLab is a lightweight classroom app for learning prompt design. It uses
the OpenAI Responses API with `gpt-5.6-luna` and medium reasoning. Students can:

1. Assemble a structured prompt from a reusable template.
2. Compare weak and improved examples.
3. Repair prompts with common failure modes.
4. Run two prompts with identical model settings, evaluate both outputs with a
   rubric, and download a report.

If the API is not configured, every activity still works in paste-only mode.
The project is pinned to Gradio 6.28.0 so Hugging Face does not silently build
the Space with a different Gradio 6 release.

## Deploy on Hugging Face Spaces

1. Create a new **Gradio** Space.
2. Upload `app.py`, `README.md`, and `requirements.txt` to the repository root.
3. In **Settings → Variables and secrets**, create these private secrets:
   - `OPENAI_API_KEY`: the instructor's OpenAI Platform API key.
   - `CLASS_ACCESS_CODE`: a password shared only with enrolled students.
4. In **Settings → Hardware**, select **CPU Basic**. PromptLab calls the OpenAI
   API and therefore performs no local model inference. Do not select ZeroGPU:
   that runtime requires a genuine GPU-dependent function decorated with
   `@spaces.GPU`, which this application neither has nor needs.
5. Wait for the Space to build, then open the app.

Optional configuration:

- `OPENAI_MODEL`: defaults to `gpt-5.6-luna`.
- `OPENAI_MAX_OUTPUT_TOKENS`: defaults to `6000`.

Never place an API key directly in `app.py`, `README.md`, or a public Space
variable. Use a private Space secret.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open the local URL shown by Gradio, normally `http://127.0.0.1:7860`.

## Teaching flow

- Ask students to build a first prompt in **Build**.
- Use **Examples** to discuss what changed and why.
- Assign one problem from **Repair** to each group.
- Run original and revised prompts in the same external model.
- Paste both answers into **Test & Evaluate** and submit the downloaded report.

The diagnostic and repair checker use visible keyword rules. They are teaching
scaffolds, not automated grades. Students should explain reasonable choices
that the checker does not recognize.

## Privacy

PromptLab has no application database. Generated reports are temporary files on
the running Space. Live prompts are sent to the OpenAI API using the
instructor's account. Students should not submit confidential, personal, or
licensed data without permission.

For a public Space, keep `CLASS_ACCESS_CODE` enabled and rotate it between
cohorts. The interface limits prompt size and model-call concurrency, but the
instructor should still configure project-level spend limits and monitor usage.
