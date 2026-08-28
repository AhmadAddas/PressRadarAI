# Third-party notices

PressRadarAI source code is licensed under the Apache License 2.0. The license does not replace
the licenses or service terms that apply to third-party components used with the project.

## Application dependencies

| Component | License |
|---|---|
| Argon2-cffi | MIT |
| email-validator | Unlicense |
| FastAPI | MIT |
| Google Cloud BigQuery Python client | Apache-2.0 |
| Google Cloud Firestore Python client | Apache-2.0 |
| HTTPX | BSD-3-Clause |
| MessagePack for Python | Apache-2.0 |
| Pydantic Settings | MIT |
| Uvicorn | BSD-3-Clause |
| Next.js | MIT |
| QRCode | MIT |
| React and React DOM | MIT |
| Sonner | MIT |
| Nodemailer | MIT-0 |

Each dependency remains subject to the license distributed with that dependency. Container base
images and their operating-system packages contain additional components under their respective
licenses.

## Local AI

| Component | License or terms |
|---|---|
| Ollama | MIT |
| Qwen 2.5 0.5B Instruct | Apache-2.0 |
| TranslateGemma 4B | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) and [Gemma Prohibited Use Policy](https://ai.google.dev/gemma/prohibited_use_policy) |

AI model weights are downloaded separately by Ollama and are not part of the PressRadarAI source
license. Users are responsible for reviewing and complying with the terms supplied with each model,
including any restrictions on use, redistribution, derivatives, or hosted access.

## Development and infrastructure

Development, testing, security, and infrastructure tools retain their own licenses. Important
examples include Docker Engine and Compose (Apache-2.0), Terraform (Business Source License 1.1),
the HashiCorp Google provider (MPL-2.0), Trivy (Apache-2.0), Playwright (Apache-2.0), axe-core
(MPL-2.0), pytest (MIT), Ruff (MIT), and TypeScript (Apache-2.0).

## Hosted services and external content

Google Cloud, Twilio, HubSpot, NewsAPI, SMTP providers, and other hosted integrations are governed
by their providers' applicable service terms. RSS and API content remains subject to the source
publisher's copyright, license, and usage terms.
