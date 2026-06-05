# PPT Polish Workflow

`ppt-polish-workflow` 是一个个人编排型 Codex skill，用来把 ChatGPT 生成的 PPT 大纲转成经过预览、批注和必要可编辑化处理的演示文稿。

它不替代现有工具，而是固定一套工作流：

1. 确认并整理 ChatGPT PPT 大纲。
2. 调用 `codex-ppt` 生成图片式视觉初稿。
3. 调用本 skill 自带的 image pre-review 服务做预览和批注。
4. 根据批注分流：直接修改、重新生成页面，或进入可编辑化阶段。
5. 只有用户明确指定页面时，才调用 `image-to-editable-ppt` 转成对象级可编辑 PPTX。

## 核心原则

- 不把第一版 PPTX 直接当作最终交付。
- 不默认把整套 deck 转成可编辑 PPT。
- `codex-ppt` 负责视觉初稿。
- 本 skill 内置 preview server 负责图片式 pre-review 和 annotation。
- `image-to-editable-ppt` 只处理用户点名的页面。
- pre-review 阶段不再调用 `ppt-master`。

## 文件结构

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   └── review_preview/
│       ├── run_server.py
│       ├── server.py
│       └── static/
└── references/
    └── review-preview.md
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

第一版聚焦 `codex-ppt` 图片式初稿的 review loop。预览批注由本 skill 自带 Flask 服务执行；可编辑化仍由 `image-to-editable-ppt` 按用户指定页面执行。
