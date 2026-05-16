# Agent Startup

Use OpenSpec as the source of truth for this repository.

Read:

- `openspec/config.yaml`
- `openspec/specs/PKG-INFO.md`
- `openspec/specs\other-packages-to-inspire-from\brainweb_mrzero.md`
- Relevant specs under `openspec/specs/`
- Relevant active change under `openspec/changes/<change>/`

For non-trivial features, behavior changes, public API changes, and refactors
with meaningful design risk:

1. Reseason about the chage with `/opsx-explore [brief description of chage]`. (optional - up to your judgment)
2. Propose with `/opsx-propose <change>`.
3. Implement with `/opsx-apply`.
4. Archive with `/opsx-archive`.


Use this Python interpreter for checks:

```powershell
C:\Users\marco\.conda\envs\pymarss\python.exe
```

Repository health check:

```powershell
& "C:\Users\marco\.conda\envs\pymarss\python.exe" -m unittest discover -s tests -v
```
