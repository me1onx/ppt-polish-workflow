# PPT Polish Workflow

`ppt-polish-workflow` 是一个个人编排型 Codex skill，用来把 ChatGPT 生成的 PPT 大纲转成经过预览、批注和必要可编辑化处理的演示文稿。

它不替代现有工具，而是固定一套工作流：

1. 确认并整理 ChatGPT PPT 大纲。
2. 调用 `codex-ppt` 生成图片式视觉初稿。
3. 调用 `ppt-master` live preview 做预览和批注。
4. 根据批注分流：直接修改、重新生成页面，或进入可编辑化阶段。
5. 只有用户明确指定页面时，才调用 `image-to-editable-ppt` 转成对象级可编辑 PPTX。

## 核心原则

- 不把第一版 PPTX 直接当作最终交付。
- 不默认把整套 deck 转成可编辑 PPT。
- `codex-ppt` 负责视觉初稿。
- `ppt-master` 负责 preview、annotation 和 review loop。
- `image-to-editable-ppt` 只处理用户点名的页面。

## 文件结构

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    └── ppt-master-bridge.md
```

## 使用方式

将本仓库内容放入 Codex skills 目录，例如：

```bash
/Users/liuchengxi/.codex/skills/ppt-polish-workflow
```

然后在 Codex 中使用：

```text
Use $ppt-polish-workflow to turn my ChatGPT PPT outline into a polished reviewed deck.
```

## 当前状态

第一版聚焦流程编排和阶段门禁，不包含额外脚本。实际生成、预览和可编辑化分别由 `codex-ppt`、`ppt-master`、`image-to-editable-ppt` 执行。
