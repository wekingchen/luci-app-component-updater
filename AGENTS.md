# LuCI Component Updater · AI 开发约定

本文件适用于整个仓库，包括未来的 AI 编程助手。**开始修改前先读本文件、`docs/project-governance.md`、`docs/acceptance-gates.md`、受影响模块文档和测试**。Wiki 只是阅读镜像，`main` 下的源码、测试和文档才是可审计事实。

## 产品边界与不可回退约束

1. 产品为 **OpenWrt 组件更新器**，目前首个组件是 NaiveProxy；不是固件升级器，也不是任意 Shell 执行平台。操作仅允许白名单组件及固定路径。
2. **opkg/IPK 与 APKv3 是两套原生适配器，共用中文 LuCI、RPC 和下载设置。**不可跨体系安装软件包，也不可因为新增 APK 而削弱既有 IPK 行为。
3. 对未知 APK 固件保持**只读/禁止安装**，不得把 AX6S 的特定适配写成“所有 OpenWrt APK 固件通用”。新增板型需独立审计文件归属、版本、架构、依赖及回滚。
4. 更新前必须校验官方来源、发布资产摘要、Manifest、实际下载包摘要、设备身份与安装预案；不得默认允许缺失校验、过期预案、并行安装、未知文件归属或自动补装网络依赖。
5. **完整恢复优先**：备份原有程序、软件包数据库信息和 UCI 配置；APK 额外保护 `/etc/apk/world`。失败自动恢复、手动回滚与中断标记不可删除。
6. 不主动重启 PassWall；但旧软件包脚本可能有副作用，**不能保证连接绝对无中断**。不暗改防火墙、代理配置、固件分区或用户 UCI 设置。
7. GitHub HTTPS 反代是可选项。默认 API 直连；若 API 也走第三方反代，必须警告信任边界。**SHA256 和 Release digest 不等于独立数字签名**；不能在文档和 UI 误称已签名。
8. 普通 UI 文案使用中文；保持桌面与移动一致、操作按钮可用、状态明确、危险操作二次确认。不要为了装饰牺牲逻辑与无障碍使用。

## 版本、发布及验证用语

- **GitHub Release 标题、功能更新说明、安装/回滚说明统一以简体中文为主**；软件包格式、技术缩写、命令和版本号可保留英文。不能因为 GitHub Actions 使用英文 Shell 就默认发布英文说明。已发布版本只允许在校验标签和资产 SHA256 后修正说明文字，不重传/覆盖软件包。

- 管理器 IPK 和 APK 必须**同一应用版本**，来自同一个主分支提交，同一次 CI 检查，并放在同一个管理器 Release；组件 IPK/APK 可分开构建与 Release，但必须使用同一个已验证的官方上游版本。
- **CI 通过 ≠ 实际设备验收**。明确区分 Python 单测、真实软件包管理器隔离 rootfs 测试、ARM64 chroot、用户反馈的真机操作、完整设备验收。
- RC 可以说明尚待实机测试，不得误称稳定版。**V0.5.6 的一次性限定设备 Stable**以 MT3600BE（IPK）和指定固件 AX6S（APK）的正常更新/手动回滚证据为准；N1 **无需真机测试**，不得宣称 N1 已实测。后续自动 APK 发布仍按 `docs/ax6s-hardware-acceptance-checklist.md` 的网络与异常/断电门禁执行，不能借本次 Stable 绕过自动发布保护。
- 保留 `AX6S_APK_AUTO_PUBLISH` 的安全门禁；禁止借修改文件或版本标记绕过它。V0.5.0 RC1 已经一次性授权并公开发布，不意味着日后通行许可。
- 不重写既有 Release 资产、不悄悄改变旧 tag 下的二进制。发布版本变更须同步修改两种管理包、Release tag、回归测试和说明。

## 开发工作步骤

1. **先查证**：读取 `README.md`、`docs/project-governance.md`、`docs/acceptance-gates.md`、组件 JSON 和受影响的代码/测试。确认设备真实能力与已有验收级别；不凭过期记忆修改。
2. **建立变更清单**：列出 IPK、APK、LuCI、rpcd、Release、回滚、供应链和文档的影响面；无法支持的环境必须保持拒绝策略。
3. **小步开发**：独立分支、最小范围修改，补正反例和边界回归。绝不删除核心安全校验来使测试变绿。
4. **运行门禁**：`python3 tools/check_docs.py`；`python3 -m unittest discover -s tests -v`；CI 内还包括 Shell、LuCI、IPK/APKv3 真实安装与恢复、ARM64 回归。
5. **交付核对**：更新事实来源 `docs/`、面向用户的 `wiki-src/`、`README.md`；核对 PR Actions；区分“测试通过”和“硬件已验证”；合并、清理分支和发布遵守明确授权。

## 文档治理

- `docs/` 保存**可审计的技术事实、验收依据、未完成项**；`wiki-src/` 是 GitHub Wiki 的**版本化中文阅读源**；`README.md` 是产品入口；本文件是 AI 开发者规则入口。
- **主仓库优先于 Wiki 页面**；如果两者不一致，停止以 Wiki 结论发布，并同步修正文档。
- 文档变动必须通过 `tools/check_docs.py`；改变接口、版本、适配器或验收状态时要同步更新相关说明。
- 详细操作见 `docs/project-governance.md`，Wiki 导航源见 `wiki-src/Home.md`。
