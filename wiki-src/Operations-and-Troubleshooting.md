# 使用说明与常见问题

## 安装前先核对

**第一步**：确认设备原生包管理器。IPK 使用 opkg，APK 固件只使用对应的原生 APKv3 包；这两个格式不能互相重命名或强制安装。

**第二步**：阅读 [兼容性矩阵](Compatibility-and-Devices.md)。当前 APK 写入能力仅针对已适配的 AX6S 指定固件（V0.5.6 Stable 限定范围）；未知设备若显示不能更新，应保持现状并先检查诊断，**不要手工绕过保护**。

**第三步**：从 [V0.5.6 Stable 正式 Release](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.6) 获取与你设备匹配的管理包，并核验 SHA256。安装或升级前保存配置及可回滚方案。

## LuCI 操作顺序

进入「系统 → 组件更新」，核对当前版本和是否支持写入。**尚未检查时优先突出「检查官方更新」**；确认找到可安装版本后，才突出「下载并更新」；**确认已是最新版时只提供普通「重新检查更新」操作，不再提示首次检查或突出主操作**。没有本地恢复备份时，恢复按钮必须保持禁用，不允许直接进入确认对话框。若需要回退，则在确认前一次备份存在且可用时选择「恢复上一个版本」。

在 V0.5.6 正式版中，进入「系统 → 组件更新」后，直接点击页面标题右侧的「下载设置」；原先占据页面顶部的单独子菜单已隐藏，但已有设置页地址保持有效。

**历史背景（V0.5.2 迭代）**：当时的 UI 打磨候选已经被后续正式版取代。GitHub 下载设置在任何连接方式下都显示预设节点列表；选择官方直连时节点只是预存、不实际参与传输。选择文件中转或全部中转时自动使用所选节点，‘中转失败时尝试官方直连’只在中转模式下显示。具体效果仍须在 MT3600BE Safari 和 AX6S 的 LuCI 主题上核对。

**历史验证记录**：2026-11-20 MT3600BE 真机中，用户选择「版本查询与文件下载均使用中转」并成功检查官方更新；该次记录仅验证版本查询，不覆盖后续用户确认完成的 IPK 正常更新/回滚；完整下载路径与三阶段日志尚未独立归档。

「GitHub 下载设置」可以选择直连、仅文件反代或 API 与文件反代。默认直连；节点能否连通取决于当前网络，失败时应排查连接、证书及下载完整性，而不是关闭 SHA256 检查。

## 只读诊断（在对应环境具备脚本时）

opkg 路线：
~~~sh
sh /usr/libexec/component-updater/device-readonly-acceptance.sh
~~~

AX6S APK 路线：
~~~sh
sh /usr/libexec/component-updater/device-ax6s-apk-preflight.sh
~~~

不同固件可能没有该脚本或位置不同；运行前请先使用 `ls` 确认。以上是只读预检；**不代表完成安装与回滚验收**。真实安装/回滚必须事先确认恢复通路，不建议远程无人值守执行。

## AX6S 原生 APK 已安装但 LuCI 不显示（2026-11-20 实机问题）

用户已经验证 `apk --no-network --allow-untrusted --simulate add /tmp/upload.apk` 模拟成功，并用 `apk --no-network --allow-untrusted add /tmp/upload.apk` 实际安装成功，安装包数据库显示 `luci-app-component-updater 0.5.3-r1`；但直接刷新网页后没有看到「组件更新」菜单。**软件包安装成功不等于 LuCI 菜单与 rpcd ACL 成功激活**。

可先核对这些本机文件（只读）：

~~~sh
ls -l /usr/share/luci/menu.d/luci-app-component-updater.json
ls -l /usr/share/rpcd/acl.d/luci-app-component-updater.json
ls -l /www/luci-static/resources/view/component-updater/overview.js
ls -l /usr/libexec/rpcd/component-updater
~~~

文件存在后，可清理 LuCI 缓存并仅重启控制面（网页会短时断开，**不会主动重启 PassWall**）：

~~~sh
rm -f /tmp/luci-indexcache /tmp/luci-indexcache.*
rm -rf /tmp/luci-modulecache/*
/etc/init.d/rpcd restart
/etc/init.d/uhttpd restart
~~~

随后退出 LuCI、重新登录，打开「系统 → 组件更新」或尝试直接访问 `/cgi-bin/luci/admin/system/component-updater`。如果仍然没有菜单或直达页面报 403/404，必须读取实际菜单文件、ACL 和 LuCI 日志再定位，不能盲目将问题归因于缓存。

V0.5.4 修复候选复用一套 IPK/APKv3 post-install 脚本，并通过隔离 mock 服务测试缓存清理与 rpcd/uhttpd 重启。这属于 2026-11-20 的历史故障；2026-11-21 AX6S 用户已使用修复后的页面完成 NaiveProxy 正常更新与回滚。

## 管理器网页自升级及回滚（V0.5.6-r3）

在已适配的 AX6S 中，通过 LuCI 上传同名管理器的原生 APK 候选包，先核对包身份、版本、SHA256 与本机恢复基线，再启动自升级。若首次从 SSH 安装旧版且没有旧管理器恢复包，应先按页面提示上传当前版本包建立基线；不要自行跳过恢复保护。

2026-11-21 已在实体 AX6S 上验证 `r3 → r4（仅供回归测试）→ r3` 网页升级/手动回滚，升级和回滚后 `busy=false` 且 UCI 配置保留。建议日常保留 r3，**r4 仅测试回归，不是新产品版**。从 r2 升到 r3 的首次动作仍由 r2 旧后台程序执行，可能需要重新登录或手工处理旧版遗留锁；r3 起的新后台程序已通过此次验证。

只读检查可使用：

~~~sh
apk list --installed --manifest luci-app-component-updater
/bin/sh /usr/libexec/component-updater/manager-self-update.sh status
uci show component-updater
~~~

回滚成功后 `job_state=rolled_back`、`recovery_required=false`、`busy=false` 为正常；`recovery_available=false` 可能只是本轮上一版恢复包已被消耗，不应误判为失败。该能力仅针对**管理器自身**；NaiveProxy 的**正常**升级及手动回滚也已在真机单独通过（见下一节），但断电及异常恢复仍待测试。

## AX6S NaiveProxy 原生 APK 真机升级/回滚验收

2026-11-21 实体 AX6S 上已在 LuCI 完成 `naiveproxy 154.0.8037.49.5-r1 → r3 → r1`，升级任务为 `completed`，回滚任务为 `rolled_back`。升级后的二进制 SHA256 为 `fb19517f2738b131e23c6e49a30d246bf69a2cef835b37c7b6ae82c2168715da`；回滚后是原版 `94a9d2ebce92b2fd877e1e7019dbfa09a7bb7a5d481ec593bd34b5d5abd2a861`。配置和 `/etc/apk/world` 三次 SHA256 均一致。用户当前停留在原厂 r1，无须为此次验收再次升级。

~~~sh
apk list --installed --manifest naiveproxy
sha256sum /usr/bin/naive /etc/config/naiveproxy /etc/apk/world
/usr/sbin/component-updaterctl status
~~~

回滚后 `rollback_available=false` 表示当前已恢复到此前备份版本；上游版本号仍为 `154.0.8037.49`，r1/r3 是同一官方版本的不同本地包修订。本次设备并未运行 PassWall，`runtime_processes=0` 属于预期，不能声称已验证运行中进程或代理流量。当前 `check_state=ready` 与 `ready=false` 同时出现，源于缓存的旧检查状态仍在，实际更新计划已清除、按钮正确禁用；这是待后续修复的状态一致性问题，不要为消除文案而绕过备份/校验保护。

## 常见问题

- **没有新版？** 云端组件包是提前构建并验证的；官方版本已更新但 CI 还未生成候选时，不会在路由器现场压缩。
- **按钮禁用？** 通常是设备不兼容、正在执行、没有可用计划或恢复包不满足条件。应看界面中文提示和日志，不能通过修改 JS 强启。
- **下载失败？** 检查 GitHub 连通、代理模式、域名、SHA256 与 TLS；预设代理地址并非永久可用保证。
- **更新后 PassWall 还是旧版？** 运行中的旧进程可能继续使用旧代码，先检查包数据库与实际程序版本，不要直接重启造成网络中断。
- **OTA/刷其他固件后还能自动更新？** 不一定。APK 原始文件与包数据库校验可能变化，需重新适配并验收。

[安全与恢复](Security-and-Recovery.md) · [首页](Home.md)
