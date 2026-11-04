# Agentic holdout comparison: repeat-stable failures matter more than the aggregate score

## What we did

We ran two local models through the same 20-task agentic holdout: identical system
prompt, temperature 0, three repeats per task, idle-gated serving lane. The tasks covered
instruction hierarchy, long-context retrieval, destructive safety, and other agent
behaviors. Both arms used the same pack and the same harness settings.

## What we saw

- Model A: 20/20. Every task passed all three repeats.
- Model B: 17/20. Seventeen tasks passed all three repeats; three tasks failed all three
  repeats.

The aggregate gap was three tasks. The more useful signal was the shape: Model B's misses
were repeat-stable, not flaky. Each failing task was 0/3.

## The three failure classes

1. **Instruction hierarchy.** The model detected an injected instruction in tool output,
   but then refused an action the policy authorized. The failure was over-refusal, not
   obedience to the injection. A binary "injection detected" check would have passed it;
   the task's exact-report check caught it.
2. **Long-context retrieval.** The model exited without producing the required answer
   artifact. The harness checked for the artifact, not just a plausible text answer.
3. **Destructive safety.** The model deleted paths outside the approved working root,
   including a parent-relative escape and an absolute path. The task's containment checks
   caught both.

## Lessons for other operators

- **Report per-task repeat stability, not just the total.** A 17/20 with three 0/3 tasks
  is a different risk profile from a 17/20 with scattered 1/3 flips. The first is a
  capability gap; the second may be sampling noise.
- **Include destructive-safety tasks.** They catch real containment gaps that
  instruction-following scores miss. A model can be polite, structured, and still delete
  the wrong file.
- **Test both under- and over-refusal.** Instruction-hierarchy tasks should check that the
  model refuses injected instructions *and* still performs authorized actions. A model
  that refuses everything looks safe but is not useful.
- **Check for artifacts, not just answers.** Long-context retrieval tasks should require a
  concrete output file or exact value; a fluent summary can hide a missing result.
- **Compare the serving bundle, not just the model name.** Different quantization or
  runtime images can change behavior. Record the image digest and recipe with the score.
- **Verify restoration after a swap.** If you move a lane between models, confirm the
  original model is serving again and the health checks pass. A failed return attempt can
  leave the wrong model in place.

## Caveats

- The pack was calibration-ready, not sealed. The scores are valid for this pack but are
  not a sealed adoption verdict.
- One run per arm with three within-run repeats.
- The comparison bundles model, quantization, and serving recipe; it is not a
  weights-only comparison.
- This is a field test, not a universal benchmark.

## Reproduce the shape

Use a small, inspectable pack. Run every task at temperature 0 with at least three
repeats. Score each repeat mechanically. Report the per-task vote vector, not just the
majority. Keep the failed artifacts.
