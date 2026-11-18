# Examples

Two built bundles for `patet scan`. Both use a made-up project address.

- **clean** holds only a browser key. `patet scan examples/clean` passes.
- **leaky** holds a fake server key, the mistake of pasting the `service_role` key into front-end code. `patet scan examples/leaky` fails with a critical finding.

CI runs the GitHub Action on both and checks that the first passes and the second fails.
