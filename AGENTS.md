# Agent Startup

Use OpenSpec as the source of truth for this repository.

## OpenSpec CLI preflight for Codex on Windows

Before running any `openspec ...` command, verify the shell is actually rooted
at this repository:

```powershell
Get-Location
Test-Path .\openspec\config.yaml
```

If `Get-Location` resolves to `C:\` or another directory that does not contain
`openspec\config.yaml`, do not conclude that the OpenSpec CLI is broken and do
not bypass it by manually applying artifacts. In Codex's Windows sandbox, the
tool `workdir` may not become the real repo path, and `Set-Location` to the
real `C:\Users\marco\...` path may fail with `Access is denied`.

Instead, switch to the Codex sandbox junction that targets this repository, then
run OpenSpec from there:

```powershell
$Repo = 'C:\Users\marco\Nextcloud\Projects\barma7_repositories\brainweb-dl'
$SandboxCwdRoot = 'C:\Users\CodexSandboxOffline\.codex\.sandbox\cwd'
$SandboxRepo = Get-ChildItem -LiteralPath $SandboxCwdRoot -Directory -Force |
    Where-Object {
        $Item = Get-Item -LiteralPath $_.FullName -Force
        $Item.LinkType -eq 'Junction' -and $Item.Target -contains $Repo
    } |
    Select-Object -First 1 -ExpandProperty FullName

if (-not $SandboxRepo) {
    throw "Could not find Codex sandbox junction for $Repo"
}

Set-Location -LiteralPath $SandboxRepo
if (-not (Test-Path .\openspec\config.yaml)) {
    throw "OpenSpec root not found after switching to $SandboxRepo"
}
```

After this preflight, commands such as
`openspec list --json`,
`openspec status --change <change> --json`,
`openspec instructions apply --change <change> --json`, and
`openspec validate <change> --strict`
should operate normally.

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
