# GitHub Wiki 首次初始化与同步权限

此页面记录 **2026-11-20 首次同步验收结果**。仓库 Wiki 选项已经开启，但主分支 [Wiki 发布工作流](https://github.com/wekingchen/luci-app-component-updater/actions/runs/44580418252) 在克隆独立 Wiki 仓库和尝试首次推送时未获成功；**主仓库文档完整，Wiki 网页尚未发布**。这不是文档测试失败，更不是管理器打包失败。

## 需要仓库所有者一次性完成的外部授权

1. 进入 [仓库 Wiki](https://github.com/wekingchen/luci-app-component-updater/wiki)。若显示“Create the first page”，建立一个名字为 `Home` 的临时页面，内容可写“由主仓库 wiki-src 自动维护”，保存它以初始化独立的 `luci-app-component-updater.wiki.git` 仓库。
2. 在 [Actions → Documentation / Publish GitHub Wiki](https://github.com/wekingchen/luci-app-component-updater/actions/workflows/wiki-publish.yml) 选择 **Run workflow**，分支 `main`。工作流会首先尝试 GitHub 提供的令牌。
3. **如果仍因 Wiki 权限而失败**，为 Wiki 推送准备一个具有适当写权限、期限受限的访问令牌，并将其存入仓库 Settings → Secrets and variables → Actions → New repository secret，名称精确为 `WIKI_PUSH_TOKEN`。令牌只放 GitHub Secrets，**不要提交代码、粘贴日志或发送给聊天助手**。公共仓库优先选择可用的最小权限；Wiki Git 权限可能与主仓库的 GitHub App/API 权限不同。
4. 再次手动执行 Wiki 发布工作流，直到明确显示 `GitHub Wiki is updated`，并打开 Wiki 首页验证中文导航和各页面。GitHub Wiki 页面 URL 是否能访问以及 Wiki 的提交是否产生，才是真正成功的证据。

## 自动化行为与安全边界

- 主仓库 `wiki-src/` 是**唯一事实源**；未来编辑 Markdown 后，`main` 分支变更会自动触发 Wiki 同步。
- 同步只覆盖当前受托管的 8 个 Markdown 页面；不会删除社区自行创建的其它 Wiki 页面，不使用 `force push`。
- 所有仓库 PR/fork 不会执行带 Wiki 写权限的推送步骤；仅可信的 `main` 触发。
- 文档合约、Wiki 内部链接、IPK/APK 管理器版本、正式发布门禁均在主 CI 校验；Wiki 发布失败会单独标红，**不会伪称成功，也不会影响已发布的 V0.5.0 RC1 二进制**。
- 完成第一次初始化后，本文件可以更新“Wiki 已实际成功同步”的日期、对应 Actions 链接和验收截图；未取得证据之前不能修改验收结论。

建议通过访问 [主仓库知识库源](../wiki-src/Home.md) 先阅读全部内容，**无需等待 Wiki 才能进行有规则约束的后续开发**。
