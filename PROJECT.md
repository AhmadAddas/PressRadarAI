# PROJECT.md

PressRadar AI product specification.

This document is authoritative for:

- Product requirements
- Business rules
- User workflows
- Domain behavior
- MVP scope
- Acceptance criteria
- Product-specific constraints

Technology choices belong in `TECHSTACK.md`.

Engineering practices belong in `AGENTS.md` and `docs/ENGINEERING.md`.

---

# Index

Codex should use this index to locate only the sections relevant to the current task.

1. [Product Overview](#1-product-overview)
2. [Business Problem](#2-business-problem)
3. [Target Users](#3-target-users)
4. [Product Principles](#4-product-principles)
5. [Core User Journey](#5-core-user-journey)
6. [MVP Scope](#6-mvp-scope)
7. [Authentication & Workspaces](#7-authentication--workspaces)
8. [Client Management](#8-client-management)
9. [Monitoring Rules](#9-monitoring-rules)
10. [Media Sources](#10-media-sources)
11. [Media Items](#11-media-items)
12. [Media Ingestion](#12-media-ingestion)
13. [Opportunity Detection](#13-opportunity-detection)
14. [Relevance Scoring](#14-relevance-scoring)
15. [AI Pitch Generation](#15-ai-pitch-generation)
16. [Human Review & Approval](#16-human-review--approval)
17. [Pitch Sending](#17-pitch-sending)
18. [Opportunity States](#18-opportunity-states)
19. [Dashboard](#19-dashboard)
20. [Urgency & Ranking](#20-urgency--ranking)
21. [Notifications](#21-notifications)
22. [HubSpot CRM Integration](#22-hubspot-crm-integration)
23. [Audit Trail](#23-audit-trail)
24. [Analytics](#24-analytics)
25. [Demo Mode](#25-demo-mode)
26. [Demo Scenario](#26-demo-scenario)
27. [AI Accuracy Rules](#27-ai-accuracy-rules)
28. [Business Invariants](#28-business-invariants)
29. [MVP Non-Goals](#29-mvp-non-goals)
30. [MVP Milestones](#30-mvp-milestones)
31. [Definition of Product Success](#31-definition-of-product-success)

---

# 1. Product Overview

## Product Name

**PressRadar AI**

## Product Category

AI-powered PR opportunity monitoring and rapid-response pitching platform.

## Core Value Proposition

PressRadar helps PR consultants identify high-intent media opportunities and respond faster than competing agencies.

The product compresses this workflow:

```text
Monitor media
→ discover opportunity
→ determine client relevance
→ research client
→ draft commentary
→ review
→ send
```

into:

```text
Opportunity detected
→ AI relevance analysis
→ AI commentary generated
→ human review
→ approve
→ send
```

The key product advantage is **speed from media opportunity to qualified response**.

---

# 2. Business Problem

PR opportunities are highly time-sensitive.

A journalist may post:

> Looking for a Dubai-based fintech founder to comment on new financial regulations.

The journalist may receive enough responses within minutes.

Traditional monitoring solutions frequently create:

- Email digests
- Large volumes of alerts
- Low-signal keyword matches
- Delayed notification workflows

The problem is not merely detecting media mentions.

The business problem is:

> Detecting an actionable opportunity, identifying the right client, and producing a usable response before competitors do.

PressRadar should significantly reduce that response time.

---

# 3. Target Users

Primary users:

- PR consultants
- PR agencies
- Communications professionals
- Account managers representing executives or companies
- Media relations teams

The MVP is primarily optimized for a PR consultant managing multiple clients.

---

# 4. Product Principles

The product should prioritize:

1. Speed
2. Relevance
3. Urgency
4. Human control
5. Accuracy
6. Low noise
7. Simple workflows

The product should not become a generic media-monitoring dashboard.

Every major feature should support the core question:

> What media opportunity needs my attention right now?

---

# 5. Core User Journey

```text
Sign in
    ↓
Create/select client
    ↓
Configure client expertise and monitoring rules
    ↓
Media item is detected
    ↓
PressRadar matches item against clients
    ↓
Relevant opportunity is created
    ↓
AI produces relevance score
    ↓
AI explains the match
    ↓
AI drafts expert commentary
    ↓
Opportunity appears on dashboard
    ↓
PR consultant reviews/edit pitch
    ↓
Consultant approves
    ↓
Pitch is sent
    ↓
Activity is recorded
```

---

# 6. MVP Scope

The MVP includes:

- Authentication
- Workspace isolation
- Client management
- Monitoring keywords/rules
- Simulated media sources
- Media ingestion
- Client/media matching
- Opportunity creation
- AI relevance scoring
- AI relevance explanation
- AI pitch generation
- Human editing
- Explicit approval
- Simulated sending
- Opportunity dashboard
- Urgency ranking
- Optional Twilio notifications
- Optional HubSpot synchronization
- Basic audit history
- Demo/seed data

---

# 7. Authentication & Workspaces

Users must be able to:

- Sign up
- Sign in
- Sign out
- Access authenticated product areas

Each user's data belongs to a workspace.

Users must not be able to access data belonging to another workspace.

Workspace ownership applies to:

- Clients
- Monitoring rules
- Media opportunities
- Pitches
- Integration configuration
- Audit history

Enterprise-grade organization management is not required for the MVP.

---

# 8. Client Management

A user can:

- Create a client
- View clients
- View an individual client
- Edit a client
- Archive/delete a client where appropriate

A client may contain:

```text
name
company
website
industry
description
location
expertise
spokesperson_name
spokesperson_title
keywords
excluded_keywords
preferred_topics
tone
```

The exact persistence shape may differ.

These fields represent product concepts, not mandatory database column names.

---

# 9. Monitoring Rules

Each client can define monitoring rules.

Initial MVP monitoring may be keyword-oriented.

Examples:

```text
Dubai AI startup
UAE AI regulation
fintech regulatory approval
digital banking UAE
startup funding Dubai
```

Monitoring rules should eventually support richer matching, but the MVP should remain simple.

Do not require users to learn a complex query language.

---

# 10. Media Sources

The MVP must support simulated media sources.

Potential source categories:

- News
- RSS-style feeds
- Journalist requests
- Social-style requests

Future providers may include:

- RSS feeds
- News APIs
- Journalist request platforms
- Social networks
- Custom webhooks

Real external media providers are not required for the first MVP.

---

# 11. Media Items

A media item represents an external story, request, or media opportunity candidate.

It may contain:

```text
source
source_type
author
journalist
headline
body
url
published_at
deadline
topics
external_id
```

Media content must be treated as external/untrusted information.

---

# 12. Media Ingestion

The system must be able to ingest media items.

For the MVP:

```text
Simulated media source
        ↓
Media ingestion
        ↓
Normalization
        ↓
Deduplication
        ↓
Client matching
```

Repeated ingestion of the same media item should not create uncontrolled duplicates.

---

# 13. Opportunity Detection

When a media item arrives:

1. Identify potentially relevant clients.
2. Determine whether the item represents an actionable opportunity.
3. Create an opportunity for meaningful matches.
4. Analyze relevance.
5. Generate a pitch when appropriate.

An opportunity conceptually contains:

```text
client
media_item
relevance_score
relevance_reason
matched_topics
status
detected_at
deadline
pitch
```

---

# 14. Relevance Scoring

AI relevance analysis produces a score from:

```text
0–100
```

Example structured result:

```json
{
  "score": 94,
  "reason": "The journalist is specifically requesting a Dubai-based AI founder, matching the client's location and expertise.",
  "matched_topics": [
    "AI governance",
    "Dubai",
    "startup leadership"
  ]
}
```

The score alone is insufficient.

The system should also explain **why** the opportunity matches.

---

# 15. AI Pitch Generation

For relevant opportunities, PressRadar generates a concise expert commentary draft.

Target length:

**Approximately three strong sentences.**

The pitch should:

- Address the actual story/request
- Reflect the client's expertise
- Be useful to a journalist
- Be concise
- Sound human
- Avoid generic promotional language
- Avoid fabricated credentials
- Avoid unsupported facts
- Avoid invented statistics

The pitch is a draft, not an autonomous final communication.

---

# 16. Human Review & Approval

Human approval is mandatory.

AI-generated pitches must never be automatically sent without explicit user approval.

The user must be able to:

```text
Review
Edit
Approve
Send
```

The approval boundary is a core business rule.

---

# 17. Pitch Sending

The MVP may use a simulated sender.

Flow:

```text
Draft generated
    ↓
User edits
    ↓
User approves
    ↓
Send action
    ↓
Simulated delivery succeeds/fails
    ↓
Status recorded
```

Future real sending mechanisms may replace the simulated sender.

The business workflow should remain unchanged.

---

# 18. Opportunity States

Use an explicit state model.

Suggested conceptual states:

```text
new
analyzing
ready
approved
sent
dismissed
failed
```

State transitions must be intentional.

Examples:

```text
new → analyzing
analyzing → ready
ready → approved
approved → sent
ready → dismissed
analyzing → failed
```

Invalid transitions should be prevented.

Example:

```text
dismissed → sent
```

should not occur accidentally.

---

# 19. Dashboard

The dashboard should immediately answer:

> What needs my attention now?

Each opportunity should show useful information such as:

- Client
- Relevance score
- Source
- Headline/request
- Journalist/author
- Detection time
- Deadline
- Why it matches
- Pitch preview
- Current state

Primary actions:

```text
Review
Edit
Approve & Send
Dismiss
```

---

# 20. Urgency & Ranking

Opportunity ordering should prioritize:

1. Deadline/urgency
2. Relevance
3. Recency

A high-relevance opportunity with a deadline in 15 minutes should be easier to notice than a less urgent general article.

The dashboard must visually communicate urgency.

---

# 21. Notifications

High-priority opportunities may trigger notifications.

Initial notification use case:

```text
High-priority opportunity detected.

Client: VertexAI Labs
Relevance: 96%
Deadline: 42 minutes
```

Default demo mode must not require a real notification provider.

Real notification delivery is optional.

---

# 22. HubSpot CRM Integration

HubSpot is an optional external integration.

Potential functionality:

- Associate opportunities with CRM records
- Synchronize selected client/contact data
- Record pitch activity
- Record sent opportunities

PressRadar remains the source of truth for its own domain data.

HubSpot must not become PressRadar's core database.

Failure to synchronize with HubSpot should normally not invalidate a completed PressRadar business action.

---

# 23. Audit Trail

Important actions should have basic history.

Examples:

```text
Opportunity detected
AI analysis started
AI analysis completed
Pitch generated
Pitch edited
Pitch approved
Pitch sent
Opportunity dismissed
Processing failed
Integration sync failed
```

The MVP does not require a full compliance-grade event-sourcing system.

---

# 24. Analytics

Product analytics may include:

- Opportunities detected
- Average relevance score
- Time from detection to review
- Time from detection to send
- Approval rate
- Pitch send rate
- Source effectiveness
- Client opportunity volume
- Dismissal rate

Analytics must not block the core workflow.

---

# 25. Demo Mode

The product must be easy to demonstrate without paid external services.

Demo mode should include:

- Demo user
- Several clients
- Monitoring rules
- Simulated media
- Opportunities with different relevance levels
- At least one urgent journalist request
- AI-generated or deterministic demo pitches
- Simulated sending

A reviewer should understand the value of PressRadar without configuring production integrations.

---

# 26. Demo Scenario

## Client

```text
Name: Nadia Rahman
Company: VertexAI Labs
Role: Founder & CEO
Location: Dubai
Industry: Artificial Intelligence

Expertise:
- AI governance
- AI startup growth
- Enterprise AI adoption
- UAE technology ecosystem
```

## Media Request

```text
Looking for Dubai-based AI founders to comment on how
new UAE AI governance requirements could affect
early-stage startups.

Deadline: 60 minutes
```

## Expected Behavior

PressRadar should:

1. Detect the match.
2. Give it a high relevance score.
3. Explain why it matches.
4. Generate useful expert commentary.
5. Surface it prominently on the dashboard.
6. Allow editing.
7. Require approval.
8. Perform simulated sending.
9. Record the action.

---

# 27. AI Accuracy Rules

AI output must not invent client facts.

Never fabricate:

- Revenue
- Funding
- Customers
- Partnerships
- Credentials
- Experience
- Titles
- Locations
- Statistics
- Quotes
- Regulatory approvals

AI context should distinguish clearly between:

```text
KNOWN CLIENT FACTS
MEDIA OPPORTUNITY
TASK
OUTPUT REQUIREMENTS
```

When information is insufficient, the generated commentary should remain conservative.

---

# 28. Business Invariants

Important business rules include:

- Workspace data must remain isolated.
- A pitch belongs to the correct opportunity.
- An opportunity belongs to the correct client.
- A generated pitch cannot bypass human approval.
- A sent pitch should not accidentally send multiple times.
- Duplicate media ingestion should not create uncontrolled duplicate opportunities.
- Opportunity state transitions must remain valid.
- External integration failures should not silently corrupt core PressRadar state.
- AI failures should not crash unrelated product functionality.

These invariants should be protected through application logic and persistence guarantees where appropriate.

---

# 29. MVP Non-Goals

Do not build these unless explicitly added to scope:

- Full X/Twitter integration
- LinkedIn scraping
- Large-scale web crawling
- Kafka
- Kubernetes
- Microservice architecture
- Enterprise RBAC
- Billing/subscription system
- Mobile applications
- Browser extension
- Custom machine-learning ranking model
- Vector database without demonstrated need
- Fully autonomous pitch sending
- Complex CRM replacement
- Massive analytics suite
- Multi-region infrastructure

---

# 30. MVP Milestones

Implementation should proceed incrementally.

## Milestone 1 — Project Foundation

- Repository structure
- Local development environment
- Backend foundation
- Frontend foundation
- Configuration
- Testing
- Basic developer documentation

## Milestone 2 — Authentication

- Sign up/sign in
- Workspace isolation
- Protected application routes

## Milestone 3 — Client Management

- Create client
- List clients
- View client
- Edit client
- Monitoring rules

## Milestone 4 — Simulated Media

- Media model
- Simulated provider
- Ingestion
- Deduplication

## Milestone 5 — Opportunities

- Matching
- Opportunity model
- Opportunity state management
- Dashboard feed

## Milestone 6 — AI Relevance

- Relevance analysis
- Score
- Explanation
- Failure handling

## Milestone 7 — AI Pitching

- Pitch generation
- Client context
- Editing
- Accuracy safeguards

## Milestone 8 — Approval & Sending

- Human approval
- Simulated sender
- Idempotent sending
- Audit history

## Milestone 9 — Dashboard Polish

- Urgency ranking
- States
- Error/loading/empty states
- Demo workflow

## Milestone 10 — Optional Integrations

- Notifications
- Twilio
- HubSpot

## Milestone 11 — Analytics

- Product events
- Analytics pipeline
- Reporting foundation

## Milestone 12 — Cloud Deployment

- Production deployment
- Infrastructure
- Operational documentation

Do not implement later milestones merely because they are described here.

Complete one logical milestone or vertical slice at a time.

---

# 31. Definition of Product Success

The MVP is successful when a user can:

```text
1. Sign in.
2. Create or open a PR client.
3. Configure expertise and monitoring keywords.
4. Ingest a simulated journalist request.
5. Have PressRadar detect the match.
6. Receive a relevance score.
7. Understand why the opportunity matches.
8. Receive an AI-generated commentary draft.
9. See the opportunity prominently on the dashboard.
10. Review and edit the draft.
11. Approve the draft.
12. Send it through the simulated sender.
13. See the opportunity marked as sent.
14. See the important action recorded.
```

The primary success metric is not the number of features.

It is whether PressRadar demonstrates a compelling reduction in:

```text
media opportunity → qualified PR response
```