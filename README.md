# LuCI 组件更新器

**V0.5.6 管理器网页自升级与安全清理候选（尚未公开发布）· OpenWrt 双包管理器中文组件更新平台**

> 已公开的管理器仍为 **V0.5.0 RC1**。2026-11-20 的 MT3600BE 手机截图确认旧版存在白底浅字、操作优先级不合理、设备信息过长的问题。V0.5.1 已经在 MT3600BE 手机上验证标题可读与主要操作。最新 V0.5.2 候选继续移除多余二级导航、处理 GL.iNet 主题蓝色条带、直接展示预设反代节点，并重新验收所有手机布局；尚不等于真机完成验收。

**MT3600BE 真机验收更新（2026-11-20）**：用户的 iPhone Safari 截图确认 V0.5.2 首页和下载设置页可读、顶部多余菜单与蓝色条带消失、预设反代节点可选择，配置保存后重新进入仍保留。用户进一步报告在「版本查询与文件下载均使用中转」模式下，官方版本查询成功。**这只证明该查询在当前设置和环境下成功，不代表下载文件、SHA256 验证、升级或回滚已经在真机完成。** V0.5.3 只修复“已是最新”但仍提示首次检查的文案及按钮强调问题，未更改代理和更新引擎。

**AX6S 真机进度（2026-11-20）**：用户已使用 `apk --no-network --allow-untrusted add /tmp/upload.apk` 安装 V0.5.3-r1（包数据库确认），但刷新 LuCI 未见菜单。这暴露出此前云端测试未覆盖的**安装后菜单/ACL 激活**缺口。用户已确认通过人工清理 LuCI 缓存并重启 rpcd/uhttpd 后菜单出现。V0.5.4 为独立 APK/IPK 构建及 OpenWrt SDK Makefile 打包均提供安装后激活钩子，并添加局部桌面导航层级隔离；这仍是代码修复候选，尚无新钩子与桌面层级修复的 AX6S 真机复测证据。V0.5.3 仍应保留作为问题复现版本。

**V0.5.4 AX6S 真机 UI 反馈（2026-11-20）**：用户已在 AX6S 的 LuCI 打开组件更新器并看到 NaiveProxy、本机架构和原生 APK 信息；但 Safari 手机截图中“组件更新”标题竖排、说明与“下载设置”重叠，向下滚动时页头挡住主体。疑似宿主对全局语义 `header` 元素设置了横向 flex / sticky；V0.5.5 将主页与设置页的组件内页头改为普通容器，显式限定布局/定位，并在恶意主题模拟浏览器回归中检查标题不换成竖排、页头不压住正文。**V0.5.5-r3 已在 AX6S 手机端实测修复，完整安装/回滚和桌面抽屉仍未验收。**

**AX6S 更新检查反馈（2026-11-20）**：设备已可联网，但 V0.5.4 实机截图中更新检查仍失败，且短暂把检查显示成安装任务；后续已从设备原始状态确认：初始检查失败由固定 16 MiB Overlay 门槛引起，具体请见下文空间预检记录。V0.5.5 候选区分检查/安装状态、补全 APK 错误提示及传输失败和 SHA256 校验失败的区别；不减弱校验门禁，仍需实机反馈。

**设置入口**：在「系统 → 组件更新」主页标题右侧点击「下载设置」即可进入；下载节点不再因为当前选择官方直连而被隐藏。设置仅更改本地 UCI 下载参数，不会自动执行安装。

在 LuCI 中完成组件版本检查、下载与 SHA256 校验、原生软件包更新、失败恢复和手动回滚。目前首个适配组件为 **NaiveProxy**；这不是固件升级器，也不允许执行任意远程命令。

> **当前状态**：管理器 IPK 与 APK 已同版本发布。AX6S APK 组件通过指定真实固件镜像、原生 APK 数据库和 ARM64 隔离环境安装/回滚测试，但**尚未完成实体 AX6S 路由器的 Flash/overlay、LuCI 浏览器和 PassWall 实际流量验收**。RC 不等于稳定版，不等于所有 OpenWrt/APK 固件都兼容。

## 知识库与规则

- [中文知识库源目录](wiki-src/Home.md) · [GitHub Wiki](https://github.com/wekingchen/luci-app-component-updater/wiki)
- [AI / 人类开发规则](AGENTS.md) · [文档治理与事实等级](docs/project-governance.md) · [Wiki 首次同步和授权](docs/wiki-initialization.md)
- [兼容与真实固件证据](docs/ax6s-apk-compatibility.md) · [AX6S 真机验收待办](docs/ax6s-hardware-acceptance-checklist.md)
- [质量验收门禁](docs/acceptance-gates.md) · [V0.5.5 手机/桌面可读性与操作验收](docs/product-ui-acceptance.md)
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

**诊断修复包编号**：V0.5.5-r1 仅为早期页面布局候选；包含 AX6S 检查状态/错误诊断修复的后续包标记为 **V0.5.5-r2**，避免用同一个版本号覆盖不同二进制。尚未完成 AX6S 检查成功的真机验收。

**2026-11-20 AX6S 空间预检真机定位**：实机状态 `check_state=unsupported`、`check_message=Insufficient space for APK backup`，其 `/tmp` 可用 115.9 MiB、`/etc` 所在 overlay 可用 12.3 MiB，之前共用的 `space_ok` 写死要求 overlay ≥16 MiB，因此在请求 GitHub 之前提前退出。V0.5.5-r3 候选改为 APK 专用空间预算：从已核验的 Release 元数据读取新旧 APK 字节数，检查阶段在 tmpfs 预下载并验证候选 APK、仅解包到 /tmp 测量真实 ELF 大小；预算覆盖持久恢复包、新包缓存、新旧 ELF 较大者与预留空间，并在安装前复查。去掉未供回滚使用的重复 `naive-old`，旧候选复用受验证硬链接，保留全量 APK 恢复及 config/world 校验。**12.3 MiB 不保证必然足够，只有动态预算满足才开放安装，真实硬件写入/回滚仍待验证。**

**V0.5.5-r3 真机回报（2026-11-21）**：AX6S / iPhone Safari 页面页头、滚动布局、GitHub 下载设置及“正在检查”状态均已正常显示；官方 Release 标签 `v154.0.8037.49-5` 成功查询，动态预算提示需至少约 16 MiB Overlay，实机只有 12.3 MiB，安全禁用安装。**仍未执行实机下载更新和回滚，也未完成桌面固件导航抽屉复测。**

**V0.5.5-r4 界面收尾候选**：将 `storage_limited` 的短暂提示从绿色成功色改为黄色警告（不影响正常检查成功与失败红色样式）；底部显示完整 `v0.5.5-r4` 管理器版本；同步两种打包格式和浏览器警告场景测试。AX6S 空间腾挪由设备管理员另行处理，不改动路由器服务或 Overlay 配置。

**V0.5.6-r1 预验收开发版**：新增 AX6S 原生 APK 管理器网页上传、SHA256/包身份/安装目录校验、后台升级及独立的上一版管理器离线恢复。首次从 SSH 安装的旧版通常没有原始包缓存，需要额外上传同版本的旧 APK 建立恢复基线；此后只上传新版。管理器恢复目录与 NaiveProxy 备份目录隔离，管理器只保存一份上一版完整包。此功能尚未完成 AX6S 实机更新/恢复，不应当作稳定版。

回滚数量与清理安全策略详见 [备份保留和空间占用](docs/backup-retention.md)。
