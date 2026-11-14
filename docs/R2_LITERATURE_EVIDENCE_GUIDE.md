# R2: literature evidence for treatment coefficients (guide and LeapSpace prompts)

Status: Proposed (14 Nov 2026). Replaces human expert scoring as the route to effectiveness numbers (Jaison,
14 Nov: "instead of expert score we will use literature to get some coefficients that can be used for
forecasting and ranking"). Extracted values go into `data/knowledge/literature_effects_template.csv`
(one row per effect, per time point). Nothing is used by the tool until the pooling plan (section 5) is
committed and run.

## 1. What coefficients the tool needs

| Use in the tool | Coefficient | Typical source quantity |
| --- | --- | --- |
| Forecast of residual oil (process model, PAH decline) | Ratio of loss-rate constants, treated vs untreated: k_T / k_0 (or half-life ratio) | TPH, PAH, alkylated PAH, hopane-normalised PAH over time |
| Forecast of biological recovery (composer, vegetation) | Ratio of recovery time constants tau_T / tau_0, or log response ratio lnRR = ln(treated / control) at fixed times | Vegetation cover, stem density, biomass, infauna or epifauna abundance |
| Forecast of physical damage | Difference in erosion or retreat rate (m/yr), sediment loss (cm) | Edge retreat, elevation change |
| Ranking: benefit | Removal efficiency: fraction of oil removed vs untreated after the same time | % oil cover, g/m2 oil, TPH |
| Ranking: do-no-harm | lnRR for an ecological endpoint, treated vs untreated oiled control | Mortality, cover, abundance, recovery time |
| Trade-offs (shown, not scored) | Production rate (m2 per person-day), waste per m2 treated, cost per m2 | Operational reports, case histories |
| Conditions | Modifiers: oil type and weathering, oiling degree, penetration depth, wave energy, substrate (ESI), season, delay after oiling | Reported per study; drive the screening rules |

Each value must come with a spread (SD, SE or interval) and n, the comparison group (untreated oiled
control is required for effect coefficients; before-after without control is graded lower), and the time
since treatment.

## 2. Literature types, best first

1. **Controlled field experiments on oiled shorelines** (randomised or blocked plots, treated vs untreated
   oiled controls, ideally BACI). Highest value: give effect sizes directly.
2. **Systematic reviews and meta-analyses** of shoreline cleanup or of a single technique. Use for the
   study list and pooled values; still extract primary values where possible.
3. **Long-term spill monitoring with untreated reference segments** (Exxon Valdez, Deepwater Horizon,
   Amoco Cadiz, Metula, Arrow, Gulf War 1991, Sea Empress, Prestige, Hebei Spirit, Wakashio).
   Observational: treatment chosen by responders, so confounded with oiling degree; record that.
4. **Mesocosm and greenhouse experiments.** Mechanism and direction; transfer to field is uncertain.
5. **Response guidance and technical reports** (NOAA OR&R, ITOPF Technical Information Papers, Cedre,
   IPIECA-IOGP good practice guides, API, Environment and Climate Change Canada shoreline manuals, EPA NCP
   Product Schedule for washing agents and solidifiers). Conditions of use, production rates, waste; rarely
   effect sizes.
6. **Net environmental benefit analysis (NEBA / SIMA)** case studies. How decisions were made; useful for
   the decision logic, not coefficients.

Lowest value for coefficients: laboratory flask studies, model-only papers, and reviews without numbers.

## 3. Master prompt for Elsevier LeapSpace

Replace the bracketed fields with the per-technology block from section 4. Run once per technology and,
where results are thin, once per habitat.

```text
I am building an evidence table for an oil-spill shoreline treatment decision tool. Find peer-reviewed
studies and authoritative technical reports that quantify the EFFECT of [TECHNOLOGY] (also called
[SYNONYMS]) on oiled shorelines, compared with an UNTREATED OILED CONTROL or reference, in [HABITATS].

Prioritise, in this order: (1) field experiments with treated and untreated oiled plots (randomised,
blocked or BACI); (2) systematic reviews or meta-analyses; (3) long-term monitoring after real spills that
compares treated and untreated segments; (4) mesocosm studies. Exclude laboratory flask-only studies and
papers without quantitative results, unless they are the only evidence.

For each study, return a table with: full citation and DOI; study design; spill or experiment name,
location, year; habitat or ESI shoreline type; oil type and weathering state; oiling degree and
penetration depth; wave energy; season and delay between oiling and treatment; treatment details
(intensity, dose, pressure, temperature, number of applications); outcome measured ([OUTCOMES]); values
for treated and control groups at each time point with SD, SE or confidence interval and sample size;
time since treatment; reported effect (percent oil removed, degradation rate constant or half-life,
recovery time, response ratio); any reported harm (vegetation, fauna, sediment loss, erosion,
remobilisation of oil); operational data (area per day, waste generated, cost); and the table or figure
number where each value appears.

Also list the conditions under which the authors found the treatment helpful, ineffective or harmful.
State clearly when a value is read from a figure rather than a table, and do not estimate or invent
numbers that the paper does not report. Cover 1975 to present.
```

Follow-up prompts to use in the same session:
- "Which of these studies have an untreated oiled control? List only those, with sample sizes."
- "For [study], give the exact table and figure numbers holding the treated and control values over time."
- "Are there meta-analyses or systematic reviews of [TECHNOLOGY] on shorelines? Give their included-study lists."
- "Which studies report harm or no benefit from [TECHNOLOGY]? Summarise conditions."

## 4. Per-technology blocks (insert into the master prompt)

Search leads are starting points to verify, not accepted evidence.

| Technology (tool code) | Synonyms | Habitats | Outcomes | Search leads (verify) |
| --- | --- | --- | --- | --- |
| Natural attenuation (`natural_attenuation`) | natural recovery, no treatment, monitored natural recovery | all; untreated controls in any cleanup study | oil persistence, TPH and PAH decline, hopane-normalised PAH, vegetation and fauna recovery time | Exxon Valdez untreated reference sites; Metula (Strait of Magellan); Arrow; Gulf War 1991 saltmarsh; DWH untreated reference plots |
| Manual removal (`manual_removal`) | manual cleanup, hand removal, raking, scraping, wiping | salt marsh, sand and gravel beaches, rocky shore | % oil removed, vegetation cover, stem density, trampling damage, erosion | Zengel 2015 and 2022 (DWH, Bay Jimmy); Michel 2013; NOAA marsh guidance |
| Passive sorbents (`passive_sorbents`) | sorbent pads, booms, snares, pom-poms | marsh, rocky shore, sheltered beaches | oil recovered per sorbent mass, residual sheen, secondary waste | NOAA and ITOPF sorbent guidance; few controlled comparisons expected |
| Vacuum removal (`vacuum_removal`) | vacuum trucks, skimming pooled oil, pumping | marsh, pooled oil areas | oil recovered, vegetation damage | NOAA marsh guidance; DWH and Mississippi River spill reports |
| Low-pressure flushing (`low_pressure_flushing`) | flooding, deluge, ambient-temperature flushing | marsh, gravel, cobble | % oil removed, sediment loss, vegetation | Exxon Valdez treatment evaluations; NOAA marsh guidance |
| Low-pressure heated flushing (`low_pressure_heated_flushing`) | warm water flushing | gravel, cobble, riprap | as above plus thermal mortality | Exxon Valdez warm-water treatment studies |
| High-pressure washing (`high_pressure_washing`) | pressure washing, cold-water washing | bedrock, boulder, seawalls, riprap | % oil removed, epibiota mortality and recovery time | Exxon Valdez rocky intertidal monitoring; Sea Empress; Prestige |
| High-pressure heated washing (`high_pressure_heated_washing`) | hot-water washing, steam cleaning | rocky shores, cobble | intertidal community recovery time vs untreated | Exxon Valdez hot-water-washed vs unwashed sites (NOAA OR&R; Mearns; Houghton; Lees) |
| Surface washing agents (`surface_washing_agents`) | shoreline cleaners, surface washing agents, Corexit 9580, PES-51, CytoSol | marsh, rocky shore, gravel | % oil removed, toxicity, vegetation response, timing after oiling | EPA NCP Product Schedule; Fiocco; Fingas; NOAA marsh guidance |
| Bioremediation (`bioremediation`) | nutrient amendment, biostimulation, bioaugmentation, fertiliser, oleophilic nutrients | sand and gravel beaches, marsh | degradation rate constants (TPH, alkanes, PAH, hopane-normalised), nutrient levels | Exxon Valdez nutrient trials; Delaware Bay field trial (Venosa); Nova Scotia and Quebec marsh trials (Lee; Garcia-Blanco); Pezeshki |
| Mechanical removal (`mechanical_removal`) | heavy equipment, excavation, beach cleaning machines, sediment removal | sand beaches, marsh | oil removed, sediment volume removed, elevation loss, vegetation, erosion | Zengel 2015 and 2022 mechanical plots; Amoco Cadiz marsh excavation; Prestige beach cleaning |
| Sediment relocation (`sediment_relocation`) | surf washing, berm relocation | sand and gravel beaches | residual oil over time vs untreated | Sea Empress; Owens and Sergy; Cedre guidance |
| Sediment mixing (`sediment_mixing`) | tilling, ploughing, harrowing | sand and gravel beaches | residual oil, degradation rate | Svalbard shoreline field trials (Owens; Sergy); Exxon Valdez tilling |
| Vegetation cutting (`vegetation_cutting`) | cropping, mowing oiled vegetation | salt marsh, freshwater marsh | regrowth, stem density, mortality, season effect | Pezeshki; NOAA marsh guidance |
| Solidifiers (`solidifiers`) | gelling agents, oil solidifying polymers | open water edges, marsh, pooled oil | recovery efficiency, residues, toxicity | Fingas; EPA NCP Product Schedule |
| In-situ burning (not in the library; in composer ranges) | marsh burning, controlled burning | marsh with standing water | vegetation recovery, soil temperature, survival vs untreated | Mendelssohn; Lin; Zengel review of marsh burning |
| Planting (restoration add-on) | revegetation, Spartina transplanting | salt marsh after cleanup | cover, erosion | Zengel 2015 and 2022 planting plots |

## 5. How the coefficients enter the tool (plan to be committed before pooling)

1. Extract into the template; each row checked against the source by a second person (Jaison), with the
   table or figure reference. Values read from figures are flagged `digitised`.
2. Grade each row: design (controlled field > observational > mesocosm > lab), control (untreated oiled
   control yes/no), risk of bias (treatment assigned by responders, confounded with oiling degree).
3. Pool by technology x habitat x outcome with a random-effects meta-analysis on the log response ratio
   (and on log rate-constant ratios), reporting the pooled effect, 95% confidence interval, 95% prediction
   interval and between-study heterogeneity. Pool only rows with a control; fewer than 3 studies: no pooled
   value, the rows are shown as single-study evidence.
4. Use in forecasting: the prediction interval (not the confidence interval) becomes the prior range for
   the tau or k multiplier in the composer and the process model, replacing the AI-proposed ranges (R6).
5. Use in ranking (F9 step 4): an option is shown as "evidence of benefit" only if its prediction interval
   excludes no effect for the relevant habitat and outcome; "evidence of harm" removes or flags it (F9
   step 3); everything else is "no clear difference from natural recovery".
6. Validation: where a pooled coefficient overlaps a dataset we hold (Zengel, DIVER, NAIP), compare
   without refitting and report agreement.
