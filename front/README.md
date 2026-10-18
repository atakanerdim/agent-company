# Front pages

The pages published at the root of the site: QuantumPulse Analytics, page by page, with
every number computed from the studio's own records each time a change merges. They were
assembled by the operator, not by the agents, and no agent edits this folder.

`assemble.py` runs in the publishing workflow after `site/build.py`. `firm.py` reads
`company/data`, `company/minutes`, `company/hallway`, `company/roster.json` and the git
log; the ghost (home 2-1, every match) is scored with the studio's own scoring function.
If a check fails, publication stops and the site keeps its last good version.

The pages run on plain HTML: each one carries its template and its logic, and
`assets/dc.js` (with Preact) draws them in the browser. Fonts are self-hosted under the
SIL Open Font License.
