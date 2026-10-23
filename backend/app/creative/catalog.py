"""Original compact planning rules, adapted from audited methods; no upstream code or excerpts."""
SOURCES = [
    ("screenwriting", "jtydhr88/screenwriting-skills", "51115f18d160aa8b2ac5813e4432b6f0b425358f", "MIT", "planning_adapted", ["plugins/screenwriting/skills/sw-scene-craft/SKILL.md", "plugins/screenwriting/skills/sw-dialogue/SKILL.md"]),
    ("visual", "smixs/visual-skills", "92be33a5a73325fb3d8e0c73b22744b114e2a90e", "CC-BY-4.0", "planning_adapted", ["image/SKILL.md", "video/SKILL.md"]),
    ("shuohao", "eternityspring/shuohao-skills", "d28a9c539b40523d081794b25ff9113016bd98e0", "Apache-2.0", "registered", ["skills/novel-storyboard/SKILL.md", "references/schema.md"]),
    ("manju", "lixiaoxiao9888-create/manju-laoli-skill", "6f16955c57053d77ea0ffbdbbf3a7985a3e0080a", "MIT", "planning_adapted", ["sd-script-engine/SKILL.md", "sd-asset-engine/SKILL.md", "sd-storyboard-engine/SKILL.md", "sd-qc-engine/SKILL.md"]),
    ("awesome-seedance", "LearnPrompt/awesome-seedance", "ba0a453130ac8bdab1cf4e574cb42cefbce23942", "MIT / CC-BY-4.0 / third-party media", "registered", ["agents/skills/seedance-production-workflow/SKILL.md"]),
    ("seedance", "Emily2040/seedance-2.0", "4668457e560eee06e95d7fcfdf441c8c0bba802e", "MIT", "registered_model_specific", ["skills/seedance-prompt/SKILL.md"]),
    ("scenario", "scenario-labs/skills", "5429dea302ccc7edbce8ace9d5c1fb6852499540", "MIT", "disabled_requires_provider_setup", ["skills/scenario/SKILL.md"]),
    ("pexo", "pexoai/pexo-skills", "f724267e45a065b6be445ea6f07312e62d3207cd", "MIT (root) / MIT-0 (frontmatter)", "disabled_pending_security_review", ["skills/seedance-2.0-prompter/SKILL.md"]),
    ("jianying", "luoluoluo22/jianying-editor-skill", "", "unknown", "blocked_source_unavailable", []),
    ("drama", "", "", "unknown", "pending_source_confirmation", []),
]
CATALOG = [{"id": key, "sourceRepo": "https://github.com/" + repo if repo else "",
            "sourceCommit": commit, "license": license, "status": status,
            "sourcePaths": paths, "adaptationVersion": "1.0.0"}
           for key, repo, commit, license, status, paths in SOURCES]
RULES = {
    "script": ("screenwriting", "围绕目标、阻力与转折组织短场景。动作可拍摄，台词推动冲突。只追加草稿，不改写已确认版本。"),
    "dialogue": ("screenwriting", "保留角色意图与事实，压缩解释性对白，通过措辞呈现冲突，不添加未经输入支持的人物事实。"),
    "assets": ("manju", "从输入提取可复用角色、地点、道具、音色描述。区分实体身份与画面表现，不虚构已存在文件或资产版本。"),
    "shots": ("manju", "把动作组织为可独立编辑的镜头，保留明确站位与视线，预计时长只供参考，不混入其他模型镜头语法。"),
    "prompt": ("visual", "按主体、动作、景别、机位、站位、环境与画风组织单镜提示。不得把参考图编号当作真实文件引用。"),
    "image": ("visual", "只规划单幅关键画面。mock 不产生真实图片，不创建已采用结果。"),
}


def provenance(operation: str) -> dict[str, object]:
    source, _ = RULES[operation]
    return dict(next(item for item in CATALOG if item["id"] == source))


def catalog_contracts() -> list[dict[str, object]]:
    from app.creative.contracts import OUTPUTS, Request
    return [{**item, "inputSchema": Request.model_json_schema(),
             "outputSchemas": {operation: OUTPUTS[operation].model_json_schema()
                               for operation, (source, _) in RULES.items() if source == item["id"]}}
            for item in CATALOG]
