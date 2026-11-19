# 开发者与 AI 协作指南

## 开发前必须查看

1. [根目录 AGENTS.md](https://github.com/wekingchen/luci-app-component-updater/blob/main/AGENTS.md)：跨会话开发规则及禁止事项。
2. [项目治理](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/project-governance.md)：事实等级、设备边界、版本及 PR 验收。
3. [验收门禁](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/acceptance-gates.md)：不同测试证明了什么。
4. 相应设备的技术事实及恢复清单：尤其 [AX6S 原生 APK](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/ax6s-apk-compatibility.md)。

## 代码位置

- `components/*.json`：官方组件元数据与受支持架构。
- `tools/`：下载、校验、UPX、原生 IPK/APK 打包及产物审计。
- `luci-app-component-updater/`：LuCI UI、样式、rpcd ACL、后端安装器、设备专属 APK 适配。
- `tests/`：安全拒绝、旧版回归、浏览器 JS、发布规则及文档合约。
- `.github/workflows/`：CI、定时预构建、真实根文件系统模拟、发布门禁和 Wiki 同步。
- `docs/`：保留真实证据与未完成项；`wiki-src/`：本 Wiki 的可追溯源文件。

## 每次 PR 交付标准

必须交代改了什么、影响哪些设备与包管理器、版本是否统一、备份回滚是否完整、官方摘要是否匹配，以及 CI/实机分别通过了什么。新增组件或适配设备需先补充测试，再开放可点击的更新操作。

在本地或 CI 执行：

~~~sh
python3 tools/check_docs.py
python3 -m unittest discover -s tests -v
node tests/luci_ui_smoke.js
~~~

这里的静态检查只是一部分；完整原生包安装与 ARM64 验收由 Actions 执行。

## Wiki 如何维护

**先在主仓库改 `wiki-src/`，不要把 Wiki 网页当作规范源。** 主分支变更触发 Wiki 同步工作流；GitHub Wiki 第一次使用可能需要初始化 `Home.md`，并按仓库安全策略设置 Wiki 写入授权。如果同步运行失败，先修复同步权限，再确认 Wiki 展示了对应源内容；主仓库文档仍然可查看。

同步保留 Wiki 原有非托管页面，不强制重写 Git 历史。改业务逻辑时，同时更新对应 `docs/` 和面向读者的页面；CI 将检查必须页面、内部链接、源文档入口和发布关键约束。

[首页](Home.md) · [架构](System-Architecture.md)
