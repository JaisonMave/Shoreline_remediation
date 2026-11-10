# NOAA Assumption Audit

Source reviewed: `manual_shore_assess_aug2013.pdf` supplied in this project.

## What NOAA supports

- Treatment selection is habitat-, oil-state-, access-, and recovery-control dependent.
- Manual removal is broadly applicable, but foot traffic, nesting periods, sensitive wetlands, and waste handling constrain it.
- Mechanical removal is for accessible substrates that can support equipment and requires storage, transport, and disposal controls.
- Sorbents require recovery of all sorbent material; performance depends on oil type, stickiness, and wave/tidal energy.
- Vacuum recovery is for pooled/free oil and can be slow; it requires access and controls for sediment and wildlife disturbance.
- Sediment reworking/tilling is mainly for sand-to-gravel substrates with subsurface oil where removal is not feasible.
- Low-pressure flushing is for fluid oil and requires containment and recovery of released oil.
- High-pressure flushing is primarily for bedrock, gravel, and structures, with runoff controls; it is not a generic sand-beach method.
- Hot-water methods require oil-temperature/pour-point compatibility and should avoid sensitive habitats or recover hot effluent.
- Vegetation cutting is justified only when wildlife or secondary-release risk exceeds the value of the vegetation and less-destructive options are inadequate.
- Biostimulation requires nutrient and oxygen monitoring; bioaugmentation has limited demonstrated effectiveness for marine/coastal spills in the manual.
- Endpoint decisions are inspection-based: meets cleanup endpoints, no further treatment recommended, or continued monitoring required.

## Model changes made

- High-pressure washing eligibility is restricted to hard/gravel substrates rather than generic non-wetland shorelines.
- NOAA treatment applicability and constraints are exposed in the dashboard cross-check tab.
- The recovery plot is explicitly labelled conceptual and planning-oriented; it is shaped like the supplied impact/recovery illustration but is not a physical prediction.

## Remaining limitations

- The model does not yet contain ESI shoreline codes, primary/secondary shoreline zones, tide height/direction, oil character codes, oil distribution class, wildlife timing, containment capability, product authorization, nutrient status, oxygen status, or monitoring observations.
- Ecological suitability values are expert-rule placeholders, not NOAA-derived numeric scores.
- Time-to-endpoint values are planning estimates, not NOAA cleanup endpoints or regulatory closure dates.
- The synthetic ML labels must be replaced or calibrated with SCAT/STR observations and repeat inspection outcomes before operational use.

## Recommended next modelling stage

Use a process-informed state-space or compartment model for oil mass and recovery, with SCAT observations updating the state over time. Use machine learning for residual tasks such as treatment effectiveness, endpoint probability, and duration calibration after enough labelled repeat-survey data exist.
