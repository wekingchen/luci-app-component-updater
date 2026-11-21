# GitHub Wiki 首次初始化与同步权限

此页面记录 **2026-11-20 Wiki 同步验收结果**。首次运行 [#44580418252](https://github.com/wekingchen/luci-app-component-updater/actions/runs/44580418252) 因 Wiki 尚未初始化或写入权限不足而失败；仓库所有者初始化 Wiki 后，重新运行 [#44581365438（第二次）](https://github.com/wekingchen/luci-app-component-updater/actions/runs/44581365438) 已成功克隆并确认 8 个页面与 `wiki-src/` 相同。

**真正的自动写回也已验证成功**：[Wiki 发布运行 #44583078586](https://github.com/wekingchen/luci-app-component-updater/actions/runs/44583078586) 记录 `Wiki sync changed: Home.md`，随后 `git push` 成功并显示 `GitHub Wiki is updated`。因此，Wiki 已初始化、页面一致性和后续变更自动推送均已通过。

## 首次设置教程（已完成，供未来排障）

1. 进入 [仓库 Wiki](https://github.com/wekingchen/luci-app-component-updater/wiki)。若显示“Create the first page”，建立一个名字为 `Home` 的临时页面，内容可写“由主仓库 wiki-src 自动维护”，保存它以初始化独立的 `luci-app-component-updater.wiki.git` 仓库。
2. 在 [Actions → Documentation / Publish GitHub Wiki](https://github.com/wekingchen/luci-app-component-updater/actions/workflows/wiki-publish.yml) 选择 **Run workflow**，分支 `main`。工作流会首先尝试 GitHub 提供的令牌。
3. **如果仍因 Wiki 权限而失败**，为 Wiki 推送准备一个具有适当写权限、期限受限的访问令牌，并将其存入仓库 Settings → Secrets and variables → Actions → New repository secret，名称精确为 `WIKI_PUSH_TOKEN`。令牌只放 GitHub Secrets，**不要提交代码、粘贴日志或发送给聊天助手**。公共仓库优先选择可用的最小权限；Wiki Git 权限可能与主仓库的 GitHub App/API 权限不同。
4. 再次手动执行 Wiki 发布工作流，直到明确显示 `GitHub Wiki is updated`，并打开 Wiki 首页验证中文导航和各页面。GitHub Wiki 页面 URL 是否能访问以及 Wiki 的提交是否产生，才是真正成功的证据。

## 自动化行为与安全边界

- 主仓库 `wiki-src/` 是**唯一事实源**；未来编辑 Markdown 后，`main` 分支变更会自动触发 Wiki 同步。
- 同步只覆盖当前受托管的 8 个 Markdown 页面；不会删除社区自行创建的其它 Wiki 页面，不使用 `force push`。
- 所有仓库 PR/fork 不会执行带 Wiki 写权限的推送步骤；仅可信的 `main` 触发。
- 文档合约、Wiki 内部链接、IPK/APK 管理器版本、正式发布门禁均在主 CI 校验；Wiki 发布失败会单独标红，**不会伪称成功，也不会影响已发布的 V0.5.6 Stable（或历史 V0.5.0 RC1）二进制**。
- 2026-11-20 已完成 Wiki 内容一致性及实际写入验收。后续如果因 token 权限变化导致同步失败，应重新核验工作流与 Wiki 页面；不得以旧的成功记录证明新一次更新成功。

可直接访问 [GitHub Wiki 首页](https://github.com/wekingchen/luci-app-component-updater/wiki) 或 [主仓库版本化源](../wiki-src/Home.md)。规则以主仓库 `AGENTS.md`、`docs/` 和测试为准。
