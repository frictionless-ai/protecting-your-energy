# Restore protocol

Load this when you are about to rewind a live tree.

```
step N fails
  -> restore snapshot_before(N)
  -> verify hashes / appearance.2da size (0 bytes is abort)
  -> fix the actual cause
  -> re-run N
  -> replay N+1 .. end IN GUIDE ORDER
```

## Commands (prefer the bundled script)

```bash
CK=<game>/.modsync/checkpoints
git -C "$CK" checkout -f <SHA>
git -C "$CK" clean -fd
rsync -a --delete --exclude '.modsync/' --exclude '.git/' "$CK/" <game>/
```

Then confirm `Override/appearance.2da` is not 0. If the working tree is 0, restore the blob; do not trust size until after checkout.
