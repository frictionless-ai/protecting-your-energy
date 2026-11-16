---
name: {{agent_name}}
description: >-
  {{agent_description}}

  <example>
  Context: {{example_1_context}}
  user: "{{example_1_user}}"
  assistant: "{{example_1_assistant}}"
  <commentary>
  {{example_1_commentary}}
  </commentary>
  </example>

  <example>
  Context: {{example_2_context}}
  user: "{{example_2_user}}"
  assistant: "{{example_2_assistant}}"
  <commentary>
  {{example_2_commentary}}
  </commentary>
  </example>
model: inherit
color: {{color}}
tools: {{tools}}
---

You are {{agent_role}}. Evidence: {{evidence_ref}}.

## What you do

{{responsibilities}}

## How you work

{{process}}

## How this person talks

{{voice}}

## Never

{{anti_patterns}}

## Output

{{output_format}}
