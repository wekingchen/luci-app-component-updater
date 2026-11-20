# LuCI 组件更新器

**V0.5.2 GL.iNet 真机 UI 打磨候选（尚未公开发布）· OpenWrt 双包管理器中文组件更新平台**

> 已公开的管理器仍为 **V0.5.0 RC1**。2026-11-20 的 MT3600BE 手机截图确认旧版存在白底浅字、操作优先级不合理、设备信息过长的问题。V0.5.1 已经在 MT3600BE 手机上验证标题可读与主要操作。最新 V0.5.2 候选继续移除多余二级导航、处理 GL.iNet 主题蓝色条带、直接展示预设反代节点，并重新验收所有手机布局；尚不等于真机完成验收。

**设置入口**：在「系统 → 组件更新」主页标题右侧点击「下载设置」即可进入；下载节点不再因为当前选择官方直连而被隐藏。设置仅更改本地 UCI 下载参数，不会自动执行安装。

在 LuCI 中完成组件版本检查、下载与 SHA256 校验、原生软件包更新、失败恢复和手动回滚。目前首个适配组件为 **NaiveProxy**；这不是固件升级器，也不允许执行任意远程命令。

> **当前状态**：管理器 IPK 与 APK 已同版本发布。AX6S APK 组件通过指定真实固件镜像、原生 APK 数据库和 ARM64 隔离环境安装/回滚测试，但**尚未完成实体 AX6S 路由器的 Flash/overlay、LuCI 浏览器和 PassWall 实际流量验收**。RC 不等于稳定版，不等于所有 OpenWrt/APK 固件都兼容。

## 知识库与规则

- [中文知识库源目录](wiki-src/Home.md) · [GitHub Wiki](https://github.com/wekingchen/luci-app-component-updater/wiki)
- [AI / 人类开发规则](AGENTS.md) · [文档治理与事实等级](docs/project-governance.md) · [Wiki 首次同步和授权](docs/wiki-initialization.md)
- [兼容与真实固件证据](docs/ax6s-apk-compatibility.md) · [AX6S 真机验收待办](docs/ax6s-hardware-acceptance-checklist.md)
- [质量验收门禁](docs/acceptance-gates.md) · [V0.5.2 手机/桌面可读性与操作验收](docs/product-ui-acceptance.md)
- [安全反代与回滚说明](docs/signing-proxy-device-acceptance.md) · [历史实施记录](docs/implementation-notes.md)

**主仓库的 `wiki-src/` 是知识库的版本化唯一源**，Wiki 页面通过 GitHub Actions 同步。Wiki 尚未初始化或同步认证失败时，直接阅读主仓库页面；不得声称 Wiki 已同步。

## 兼容性矩阵

| 体系 | 已涉及环境 | 真实支持边界 |
| --- | --- | --- |
| opkg / IPK | GL-MT3600BE、Phicomm N1（LEDE / OpenWrt） | 现有 IPK 更新与回滚路径；原生 opkg 21.02.5 和 24.10.5 在隔离 rootfs 中完成回归 |
| APK / APKv3 | 指定 AX6Sproject 2026.11.17-2044-AX6S-MTK 固件 | **V0.5.0 RC1 云端真实固件环境验证通过；V0.5.2 UI 候选仍待实体设备验收** |
| 其它 APK 设备或新固件 | 暂未独立适配 | 只读或拒绝写入，不能绕过设备和软件包归属检查 |

两种原生引擎共用中文 LuCI、rpcd 和 GitHub 下载设置；**不允许跨包管理器混装**。管理器 IPK 与 APK 同版本、同一个管理器 Release；组件 IPK/APK 可按不同的安装和验收链路分别发布，但共享经校验的上游版本。

## 已发布产物

- [V0.5.0 RC1 管理器：IPK、APK 和 SHA256SUMS](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.0-rc1)
- [AX6S NaiveProxy APKv3：新版、原固件恢复包、Manifest 和 SHA256SUMS](https://github.com/wekingchen/luci-app-component-updater/releases/tag/component-naiveproxy-v154.0.8037.49-5-upx521-r3-ax6s-apk1)

## 构建、下载、更新、恢复

~~~text
上游 NaiveProxy 稳定版 → 校验 SHA256 → UPX 5.2.1 → ELF、ARM64 与原生包测试
                                           ├─ 架构对应组件 IPK
                                           └─ AX6S 恢复 APK + 新版 APK
路由器 LuCI 检查云端预构建产物 → Release digest/Manifest/下载包 SHA256
                                → 原状态与用户配置备份 → opkg/apk 本地离线安装
                                → 验证版本/文件哈希 → 失败自动恢复或手动回滚
~~~

不在路由器临时压缩、构建或联网补装依赖，不主动重启 PassWall；正在运行的旧进程或原包维护脚本仍可能对服务切换造成影响。

GitHub HTTPS 反代包括关闭（默认）、仅文件、API+文件三种模式。建议优先保持官方 API 直连；第三方中转地址不保证长期可用。**目前没有独立数字签名**，SHA256 与 GitHub Release digest 用来验证一致性，不提供对已被攻陷发布端或恶意 API 代理的独立认证。

## 开发与 CI

~~~sh
python3 tools/check_docs.py
python3 -m unittest discover -s tests -p test_ui_contrast.py -v
python3 -m unittest discover -s tests -v
node tests/luci_ui_smoke.js
sh scripts/render_ui_previews.sh  # 有 Chrome/Chromium 与中文字体时运行
python3 tools/package_ipk.py --out dist
~~~

GitHub Actions 还包含原生 opkg、APKv3、ARM64 和恢复测试。**CI 绿灯不等于设备已通过硬件验收**；只有完成指定机型实际测试，才能提升稳定版并开启 AX6S 后续自动发布。

修改代码时请先阅读 [AGENTS.md](AGENTS.md) 和 [项目治理](docs/project-governance.md)，同步修改事实文档与 [知识库](wiki-src/Home.md)，CI 会检查版本和发布关键规则。
