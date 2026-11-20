# 使用说明与常见问题

## 安装前先核对

**第一步**：确认设备原生包管理器。IPK 使用 opkg，APK 固件只使用对应的原生 APKv3 包；这两个格式不能互相重命名或强制安装。

**第二步**：阅读 [兼容性矩阵](Compatibility-and-Devices.md)。当前 APK 写入能力仅为特定 AX6S 固件的 RC 适配；未知设备若显示不能更新，应保持现状并先检查诊断，**不要手工绕过保护**。

**第三步**：从 [管理器 V0.5.0 RC1 Release](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.0-rc1) 获取与你设备匹配的管理包，并核验 SHA256。安装或升级前保存配置及可回滚方案。

## LuCI 操作顺序

进入「系统 → 组件更新」，核对当前版本和是否支持写入。**尚未检查时优先突出「检查官方更新」**；确认找到可安装版本后，才突出「下载并更新」；**确认已是最新版时只提供普通「重新检查更新」操作，不再提示首次检查或突出主操作**。没有本地恢复备份时，恢复按钮必须保持禁用，不允许直接进入确认对话框。若需要回退，则在确认前一次备份存在且可用时选择「恢复上一个版本」。

在最新版候选中，进入「系统 → 组件更新」后，直接点击页面标题右侧的「下载设置」；原先占据页面顶部的单独子菜单已隐藏，但已有设置页地址保持有效。

V0.5.2 是未公开发布的 UI 打磨候选。GitHub 下载设置在任何连接方式下都显示预设节点列表；选择官方直连时节点只是预存、不实际参与传输。选择文件中转或全部中转时自动使用所选节点，‘中转失败时尝试官方直连’只在中转模式下显示。具体效果仍须在 MT3600BE Safari 和 AX6S 的 LuCI 主题上核对。

2026-11-20 MT3600BE 真机记录：用户选择「版本查询与文件下载均使用中转」并成功检查官方更新；文件下载与 SHA256 校验尚未实测。

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

V0.5.4 修复候选复用一套 IPK/APKv3 post-install 脚本，并通过隔离 mock 服务测试缓存清理与 rpcd/uhttpd 重启。**固件真机 UI 尚未验收通过，暂不进行 NaiveProxy 实机更新。**

## 常见问题

- **没有新版？** 云端组件包是提前构建并验证的；官方版本已更新但 CI 还未生成候选时，不会在路由器现场压缩。
- **按钮禁用？** 通常是设备不兼容、正在执行、没有可用计划或恢复包不满足条件。应看界面中文提示和日志，不能通过修改 JS 强启。
- **下载失败？** 检查 GitHub 连通、代理模式、域名、SHA256 与 TLS；预设代理地址并非永久可用保证。
- **更新后 PassWall 还是旧版？** 运行中的旧进程可能继续使用旧代码，先检查包数据库与实际程序版本，不要直接重启造成网络中断。
- **OTA/刷其他固件后还能自动更新？** 不一定。APK 原始文件与包数据库校验可能变化，需重新适配并验收。

[安全与恢复](Security-and-Recovery.md) · [首页](Home.md)
