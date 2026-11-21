# 组件更新器 · 本地恢复备份与空间策略

## 当前实现与空间影响

NaiveProxy 的恢复文件存放在 `/etc/component-updater/backups/naiveproxy/`。
`/etc/component-updater/installed/naiveproxy.json` 记录当前安装的回滚入口。
原生 APK 还使用 `/etc/component-updater/installed/naiveproxy-active.apk`
保存当前已验证的安装包，供后续离线更新或恢复。该文件不是第三份可直接选择的历史恢复点。

- 正常完成一轮安装后，最多保留 **两个经收据引用的历史备份目录**。LuCI
  的“恢复上一个版本”仍只按当前收据选择目标，而非开放任意历史版本。
- 对 APK，在同一 Overlay 文件系统上复用硬链接，不为同一份旧包生成多份完整拷贝。
  硬链接的多个目录项不代表多个独立的数据块；不要简单按 `ls -lh` 大小相加。
- 对 IPK，将旧二进制封装为 `previous.ipk`。备份与正在使用的新二进制都会占用
  Overlay，因此 **有数量上限不代表固定兆字节上限**。
- 下载候选和安装任务的工作目录位于 `/tmp/component-updater`（tmpfs）。
  重启会清除这些临时内容，但不会清除持久化恢复备份。

## 防误删门禁

删除旧目录时，先读取当前收据的 `previous_backup`，再读取该备份
`receipt.json` 可能引用的上一层。该逻辑对 APK 与 OPKG 通用。

1. 遇到 `/etc/component-updater/transaction.json` 未完成事务，**完全停止自动清理**。
2. 当前回滚引用格式异常或其目录缺失，**保留所有目录以供人工修复**。
3. 如果更早的上上级目录已被历史上限正常清除，只保留当前有效回滚，不因此冻结清理。
4. 仅清理固定备份根目录下、目录名仅含数字和连字符且非符号链接的孤立目录。
5. 安装完成、确认恢复完成，以及未进入持久事务的失败任务退出时，才允许执行清理。
   安装或恢复失败且存在事务标记时，绝不清理。

此策略不能代替存储配额。**V0.5.6 已实现管理器自升级的独立恢复目录**，最多保留一份上一版本；不得把管理器备份混入 NaiveProxy 目录，也不得在存在未完成事务时清理。

## 只读检查

```sh
du -sk /etc/component-updater/backups/naiveproxy /etc/component-updater/installed 2>/dev/null
ls -lah /etc/component-updater/backups/naiveproxy 2>/dev/null
df -h /etc /tmp
```

在 AX6S 等小 Overlay 设备上，若需要进一步降低历史数量，必须同时评估可恢复链、
`apk` 包数据库和缓存占用，不建议通过 SSH 直接手动删除有引用的恢复目录。

## 管理器 APK 自我更新（V0.5.6）

独立于 NaiveProxy 目录，使用 `/etc/component-updater/manager/` 保存最多一个管理器历史恢复包及当前已验证 APK 缓存。上传包固定暂存 `/tmp/component-updater-manager-*.apk`，只允许从 LuCI 指定路径导入，严格校验文件摘要、包名、架构及安装文件路径，拒绝任意 APK/命令。首次更新须上传与当前安装版本一致的旧 APK，保障恢复可用。背景 worker 在 `/tmp` 执行，安装时禁用包内脚本，校验结果持久可观察；更新成功再单独重载 rpcd/uhttpd，绝不主动重启 PassWall。

自我更新属于高权限功能，SHA256 与包名检查不等于独立代码签名；本地文件来源的可信度须由上传者判断。AX6S 实机已完成 V0.5.6-r3 → 仅供测试 r4 → r3 的管理器自升级及手动回滚，配置保留且任务终态正常；这不等于已测试异常写入、受控断电或运行中的代理流量。

## 2026-11-21 AX6S V0.5.6-r1 → r2 事故复盘（历史故障）

> 以下是 r1/r2 期间发生时的现场证据及修复要求。**后续 r3→测试 r4→r3 已完成实体 AX6S 正常更新及回滚验收**，详情见 [真机验收记录](ax6s-hardware-acceptance-checklist.md)；仍不能据此推断真实断电/故障自动恢复。

用户通过 LuCI 网页提交管理器自升级，浏览器停留在“后台任务已提交”且不自动更新；手动刷新后被登出，输入原密码时 LuCI 返回“无效的用户名或密码”。随后用户重启后恢复登录，**原 root 密码未改变**。

来自设备日志的实证：
- `/tmp/component-updater-manager/state.json` 为 `completed`，无 `/etc/component-updater/manager/transaction.json` 未完成事务；
- 原生 APK DB 显示 `luci-app-component-updater 0.5.6-r2`，安装日志有 `Upgrading ... (0.5.6-r1 -> 0.5.6-r2)` 与 `OK`，因此安装确实成功；
- LuCI `dispatcher.uc` 在当晚记录连续的 `failed login`，但重启后原密码可用，**无法支持“升级器修改了密码”的推断**；
- 当前 AX6S 上 `/etc/init.d/rpcd restart` 返回 `Command failed: Not found`，进程检查未显示独立 `rpcd` 进程；`ubus -S list session` 仍返回 `session`。不能假定该 ImmortalWrt 构建支持标准 rpcd init-service 重启；
- 旧版后台 worker 不管升级成功或失败都会尝试重启 `rpcd` 与 `uhttpd`，并且 JS 轮询吞掉所有请求错误。这两项均为确定的代码缺陷。与登录异常的因果关系有较强嫌疑，但尚缺事故发生时的实时服务日志，不能声称已证明唯一根因；
- `apk` 在保留原 UCI 文件的情况下新增 `/etc/config/component-updater.apk-new`，属配置冲突副本，并非密码文件，不能当作登录故障原因。

修复方向：管理器原生自升级**绝不主动重启 rpcd/uhttpd**，后台轮询反馈成功状态和持续认证错误，保持配置、密码和代理服务不变。任何新版本的物理 AX6S 实机升级/回滚必须重新验证 LuCI 会话及重新登录；不以隔离 chroot 回归代替此验收。此句是当时的修复门禁，后续 PR #19 已合并，V0.5.6 以限定设备范围正式发布；自动发布后续新版本的保护门禁仍保留。

只读核查上一版恢复包：

```sh
ls -lh /etc/component-updater/manager/previous/previous.apk 2>/dev/null
cat /etc/component-updater/manager/previous/version 2>/dev/null
sha256sum /etc/component-updater/manager/previous/previous.apk 2>/dev/null
cat /etc/component-updater/manager/previous/previous.sha256 2>/dev/null
```

## V0.5.6-r3 已合并修复与旧版本升级过渡限制

PR #19 提供保持 LuCI 服务会话、后台状态轮询、终态残留锁安全清理及活跃任务标记。AX6S 当前 r2 → r3 **由旧 r2 的 worker 执行安装**，故并不能证明此过程会自动刷新，也仍可能受 r2 的 rpcd/uhttpd 重启及旧锁问题影响。安装后的 r3 页面状态查询会尝试在无持久事务、无运行 worker、且锁内无活动标记的安全终态下清理旧式空锁。后续 r3 → r4 才是新 worker 的完整无感升级验收。

**验收结论（2026-11-21）**：真实 AX6S 网页升级 r3→测试 r4、网页恢复 r4→r3 均成功，`busy=false`，恢复包按预期消费，原 UCI 设置保留。V0.5.6 已公开正式版；无需为验证备份机制再重新刷机或运行 PassWall。
