# DHI-Informed LHS SCAT Process Model

## Purpose

This module provides a transparent screening simulation for longitudinal SCAT observations. It is not the full MIKE Oil Spill Model, a calibrated fate-and-transport model, or a regulatory cleanup endpoint model.

## DHI model basis

The supplied `DHI_OilSpill_Model.pdf` describes oil as multiple state variables. The implementation adapts that structure from a water-column particle to a shoreline segment with six states:

- Surface volatile oil mass
- Surface heavy oil mass
- Subsurface volatile oil mass
- Subsurface heavy oil mass
- Wax mass
- Asphaltene mass

DHI identifies volatile and heavy fractions as active weathering components and wax/asphaltenes as conservative residues. Representative fraction, evaporation, dissolution, and biodegradation parameters are taken from the DHI parameter tables for light, medium, heavy, and solid oil classes.

## Equations

The DHI-inspired shoreline adaptation uses:

$$
\frac{dM_{sv}}{dt} = -(k_{evap}+k_{diss}+k_{bio,v})M_{sv} - R_{ts,v} + k_{transfer}M_{bv}
$$

$$
\frac{dM_{sh}}{dt} = -(0.25k_{diss}+k_{bio,h})M_{sh} - R_{ts,h} + k_{transfer}M_{bh}
$$

$$
\frac{dM_{bv}}{dt} = -(0.10k_{diss}+0.35k_{bio,v})M_{bv} - R_{tb,v} - k_{transfer}M_{bv}
$$

$$
\frac{dM_{bh}}{dt} = -0.35k_{bio,h}M_{bh} - R_{tb,h} - k_{transfer}M_{bh}
$$

$$
\frac{dM_{wax}}{dt}=0, \qquad \frac{dM_{asphaltene}}{dt}=0
$$

Where:

- $k_{evap}$ uses the DHI/Fingas logarithmic evaporation parameterization with oil-specific $A$, $B$, temperature, and age.
- $k_{diss}$ is an effective dissolution rate adjusted by wave class.
- $k_{bio,v}$ and $k_{bio,h}$ are first-order biodegradation rates.
- $R_{ts}$ and $R_{tb}$ are treatment removal terms for surface and subsurface oil.
- $k_{transfer}$ is a simplified subsurface-to-surface transfer term.

DHI's documented process basis includes evaporation, dissolution, emulsification, sedimentation, biodegradation, photooxidation, and vertical dispersion. The current shoreline adaptation does not yet implement hydrodynamic advection, Lagrangian particle tracks, emulsification water fraction, droplet diameter, slick area, vertical dispersion, sedimentation, photooxidation, or shoreline re-oiling.

## Generated SCAT fields

The LHS dataset contains:

- Survey date
- Segment ID
- Latitude and longitude
- Shoreline type
- Surface oil distribution
- Oil thickness and character
- Oil category
- Subsurface oil interval
- Treatment applied
- Treatment start and end dates
- Weather, tide, wave, and temperature classes
- Initial oil mass
- Surface, subsurface, volatile, heavy, wax, and asphaltene masses
- Total residual oil
- Residual oil percentage
- Habitat recovery index
- Endpoint decision
- Continued-monitoring status
- Model version

## LHS sampling

`scipy.stats.qmc.LatinHypercube` generates eight input dimensions covering shoreline type, oil category, location, surface distribution, thickness/character, subsurface interval, treatment, and segment timing. The default artifact contains 100 segments and 800 repeat-survey observations using seed 42.

## Endpoint logic

The screening endpoint is reached when residual oil is at or below 20% of initial oil and the habitat recovery index is at least 80%. The output states mirror the NOAA/SCAT workflow:

- Meets cleanup endpoints
- No further treatment recommended
- Continued monitoring required

These thresholds are project screening assumptions, not universal NOAA thresholds or regulatory closure criteria.

## Calibration path

Replace the synthetic LHS data with repeat SCAT/SOS/STR observations. Estimate treatment-specific $R_{ts}$ and $R_{tb}$ rates using held-out segments. Calibrate DHI oil fractions and weathering parameters using measured oil chemistry, temperature, wave/tide conditions, and residual oil. Report uncertainty intervals and validate endpoint classifications separately from parameter fitting.

The DHI document references Mackay et al., Fingas, Reed, Delvigne and Sweeney, Xie et al., and French-McCay for the underlying oil-spill process formulations.
