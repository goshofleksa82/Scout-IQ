# Privacy and beta terms requirements

This is an operator completion brief, not a finalized privacy notice or service agreement. No binding terms-acceptance or payment flow is enabled. Hosting, operator identity and external beta participation remain undecided.

## Implemented controls

Accounts store username/email/password hash and session metadata. Refresh tokens are hashed and rotated; cookies are HttpOnly, Secure on hosted environments and SameSite Lax. Watchlists and report histories are owner-private, including against other administrators. Feedback is visible to the author and administrators; staff triage notes stay administrative. Audit payloads omit account contact details, credentials and private observation/feedback text.

Product analytics is optional and off by default. Events contain account ID, one approved feature name and time, deduplicated per feature/account/minute. They exclude queries, player selections, observations, IP addresses and device identifiers. Opt-out deletes the account's feature events. A 90-day expiry command is included and must be scheduled at deployment; it is not currently a hosted schedule. Aggregate metrics are restricted to administrators and identify consent/sample limitations.

## Operator decisions and procedures

| Area | Required before external testing |
| --- | --- |
| Identity/contact | Identify the operator/controller, privacy contact, business address where required, and the support/complaint route. |
| Purposes/lawful basis | Document account/service operation, security audit, feedback and optional analytics separately; choose and record the applicable basis. |
| Recipients/locations | Confirm hosting/database/backup processors, access roles, locations, agreements and any international-transfer mechanism. |
| Retention | Set account, private report/history, feedback, audit, request-log and backup retention; enable event expiry and document exceptions. |
| Access/export/deletion | Provide authenticated request handling, an ownership-checked export and an approved deletion workflow, including backup expiry and minimal audit retention. These operational workflows need finalization; there is no self-service account-deletion API. |
| Transparency | Publish the completed notice before collection; explain optional analytics, session storage, rights, contact and complaints. |
| Data licensing | Preserve the demo's CC BY attribution and source/transformations; verify permissions for every additional import and redistribution. |
| Sensitive observations | Minimize unnecessary personal information and avoid sensitive player information without an appropriate purpose, access control and review. |
| Incidents | Assign responsibility, detection, response, communication and applicable notification assessment. Test recovery on the hosted environment. |
| Terms | Define eligibility, permitted use, account security, ownership/permissions, beta availability limits, termination, dispute handling and governing law; review liability and user-rights language appropriately. |

For an EU/EEA deployment, assess the GDPR's scope and applicable obligations, including principles, legal basis, notice content, individual rights, processors and security. The official [Regulation (EU) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj) is the primary reference; the intended jurisdiction and operator circumstances must be established. Do not treat these requirements or the in-app overview as a finding of legal compliance.
