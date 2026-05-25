#!/usr/bin/env python3
"""Generate `mock_knowledge_base.csv` — a 1000+ row fictional product
knowledge base for the lead-qualification RAG demo.

The output CSV is meant to be uploaded through the static web tool; n8n
will chunk and embed the rows into Supabase, after which the Telegram
bot can answer prospect questions about the fictional product
"Bellrock CRM".

Usage:
    python3 scripts/generate_mock_knowledge_base.py
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

PRODUCT = "Bellrock CRM"
OUT = Path(__file__).resolve().parent.parent / "mock_knowledge_base.csv"
TARGET_ROWS = 1000

random.seed(42)


# ---------------------------------------------------------------- catalogs

FEATURES: list[tuple[str, str]] = [
    ("lead scoring", "AI-driven lead scoring with custom rules and ML-based fit and intent models"),
    ("pipeline management", "drag-and-drop kanban pipelines with custom stages per team"),
    ("email tracking", "real-time email open and click tracking, plus reply detection"),
    ("call logging", "automatic call logging with VoIP integration and transcript capture"),
    ("meeting scheduler", "shared availability scheduler with calendar sync and round-robin assignment"),
    ("workflow automation", "no-code automation builder with 200+ triggers and actions"),
    ("contact enrichment", "live data enrichment from 12 providers including Clearbit and Apollo"),
    ("forecasting", "weighted forecasting with manual overrides and historical trend analysis"),
    ("custom dashboards", "drag-and-drop dashboards with 40+ widget types"),
    ("territory management", "rule-based territory assignment with overlap detection"),
    ("quote builder", "branded quote and proposal templates with e-signature"),
    ("playbooks", "step-by-step rep playbooks tied to deal stages"),
    ("activity timeline", "unified timeline of every contact touchpoint across email, calls, and chat"),
    ("two-way email sync", "bidirectional sync with Gmail and Outlook 365"),
    ("cadence sequences", "multi-step sales cadences with branching logic"),
    ("lead routing", "round-robin or rule-based lead routing with SLA escalation"),
    ("duplicate detection", "fuzzy match deduplication across contacts, leads, and accounts"),
    ("data import wizard", "CSV/XLSX import with column mapping and rollback"),
    ("audit logs", "tamper-evident audit logs with seven-year retention"),
    ("custom objects", "design custom objects with relationships, layouts and permissions"),
]

INTEGRATIONS: list[str] = [
    "Salesforce", "HubSpot", "Slack", "Microsoft Teams", "Gmail", "Outlook 365",
    "Zoom", "Google Meet", "Zapier", "Make", "Workato", "Webhook",
    "Mailchimp", "Marketo", "Pardot", "Intercom", "Drift", "Calendly",
    "DocuSign", "PandaDoc", "Stripe", "Chargebee", "QuickBooks", "Xero",
    "NetSuite", "SAP", "Workday", "BambooHR", "Greenhouse", "Lever",
    "Jira", "Asana", "Trello", "Monday.com", "ClickUp", "Notion",
    "Twilio", "RingCentral", "Aircall", "Dialpad",
]

PLANS: list[tuple[str, str, str]] = [
    ("Starter",    "$29/user/month",  "up to 3 users, 10,000 contacts, basic pipeline + email tracking"),
    ("Growth",     "$79/user/month",  "up to 25 users, 100,000 contacts, automation, forecasting, integrations"),
    ("Pro",        "$149/user/month", "unlimited users, 1M contacts, custom objects, sandbox, full API access"),
    ("Enterprise", "custom pricing",  "unlimited everything, SSO, SCIM, audit logs, dedicated CSM, signed SLA"),
]

INDUSTRIES: list[str] = [
    "SaaS", "fintech", "manufacturing", "logistics", "healthcare",
    "professional services", "education", "real estate", "construction",
    "media", "retail", "non-profits", "automotive", "telecom", "energy",
]

ROLES: list[str] = [
    "sales reps", "sales managers", "RevOps leaders", "marketing managers",
    "customer success teams", "founders", "VPs of sales",
]

ENDPOINTS: list[tuple[str, str]] = [
    ("/contacts",     "manage contact records"),
    ("/leads",        "create, update and convert leads"),
    ("/deals",        "manage deals and pipeline stages"),
    ("/companies",    "manage account records"),
    ("/activities",   "log calls, emails and meetings"),
    ("/notes",        "attach notes to any record"),
    ("/tasks",        "create and update tasks"),
    ("/users",        "manage user provisioning"),
    ("/teams",        "manage team membership and territories"),
    ("/automations",  "trigger or pause workflow automations"),
    ("/webhooks",     "register webhooks for record events"),
    ("/imports",      "kick off bulk imports"),
    ("/exports",      "schedule exports of CRM data"),
    ("/files",        "upload and attach files"),
    ("/reports",      "fetch report results as JSON"),
    ("/dashboards",   "list and export dashboards"),
    ("/products",     "manage product catalog"),
    ("/quotes",       "generate quotes"),
    ("/orders",       "track orders and revenue"),
    ("/auth/tokens",  "manage OAuth and API tokens"),
]

ISSUES: list[str] = [
    "imported CSV not appearing", "duplicate contacts after sync",
    "email tracking pixel blocked", "calendar sync stuck",
    "API rate limit errors", "automation not firing",
    "MFA reset", "SAML SSO failing", "missing fields after migration",
    "two-way sync conflict", "inactive seat billing", "webhook 401 errors",
    "password reset email not received", "export job stalled",
    "report shows wrong totals", "Slack notifications missing",
    "mobile app crash on launch", "deal stage probability override",
    "contact owner reassignment failing", "audit log export incomplete",
]


# ---------------------------------------------------------------- builders

rows: list[dict[str, str]] = []


def add(category: str, question: str, answer: str) -> None:
    rows.append(
        {"category": category, "question": question.strip(), "answer": answer.strip()}
    )


# 1. Features  (20 features × 11 templates = 220)
feature_templates = [
    ("How does {p}'s {f} work?",
     "{p} provides {desc}. The capability is included on the Growth plan and above and configurable per workspace."),
    ("Can I customize {f} in {p}?",
     "Yes — admins configure {f} under Settings → Workflow → {ft}. Common customizations include thresholds, custom-field mappings and per-team overrides."),
    ("Is {f} available on the free trial?",
     "{ft} is available during the 14-day Growth-tier trial. Starter plans do not include it."),
    ("Does {f} support custom fields?",
     "Yes. {p}'s {f} reads any custom field on the Contact, Lead or Deal object, including formula and rollup fields."),
    ("Where do I enable {f}?",
     "Open Settings → {ft} → Enable. The first run takes about 60 seconds to backfill historical records."),
    ("Does {f} work for international users?",
     "Yes — {f} respects user locale, timezone and currency settings. Multi-currency support requires the Pro plan or higher."),
    ("How accurate is {p}'s {f}?",
     "Internal benchmarks show {f} delivers strong precision on production datasets. Customers can tune sensitivity per workspace."),
    ("Can {f} be disabled per user?",
     "Yes. Admins can disable {f} for specific roles or individual users under Settings → Users → Permissions."),
    ("What data does {f} need?",
     "{ft} relies on the standard Contact and Deal fields plus any custom fields you map. The setup wizard surfaces missing data on first run."),
    ("Is {f} included in the API?",
     "Yes — every {f} action is exposed in the REST and GraphQL API and emits webhooks for downstream automation."),
    ("Does {f} have an audit trail?",
     "Yes. Every change made by {f} is captured in the audit log with user, timestamp and before/after values, retained for seven years."),
]

for name, desc in FEATURES:
    title = name.title()
    for q_t, a_t in feature_templates:
        q = q_t.format(p=PRODUCT, f=name, ft=title)
        a = a_t.format(p=PRODUCT, f=name, ft=title, desc=desc)
        add("features", q, a)


# 2. Integrations  (40 × 5 = 200)
integration_templates = [
    ("Does {p} integrate with {i}?",
     "Yes. The {i} integration is native and installed from Settings → Marketplace. It supports two-way sync for the standard objects."),
    ("How do I connect {i} to {p}?",
     "Go to Settings → Integrations → {i} → Connect. Sign in with an admin account on {i} and authorize the OAuth scopes. Initial sync takes 5–15 minutes."),
    ("What syncs between {p} and {i}?",
     "Contacts, companies, deals, activities and custom fields sync bidirectionally with {i}. Conflict resolution defaults to last-write-wins, configurable per object."),
    ("Is the {i} integration on every plan?",
     "{i} is available on the Growth plan and above. Some advanced field mappings and webhook hooks require Pro."),
    ("Where do I troubleshoot {i} sync errors?",
     "Settings → Integrations → {i} → Health surfaces the last 100 errors with a Retry button. Persistent 401 errors usually mean the auth token was revoked on the {i} side."),
]

for integration in INTEGRATIONS:
    for q_t, a_t in integration_templates:
        q = q_t.format(p=PRODUCT, i=integration)
        a = a_t.format(p=PRODUCT, i=integration)
        add("integrations", q, a)


# 3. Pricing  (4 plans × 6 templates = 24, plus 14 extras = 38)
pricing_templates = [
    ("How much does the {plan} plan cost?",
     "The {plan} plan is {price} when billed monthly, with 20% off when billed annually. It includes {desc}."),
    ("What is included in the {plan} plan?",
     "{plan} includes {desc}. See the comparison table at /pricing for the full feature matrix and limits."),
    ("Can I downgrade from {plan}?",
     "Yes — downgrades take effect at the end of the current billing period. We don't pro-rate downgrades, so you keep all included features until renewal."),
    ("Is there a free trial of the {plan} plan?",
     "Every plan ships with a 14-day free trial. No credit card is required for Starter or Growth; Enterprise trials are arranged through sales."),
    ("Does the {plan} plan include support?",
     "{plan} includes email support with a 24-hour first-response SLA. Pro and Enterprise add chat, phone and a dedicated CSM."),
    ("How are users counted on the {plan} plan?",
     "Any user who logs in during a billing period counts as a paid seat on {plan}. Read-only viewers are free up to five times the paid seat count."),
]

for plan, price, desc in PLANS:
    for q_t, a_t in pricing_templates:
        q = q_t.format(plan=plan, price=price)
        a = a_t.format(plan=plan, price=price, desc=desc)
        add("pricing", q, a)

pricing_extras = [
    ("Do you offer annual discounts?",
     "Yes — annual billing is 20% cheaper than monthly across all plans. Multi-year commitments unlock additional discounts on Enterprise."),
    ("Can I add seats mid-cycle?",
     "Yes. New seats are pro-rated to the next renewal. Removing seats takes effect at the end of the current billing period."),
    ("What happens at the end of the trial?",
     "The workspace remains accessible in read-only mode for 30 days. Choose a plan or contact sales to keep editing."),
    ("Do you offer non-profit pricing?",
     "Yes — verified 501(c)(3) and equivalent non-profits get 30% off Growth and Pro."),
    ("Is there a startup program?",
     "Yes. Companies under three years old with under 30 employees qualify for our startup discount: 50% off Growth for the first year."),
    ("Can I pay by invoice instead of credit card?",
     "Annual contracts on Pro and Enterprise can pay by ACH, wire transfer or check. Monthly billing is credit card only."),
    ("What is your refund policy?",
     "We offer a 30-day money-back guarantee on the first invoice for new customers. Renewals are non-refundable."),
    ("Is there a setup fee?",
     "No setup fees on Starter, Growth or Pro. Enterprise contracts include a one-time onboarding fee that varies by scope and migration complexity."),
    ("Do you charge for sandbox environments?",
     "Each Pro workspace includes one sandbox; Enterprise includes three. Additional sandboxes are $99/month each."),
    ("How do I get a quote for Enterprise?",
     "Contact sales@bellrock.example or book a call at calendly.com/bellrock-sales. Quotes are typically returned within two business days."),
    ("Can I switch plans whenever I want?",
     "Yes — upgrade at any time and we'll pro-rate the difference. Downgrades take effect at the next renewal."),
    ("Do you offer multi-workspace pricing?",
     "Customers running multiple workspaces under one parent org qualify for consolidated billing and volume discounts on Pro and Enterprise."),
    ("Is currency conversion supported in billing?",
     "We bill in USD, EUR, GBP, AUD, CAD, JPY and SGD. The billing currency is set at workspace creation and locked for the term."),
    ("Are there usage-based add-ons?",
     "Yes — extra contact storage, extra API quota and premium support are available as monthly add-ons on every plan."),
]
for q, a in pricing_extras:
    add("pricing", q, a)


# 4. Use cases  (15 industries × 7 roles × 3 templates = 315)
use_case_templates = [
    ("How do {role} in {ind} use {p}?",
     "{role_t} at {ind} companies typically use {p} to manage a high-velocity pipeline, track every prospect touchpoint and automate hand-offs between SDR, AE and CSM. {ind}-specific pipeline templates ship in the marketplace."),
    ("Is {p} a good fit for {ind} {role}?",
     "{p} is widely used by {role} in {ind}. Common reasons cited are the {ind} field templates, the no-code automation builder and the granular permissions model that supports regulated workflows."),
    ("Can you share a customer story for {ind} {role}?",
     "Several {ind} customers run their full revenue cycle on {p}. A typical {role} success story is a 30%+ uplift in pipeline coverage and a halving of admin time within the first quarter, as documented at bellrock.example/customers/{ind}."),
]

for industry in INDUSTRIES:
    for role in ROLES:
        for q_t, a_t in use_case_templates:
            q = q_t.format(p=PRODUCT, role=role, ind=industry)
            a = a_t.format(p=PRODUCT, role=role, role_t=role.capitalize(), ind=industry)
            add("use_cases", q, a)


# 5. API & developers  (20 endpoints × 5 = 100)
api_templates = [
    ("What is the {ep} endpoint used for?",
     "Use {ep} to {desc}. It supports GET (list/read), POST (create), PATCH (partial update) and DELETE."),
    ("What's the rate limit on {ep}?",
     "API endpoints share a per-token rate limit of 100 req/min on Growth, 500 on Pro and 2000 on Enterprise. {ep} respects this shared limit."),
    ("Does {ep} support pagination?",
     "Yes — pass `?limit=100&cursor=...` for cursor pagination on {ep}. Responses include `next_cursor` in the envelope when more results are available."),
    ("How do I authenticate to {ep}?",
     "Send the `Authorization: Bearer <token>` header with a personal API token from Settings → API or an OAuth2 access token. {ep} accepts both."),
    ("Are there webhooks for {ep} events?",
     "Yes — every create, update and delete on {ep} can fan out to a webhook endpoint. Configure subscribers under Settings → API → Webhooks."),
]

for endpoint, desc in ENDPOINTS:
    for q_t, a_t in api_templates:
        q = q_t.format(ep=endpoint)
        a = a_t.format(ep=endpoint, desc=desc)
        add("api", q, a)


# 6. Security & compliance  (~20)
security = [
    ("Is {p} SOC 2 compliant?",
     "Yes — {p} is SOC 2 Type II certified. The latest report is available from your account team under NDA."),
    ("Does {p} comply with GDPR?",
     "Yes — {p} is GDPR compliant. We act as a data processor, offer a DPA, support EU-region data residency and provide DSR tooling."),
    ("Where is my data stored?",
     "Customer data is stored in AWS us-east-1 by default. EU customers can opt into eu-west-1 residency on the Pro plan; APAC residency in ap-southeast-1 is on Enterprise."),
    ("Is data encrypted at rest?",
     "Yes — AES-256 at rest in RDS and S3. Per-tenant KMS keys are available on Enterprise."),
    ("Is data encrypted in transit?",
     "Yes — TLS 1.2+ for all connections, both web and API. Older protocols are explicitly disabled at the load balancer."),
    ("Do you support SSO?",
     "Yes — SAML 2.0 and OIDC SSO are available on the Pro plan and above. Common IdPs (Okta, Azure AD, Google Workspace) ship with pre-built configurations."),
    ("Is SCIM supported?",
     "SCIM 2.0 user provisioning and de-provisioning is available on the Enterprise plan."),
    ("Can I configure session timeouts?",
     "Yes — admins set both idle and absolute session timeouts per workspace under Settings → Security → Sessions."),
    ("How long are backups retained?",
     "Daily backups are retained 30 days, weekly backups 90 days and monthly backups one year on Enterprise."),
    ("Do you support IP allowlisting?",
     "Yes — IP allowlists at the workspace and API-token level are available on Pro and Enterprise."),
    ("Are penetration tests run regularly?",
     "Yes — third-party penetration tests run twice yearly, plus an internal red-team exercise annually. Executive summaries are shareable under NDA."),
    ("Is HIPAA supported?",
     "HIPAA is supported on Enterprise with a signed BAA. Contact sales to enable PHI handling on a workspace."),
    ("Do you support customer-managed encryption keys?",
     "Yes — bring-your-own-key (BYOK) via AWS KMS is available on Enterprise. Key rotation is on a customer-controlled schedule."),
    ("How do I report a security issue?",
     "Email security@bellrock.example with details. We acknowledge within 24 hours and follow a coordinated disclosure policy with a 90-day window."),
    ("Is the audit log exportable?",
     "Yes — audit logs export as CSV or JSONL via the UI and API. Real-time SIEM streaming to Splunk and Datadog is available on Enterprise."),
    ("Are you ISO 27001 certified?",
     "Yes — ISO 27001 certified since 2023. The current certificate is available from your account team."),
    ("Do you offer a status page?",
     "Yes — status.bellrock.example tracks API, web, automation, integrations and mobile uptime. Subscribe by email, RSS or Slack."),
    ("How is multi-tenancy isolated?",
     "Each tenant has logical isolation in shared infrastructure with row-level security. Enterprise customers can opt for dedicated database instances."),
    ("What is the historical uptime?",
     "Trailing-12-month uptime is 99.97% across all production regions. Monthly uptime numbers are published on status.bellrock.example."),
    ("Do you support FedRAMP?",
     "FedRAMP Moderate authorization is in progress with a target completion later this year. Customers needing it today can run on our GovCloud beta."),
]
for q, a in security:
    add("security", q.format(p=PRODUCT), a.format(p=PRODUCT))


# 7. Onboarding & setup  (~20)
onboarding = [
    ("How long does onboarding take?",
     "Most teams are productive within 1–2 weeks. Enterprise customers get a dedicated onboarding manager and a structured 4-week program."),
    ("Do you migrate data from another CRM?",
     "Yes — free migration from Salesforce, HubSpot, Pipedrive, Zoho and Copper is included for Pro and Enterprise customers."),
    ("Is training included?",
     "Live training sessions and self-paced courses on Bellrock University are free for all plans, including the trial."),
    ("Can I import contacts from a CSV?",
     "Yes — Settings → Imports → Upload CSV/XLSX. The wizard maps columns, runs deduplication, supports rollback and handles up to 250,000 rows per file."),
    ("How do I invite teammates?",
     "Settings → Users → Invite. Bulk invite supports CSV upload of email addresses with role and team assignment in one step."),
    ("Can I create custom fields?",
     "Yes — Settings → Object Manager → [Object] → Fields. Custom fields support text, number, date, picklist, multi-select, formula, rollup and lookup types."),
    ("Where do I set up email sync?",
     "Settings → Personal → Email → Connect. We support Gmail, Outlook 365 and IMAP/SMTP for legacy mail servers."),
    ("How do I set up the mobile app?",
     "Download Bellrock CRM from the App Store or Google Play, then sign in with your workspace URL and credentials. Biometric login is enabled by default."),
    ("Do you offer professional services?",
     "Yes — implementation, integration and custom development packages are available through our Professional Services team and certified partners."),
    ("Where can I find example workflows?",
     "The Bellrock marketplace ships 200+ pre-built workflow templates. Browse Settings → Marketplace → Templates and one-click install."),
    ("How do I set up custom roles?",
     "Settings → Permissions → Roles → New Role. Each role exposes 50+ granular permissions across objects, fields and actions."),
    ("Is there a sandbox environment?",
     "Pro plans include one sandbox; Enterprise includes three. Sandboxes mirror the production schema and can be refreshed weekly."),
    ("Can I customize the UI?",
     "Yes — workspace branding, custom layouts per role and field-level customization are available from Pro upward."),
    ("How do I import deals from Excel?",
     "Use the Imports wizard with a deals XLSX. Required columns: Name, Stage, Amount, Close Date. Owner email is optional but recommended."),
    ("Where do I configure currency?",
     "Settings → Workspace → Currency. Multi-currency with daily exchange rates is available on Pro and Enterprise."),
    ("Can I bulk-update records after import?",
     "Yes — Settings → Imports → Bulk Update accepts CSV with an `id` column to update existing records in place."),
    ("How do I set up data validation rules?",
     "Settings → Object Manager → [Object] → Validation Rules. Rules use a formula syntax similar to spreadsheet formulas."),
    ("Where do I configure email templates?",
     "Settings → Templates → Email. Templates support merge fields, conditional blocks and rich-text formatting."),
    ("How do I configure deal stages?",
     "Settings → Pipelines → [Pipeline] → Stages. Each stage has a probability, a default duration and optional required fields."),
    ("Can I have multiple pipelines?",
     "Yes — Pro and Enterprise support unlimited pipelines per workspace, each with its own stages, fields and automation rules."),
]
for q, a in onboarding:
    add("onboarding", q, a)


# 8. Troubleshooting  (20 issues × 3 = 60)
trouble_templates = [
    "I'm seeing '{issue}' — what should I do?",
    "How do I fix '{issue}'?",
    "Why am I getting '{issue}'?",
]
trouble_answer = (
    "If you're hitting '{issue}', first check Settings → System → Health for an active incident. "
    "Common fixes: re-authorize the integration, clear browser cache and cookies, retry the operation. "
    "If the issue persists, open a ticket with your workspace ID, the time of the failure and a screenshot — "
    "support typically responds within four business hours on Pro and one business hour on Enterprise."
)

for issue in ISSUES:
    for q_t in trouble_templates:
        q = q_t.format(issue=issue)
        a = trouble_answer.format(issue=issue)
        add("troubleshooting", q, a)


# 9. Mobile  (~12)
mobile = [
    ("Does the mobile app work offline?",
     "Yes — the iOS and Android apps cache contacts, deals and your today view. Edits sync when connectivity returns."),
    ("Is biometric login supported?",
     "Yes — Face ID, Touch ID and Android biometric prompts are supported on the mobile apps."),
    ("Can I log calls from the mobile app?",
     "Yes — call logging detects incoming and outgoing calls (with permission) and prompts to log them on the related contact."),
    ("Does the mobile app support push notifications?",
     "Yes — get notified on @-mentions, new lead assignments, deal stage changes and meeting reminders."),
    ("Can I scan business cards?",
     "Yes — the mobile app's card scanner uses on-device OCR to create new contacts in seconds."),
    ("Is there a tablet-optimized layout?",
     "Yes — both iPad and Android tablets render the multi-column dashboard layout."),
    ("How do I switch workspaces in the mobile app?",
     "Tap your avatar → Switch Workspace. Up to 10 workspaces can stay signed in simultaneously."),
    ("Why are my offline edits missing after sync?",
     "Conflicts default to last-write-wins. Check Settings → Sync log for any rejected edits and re-apply them manually if needed."),
    ("Does the mobile app support voice notes?",
     "Yes — record voice notes on any contact or deal. Transcription is automatic on the Pro plan."),
    ("Can I disable the mobile app for some users?",
     "Yes — admins can restrict mobile access per role under Settings → Permissions → Mobile."),
    ("Does the mobile app support dark mode?",
     "Yes — dark mode follows the OS setting on iOS and Android, or can be forced under Settings → Appearance in the app."),
    ("Can I use the mobile app in airplane mode?",
     "Yes — read-only access to cached records works in airplane mode. New edits queue locally and flush on reconnect."),
]
for q, a in mobile:
    add("mobile", q, a)


# 10. Reporting & analytics  (~12)
reporting = [
    ("How do I create a custom report?",
     "Reports → New → Custom. Choose a base object, drag fields onto rows and columns, set filters and group-bys, then save and share."),
    ("Can I schedule a report by email?",
     "Yes — every saved report has a Schedule option (daily, weekly, monthly) that emails CSV or PDF to selected recipients."),
    ("Are there pre-built sales dashboards?",
     "Yes — pipeline health, forecast accuracy, conversion funnel, activity volume, win/loss reasons and rep leaderboards ship out of the box."),
    ("Can I drill down from a chart?",
     "Yes — clicking a bar, slice or line opens the underlying record list, fully filtered to the selected segment."),
    ("Do reports update in real time?",
     "Most reports refresh on a 5-minute cadence. Pinned dashboards refresh on view; large historical reports refresh hourly."),
    ("Can I export reports as PDF?",
     "Yes — every report has an Export → PDF action. Branded PDF templates are configurable on Pro and Enterprise."),
    ("Is there a report API?",
     "Yes — `GET /reports/{id}/results` returns the report JSON. Long-running reports return an async job ID with a webhook on completion."),
    ("How long is report data retained?",
     "Live record data is retained for the life of the workspace. Aggregated report snapshots roll off after seven years on Enterprise and three years on Pro."),
    ("Can I add filters that prompt the viewer?",
     "Yes — interactive filters let viewers re-slice a report without editing it."),
    ("Are there cohort and funnel reports?",
     "Yes — cohort and funnel report types are available on the Pro and Enterprise plans."),
    ("Can I embed dashboards in another tool?",
     "Yes — signed embed URLs let you display dashboards in Notion, Confluence, internal portals or any iframe-friendly host."),
    ("Do you support row-level security on reports?",
     "Yes — reports respect the viewer's record permissions, so two users opening the same report may see different rows."),
]
for q, a in reporting:
    add("reporting", q, a)


# 11. Misc / general  (~25)
misc = [
    ("Where do I find my workspace URL?",
     "Your workspace URL is `https://<subdomain>.bellrock.example`. Find it under Settings → Workspace → General."),
    ("How do I reset my password?",
     "On the sign-in page, click Forgot Password. The reset link is valid for 60 minutes and single-use."),
    ("Can I have multiple admins?",
     "Yes — assign the Admin role to as many users as you need. There is no upper limit on admin seats."),
    ("Is multi-language UI supported?",
     "The UI is available in English, Spanish, French, German, Portuguese, Japanese, Korean and Simplified Chinese."),
    ("Where do I download invoices?",
     "Settings → Billing → Invoices. Invoices are also emailed to the billing contact within 24 hours of each renewal."),
    ("Who is my account manager?",
     "Pro and Enterprise customers have a named CSM listed under Settings → Help → Your Team."),
    ("How do I request a feature?",
     "Use the in-app feedback widget or post on community.bellrock.example. Product reviews requests weekly."),
    ("Is there a community forum?",
     "Yes — community.bellrock.example is open to all customers and free-tier users. Staff respond on weekdays."),
    ("Can I see the product roadmap?",
     "Yes — the public roadmap lives at roadmap.bellrock.example. Customers can vote and comment on upcoming features."),
    ("How do I delete my workspace?",
     "Owners can request deletion under Settings → Workspace → Delete. All data is purged after 30 days unless legal hold applies."),
    ("How do I report a bug?",
     "Use Help → Report a Bug from any screen. Include reproduction steps, screenshots and the time of the issue."),
    ("Do you have a partner program?",
     "Yes — partners.bellrock.example. We offer referral, affiliate and reseller tiers with revenue share."),
    ("How do I become a partner?",
     "Apply at partners.bellrock.example. Approved partners receive portal access, product training and a partner manager."),
    ("What languages does the API support?",
     "Official SDKs are published for Python, JavaScript/Node, Ruby, Java, Go and PHP. The OpenAPI spec is at /docs/api/openapi.yaml."),
    ("Are there per-user API rate limits?",
     "API rate limits apply per token. Workspace-wide limits stack on top of per-token limits."),
    ("How do I rotate an API token?",
     "Settings → API → Tokens → Rotate. The old token continues to work for 24 hours to allow zero-downtime cutover."),
    ("Are webhooks signed?",
     "Yes — every webhook includes an `X-Bellrock-Signature` HMAC-SHA256 header you can verify against your webhook secret."),
    ("How do I retry a failed webhook?",
     "Failed webhooks retry automatically with exponential backoff for 24 hours. Manual retry is available from the webhook log."),
    ("Can I use {p} on Linux?",
     "{p} is a web app — it runs in any modern browser on Linux, macOS, Windows or ChromeOS. The desktop apps for macOS and Windows are optional."),
    ("Is there a desktop app?",
     "Yes — native macOS and Windows desktop apps are available, with system tray notifications and global keyboard shortcuts."),
    ("How is uptime measured?",
     "Uptime is measured against the public API and web app from synthetic probes in five global regions, published on status.bellrock.example."),
    ("Do you offer a service level agreement?",
     "Pro plans include a 99.9% SLA; Enterprise contracts include a 99.95% SLA with service credits for missed targets."),
    ("Where do I find release notes?",
     "Release notes are published weekly at changelog.bellrock.example and surfaced in-app under Help → What's New."),
    ("How do I subscribe to the changelog?",
     "Email subscription is available at changelog.bellrock.example/subscribe. RSS and JSON feeds are also published."),
    ("Can I get a personalized demo?",
     "Yes — book a 30-minute demo at calendly.com/bellrock-demo. A solutions engineer will tailor the demo to your industry and team size."),
]
for q, a in misc:
    add("misc", q.format(p=PRODUCT), a.format(p=PRODUCT))


# ---------------------------------------------------------------- write

random.shuffle(rows)

if len(rows) < TARGET_ROWS:
    raise SystemExit(
        f"Generator only produced {len(rows)} rows; expected at least {TARGET_ROWS}."
    )

with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "category", "question", "answer"])
    writer.writeheader()
    for i, row in enumerate(rows, start=1):
        writer.writerow({"id": i, **row})

print(f"wrote {OUT.name} with {len(rows)} rows")
