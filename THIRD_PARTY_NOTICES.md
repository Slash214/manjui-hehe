# 第三方来源与改编说明

本增量没有安装或执行这些仓库的脚本，没有复制案例媒体、书籍或剧本摘录。`backend/app/creative/catalog.py` 的短规则由本项目重新撰写，参考经审核的方法分类；不是上游完整 Skill，也不代表供应商执行能力。

- **Screenwriting Skills** — Terry Jia，MIT。来源 https://github.com/jtydhr88/screenwriting-skills/tree/51115f18d160aa8b2ac5813e4432b6f0b425358f 。保留 [LICENSE](docs/licenses/screenwriting-LICENSE.txt) 和 [NOTICE](docs/licenses/screenwriting-NOTICE.txt)。改编：场景目标、阻力、转折和对白意图形成独立 JSON 输出模板。书籍、剧本、译文引文排除。
- **Visual Skills** — Serge Shima，CC BY 4.0。来源 https://github.com/smixs/visual-skills/tree/92be33a5a73325fb3d8e0c73b22744b114e2a90e 。保留 [LICENSE](docs/licenses/visual-LICENSE.txt) 和 [NOTICE](docs/licenses/visual-NOTICE.txt)，包括原项目对 agentara 的致谢。改编：单镜画面元素顺序，排除上游 logo、案例及可调用模型能力声明。许可 https://creativecommons.org/licenses/by/4.0/ 。
- **manju-laoli-skill** — MIT。来源 https://github.com/lixiaoxiao9888-create/manju-laoli-skill/tree/6f16955c57053d77ea0ffbdbbf3a7985a3e0080a 。保留 [LICENSE](docs/licenses/manju-LICENSE.txt)。改编：资产提取和独立镜头规划规则，未复制整套根提示词或所谓云 API 载荷。

其他七项只登记来源及审计状态，没有复制实现或启用服务。详细 commit、路径和许可差异见 [技能计划](docs/SKILL-INTEGRATION-PLAN.md)。将来使用 shuohao 时须附 Apache 2.0 LICENSE/NOTICE 和修改说明；LearnPrompt 案例不整体打包；Pexo 根许可与 frontmatter 差异须保留。
