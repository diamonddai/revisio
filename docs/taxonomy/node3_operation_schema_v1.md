# Node3 Operation Schema v1 (Draft)

## Scope

This document translates taxonomy operations into backend-executable rules for Node3.
It is aligned with:

- `docs/taxonomy/taxonomy_codebook.md` (full operation set)
- current backend contracts and enums (`none|minor|sig|major`)
- current Vega-Lite case data shape in `data/*/chart_spec.json`

This is an implementation draft for engineering execution and taxonomy review.

## Operation Naming

Canonical op names use snake_case in backend.
Human-readable aliases from codebook are preserved as aliases.

## Full Operation Catalog

### Data Layer

- `select_data_variables` (alias: `select data variables`)
- `add_data_variables` (alias: `add data variables`)
- `select_data_range` (alias: `select time range`)
- `change_data_granularity` (alias: `change data granularity`)

### Visual Layer

- `change_chart_type` (alias: `change type`)
- `change_color` (alias: `change color`)
- `add_background` (alias: `add background`)
- `simplify_axis` (alias: `simplify axis`)
- `change_aspect_ratio` (alias: `change aspect ratio`)
- `change_axis_scale` (alias: `change axis scale`)

### Text Layer

- `change_title` (alias: `change title`)
- `add_annotation` (alias: `add annotation`)
- `change_annotation` (alias: `change annotation`)
- `delete_source` (alias: `delete source`)
- `change_legend` (alias: `change legend`)
- `add_legend` (alias: `add legend`)

## Key Execution Rules

- Max operations per node: `5`
- Mutual exclusion:
  - `add_title` and `change_title` (reserved compatibility rule)
  - `add_annotation` and `change_annotation` in same target slot
- Canonical layer mapping follows taxonomy codebook:
  - `delete_source` is treated as `text`

## Who/Where/How Strategy Guidance (v1.1 Add-on)

The schema should guide not only syntax validation but also operation planning quality.
For NodeB planning and Node3 execution, we now formalize:

1. **Who (role signatures)**
   - `Amplifier`: text+visual priority, data edits are rare
   - `Extender`(`Analyst` in backend): data+text priority, mainly `select_data_variables` + contextual title/annotation
   - `Bridger`: visual clarity + light text, minimal data rewriting
   - `Adverser`: cross-layer combinations with selective data framing
2. **Where (platform/institution bias)**
   - T1 authority contexts should prefer minimal-to-moderate modification
   - T2 media contexts can use moderate reframing
   - T3 social/community contexts allow moderate-to-substantial reframing
3. **How (content-aware intent)**
   - Operation intents should include topic semantics from parent content
   - `change_title` supports exact-target intent via `title:` prefix
   - `change_color` supports semantic tokens (risk/forest/neutral) and explicit hex

This closes the gap where operations were valid but not sufficiently aligned with content semantics.

## add_annotation Policy (Important)

`add_annotation` is executed with "in-chart first, metadata fallback":

1. Prefer creating or appending chart text marks inside `$.layer[]`:
   - `mark.type = "text"`
   - position with default `encoding.x.value` / `encoding.y.value`
2. If insertion cannot be safely computed, fallback to:
   - `$.description` append mode
   - `$.usermeta.annotations[]` append mode

This keeps behavior consistent with real case artifacts where annotations are often in chart text layers.

## simplify_axis Policy

`simplify_axis` currently follows a conservative first-step policy:

1. Simplify **x-axis first** (not both axes yet).
2. Apply:
   - `labels = false`
   - `ticks = false`
   - `grid = false`
   - `title = null`

Rationale: reduce visual clutter while controlling semantic risk from over-simplifying y-axis.

## add_legend Policy

`add_legend` is allowed only when:

1. The target spec currently has **no existing legend**.
2. The operation intent indicates **emphasis/highlight/focus** semantics.

If either precondition is not met, executor performs `skip_op` for this operation.

## delete_source Policy (Strict Match + Safe Guard)

`delete_source` only removes visible source attribution text, not data pipeline fields.

### Match rule

- Case-insensitive prefix match for text beginning with:
  - `source:`
  - `sources:`
  - `data source`
  - `via`
  - `from`

### Candidate carriers

- Text marks in `$.layer[*].mark.text`
- Descriptive text in `$.description`
- Optional metadata fields such as `$.usermeta.source`

### Protected fields (must not be removed by delete_source)

- `$.data`
- `$.datasets`
- `$.transform`
- `$.encoding`
- `$.mark` (except text content replacement in text marks)

Rationale: remove attribution narrative, but keep chart renderability and data integrity.

## Intent Conventions (Execution Contract)

### `change_title`

- If intent starts with `title:` or `headline:`, executor writes exact title text.
- Otherwise executor uses generic reframing fallback (`Reframed: ...`).

### `change_color`

- Intent semantic tokens map to palette:
  - risk/alarm -> red
  - forest/deforestation/environment -> green
  - neutral/objective -> blue
- Explicit hex (e.g. `#2E8B57`) is allowed and takes priority.

### `add_annotation`

- Annotation text should be data-grounded (not abstract slogans).
- Keep intent as plain annotation sentence; avoid mechanical directives in visible text.
- Trendline and wrapping are controlled through `params`.

## Params Conventions (Structured Execution Contract)

`selected_operations[]` supports `params` for deterministic execution:

- `change_title.params.max_line_chars` (int, default `36`): auto-wrap long titles.
- `add_annotation.params.include_trendline` (bool, default `false`): add trend line layer.
- `add_annotation.params.max_line_chars` (int, default `32`): auto-wrap long annotation text while keeping complete sentence.
- `add_annotation.params.min_font_size` (int, default `14`): keep annotation readable.
- `add_annotation.params.prune_offtopic_annotations` (bool, default `true`): clear existing off-topic annotation snippets.
- `add_annotation.params.narrative_keywords` (string[]): keyword list for annotation pruning.
- `change_annotation.params` supports the same readability/pruning fields (`max_line_chars=32` default, `min_font_size`, `prune_offtopic_annotations`, `narrative_keywords`) and `emphasis_style` (`none|amplify`).
- `change_color.params.scope` (`mark|chart_global`, default `chart_global`): apply color to full chart palette.
- `change_color.params.palette_style` (`default|social_contrast`, default `default`): social-contrast vivid palette for Amplifier/Adverser media-social contexts.
- `change_color` only targets data marks (bar/line/area/point etc.), not text marks.
- `simplify_axis.params.target_axis` (`x|y|both`, default `x`): axis simplification scope.
- `simplify_axis.params.mode` (`compact_hide|interval_labels`, default `compact_hide`): keep sparse readable labels or hide labels.
- `simplify_axis.params.label_interval` (int, default `5`): for quantitative x-axis, show labels every N values in `interval_labels` mode.
- `select_data_range.params`:
  - `x_field` (optional): explicit x channel field
  - `start` / `end` (optional): inclusive range window; when both present executor writes a datum-based JS range filter expression

## Suggested Default Execution Order

1. `delete_source`
2. `select_data_range`
3. `select_data_variables`
4. `add_data_variables`
5. `change_data_granularity`
6. `change_chart_type`
7. `change_axis_scale`
8. `simplify_axis`
9. `change_aspect_ratio`
10. `change_color`
11. `add_background`
12. `change_title`
13. `change_legend`
14. `add_legend`
15. `change_annotation`
16. `add_annotation`

## Content Example (Deforestation Case)

Observed pattern from taxonomy examples (BBC + environment reporting):

- Amplifier path:
  - `change_title` -> `title: Amazon Deforestation Highest Since 2006`
  - `change_color` -> `theme forest green highlight`
  - `simplify_axis` -> reduce clutter for narrative focus
- Counter-frame path:
  - `change_title` -> `title: Rate of Deforestation Fell in 2023`
  - `change_color` -> `risk alarm red contrast`
  - `simplify_axis` -> focus selected segment

Both are valid operation sets, but the resulting framing direction diverges because of role+platform+intent semantics.

## Validation and Rollback

- Per-op validation failure: `skip_op`
- Node-level structural failure: `node_rollback` to parent spec
- All-op failure or unrecoverable state: `fallback_text`
- Every op must log provenance with:
  - `operation`, `params`, `target_paths`, `before`, `after`, `status`, `error`

