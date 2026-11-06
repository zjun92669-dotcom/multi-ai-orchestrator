# 分发与许可证说明

本文档说明本 Skill 的本地安装、公开仓库与开源之间的区别，以及许可证要求。对应视频结论第 10 条：公开源码不等于开源。

## 本地安装

本 Skill 以目录形式存在，包含 SKILL.md、scripts/、references/、assets/。本地安装方式：

- 项目级：将本目录放到项目的 `.codebuddy/skills/multi-ai-orchestrator/`。
- 用户级：将本目录放到 `~/.codebuddy/skills/multi-ai-orchestrator/`。
- 界面导入：在 WorkBuddy 的"专家·技能·连接器"中导入本 Skill 目录或压缩包。

说明：`.codebuddy/skills/<skill-name>/` 为约定目录。若当前 WorkBuddy 版本界面不支持该路径，以"专家·技能·连接器"导入为准，不要编造其他路径。

## 公开仓库与开源的区别

- 公开源码：把仓库设为公开可见，他人可以查看。这不等于开源。
- 真正开源：除公开完整源文件外，还需明确写明使用许可（LICENSE），说明他人可以如何使用、修改、再分发。
- 没有许可证的公开仓库，在法律上默认"保留所有权利"，他人无权自由使用、修改或再分发。

## 许可证状态

**本 Skill 已选定 MIT 许可证。** LICENSE 文件已添加到技能根目录。

- 许可证类型：MIT License
- 添加日期：2026-11-06
- 版权声明：Copyright (c) 2026 multi-ai-orchestrator contributors
- 核心条款：任何人可自由使用、复制、修改、合并、发布、分发、再授权和/或出售本 Software，前提是在所有副本中保留版权声明和许可声明。
- 本 Skill 现在可以正式称为开源项目。
- 本 Skill 引用的第三方脚本（如 skill-creator 的 init_skill.py、package_skill.py）遵循其各自的许可，使用前需确认与 MIT 的兼容性。MIT 与大多数主流开源许可证兼容。

## 分发检查清单

- [x] LICENSE 文件已添加（MIT）。
- [x] 许可证条款已写明。
- [ ] 是否包含第三方代码？→ 确认其许可证与 MIT 兼容。
- [ ] 公开仓库 README 中是否标注许可证类型和 LICENSE 文件位置？