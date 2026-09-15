# Canonical data model

## Surface

Key fields:

- `surface_id`
- `family_id`
- `name`
- `vendor`
- `surface_type`
- `regions`
- `languages`
- `distribution_channels`
- `commercial_priority`
- `status`

## Evidence source

- `source_id`
- publisher/vendor
- URL/canonical URL
- source class/tier
- publication date
- capture date
- content hash
- language/region
- source methodology summary
- paywall/access status
- raw snapshot locator

## Study / observation

- study ID
- source ID
- surfaces covered
- time window
- geography
- sample size
- unit of analysis
- methodology
- vendor/tool used
- limitations

## Claim

A claim is the atomic unit shown in the observation plane.

- claim ID
- surface(s)
- topic (`audience`, `retrieval`, `index`, `search_trigger`, `fanout`, `citation`, `crawler`, `shopping`, `ads`, `referral`, `measurement`, etc.)
- normalized statement
- numeric values/units where applicable
- valid/effective period
- observed/published date
- geography/language
- evidence IDs
- relationship to prior claim (`supports`, `updates`, `contradicts`, `supersedes`, `contextualizes`)
- evidence confidence
- commercial significance
- status (`current`, `contested`, `historical`, `watch`)

## Change event

- event ID
- affected claims/surfaces
- event type
- first observed
- effective date when known
- before/after
- evidence
- significance/confidence
- POV sections affected

## POV revision

- revision ID/date
- changed section
- old/new text
- triggering claim/event IDs
- editor/agent
- reason

## Critical rule

Never overwrite a previous claim or methodology in place. Append history and mark supersession/contradiction explicitly.
