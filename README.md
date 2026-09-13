# Revisio

**Revisio** is an LLM-based multi-agent simulation system for exploring how framing shifts emerge as data visualizations circulate in online discourse. Given a source visualization and configurable circulation conditions, it simulates how heterogeneous actors reinterpret and transform the chart, producing a visualization lineage through which framing shifts can be traced, attributed, and explored.

## Overview

Data visualizations have become integral to online discourse. They circulate across social media and other platforms as resources for expressing positions and constructing contested narratives. As visualizations are interpreted, reused, and sometimes modified by diverse actors, their meaning is shaped by **framing**: the selection and emphasis of aspects of reality that promote particular interpretations. In visualization, framing is established through choices about data inclusion, visual encoding, and narrative organization.

That framing does not settle at publication. Subsequent actors may reinterpret, annotate, and modify these representational choices, producing cumulative interpretive transformations that we define as **framing shifts**. Such shifts can fundamentally alter how social issues are understood through data. For example, Dhawka et al. document a lineage of visualizations derived from U.S. border apprehension statistics: originating as a Senate visual aid, the same dataset was progressively reframed through added annotations, new data series, and rewritten narratives until it appeared as a political centerpiece at a campaign rally.

Prior visualization research has shown how design choices function as rhetorical strategies that guide interpretation. Those studies, however, treat framing as a property fixed at the moment of creation, leaving the *afterlife* of visualizations largely unexamined. Addressing this gap raises two challenges:

* **Taxonomy.** Circulation involves heterogeneous actors, platforms, and transformative operations. No existing taxonomy characterizes these actors in a way that supports analysis of how framing shifts emerge.
* **Simulation.** Real-world circulation is neither controlled nor fully observable, so it is difficult to examine how different conditions give rise to alternative framing shifts.

Revisio addresses both challenges. A corpus-based taxonomy describes the actors who produce framing shifts. An LLM-based multi-agent framework then operationalizes that taxonomy, so researchers and practitioners can inspect typically invisible framing shifts under configurable scenarios.

## Taxonomy

The taxonomy is derived from qualitative coding of **22 real-world visualization lineages** (83 variants). It describes each actor along three dimensions:

* **Role (*who*):** Bridger, Amplifier, Extender, or Adverser — the actor's strategic intent in reshaping interpretation.
* **Platform (*where*):** the media environment in which the actor publishes or circulates a variant (e.g., Official Institution, News Media, Social Media).
* **Framing Operations (*how*):** the concrete modifications applied to a variant, grouped into Data Manipulation, Visual Encoding, and Textual Elements.

Together, these dimensions provide a structured basis for analyzing how visualizations are transformed after publication.

## Framing Shift Simulation

Given a source visualization and circulation settings (agent count, depth, and actor mix), Revisio instantiates heterogeneous agents from the taxonomy and simulates successive reinterpretation. Users can:

1. **Trace** framing shifts along a generated visualization lineage;
2. **Attribute** key transformations to specific roles, platforms, and operations;
3. **Explore** counterfactual scenarios by changing circulation conditions.

Rather than treating circulation as random diffusion, Revisio models each hop as a cognition-driven adjustment: agents respond to the discrepancy between an incoming visualization and their own disposition.

## System Workflow

The simulation framework consists of three modules:

**1. Agent Configuration**

User-specified circulation parameters are mapped to agent dispositions. Role and Platform jointly define how an agent tends to interpret an incoming visualization, and they constrain the framing operations available to that agent.

**2. Dissonance-driven Framing Adjustment (DFA)**

Each agent runs DFA on the visualization it receives:

* *Dissonance Assessment* extracts data, visual, and textual information, compares them with the agent disposition, and assigns a dissonance state (Resonance, Tension, Conflict, or Noise) together with an inner monologue.
* *Operation Selection* turns that assessment into an executable operation plan, checked against the agent's Role–Platform operation set.
* *Shift Execution* applies the plan to the parent Vega-Lite specification and outputs a new visualization variant.

**3. Topology Formation**

Local DFA outputs are combined with role-transition and platform-flow priors from the corpus. Each path may continue, branch, or terminate, progressively forming a visualization lineage: variants as nodes and framing operations as edges.

## Evaluation

We evaluate Revisio through an experiment, two case studies, and expert interviews. The evaluation examines whether the system generates plausible and interpretable simulations of framing shifts, and whether it supports tracing, attribution, and counterfactual exploration. Results indicate that Revisio can make typically invisible framing shifts observable and analyzable.

## Contributions

This work makes three main contributions:

* We constructed a **corpus-based taxonomy** that characterizes actors in visualization framing shifts along Role, Platform, and Framing Operations, providing a structured basis for analyzing how visualizations are transformed after publication.

* We developed **Revisio**, a simulation system built on a multi-agent framework that operationalizes the taxonomy into agent behaviors. The framework incorporates the **Dissonance-driven Framing Adjustment (DFA)** algorithm to model how framing shifts emerge through interactions among heterogeneous actors.

* We evaluated Revisio through an experiment, two case studies, and expert interviews, demonstrating that the system can support tracing, attribution, and exploration in circulation scenarios.

## Corpus and Code

The encoded taxonomy corpus (22 lineages; Role, Platform, and framing operations per node and edge) is included in this repository under [`docs/figures/corpus.json`](docs/figures/corpus.json). Original published chart images are not redistributed; each lineage identifies its public source.

Seed Vega-Lite charts used as simulation inputs are in [`data/`](data/). They are starting points for Revisio, not the 22 encoded lineages.

## Getting Started

```bash
conda activate frame
cd backend
./scripts/dev.sh
```



