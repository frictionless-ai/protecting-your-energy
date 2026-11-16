# Limits

Four things stay unsolved after every repo in [stack.md](stack.md) is installed. They are properties of the problem.

## Universal program equivalence

Deciding whether two arbitrary programs compute the same function is undecidable. What works: restricted classes under stated semantics. Alive2 proves LLVM IR transformations under LLVM's semantics. CounterTV aligns optimized x86 with the IR it came from. objdiff proves byte identity, which is stronger than equivalence and narrower. Fuzzing finds differences; it never proves their absence.

So a Verified claim always names its proof: "byte-identical under objdiff rules R", "equivalent under semantics S for inputs in B". Never "equivalent".

## Unique source recovery

Compilation is lossy. Names go. Types collapse to widths. Function boundaries move with inlining. `for` and `while` can emit the same bytes. Two different source files can compile to one identical object, and nothing in the object says which one was written.

So byte parity proves the recovered source *produces* the original. It does not prove the recovered source *is* the original. Readable C that matches is the target because it is useful and checkable, not because it is the author's text.

## Hardware reproduction

Renode's peripheral models are functional: they return what the register would return. They do not reproduce bus timing, analog behaviour, or undocumented side effects. PANDA records and replays whole-system execution faithfully for what the emulator models. avatar² hands the unmodelled parts to real hardware, which is the only source of truth for them, and which does not scale.

So runtime evidence is labelled with its substrate: emulator, model, or hardware. Behaviour observed on a model is a claim about the model.

## Ambiguous evidence

Two functions in two builds can match on every witness and still be different functions. Two names can both explain a routine. Two struct layouts can both satisfy every observed access. No confidence score distinguishes them, because the distinguishing observation was never made.

So the coordinator keeps both as contested, names the observation that would separate them, and exports the ambiguity. An agent that picks one and continues has produced fiction with provenance.

## What this means for "complete"

Completeness is defined against a target: this set of binaries, this set of platforms, this proof contract. "Every function in build X is Verified under objdiff rules R" is a reachable claim. "The program is fully recovered" is not a claim this stack makes.
