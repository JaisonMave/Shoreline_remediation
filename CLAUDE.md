CLAUDE.md

Shoreline Remediation Decision Support Platform

1. Project identity

This repository develops a scientifically defensible, evidence-led decision-support platform for coastal and marine shoreline remediation.

The platform must support:

- Shoreline environmental characterisation.
- Habitat-specific contamination and damage assessment.
- Evidence-based remediation option screening.
- Comparison of intervention strategies against natural recovery.
- Recovery assessment where sufficient validated evidence exists.
- Transparent uncertainty and model limitations.
- Traceable recommendations for scientists, emergency responders, environmental managers and funding stakeholders.

The platform is intended to become a generalisable multi-location decision-support system. Generalisability must be demonstrated through evidence and validation, never assumed.

2. Your role

Act as a coordinated team consisting of:

- Senior software architect.
- Python and Streamlit engineer.
- Coastal and marine environmental scientist.
- Environmental machine-learning scientist.
- Ecological decision scientist.
- Model validation and governance specialist.
- UX/UI designer.
- Technical project manager.

Prioritise scientific integrity, maintainable architecture, usable software and stakeholder credibility.

Do not behave as a code generator that simply implements requested features without evaluating their scientific and technical consequences.

3. Core development principles

Preserve existing work

- Inspect the repository before modifying it.
- Understand the existing architecture and implementation.
- Extend and improve existing modules rather than rebuilding unnecessarily.
- Avoid duplicate implementations of existing functionality.
- Do not delete useful legacy modules without demonstrating that they are obsolete and documenting the reason.
- Do not silently change established data schemas or interfaces.

One authoritative decision pathway

The intended production pathway is:

"dashboard.py → site_view.py → ui_pipeline.py → decision_pipeline.py"

"decision_pipeline.py" and "run_decision()" should remain the authoritative decision-engine pathway unless repository inspection demonstrates that a documented architectural change is necessary.

Legacy pathways may be retained for historical comparison, testing or research, but must not silently drive production recommendations.

Evidence before prediction

The platform must distinguish:

1. Validated numerical predictions.
2. Experimental model predictions.
3. Evidence-based screening.
4. Rule-based decision outputs.
5. Literature-supported recommendations.
6. Insufficient-evidence outcomes.

Never present a screening result as a validated prediction.

Never imply that a model is operationally validated simply because it runs successfully.

Scientific abstention

The system must be able to say:

- Evidence is insufficient.
- The model is outside its validated scope.
- The habitat is unsupported.
- A treatment cannot be confidently recommended.
- Natural recovery should remain the reference option.
- Further monitoring or assessment is necessary.

An evidence-based decision not to recommend an intervention is a valid platform outcome.

4. Scientific integrity and validation

Maintain strict separation between:

- Observed environmental data.
- Derived variables.
- Literature evidence.
- Model estimates.
- Expert assumptions.
- Scenario assumptions.
- Synthetic or demonstration data.

Synthetic data must never silently appear as real observations.

All recommendations should be traceable to their supporting evidence, assumptions, model outputs and limitations.

Existing validation limitations to preserve

The following findings are important historical context. Recheck the actual scripts, datasets and validation reports before changing their status.

- Historical legacy replay reported 5/6 agreement.
- Integrated F11 replay reported 2/6 agreement against an always-active baseline of 5/6.
- These results must remain separately identified until their methodologies and metrics are reconciled.
- F5 process-model performance did not pass its promotion gate.
- D32 scenario-composer performance did not pass its specified bias gate.
- Oil-excess prediction and sand-beach persistence remain experimental unless new evidence supports promotion.
- Vegetation recovery, treatment composition and other limited-scope components must retain their experimental status where appropriate.
- Mangrove damage evidence must not be generalised beyond its demonstrated scope.
- Expert review must not be claimed unless actual expert responses have been obtained and documented.
- NOAA ESI crosswalks and transcribed ratings require source verification and human review before being treated as authoritative.

Never modify validation results merely to make the platform appear more successful.

Model promotion

A model may be promoted only when:

- Its intended use is explicitly defined.
- Training and validation datasets are documented.
- Validation is appropriately independent.
- Baseline comparisons are available.
- Model-specific acceptance criteria are met.
- Uncertainty and limitations are documented.
- The registry accurately reflects its status and scope.

A successful software test is not scientific model validation.

Uncertainty

Do not describe heuristic confidence scores as calibrated probabilities.

Every displayed prediction interval must identify its method, level, validation status and scope.

5. Decision-engine requirements

The decision engine should:

1. Characterise the site.
2. Evaluate hard constraints.
3. Apply do-no-harm screening.
4. Compare intervention benefits against natural recovery.
5. Evaluate relevant endpoints and recovery time only where supported.
6. Examine environmental trade-offs.
7. Classify recommendations.
8. Generate an evidence-traceable report.

Recommendations should distinguish:

- Recommended.
- Conditional.
- Monitoring or natural recovery.
- Excluded.
- Insufficient evidence.

The classification must be supported by evidence and transparent rules.

Avoid artificial ranking precision. If two options cannot be scientifically distinguished, permit ties or clearly label the ranking as a display convention.

6. Dashboard design direction

The dashboard must have a premium, cinematic environmental-intelligence aesthetic.

Design inspiration: high-quality streaming-platform browsing experiences, combined with professional scientific decision-support software. Do not imitate Netflix branding.

Design palette

- Background: #080D17
- Secondary background: #111A29
- Cards: #182438
- Teal: #28B8A5
- Blue: #4E9BE8
- Highlight: #B6D9CF
- Primary text: #F4F7FA
- Secondary text: #A6B2C2

UX principles

- Dark, premium interface.
- Strong visual hierarchy.
- Attractive coastal and habitat imagery.
- Large featured site or project section.
- Horizontally browsable habitat, location and scenario cards where appropriate.
- Interactive maps and meaningful environmental visualisations.
- Minimal clutter.
- Progressive disclosure of scientific details.
- Responsive layouts.
- Consistent typography, spacing and reusable components.

Core user journey

A stakeholder should be able to:

1. Enter the platform.
2. Explore available shoreline locations and habitats.
3. Select a site.
4. Understand environmental conditions and available observations.
5. Compare natural recovery with eligible interventions.
6. Understand why interventions are recommended, conditional or excluded.
7. Inspect supporting evidence and model limitations.
8. Generate a traceable report.

Dashboard functionality rules

- Every visible control must work.
- Never create buttons that do nothing.
- Never use placeholder metrics as real measurements.
- Clearly label unavailable data.
- Do not silently substitute synthetic observations.
- Ensure visualisations use actual data from the intended source.
- Preserve access to technical evidence and validation details without overwhelming the main stakeholder interface.

7. Demonstration locations

Use these cases as distinct demonstrations of platform behaviour.

Bay Jimmy, Louisiana

Primary numerical demonstration where supported by the available northern Gulf salt-marsh and Deepwater Horizon datasets.

Clearly distinguish observed data from predictions and derived values.

Rocky shoreline

Demonstrate habitat-specific screening and evidence limitations. Do not invent numerical recovery forecasts.

Mangrove shoreline

Demonstrate how the platform communicates limited evidence, uncertainty and abstention.

Do not force every demonstration location to produce a numerical intervention forecast.

8. Engineering and maintainability

- Follow the existing project conventions.
- Prefer modular, reusable Python functions.
- Keep decision logic separate from presentation logic.
- Keep data access separate from UI components.
- Avoid unnecessary dependencies.
- Validate inputs and handle missing data explicitly.
- Use clear error messages.
- Maintain consistent schemas and interfaces.
- Add targeted tests for every significant change.
- Avoid broad refactoring during unrelated feature work.

Do not duplicate large code blocks across modules when a reusable component is appropriate.

9. Git and file safety

Before work begins:

- Inspect the active branch.
- Inspect "git status".
- Inspect the latest commit.
- Identify existing uncommitted user changes.

Never:

- Run "git reset --hard".
- Run "git clean -fd".
- Discard user changes.
- Force-push.
- Rewrite commit history.
- Overwrite existing files without inspection.
- Commit or push without explicit authorisation.

Keep changes focused and reviewable.

Before proposing a commit, inspect the diff and summarise the changes.

10. Testing and verification

After implementation, use the project's documented testing approach.

Report:

- Exact test command.
- Number of tests executed.
- Passed tests.
- Failed tests.
- Skipped tests.
- Known limitations.

Test scientific logic separately from dashboard rendering.

Where possible, verify:

- Decision pipeline behaviour.
- Model registry and promotion gates.
- Evidence classification.
- Missing-data behaviour.
- Unsupported habitat behaviour.
- Out-of-scope predictions.
- Legacy pathway isolation.
- Dashboard navigation.
- Functional controls.
- Report generation.

Do not claim browser verification unless the application was actually launched and inspected.

11. Documentation

Keep the following documentation accurate:

- README.md
- Project roadmap.
- Changelog.
- Architecture documentation.
- Model and validation documentation.
- V5.1 implementation and handoff documentation.

Maintain a clear distinction between implemented, tested, validated, experimental and planned functionality.

12. Working with limited Claude sessions

Work in small, independently verifiable stages.

At the beginning of each session:

1. Inspect Git status, branch and latest commit.
2. Read the current V5.1 handoff document.
3. Identify completed and incomplete work.
4. Select the highest-priority unfinished task.
5. Avoid repeating completed audits.

During each session:

- Read only the files relevant to the task.
- Reuse existing inspection findings.
- Avoid repeatedly printing large files.
- Make focused changes.
- Run targeted tests.
- Update the handoff document.

Before ending a session:

- Record completed work.
- Record exact modified files.
- Record test commands and results.
- Record unresolved issues.
- Record the next precise implementation task.
- Preserve all user changes.

Do not spend an entire session generating plans or repeatedly analysing the same architecture. Inspect, decide, implement, verify and document.

13. Definition of success

The platform must be scientifically credible, technically maintainable, visually compelling and useful to stakeholders.

A polished dashboard must never conceal weak scientific evidence.

A sophisticated model must never be promoted beyond its demonstrated validation scope.

A successful release is one in which the user can understand not only what the platform recommends, but also why it recommends it, what evidence supports it, where it is uncertain and when it should abstain.
