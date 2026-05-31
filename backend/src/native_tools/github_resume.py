"""GitHub Resume Generator — STAR bullets from public repo metadata."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from src.native_tools.artifact_store import NativeArtifactMeta, NativeArtifactStore, tool_response

TOOL_ID = "github_resume_generator"

_REPO_RE = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?]+)",
    re.I,
)


def _parse_repo_url(url: str) -> tuple[str, str] | None:
    m = _REPO_RE.search(url.strip())
    if not m:
        return None
    return m.group("owner"), m.group("repo").removesuffix(".git")


def _fetch_github_repo(owner: str, repo: str) -> dict[str, Any] | None:
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    req = urllib.request.Request(
        api_url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Y-Scape-Native-Tools"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        return None


def _star_bullets(
    owner: str,
    repo: str,
    meta: dict[str, Any] | None,
    *,
    language: str,
    role_target: str,
) -> str:
    lang = meta.get("language") if meta else "Unknown"
    stars = meta.get("stargazers_count", 0) if meta else 0
    desc = meta.get("description") or f"Open-source project {owner}/{repo}" if meta else f"Repository {owner}/{repo}"
    topics = meta.get("topics", []) if meta else []
    role = role_target.strip() or ("软件工程师" if language == "zh" else "Software Engineer")

    if language == "zh":
        bullets = [
            f"## {owner}/{repo} — STAR 简历要点",
            "",
            f"**目标角色：** {role}",
            "",
            "### Situation（情境）",
            f"- 在 GitHub 开源项目 **{owner}/{repo}** 中，项目定位为：{desc}。",
            "",
            "### Task（任务）",
            f"- 作为贡献者/维护者，负责推动项目在 **{lang}** 技术栈下的功能迭代与代码质量。",
            "",
            "### Action（行动）",
            f"- 分析仓库结构与模块边界，梳理核心功能实现路径；",
            f"- 通过 Issue/PR 流程协作，完善文档、测试与可维护性；",
            f"- 关注社区反馈（⭐ {stars}），持续优化开发者体验。",
            "",
            "### Result（结果）",
            f"- 项目获得 **{stars}** Stars，形成可展示的开源贡献案例；",
            f"- 产出结构化技术总结，可直接用于 **{role}** 岗位简历。",
        ]
        if topics:
            bullets += ["", f"**Topics:** {', '.join(topics[:8])}"]
    else:
        bullets = [
            f"## {owner}/{repo} — STAR Resume Bullets",
            "",
            f"**Target role:** {role}",
            "",
            "### Situation",
            f"- Open-source project **{owner}/{repo}**: {desc}.",
            "",
            "### Task",
            f"- Drive feature delivery and code quality using **{lang}** within the repository.",
            "",
            "### Action",
            "- Mapped architecture and module boundaries to plan incremental improvements;",
            "- Collaborated via Issues/PRs; improved docs, tests, and maintainability;",
            f"- Responded to community signals ({stars} stars) to refine developer experience.",
            "",
            "### Result",
            f"- Earned **{stars}** GitHub stars as a portfolio-ready contribution;",
            f"- Produced structured bullets suitable for **{role}** applications.",
        ]
        if topics:
            bullets += ["", f"**Topics:** {', '.join(topics[:8])}"]

    if meta is None:
        bullets += [
            "",
            "---",
            "*Note: GitHub API unavailable — template generated from URL. Configure network or token for live metadata.*",
        ]

    return "\n".join(bullets)


async def generate_resume(
    store: NativeArtifactStore,
    *,
    repo_url: str,
    language: str = "zh",
    role_target: str = "",
) -> dict[str, Any]:
    parsed = _parse_repo_url(repo_url)
    if not parsed:
        return tool_response(ok=False, tool_id=TOOL_ID, error="Invalid GitHub repository URL")

    owner, repo = parsed
    meta = _fetch_github_repo(owner, repo)
    lang = "zh" if language.lower().startswith("zh") else "en"

    analysis = {
        "repoUrl": repo_url,
        "owner": owner,
        "repo": repo,
        "language": lang,
        "roleTarget": role_target,
        "githubApiUsed": meta is not None,
        "metadata": {
            "description": meta.get("description") if meta else None,
            "stars": meta.get("stargazers_count") if meta else None,
            "language": meta.get("language") if meta else None,
            "topics": meta.get("topics", []) if meta else [],
            "htmlUrl": meta.get("html_url") if meta else f"https://github.com/{owner}/{repo}",
        },
    }

    md = _star_bullets(owner, repo, meta, language=lang, role_target=role_target)

    job_id = store.create_job(TOOL_ID)
    artifacts: list[NativeArtifactMeta] = []
    artifacts.append(store.write_text(job_id, TOOL_ID, "resume_bullets.md", md, artifact_type="markdown"))
    artifacts.append(
        store.write_text(
            job_id,
            TOOL_ID,
            "repo_analysis.json",
            json.dumps(analysis, indent=2, ensure_ascii=False),
            artifact_type="json",
        )
    )

    return tool_response(
        ok=True,
        tool_id=TOOL_ID,
        message=f"Generated STAR resume bullets for {owner}/{repo}",
        artifacts=artifacts,
        data=analysis,
    )
