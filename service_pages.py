"""Copy and metadata for the dedicated service pages (/service/<slug>.html).

Kept out of build.py because it is prose the owner reviews, not logic. Everything
here restates what services.html already commits to: no prices, no client names,
no certifications, and "reduce and evidence", never "prevent" or "guarantee"
(decisions E5 and the plan's Never list).

`offer` is the Service @id slug on services.html (see _SERVICE_OFFERS in build.py)
and `subject` the contact-form subject the CTA preselects. `related` lists the
other pages' slugs shown as "Related".
"""
from __future__ import annotations

SERVICE_PAGES: list[dict] = [
    {
        "slug": "rag-pipelines",
        "offer": "build",
        "subject": "build",
        "nav_name": "RAG pipeline review & sprint",
        "title": "RAG Pipeline Consulting: Review & Sprint",
        "meta": ("A fixed-scope review or fresh design of your RAG pipeline: tuned on "
                 "your own questions, measured with an evaluation set, sources on every answer."),
        "h1": "RAG pipeline review & sprint",
        "lede": ("A retrieval-augmented generation (RAG) pipeline answers questions from your "
                 "own documents and shows where each answer came from. We review the one you "
                 "have, or design a new one, and measure it against your real questions so "
                 "quality is shown and not assumed."),
        "facts": "Fixed scope · typically 2 weeks",
        "get": [
            "Review of your current retrieval setup, or a fresh design",
            "Chunking, indexing and ranking tuned on your own questions",
            "An evaluation set, so quality is measured and not guessed",
            "Source attribution and an audit trail for every answer",
        ],
        "fit_title": "When this fits",
        "fit": [
            "You have documents or data you want an AI assistant to answer from.",
            "A prototype gives plausible answers, but you cannot tell how often they are right.",
            "You need every answer to carry its sources, for users or for an audit.",
        ],
        "steps": [
            ("Look at the questions",
             "We start from the questions your users actually ask, and the documents that should answer them."),
            ("Tune and measure",
             "Chunking, indexing and ranking are adjusted and scored against an evaluation set built from those questions."),
            ("Hand over",
             "You receive the pipeline or the design, the evaluation set to re-run it, and the audit trail it produces."),
        ],
        "faq": [
            ("What is a RAG pipeline?",
             "Retrieval-augmented generation first retrieves the passages of your documents that "
             "are relevant to a question, then has a language model answer from them. Because "
             "the answer is built from retrieved text, it can cite its sources."),
            ("Why does it need an evaluation set?",
             "Without one, a change that improves one answer can quietly break another. An "
             "evaluation set of real questions turns “it seems better” into a measured "
             "result you can re-run after every change."),
            ("Can the pipeline run on private models?",
             "Yes. A RAG pipeline works with a commercial API or with open models on your own "
             "infrastructure. See private AI implementation for the second case."),
            ("How long does it take, and what does it cost?",
             "The sprint is fixed scope and typically two weeks. You receive a one-page written "
             "scope first, and nothing starts until you agree to it."),
        ],
        "related": ["private-ai", "ai-security-review"],
    },
    {
        "slug": "private-ai",
        "offer": "private-ai",
        "subject": "build",
        "nav_name": "Private AI implementation",
        "title": "Private AI Implementation on Open Models",
        "meta": ("Assistants and pipelines on open models, deployed on your own infrastructure "
                 "with no third-party AI service in the loop. Scoped per project."),
        "h1": "Private AI implementation",
        "lede": ("Private AI means the model runs where your data stays: on your hardware or "
                 "private cloud, with no third-party AI service in the loop. We implement "
                 "assistants and pipelines on open models, the same approach we run every week "
                 "to produce this newsletter."),
        "facts": "Scoped per project",
        "get": [
            "Open-model selection and sizing for your hardware or private cloud",
            "Deployment on your infrastructure, with no third-party AI service in the loop",
            "The same approach we run every week for this newsletter",
            "Hooks for guardrails and audit logging from day one",
        ],
        "fit_title": "When this fits",
        "fit": [
            "Your data cannot be sent to a third-party AI service.",
            "You want to know what hardware an open model needs before you buy it.",
            "You need logging and guardrail hooks built in, not added later.",
        ],
        "steps": [
            ("Size it",
             "We match open models to the task and to the hardware or private cloud you have."),
            ("Deploy it where your data is",
             "The assistant or pipeline is installed on your infrastructure and tested without sending your data out."),
            ("Hand over",
             "You keep the code in your repository, with the guardrail and audit-logging hooks in place."),
        ],
        "faq": [
            ("What is private AI?",
             "Models that run on infrastructure you control, so prompts and documents are not "
             "passed to a commercial AI provider. Open models make this possible because you "
             "can run them yourself."),
            ("Can you build and test without our data leaving the building?",
             "Yes. We run mainly on open models on our own hardware, and we can build and test "
             "on your infrastructure, so your documents are not handed to a commercial AI API "
             "to log or train on."),
            ("Do we still need guardrails if the model is private?",
             "Yes. Where the model runs does not change what an agent can reach or what an "
             "application can say. That is why the implementation includes hooks for guardrails "
             "and audit logging, and why the security review covers private and commercial AI alike."),
            ("What does it cost?",
             "It is scoped per project. You receive a one-page written scope with deliverables "
             "and timing, and nothing starts until you agree to it."),
        ],
        "related": ["rag-pipelines", "ai-guardrails"],
    },
    {
        "slug": "ai-guardrails",
        "offer": "secure",
        "subject": "secure",
        "nav_name": "AI guardrails",
        "title": "AI Guardrails for Agents, LLM Apps and RAG",
        "meta": ("We review the guardrails around your agents and LLM applications: tool "
                 "permissions, blocking rules, audit logs and content safeguards."),
        "h1": "AI guardrails for agents, LLM apps and RAG",
        "lede": ("Guardrails are the controls around a model: what an agent is allowed to do, "
                 "what gets logged, what gets blocked, and what the model may say. We review "
                 "whether yours exist, whether they hold, and what evidence they leave, for "
                 "private and commercial AI and for RAG architectures."),
        "facts": "Fixed scope · typically 2–3 weeks",
        "get": [
            "Tool and permission review: which actions each agent can reach",
            "Audit logging and blocking rules for unauthorized tool calls and agent actions",
            "Guardrails for private and commercial AI and for RAG architectures",
            "Content safeguards against toxic, biased or inaccurate output",
        ],
        "fit_title": "When this fits",
        "fit": [
            "Agents or LLM applications are about to reach real data and real tools.",
            "You have guardrails on paper but cannot show that they work.",
            "You need to know afterwards what an agent did, and why it was allowed to.",
        ],
        "steps": [
            ("Map what can happen",
             "We list the tools, data and actions each agent can reach, and what the model can be made to say."),
            ("Test the controls",
             "We check whether unauthorized tool calls and agent actions are logged and blocked, and how failures are detected."),
            ("Report",
             "You receive prioritised findings you can act on. Implementing the controls is scoped separately."),
        ],
        "faq": [
            ("What are AI guardrails?",
             "Controls that limit and record what an AI system can do: permissions on the tools "
             "an agent may call, rules that block unauthorized actions, logs that show what "
             "happened, and safeguards on the content a model produces."),
            ("Can guardrails stop all harmful or inaccurate output?",
             "No. We can reduce it and show you the evidence. No safeguard catches everything, "
             "so the review also sets how failures are detected and handled."),
            ("Do you implement the guardrails too?",
             "The review comes first and ends in prioritised findings. Implementing the controls "
             "is scoped separately once the review is done."),
            ("Does it apply to a private model as well as a commercial API?",
             "Yes. The review covers agents and LLM applications whether the model is private or "
             "a commercial API."),
        ],
        "related": ["ai-security-review", "private-ai"],
    },
    {
        "slug": "ai-security-review",
        "offer": "secure",
        "subject": "secure",
        "nav_name": "AI security review",
        "title": "AI Security Review for Agents and LLM Apps",
        "meta": ("A fixed-scope security review of what your agents and LLM applications can "
                 "reach and do, ending in prioritised findings you can act on."),
        "h1": "AI security review for agents and LLM applications",
        "lede": ("A fixed-scope review of what your agents and LLM applications can reach, what "
                 "they can do with it, and what you can prove afterwards. The aim is to reduce "
                 "risk and give you evidence, not to promise that nothing gets through."),
        "facts": "Fixed scope · typically 2–3 weeks",
        "get": [
            "Tool and permission review: which actions each agent can reach",
            "Audit logging and blocking rules for unauthorized tool calls and agent actions",
            "Guardrails for private and commercial AI and for RAG architectures",
            "Prioritised findings you can act on",
        ],
        "fit_title": "When this fits",
        "fit": [
            "You are putting agents or LLM applications in front of real data and real tools.",
            "Someone, a customer, auditor or board, will ask how you know it is safe.",
            "You want a written, prioritised list of what to fix first.",
        ],
        "steps": [
            ("Short call and written scope",
             "A 30-minute call or an email, then a one-page scope with deliverables and timing. Nothing starts until you agree to it."),
            ("Review",
             "Two to three weeks looking at tools, permissions, logging, blocking and guardrails around your system."),
            ("Findings",
             "A prioritised report you can act on. Fixing the findings is scoped separately."),
        ],
        "faq": [
            ("What does the review cover?",
             "What your agents and LLM applications can reach and do: which tools and actions "
             "each agent is allowed, whether unauthorized tool calls and agent actions are logged "
             "and blocked, and what guardrails sit around private and commercial AI and RAG "
             "architectures."),
            ("What do we receive at the end?",
             "Prioritised findings you can act on. Implementing the controls is scoped separately "
             "afterwards."),
            ("Do you follow this area closely?",
             "Every weekly issue of this newsletter covers AI and security news, including "
             "attacks on agents and AI infrastructure. That reading is part of how we know what "
             "to look for."),
            ("Does it guarantee we are secure?",
             "No, and we say so up front. The review reduces risk and gives you evidence; no "
             "review can promise that nothing gets through."),
        ],
        "related": ["ai-guardrails", "rag-pipelines"],
    },
]
