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

此策略不能代替存储配额。未来管理器自我更新若增加单独的管理器恢复包，应采用
**独立目录、默认最多一份、容量预检、不可与 NaiveProxy 混算、恢复期间不清理**
的策略，不得把新管理器备份直接混入 NaiveProxy 恢复目录。

## 只读检查

```sh
du -sk /etc/component-updater/backups/naiveproxy /etc/component-updater/installed 2>/dev/null
ls -lah /etc/component-updater/backups/naiveproxy 2>/dev/null
df -h /etc /tmp
```

在 AX6S 等小 Overlay 设备上，若需要进一步降低历史数量，必须同时评估可恢复链、
`apk` 包数据库和缓存占用，不建议通过 SSH 直接手动删除有引用的恢复目录。
