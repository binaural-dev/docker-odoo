"""Maintenance actions: init addons, sync repos.

These are the "I just want to set up / refresh the local source tree"
actions. They don't talk to the docker daemon directly; they touch
the filesystem (the ``src/`` directory tree) and the local git
remotes of each custom repo.

``BASE_PATH`` is taken from ``os.getcwd()`` (the ``./odoo`` launcher
does ``os.chdir(BASE_PATH)`` at the top of ``main()``).
"""

from __future__ import annotations

import configparser
import os
import re
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner

from generators.config_loader import resolve_instance_config


# ============================================================
# init: discover / report the addons state
# ============================================================


def init_addons(runner: "Runner", config: dict, instance: str | None) -> None:
    """Inspect the addons state for ``instance`` (or all instances).

    Reports which addon paths already exist locally and which ones
    need to be cloned. This is a *report* action: it does not clone
    anything (the legacy ``./odoo init`` behavior).
    """
    if instance:
        runner.info(
            f"\n=== 📦 INICIALIZANDO ADDONS EN: {instance.upper()} ===\n"
        )
    else:
        runner.info(
            "\n=== 📦 INICIALIZANDO ADDONS EN TODAS LAS INSTANCIAS ===\n"
        )

    instances_to_init = (
        [instance] if instance else list(config["instances"].keys())
    )
    base_path = os.getcwd()

    for inst_name in instances_to_init:
        inst_conf = config["instances"][inst_name]
        odoo_conf = resolve_instance_config(inst_conf, config)
        addons = odoo_conf.get("addons", [])
        odoo_version = inst_conf["odoo_version"]

        runner.info(
            f"\n=== Init para instancia: {inst_name} (Odoo {odoo_version}) ==="
        )
        for addon_path in addons:
            # addon_path is like "src/enterprise" or "src/custom/<instance-name>"
            local_path = os.path.join(base_path, addon_path)
            if os.path.isdir(local_path):
                runner.info(f"  ✓ {addon_path} ya existe")
            else:
                runner.info(
                    f"  → {addon_path} no encontrado. Créalo manualmente "
                    f"o clona el repositorio correspondiente en {local_path}"
                )

    runner.info("")


# ============================================================
# Shared submodule helpers (used by ``sync`` and ``update_tags``)
# ============================================================


def _discover_submodules(project_path: str) -> list[str]:
    """List submodule paths declared in ``project_path/.gitmodules``.

    Only paths that actually exist as a directory are returned (a
    submodule can be declared but not yet initialized). Uses
    ``configparser`` directly on ``.gitmodules`` — no git subprocess
    needed, so this is trivially unit-testable with a fixture file.
    """
    gitmodules_path = os.path.join(project_path, ".gitmodules")
    if not os.path.isfile(gitmodules_path):
        return []

    parser = configparser.ConfigParser()
    try:
        parser.read(gitmodules_path)
    except configparser.Error:
        return []

    paths = []
    for section in parser.sections():
        if not parser.has_option(section, "path"):
            continue
        rel_path = parser.get(section, "path")
        if os.path.isdir(os.path.join(project_path, rel_path)):
            paths.append(rel_path)
    return paths


def _filter_tags(tags: list[str], text_filter: str | None) -> list[str]:
    """Narrow ``tags`` to those matching every term in ``text_filter``.

    ``tags`` is expected to already be sorted (e.g. by
    ``git tag --sort=-v:refname``); this only filters, it doesn't
    reorder. An empty/``None`` filter returns ``tags`` unchanged.

    ``text_filter`` may hold several comma/space-separated terms (e.g.
    ``"19, alpha"`` or ``"19 alpha"``) — a tag must contain all of
    them (case-insensitive, AND) to match, so version and stage can be
    combined in one go instead of narrowing in separate passes.
    """
    if not text_filter:
        return list(tags)
    needles = [n for n in re.split(r"[,\s]+", text_filter.strip().lower()) if n]
    if not needles:
        return list(tags)
    return [t for t in tags if all(n in t.lower() for n in needles)]


def _suggest_branch_name(bumps: list[tuple[str, str]], branch_origin: str) -> str:
    """Suggest a PR branch name that names every (submodulo, tag) bump.

    Caps at the first 3 bumps to keep the name usable — a run that
    bumps many submodules still gets a sane branch name, just with a
    ``+N-mas`` suffix instead of spelling out every single one.

    Nests the name under ``branch_origin`` so the branch itself says
    which base it targets — otherwise several update-tags branches for
    different bases (e.g. ``17.0`` vs ``18.0``) look identical once
    they pile up locally. Any ``/`` already in ``branch_origin`` (e.g.
    ``release/17.0``) just becomes extra nesting, which git allows and
    ``_branch_ref_conflict`` already checks for.
    """
    segments = [f"{s}-{t}" for s, t in bumps]
    shown, rest = segments[:3], segments[3:]
    # "bump/", not "update/": several projects use a plain branch named
    # "update" as their working branch, which collides with the
    # "update/<slug>" ref path at the git level (a ref can't be both a
    # leaf and a directory) — see refs/heads/update vs refs/heads/update/x.
    name = f"bump/{branch_origin}/" + "_".join(shown)
    if rest:
        name += f"_+{len(rest)}-mas"
    return name


def _branch_exists(branch: str) -> bool:
    """Whether ``branch`` already exists locally, in the current repo."""
    return (
        subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        ).returncode
        == 0
    )


def _branch_ref_conflict(candidate: str) -> str | None:
    """The existing branch blocking ``candidate``, if any.

    Git stores branches as a directory tree under ``refs/heads/``, so a
    branch named e.g. ``update`` and one named ``update/foo`` can't
    coexist — one needs ``update`` to be a leaf (a file), the other a
    directory. ``git checkout -b`` fails on this with a raw "cannot
    lock ref" error, so it's checked for up front to give a clear
    message instead.
    """
    parts = candidate.split("/")
    for i in range(1, len(parts)):
        prefix = "/".join(parts[:i])
        if _branch_exists(prefix):
            return prefix
    return None


def _gh_repo_slug(cwd: str | None = None) -> str | None:
    """Best-effort ``owner/repo`` for the ``origin`` remote of ``cwd``.

    Passed straight to ``gh pr create --repo``, so it never has to
    guess which GitHub repo the current directory belongs to. Without
    it, a project ``gh`` hasn't seen before — every freshly cloned
    project — makes it stop and ask the user to run
    ``gh repo set-default owner/repo`` first, which hangs our
    non-interactive ``subprocess.run`` call instead of failing loudly.

    Returns ``None`` if ``origin`` isn't set or doesn't look like a
    GitHub remote (SSH or HTTPS) — callers fall back to letting ``gh``
    resolve it on its own.
    """
    url = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    ).stdout.strip()
    match = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?$", url)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def _describe_submodule_ref(submodule_path: str) -> str:
    """Describe what ``submodule_path`` is currently checked out to.

    Prefers an exact tag match (``git describe --tags --exact-match``);
    falls back to the branch name if it's on one; falls back to the
    short commit hash (marked as detached) otherwise.
    """
    tag = subprocess.run(
        ["git", "describe", "--tags", "--exact-match"],
        cwd=submodule_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if tag.returncode == 0:
        return tag.stdout.strip()

    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=submodule_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    branch_name = branch.stdout.strip()
    if branch.returncode == 0 and branch_name and branch_name != "HEAD":
        return branch_name

    short_hash = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=submodule_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return f"{short_hash.stdout.strip()} (detached)"


def _describe_submodule_at_ref(
    project_path: str, submodulo: str, ref: str
) -> str:
    """Describe what ``submodulo`` is pinned to in ``ref``, without checkout.

    Reads the submodule's commit pointer straight out of the project
    repo's tree for ``ref`` (``git ls-tree``) — no ``checkout``/``pull``,
    so the working tree and current branch are untouched. The commit is
    then resolved to a tag inside the submodule's own local clone
    (``git describe --tags --exact-match``); this only works if that
    commit object was already fetched into the submodule at some point,
    since this never fetches either. Falls back to the short hash when
    no exact tag matches or the object isn't present locally.

    When ``ref`` is a plain branch name (no ``/``, so not already a
    remote-tracking ref, tag, or hash) and ``origin/<ref>`` exists,
    that remote-tracking ref is used instead. A local branch like
    ``release`` is often stale — nothing here ever fetches — while
    ``origin/release`` reflects whatever the last fetch already saw,
    which is what "what's on release" almost always means.
    """
    resolved_ref = ref
    if "/" not in ref:
        remote_ref = f"origin/{ref}"
        check = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", remote_ref],
            cwd=project_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if check.returncode == 0:
            resolved_ref = remote_ref

    ls_tree = subprocess.run(
        ["git", "ls-tree", resolved_ref, "--", submodulo],
        cwd=project_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if ls_tree.returncode != 0:
        return f"(ref '{resolved_ref}' no existe)"
    line = ls_tree.stdout.strip()
    if not line:
        return f"(no está en '{resolved_ref}')"
    commit = line.split()[2]

    submodule_path = os.path.join(project_path, submodulo)
    tag = subprocess.run(
        ["git", "describe", "--tags", "--exact-match", commit],
        cwd=submodule_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if tag.returncode == 0:
        return tag.stdout.strip()

    short = commit[:7]
    return f"{short} (sin tag exacto — puede necesitar fetch)"


# ============================================================
# sync: refresh custom repos and their submodules
# ============================================================


def sync(
    runner: "Runner",
    repo_names: str | list[str],
    branch: str,
    show: bool = False,
) -> None:
    """Sync the named custom repos to ``branch``.

    For each repo we:
      1. ``git stash`` any local changes (so the checkout doesn't
         fail on dirty trees).
      2. ``git checkout <branch>``.
      3. ``git fetch origin --prune`` (refreshes remote-tracking refs
         and drops the ones for branches deleted upstream — ``pull``
         alone fetches too, but doesn't prune).
      4. ``git pull origin <branch>``.
      5. ``git submodule update --init --checkout --recursive`` (same
         flags as ``update_tags``'s submodule refresh, for consistency).
      6. ``git submodule foreach "git fetch origin --prune"`` (same
         refresh, one level down, so each submodule's remote-tracking
         refs are current too before we report their state).

    With ``show=True`` the git output is left visible; otherwise it
    is silenced (``subprocess.DEVNULL``) so the user only sees our
    progress messages.
    """
    runner.info(
        f"\n=== 🔄 SINCRONIZANDO REPOSITORIOS (Rama: {branch}) ===\n"
    )
    if isinstance(repo_names, str):
        repo_names = [repo_names]

    base_path = os.getcwd()

    for repo_name in repo_names:
        repo_path = os.path.join(base_path, "src", "custom", repo_name)
        if not os.path.isdir(repo_path):
            runner.error(
                f"Error: Repositorio '{repo_name}' no encontrado en src/custom/"
            )
            continue

        runner.info(f"\n=== Sincronizando {repo_name} (Rama: {branch}) ===")
        os.chdir(repo_path)

        stdout = subprocess.DEVNULL if not show else None

        try:
            runner.info("→ Guardando cambios locales (stash)...")
            subprocess.run(["git", "stash"], stdout=stdout)

            runner.info(f"→ Cambiando a rama {branch}...")
            subprocess.run(["git", "checkout", branch], stdout=stdout)

            runner.info("→ Actualizando remotos (fetch --prune)...")
            subprocess.run(["git", "fetch", "origin", "--prune"], stdout=stdout)

            runner.info("→ Trayendo últimos cambios (pull)...")
            subprocess.run(["git", "pull", "origin", branch], stdout=stdout)

            runner.info("→ Actualizando submódulos (init --checkout --recursive)...")
            subprocess.run(
                ["git", "submodule", "update", "--init", "--checkout", "--recursive"],
                stdout=stdout,
            )

            runner.info("→ Actualizando remotos de submódulos (fetch --prune)...")
            subprocess.run(
                ["git", "submodule", "foreach", "git fetch origin --prune"],
                stdout=stdout,
            )

            runner.info(f"✅ {repo_name} sincronizado.")
            for submodulo in _discover_submodules(repo_path):
                estado = _describe_submodule_ref(
                    os.path.join(repo_path, submodulo)
                )
                runner.info(f"   • {submodulo}: {estado}")
        except Exception as e:
            runner.error(f"❌ Error sincronizando {repo_name}: {e}")
        finally:
            os.chdir(base_path)


# ============================================================
# update-tags: bump one submodule to a tag, on a fresh PR branch
# ============================================================


def _resolve_bump_checkout(
    runner: "Runner",
    project_path: str,
    submodulo: str | None,
    tag: str | None,
    stdout,
) -> tuple[str, str] | None:
    """Resolve one (submodulo, tag) pair and check the tag out.

    Returns the ``(submodulo, tag)`` resolved, or ``None`` if it
    couldn't be resolved (already reported via ``runner.error`` — the
    caller should stop the loop). Only checks the tag out inside the
    submodule; it does **not** commit — that happens once the PR
    branch exists (see :func:`_commit_bump` / :func:`update_tags`), so
    the branch is only ever created once every checkout the user
    wants is already done.
    """
    from odoo_cli.core.prompts import prompt_for_submodule, prompt_for_tag

    if submodulo is None:
        submodulo = prompt_for_submodule(runner, project_path)
    if not submodulo:
        runner.error("No se seleccionó ningún submódulo.")
        return None

    submodule_path = os.path.join(project_path, submodulo)
    if not os.path.isdir(submodule_path):
        runner.error(f"Error: Submódulo '{submodulo}' no encontrado en el proyecto")
        return None

    if tag is None:
        tag = prompt_for_tag(runner, submodule_path)
        if not tag:
            runner.error("No se seleccionó ningún tag.")
            return None
    else:
        existing = subprocess.run(
            ["git", "tag", "--list", tag],
            cwd=submodule_path,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.split()
        if tag not in existing:
            runner.error(f"Error: El tag '{tag}' no existe en {submodulo}")
            return None

    runner.info(f"→ Checkout de {submodulo} a {tag}...")
    subprocess.run(["git", "checkout", tag], cwd=submodule_path, stdout=stdout)
    return submodulo, tag


def _commit_bump(runner: "Runner", submodulo: str, tag: str, stdout) -> None:
    """Commit the already-checked-out bump of ``submodulo`` to ``tag``.

    If the current branch already had this exact bump — e.g. a
    previous run already committed it on a branch that got reused —
    ``git commit`` has nothing to stage; that's reported as a no-op
    (info), not an error, since the desired state is achieved either
    way.
    """
    runner.info(f"→ Commiteando el bump de {submodulo}...")
    subprocess.run(["git", "add", submodulo], stdout=stdout)
    commit = subprocess.run(
        ["git", "commit", "-m", f"chore: update {submodulo} to {tag}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if commit.returncode != 0:
        runner.info(
            f"ℹ {submodulo} ya estaba en {tag} — nada nuevo para commitear."
        )
        return

    runner.info(f"✅ {submodulo} @ {tag} commiteado.")


def update_tags(
    runner: "Runner",
    project: str,
    branch_origin: str | None,
    submodulo: str | None,
    tag: str | None,
    show: bool = False,
) -> None:
    """Bump one or more submodules of ``project`` on a new PR branch.

    Any of ``branch_origin``/``submodulo``/``tag`` left as ``None`` is
    resolved interactively via the ``runner``, in order, because each
    depends on git state left by the previous steps (you can't list a
    project's submodules before ``submodule update --init`` has run,
    and you can't list a submodule's tags before it's been fetched).

    Order of operations, deliberately in this sequence:

    1. Check out every submodule tag the user wants, still on
       ``branch_origin`` (nothing committed yet). After each one,
       ``runner.confirm`` asks whether to bump another — this loops
       until they say no.
    2. Only once every checkout is done does it create (or reuse) the
       PR branch — so a bogus submodulo/tag never leaves behind a
       half-baked branch, and the branch only ever exists once there's
       something real to put on it.
    3. Commit each bump on that branch — one commit per submodule, so
       the history stays granular — then ask whether to push, and —
       only if that push succeeds — whether to open the PR (via
       ``gh pr create``). Both are gated by an explicit confirmation
       each; nothing touches the remote unless the user says so.
    4. Only once the PR exists, ask whether to merge it — a direct
       ``gh pr merge --merge --delete-branch`` (not ``--auto``, so the
       result — merged or blocked by required checks/reviews — is
       known immediately). Only if that merge succeeds does it ask
       whether to also delete the local branch. Every one of these is
       its own confirmation; declining any of them just stops there,
       leaving whatever already happened (the branch, the push, the
       PR) intact.

    If the target branch already exists locally (e.g. a retry after a
    previous run stopped before the push), the user is offered a
    reuse of that branch instead of a hard failure.
    """
    import shutil

    from odoo_cli.core.prompts import prompt_for_branch_origin

    base_path = os.getcwd()
    project_path = os.path.join(base_path, "src", "custom", project)
    if not os.path.isdir(project_path):
        runner.error(f"Error: Proyecto '{project}' no encontrado en src/custom/")
        return

    runner.info(f"\n=== 🔀 UPDATE-TAGS: {project} ===\n")
    os.chdir(project_path)
    stdout = subprocess.DEVNULL if not show else None

    try:
        if branch_origin is None:
            branch_origin = prompt_for_branch_origin(runner, project_path)

        runner.info("→ Guardando cambios locales (stash)...")
        subprocess.run(["git", "stash"], stdout=stdout)

        runner.info(f"→ Cambiando a rama base {branch_origin}...")
        subprocess.run(["git", "checkout", branch_origin], stdout=stdout)

        runner.info(f"→ Trayendo últimos cambios (pull origin {branch_origin})...")
        subprocess.run(["git", "pull", "origin", branch_origin], stdout=stdout)

        runner.info("→ Actualizando submódulos (init --checkout --recursive)...")
        subprocess.run(
            ["git", "submodule", "update", "--init", "--checkout", "--recursive"],
            stdout=stdout,
        )

        runner.info("→ Actualizando remotos de submódulos (fetch --prune)...")
        subprocess.run(
            ["git", "submodule", "foreach", "git fetch origin --prune"],
            stdout=stdout,
        )

        # 1) Resolve + check out every bump the user wants, still on
        # branch_origin — nothing is committed yet, so nothing
        # half-baked ever becomes a branch (see step 2).
        bumps: list[tuple[str, str]] = []
        next_submodulo, next_tag = submodulo, tag
        while True:
            resolved = _resolve_bump_checkout(
                runner, project_path, next_submodulo, next_tag, stdout
            )
            if resolved:
                bumps.append(resolved)

            again = runner.confirm(
                "\n¿Actualizar otro submódulo en esta misma rama?", default=False
            )
            if not again:
                break
            next_submodulo, next_tag = None, None

        if not bumps:
            runner.error("❌ No se seleccionó ningún bump — no hay nada para PR.")
            return

        # 2) Now that every submodule already sits on its target tag,
        # create (or reuse) the PR branch — the uncommitted submodule
        # pointer changes from step 1 carry over onto it untouched.
        suggested_branch = _suggest_branch_name(bumps, branch_origin)
        new_branch = None
        while new_branch is None:
            candidate = runner.prompt_text(
                "\nNombre de la rama nueva para el PR", default=suggested_branch
            ).strip() or suggested_branch

            if _branch_exists(candidate):
                reuse = runner.confirm(
                    f"La rama '{candidate}' ya existe localmente. "
                    "¿Seguir usándola para agregar más bumps?",
                    default=True,
                )
                if not reuse:
                    suggested_branch = f"{candidate}-2"
                    continue
                runner.info(f"→ Reusando la rama existente {candidate}...")
                checkout_cmd = ["git", "checkout", candidate]
            else:
                conflict = _branch_ref_conflict(candidate)
                if conflict:
                    runner.error(
                        f"❌ No se puede crear '{candidate}': ya existe una "
                        f"rama local llamada '{conflict}' en este repo, y "
                        f"Git no permite que '{conflict}' sea a la vez una "
                        "rama y una carpeta de ramas. Borrá o renombrá "
                        f"'{conflict}' (por ejemplo, git branch -d "
                        f"{conflict}), o elegí otro nombre acá abajo."
                    )
                    suggested_branch = candidate
                    continue
                runner.info(f"→ Creando rama {candidate} desde {branch_origin}...")
                checkout_cmd = ["git", "checkout", "-b", candidate]

            result = subprocess.run(
                checkout_cmd, stdout=stdout, stderr=subprocess.PIPE, text=True
            )
            if result.returncode != 0:
                runner.error(
                    f"❌ No se pudo preparar la rama '{candidate}': "
                    f"{result.stderr.strip()}"
                )
                return
            new_branch = candidate

        # 3) Commit each bump on the new branch — one commit per
        # submodule, so the history stays granular.
        for bump_submodulo, bump_tag in bumps:
            _commit_bump(runner, bump_submodulo, bump_tag, stdout)

        resumen = ", ".join(f"{s}@{t}" for s, t in bumps)

        # If every bump above was a no-op (all submodules already sat
        # on their target tag), the new branch is identical to
        # branch_origin: pushing it would be pointless and `gh pr
        # create` would fail with "No commits between...". Bail out
        # here, before touching the remote at all.
        rev_count = subprocess.run(
            ["git", "rev-list", "--count", f"{branch_origin}..{new_branch}"],
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        if rev_count == "0":
            runner.info(
                f"\nℹ {resumen} — ya estaban en esos tags. La rama "
                f"'{new_branch}' no tiene commits nuevos respecto a "
                f"'{branch_origin}', así que no hay nada para pushear ni "
                "un PR que crear.\n"
            )
            return

        runner.info(f"\n✅ Rama '{new_branch}' lista con: {resumen}\n")

        do_push = runner.confirm(
            f"¿Hacer push de '{new_branch}' a origin?", default=False
        )
        if not do_push:
            runner.info(
                "   Rama lista localmente. Push y PR quedan pendientes para "
                "cuando estés conforme.\n"
            )
            return

        runner.info(f"→ Pusheando {new_branch} a origin...")
        push = subprocess.run(
            ["git", "push", "-u", "origin", new_branch],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if push.returncode != 0:
            runner.error(f"❌ Error al hacer push: {push.stderr.strip()}")
            return
        runner.info(f"✅ Rama '{new_branch}' pusheada a origin.")

        do_pr = runner.confirm(
            "¿Crear el Pull Request ahora (gh pr create)?", default=False
        )
        if not do_pr:
            return

        if shutil.which("gh") is None:
            runner.error(
                "❌ 'gh' (GitHub CLI) no está instalado — no se puede crear "
                "el PR automáticamente. Abrilo manualmente desde GitHub."
            )
            return

        suggested_title = f"Update {resumen}"
        title = runner.prompt_text(
            "Título del PR", default=suggested_title
        ).strip() or suggested_title
        suggested_body = "\n".join(f"- {s} → {t}" for s, t in bumps)
        body = runner.prompt_text(
            "Cuerpo del PR", default=suggested_body
        ).strip() or suggested_body

        runner.info("→ Creando PR con gh...")
        gh_pr_cmd = [
            "gh", "pr", "create",
            "--base", branch_origin,
            "--head", new_branch,
            "--title", title,
            "--body", body,
        ]
        repo_slug = _gh_repo_slug()
        if repo_slug:
            gh_pr_cmd += ["--repo", repo_slug]
        pr = subprocess.run(
            gh_pr_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if pr.returncode != 0:
            runner.error(f"❌ Error creando el PR: {pr.stderr.strip()}")
            return
        runner.info(f"✅ PR creado: {pr.stdout.strip()}")

        # 4) Merge is a direct (non-``--auto``) ``gh pr merge`` — it
        # resolves immediately (success or a clear error), so we know
        # right away whether it's safe to offer deleting the local
        # branch next. If the base branch has required checks/reviews
        # and the caller has no bypass rights, ``gh`` just errors out
        # here and neither branch gets touched.
        do_merge = runner.confirm(
            f"¿Mergear el PR de '{new_branch}' ahora (gh pr merge)?",
            default=False,
        )
        if not do_merge:
            return

        runner.info("→ Mergeando PR (gh pr merge --merge --delete-branch)...")
        gh_merge_cmd = [
            "gh", "pr", "merge", new_branch,
            "--merge", "--delete-branch",
        ]
        if repo_slug:
            gh_merge_cmd += ["--repo", repo_slug]
        merge = subprocess.run(
            gh_merge_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if merge.returncode != 0:
            runner.error(
                "❌ No se pudo mergear el PR (¿faltan checks o aprobaciones "
                f"requeridas?): {merge.stderr.strip()}"
            )
            # `gh` itself suggests `--admin` in its stderr when the
            # only thing blocking the merge is branch policy (not a
            # failing check) — that's the signal it's even worth
            # offering the bypass retry instead of just giving up.
            if "--admin" not in merge.stderr:
                return
            do_admin_merge = runner.confirm(
                "¿Reintentar con privilegios de administrador (gh pr merge "
                "--admin), saltando la protección de la rama?",
                default=False,
            )
            if not do_admin_merge:
                return
            runner.info("→ Reintentando merge con --admin...")
            merge = subprocess.run(
                gh_merge_cmd + ["--admin"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if merge.returncode != 0:
                runner.error(
                    f"❌ No se pudo mergear ni con --admin: {merge.stderr.strip()}"
                )
                return
        runner.info(f"✅ PR mergeado — rama remota '{new_branch}' borrada.")

        do_delete_local = runner.confirm(
            f"¿Borrar también la rama local '{new_branch}'?", default=True
        )
        if not do_delete_local:
            return

        runner.info(f"→ Volviendo a '{branch_origin}' y borrando rama local...")
        subprocess.run(["git", "checkout", branch_origin], stdout=stdout)
        delete = subprocess.run(
            ["git", "branch", "-d", new_branch],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if delete.returncode != 0:
            runner.error(f"❌ No se pudo borrar la rama local: {delete.stderr.strip()}")
            return
        runner.info(f"✅ Rama local '{new_branch}' borrada.")
    except Exception as e:
        runner.error(f"❌ Error en update-tags: {e}")
    finally:
        os.chdir(base_path)


# ============================================================
# update-tags-bulk: bump one submodule to one tag, across every
# project on a given Odoo version
# ============================================================


def _prepare_bulk_project(
    runner: "Runner", project_path: str, branch_origin: str | None, stdout
) -> str:
    """Stash, land on ``branch_origin`` (or stay put), refresh submodules.

    Assumes the caller has already ``os.chdir``'d into ``project_path``
    (same convention as :func:`update_tags`/:func:`sync`).

    With ``branch_origin=None`` the project is **never** checked out to
    a different branch — it stays exactly where it already was, and the
    branch it's on is read back via ``git rev-parse`` to use as the
    effective base for the new bump branch. With ``branch_origin`` given,
    every project is moved onto it (``checkout`` + ``pull``) before its
    submodules are refreshed, so the tag check that follows sees what's
    actually pinned on that branch, not whatever the project happened to
    be on before.

    Either way, submodules are refreshed (``submodule update --init
    --checkout --recursive`` + ``submodule foreach fetch --prune``)
    before returning — the caller relies on this to check out/validate
    the target tag against fresh remotes.
    """
    runner.info("→ Guardando cambios locales (stash)...")
    subprocess.run(["git", "stash"], stdout=stdout)

    if branch_origin is not None:
        runner.info(f"→ Cambiando a rama base {branch_origin}...")
        subprocess.run(["git", "checkout", branch_origin], stdout=stdout)
        runner.info(f"→ Trayendo últimos cambios (pull origin {branch_origin})...")
        subprocess.run(["git", "pull", "origin", branch_origin], stdout=stdout)
        effective_branch_origin = branch_origin
    else:
        current = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        ).stdout.strip()
        effective_branch_origin = current or "HEAD"

    runner.info("→ Actualizando submódulos (init --checkout --recursive)...")
    subprocess.run(
        ["git", "submodule", "update", "--init", "--checkout", "--recursive"],
        stdout=stdout,
    )
    runner.info("→ Actualizando remotos de submódulos (fetch --prune)...")
    subprocess.run(
        ["git", "submodule", "foreach", "git fetch origin --prune"],
        stdout=stdout,
    )
    return effective_branch_origin


def update_tags_bulk(
    runner: "Runner",
    odoo_version: str,
    projects: list[str],
    submodulo: str | None,
    tag: str | None,
    branch_origin: str | None,
    show: bool = False,
) -> None:
    """Bump one submodule to one tag, across every project in ``projects``.

    Unlike :func:`update_tags` (one project, any number of bumps,
    confirmed step by step), this bumps exactly **one** ``(submodulo,
    tag)`` pair across **many** projects — the submodule and tag are
    resolved interactively only once (against the first project in
    ``projects``, used as a reference), and push/PR/merge are each
    confirmed once for the whole batch instead of once per project.
    To bump a different submodule too, run this again.

    A project missing the target submodule, or whose submodule doesn't
    have the target tag, is skipped (reported, not fatal) — not every
    project on a given Odoo version necessarily carries every shared
    submodule. Likewise, any per-project git/gh failure is caught and
    reported without aborting the rest of the batch (same
    continue-on-error pattern as :func:`sync`/:func:`submodule_status`).
    """
    import shutil

    from odoo_cli.core.prompts import prompt_for_submodule, prompt_for_tag

    base_path = os.getcwd()
    stdout = subprocess.DEVNULL if not show else None

    valid_projects = []
    for project in projects:
        if os.path.isdir(os.path.join(base_path, "src", "custom", project)):
            valid_projects.append(project)
        else:
            runner.error(
                f"Error: Proyecto '{project}' no encontrado en src/custom/ "
                "— se omite del lote."
            )
    if not valid_projects:
        runner.error("❌ Ningún proyecto válido para procesar.")
        return

    runner.info(
        f"\n=== 🔀 UPDATE-TAGS-BULK: Odoo {odoo_version} — "
        f"{len(valid_projects)} proyecto(s) ===\n"
    )
    runner.info(
        f"Se actualizarán {len(valid_projects)} proyectos en Odoo "
        f"{odoo_version}: {', '.join(valid_projects)}"
    )

    # 1) Resolve submodulo + tag ONCE, against the first project as a
    # reference — prepared the same way every project will be prepared
    # in the loop below, so the tags it lists are the ones that'll
    # actually be checked against every other project.
    ref_project = valid_projects[0]
    ref_path = os.path.join(base_path, "src", "custom", ref_project)
    os.chdir(ref_path)
    try:
        runner.info(f"\n--- Preparando {ref_project} (referencia) ---")
        _prepare_bulk_project(runner, ref_path, branch_origin, stdout)
    finally:
        os.chdir(base_path)

    if submodulo is None:
        submodulo = prompt_for_submodule(runner, ref_path)
    if not submodulo:
        runner.error("No se seleccionó ningún submódulo.")
        return

    if tag is None:
        submodule_path = os.path.join(ref_path, submodulo)
        if not os.path.isdir(submodule_path):
            runner.error(
                f"Error: Submódulo '{submodulo}' no encontrado en "
                f"'{ref_project}' (proyecto de referencia)."
            )
            return
        tag = prompt_for_tag(runner, submodule_path)
    if not tag:
        runner.error("No se seleccionó ningún tag.")
        return

    # 2) Batch-level confirmations — asked once, applied to every
    # project. Nested the same way update_tags nests them per-project:
    # no point asking about PRs if push was declined, etc.
    do_push = runner.confirm(
        f"\n¿Pushear las ramas de los {len(valid_projects)} proyectos?",
        default=False,
    )
    do_pr = do_push and runner.confirm(
        "¿Crear el PR en cada proyecto (gh pr create)?", default=False
    )
    do_merge = do_pr and runner.confirm(
        "¿Mergear los PRs creados (gh pr merge)?", default=False
    )
    do_admin_retry = do_merge and runner.confirm(
        "¿Reintentar con --admin los merges bloqueados solo por "
        "branch protection?",
        default=False,
    )

    if do_pr and shutil.which("gh") is None:
        runner.error(
            "❌ 'gh' (GitHub CLI) no está instalado — no se pueden crear "
            "PRs automáticamente. Se pushearán las ramas nada más."
        )
        do_pr = do_merge = do_admin_retry = False

    # 3) Loop over every project — one project's failure never aborts
    # the batch (same continue-on-error pattern as sync/submodule_status).
    results: list[tuple[str, str]] = []
    for project in valid_projects:
        project_path = os.path.join(base_path, "src", "custom", project)
        os.chdir(project_path)
        try:
            runner.info(f"\n--- {project} ---")
            if project == ref_project:
                # Already prepared above (as the reference project) —
                # re-preparing here would just redo the same stash/
                # checkout/pull/submodule-refresh for no benefit.
                effective_branch_origin = (
                    branch_origin
                    if branch_origin is not None
                    else subprocess.run(
                        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                        cwd=project_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        text=True,
                    ).stdout.strip()
                    or "HEAD"
                )
            else:
                effective_branch_origin = _prepare_bulk_project(
                    runner, project_path, branch_origin, stdout
                )

            resolved = _resolve_bump_checkout(
                runner, project_path, submodulo, tag, stdout
            )
            if not resolved:
                results.append(
                    (project, "sin ese submódulo/tag — salteado")
                )
                continue
            bump_submodulo, bump_tag = resolved

            suggested_branch = _suggest_branch_name(
                [(bump_submodulo, bump_tag)], effective_branch_origin
            )
            new_branch = suggested_branch
            suffix = 2
            while _branch_exists(new_branch) or _branch_ref_conflict(new_branch):
                new_branch = f"{suggested_branch}-{suffix}"
                suffix += 1

            runner.info(f"→ Creando rama {new_branch} desde {effective_branch_origin}...")
            checkout_b = subprocess.run(
                ["git", "checkout", "-b", new_branch],
                stdout=stdout, stderr=subprocess.PIPE, text=True,
            )
            if checkout_b.returncode != 0:
                runner.error(
                    f"❌ {project}: no se pudo crear la rama '{new_branch}': "
                    f"{checkout_b.stderr.strip()}"
                )
                results.append((project, "error creando rama nueva"))
                continue

            _commit_bump(runner, bump_submodulo, bump_tag, stdout)

            rev_count = subprocess.run(
                ["git", "rev-list", "--count",
                 f"{effective_branch_origin}..{new_branch}"],
                stdout=subprocess.PIPE, text=True,
            ).stdout.strip()
            if rev_count == "0":
                results.append(
                    (project, f"sin cambios — ya estaba en {bump_tag}")
                )
                continue

            if not do_push:
                results.append(
                    (project, f"rama '{new_branch}' lista localmente (sin push)")
                )
                continue

            runner.info(f"→ Pusheando {new_branch} a origin...")
            push = subprocess.run(
                ["git", "push", "-u", "origin", new_branch],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            if push.returncode != 0:
                runner.error(f"❌ {project}: error al hacer push: {push.stderr.strip()}")
                results.append((project, "error en push"))
                continue

            if not do_pr:
                results.append((project, f"rama '{new_branch}' pusheada (sin PR)"))
                continue

            repo_slug = _gh_repo_slug()
            title = f"Update {bump_submodulo} to {bump_tag}"
            body = f"- {bump_submodulo} → {bump_tag}"
            gh_pr_cmd = [
                "gh", "pr", "create",
                "--base", effective_branch_origin,
                "--head", new_branch,
                "--title", title,
                "--body", body,
            ]
            if repo_slug:
                gh_pr_cmd += ["--repo", repo_slug]
            runner.info("→ Creando PR con gh...")
            pr = subprocess.run(
                gh_pr_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            if pr.returncode != 0:
                runner.error(f"❌ {project}: error creando el PR: {pr.stderr.strip()}")
                results.append((project, "push ok, error creando PR"))
                continue
            pr_url = pr.stdout.strip()
            runner.info(f"✅ {project}: PR creado: {pr_url}")

            if not do_merge:
                results.append((project, f"PR creado: {pr_url}"))
                continue

            gh_merge_cmd = [
                "gh", "pr", "merge", new_branch, "--merge", "--delete-branch",
            ]
            if repo_slug:
                gh_merge_cmd += ["--repo", repo_slug]
            runner.info("→ Mergeando PR (gh pr merge --merge --delete-branch)...")
            merge = subprocess.run(
                gh_merge_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            if merge.returncode != 0 and do_admin_retry and "--admin" in merge.stderr:
                runner.info(f"→ {project}: reintentando merge con --admin...")
                merge = subprocess.run(
                    gh_merge_cmd + ["--admin"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                )
            if merge.returncode != 0:
                runner.error(
                    f"❌ {project}: no se pudo mergear el PR: {merge.stderr.strip()}"
                )
                results.append((project, f"PR creado ({pr_url}), no mergeado"))
                continue

            runner.info(f"✅ {project}: PR mergeado.")
            results.append((project, f"mergeado: {pr_url}"))
        except Exception as e:
            runner.error(f"❌ Error procesando {project}: {e}")
            results.append((project, f"error: {e}"))
        finally:
            os.chdir(base_path)

    # 4) Final summary — one line per project, so the outcome of all
    # N projects is visible at a glance.
    runner.info("\n=== 📋 RESUMEN update-tags-bulk ===")
    for project, outcome in results:
        runner.info(f"  • {project}: {outcome}")
    runner.info("")


# ============================================================
# submodule-status: report-only — what tag/branch/hash is each
# submodule checked out to, right now
# ============================================================


def submodule_status(
    runner: "Runner", project: str | None = None, refs: list[str] | None = None
) -> None:
    """Report each submodule's current tag/branch/hash, read-only.

    With ``project`` given, only that project's submodules are
    reported. Without it, every project under ``src/custom/`` is
    reported. Unlike ``sync``/``update_tags``, this never touches git
    state — no ``stash``/``checkout``/``pull``/``fetch``, only the
    read-only ``git describe``/``rev-parse``/``ls-tree`` calls inside
    :func:`_describe_submodule_ref`/:func:`_describe_submodule_at_ref`.
    A missing project is reported as an error and skipped, not a hard
    stop, so one typo doesn't hide the status of every other project
    when running over all of them.

    With ``refs`` given (e.g. ``["release", "staging"]``), the working
    tree is bypassed entirely: each submodule's pin is read straight
    out of the project repo's tree for that ref via
    :func:`_describe_submodule_at_ref`, one section per ref, so
    comparing two branches doesn't require checking either of them
    out. Without ``refs``, the report reflects whatever is physically
    checked out right now, same as before.

    Each project's header also shows the *project repo's own* current
    branch/tag/hash (via the same ``_describe_submodule_ref``, which
    works on any git repo, not just submodules) — a submodule's
    checkout state is independent of which branch the project repo is
    on, so without this the status list has no context to read it in.
    This header is skipped when ``refs`` is given, since the ref
    itself already says what's being reported on.
    """
    if project:
        projects = [project]
    else:
        from odoo_cli.core.instance import get_custom_repos

        projects = get_custom_repos()
        if not projects:
            runner.info("No se encontraron proyectos en src/custom/.")
            return

    base_path = os.getcwd()
    for proj in projects:
        project_path = os.path.join(base_path, "src", "custom", proj)
        if not os.path.isdir(project_path):
            runner.error(f"Error: Proyecto '{proj}' no encontrado en src/custom/")
            continue

        submodulos = _discover_submodules(project_path)

        if refs:
            for ref in refs:
                runner.info(f"\n=== {proj} (ref: {ref}) ===")
                if not submodulos:
                    runner.info("   (sin submódulos)")
                    continue
                for submodulo in submodulos:
                    estado = _describe_submodule_at_ref(project_path, submodulo, ref)
                    runner.info(f"   • {submodulo}: {estado}")
            continue

        proj_ref = _describe_submodule_ref(project_path)
        runner.info(f"\n=== {proj} (rama: {proj_ref}) ===")
        if not submodulos:
            runner.info("   (sin submódulos)")
            continue
        for submodulo in submodulos:
            estado = _describe_submodule_ref(os.path.join(project_path, submodulo))
            runner.info(f"   • {submodulo}: {estado}")


__all__ = [
    "init_addons",
    "sync",
    "update_tags",
    "update_tags_bulk",
    "submodule_status",
]
