# V0.1 组件更新器验收门禁（必须逐级通过）

状态定义：`NOT_TESTED`（未测）/ `PASS` / `FAIL` / `BLOCKED`。GitHub Actions 的绿灯**不等于**路由器兼容或代理功能验收。

## G0 — 单元、模拟设备与发布包校验（自动化必过）

每个 push / PR 必须完成：

1. `python3 -m unittest discover -s tests -v`。对损坏的 SHA256、错误架构、错误版本、压缩包多余文件、旧预案残留、计划过期、符号链接目标、并发更新、未完成事务及回滚执行负向测试。
2. `shellcheck -S warning`、`sh -n`、LuCI JS 解析、JSON 定义/ACL 合法性检查。
3. 生成 `all.ipk`，验证 `ar` 布局、脚本执行权限、ACL、菜单与前端文件。
4. 测试只使用隔离的临时目录与本地 GitHub 响应/下载文件模拟。**禁止**测试脚本读写设备原生 `/usr/bin/naive` 或连接真实代理。
5. 失败立即阻止候选 IPK 进入推荐下载位置。

## G1 — 真实官方发布包与 GitHub Release 构建（自动化必过）

1. 查询官方稳定版 Release 并验证每个官方资产自带的 SHA256 digest。
2. 两个 OpenWrt ARM64 目标：`aarch64_cortex-a53`、`aarch64_generic`。
3. 使用 UPX 5.2.1 `--lzma --best`；`upx -t`、解压往返字节完全相同、ELF e_machine、大小检查。
4. `tools/validate_artifacts.py --manifest dist/manifest.json`：所有 tar.xz 与 Manifest SHA256 匹配；归档仅允许目标二进制和 METADATA.json；原始来源和压缩后哈希一致。
5. 工作流**只能**发布 `--prerelease` 候选。CI Artifacts 和预发布 Release 是两个不同的验收状态。
6. 发布后再从 GitHub Releases 下载公开的同名文件，复验哈希和 Archive；发布失败或缺文件时设备端只能显示“云端未就绪”。

## G2 — 软件安装与前端验收（双真机必过）

- [ ] GL-MT3600BE 原厂 4.x 定制 OpenWrt 21.02，`aarch64_cortex-a53`：IPK 依赖安装成功；LuCI 菜单可见、手机/桌面界面、rpcd/ACL 方法工作。
- [ ] Phicomm N1 OpenWrt/LEDE 24.10.x，`aarch64_generic`：同上。
- [ ] 只读状态准确显示 `naive --version`、opkg 包登记版本和完整上游 Tag（历史手工安装时应显示“未知”，不能猜测）。
- [ ] `component-updaterctl check` 在“最新已准备好”、“官方已更新但预压缩未发布”、“GitHub 连接失败”三种情况均区分显示，且无旧预案可误用。
- [ ] 已存在的新版本必须无需现场调用 GitHub Actions 即可下载。

## G3 — 安装与回滚事务（双真机必过）

**执行前先确保有物理/独立备用管理通路，不能通过唯一运行中的代理进行唯一远程验收。**

- [ ] 下载完成、哈希/二进制版本验证和备份完整之前，`/usr/bin/naive` 的 SHA256/权限/路径不变。
- [ ] 下载失败、错误架构、低磁盘空间、包结构篡改、版本不符，均拒绝替换且原代理不断线。
- [ ] 原子替换后版本和哈希准确，且不改变 `/tmp/etc/passwall/bin/naive -> /usr/bin/naive` 关系。
- [ ] 原有 PassWall 进程不自动重启；UI 分开显示“文件更新”和“正在运行进程版本切换”状态。
- [ ] 用户执行回滚可恢复更新前 SHA256、文件执行权限及旧 receipt；`opkg` 版本数据库不被篡改。
- [ ] 模拟更新中断/重启后，`recovery_required` 标记存在，新的安装被阻止；旧二进制可恢复。
- [ ] 多次点击更新、重复更新、同时回滚不能导致交错写入或备份覆盖。
- [ ] 回滚失效或不可判断的异常必须明显提示，不能伪报成功。

## G4 — 正式推荐门禁（暂未满足）

1. 签名 Manifest + 设备端固定公钥验签（当前只有 SHA256，不能等同认证来源）。
2. GL-MT3600BE 与 N1 各完成 G2/G3 验收，并保留检查结果、实际设备固件信息与日志。
3. 使用正式打包工具链及两种固件的依赖检查；确认安装后 rpcd/LuCI 兼容。
4. 无 P0/P1 未解决问题，才允许将版本从预发布提升到正式稳定 Release；无人值守**自动安装不纳入首版**。

## 用户体验 / 更新时效

- GitHub Actions 在 **默认分支**每 20 分钟检查一次官方新版本，已经存在相同完整构建 Tag 的 Release 直接跳过，**不重复 UPX**。
- LuCI `检查更新` 只读取官方版本与已经准备好的预压缩 Release，不会启动云端压缩任务。
- 官方已经更新但候选文件还没发布：显示 `pending`，禁用安装按钮；原版本不受影响，稍后重查。
- 新版可用以后：用户点击安装只需下载已打包资源、校验、备份和替换；下载时长取决于 GitHub 网络状况。
- 实际延迟 = 下次定时发现的等待 + Actions 排队/压缩/上传 + GitHub Releases 传播。20 分钟只是检查间隔，不是对总延迟的保证；GitHub 的 schedule 可能推迟甚至被丢弃。
- Actions 的定时工作流只会在默认分支运行，**开发 PR 不会激活自动定时发布**。

## 更新前只读检测命令

```sh
component-updaterctl status
component-updaterctl check
component-updaterctl plan
ubus -v list component-updater
opkg status naiveproxy | grep -E '^(Package|Version|Architecture|Status):'
ls -l /usr/bin/naive /tmp/etc/passwall/bin/naive 2>/dev/null
```

在 G0/G1 完成但 G2/G3 尚未通过时，必须标记为开发测试版本，不建议刷入生产环境执行替换操作。
