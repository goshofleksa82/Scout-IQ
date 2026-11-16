# ScoutIQ focused beta plan

## First customer group

Independent football scouts and analysts at small clubs or agencies who already work with licensed datasets and need a clear shortlist-to-report workflow. The initial job is to turn a position/age brief into a small, evidence-backed shortlist and an explicit human observation report.

## MVP scope

Include authenticated accounts, player discovery, historical/season profiles, transparent rates and scores, compatible comparisons, private watchlists, revisioned reports, source/quality review, and structured feedback. The first beta does not include payments, automated recruitment decisions, live data feeds, video hosting, club-wide sharing, or claims of predictive player quality.

The landing page is `/welcome` and the guest home page. New account registration leads to `/onboarding`; existing accounts can reopen orientation from account settings. `/feedback` collects structured category, feature, usefulness rating, a task description and optional follow-up preference. `/admin/beta` supports review status and priority.

## Demonstration evidence

The bundled CC BY 4.0 historical subset and its guarded loader are in `backend/demo`. It contains 42 players, 12 national teams, 13 matches and 195 appearance records from France/Croatia at the 2018 World Cup. Ages are at 15 July 2018. Two unreconstructable late-substitution samples are omitted; tackles/progressive actions are unknown. Preserve attribution and the transformation manifest. Existing development records are not redistributed or automatically relicensed.

## Readiness before invitations

- Choose a free host, deploy to a new isolated staging database, verify TLS/readiness and restore a hosted backup. Hosting is explicitly deferred by the user.
- Run the prepared CI pipeline and both Docker images on a working Docker host. Docker is unavailable on this workstation; container execution remains unverified here.
- Finalize the operator identity, contact route, privacy/terms requirements, retention schedule, deletion/export procedure, and processor/access agreements.
- Enable the daily product-event expiry job, backup retention and failure alerts. Test their actual hosted behavior.
- Create a separate viewer account for each tester; preserve account ownership restrictions. Do not share a public administrator password.
- Confirm source attribution, unknown values and historical period are visible. Review the demo's statistical limitations before testing.

## Recruit a small first cohort

Target five professionals across independent scouts, small-club analysts and recruitment analysts. Seek people who can describe a real current workflow and can legally use their own evaluation material. Record their recruitment and follow-up preferences. No recruitment messages have been sent, no tester identities are assumed, and no real feedback has been fabricated.

Use `beta-testers-template.csv` as an empty tracker. Obtain permission and the actual recipients before sending invitations. Draft invitation:

> I’m preparing a small ScoutIQ beta for football scouts and analysts. It covers player search, transparent comparisons, private shortlists and structured reports. Would you be willing to try a 25-minute task session and describe what helps or gets in the way? The demonstration evidence is historical and attributed; you can also use material you have permission to process. Participation is optional, and feedback will guide the next changes.

## Moderated session, 25 minutes

1. Ask the tester to describe their current scouting workflow and the last decision for which they needed evidence.
2. Give a position/age brief. Ask them to find a candidate, explain the season/source/minutes shown, and identify one missing measurement.
3. Compare two compatible players. Ask what a percentile means, why an axis might be absent, and what the score does not establish.
4. Create a private watchlist and add a candidate. Write an observation report, edit it, and locate the earlier revision.
5. Ask for a usefulness rating and the most important blocked task. Submit category/feature/rating/task details through `/feedback`, or capture the same fields in the interview notes.

Record task completion, time, help required, interpretation errors, usefulness, and the next action. Do not convert a five-person study into a market-size or adoption claim. Only opted-in feature activity appears in product metrics; those counts are not total usage or a representative sample.

## Triage and success signals

Urgent: an access-control or data-loss issue; suspend affected testing. High: a core task is blocked. Medium: repeated friction with a workaround. Low: a minor refinement. Reproduce a problem, preserve non-sensitive evidence, record its impact and assign an owner before planning it.

Start with these learning questions: Can testers finish the core brief-to-report journey? Can they explain missing data, source compatibility and score limitations? Which step saves time in their actual workflow? Would they return with a legally usable dataset? Treat the answers as observations, not a commercial-readiness guarantee.

`beta-issues-template.csv` starts empty. Current engineering/operational prerequisites above are known work, not invented customer feedback. The beta-launch milestone is complete only after real users have evaluated the hosted application and their feedback has been reviewed.
