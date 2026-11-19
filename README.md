# luci-app-component-updater

OpenWrt 通用组件更新平台：**配置驱动的 GitHub Actions 构建器 + 独立组件定义 + LuCI 设备更新器**。V0.1 首个适配组件是 NaiveProxy，其余组件按需新增，而不是复制构建工作流。

> 当前为首版开发候选（pre-release）。已完成本地 Python 单测和 IPK 打包，**尚未经过 GL-MT3600BE / Phicomm N1 的真实安装验收**。未经验证，请不要在远程唯一网络通道上执行替换。

## 目标设备

- GL.iNet GL-MT3600BE：运行 OpenWrt 21.02-SNAPSHOT 定制系统，opkg `aarch64_cortex-a53`，内核 5.4.281。
- Phicomm N1：OpenWrt/LEDE 24.10.x，`aarch64_generic`。

IPK 属于 `all` 架构。是否兼容具体固件的旧版 LuCI / rpcd，必须在设备上进一步测试。

## 架构

```text
components/*.json                  单一组件定义及架构资源规则
           │
           ├── tools/component_builder.py
           │     官方 Releases → digest 校验 → ELF → UPX → 回解校验
           │     → manifest.json / tar.xz / 来源哈希
           │
           └── device adapter (V0.1 NaiveProxy)
                 ├── /usr/sbin/component-updaterctl
                 ├── /usr/libexec/rpcd/component-updater
                 ├── LuCI 原生 JS 页面
                 └── 备份 / 原子替换 / 手动回滚
```

## GitHub Actions

- **Component Updater / CI & IPK**：单测、Shell/JS 静态检查、通用 `all.ipk` 构建，PR 会运行。CI Artifacts 中可获取安装包。
- **Component Builder / Official Releases & UPX**：每 20 分钟检查最新官方 Release，也可手动执行。上游未变化且已有同名 Release 时跳过。对 NaiveProxy 提取两个 OpenWrt ARM64 官方资源，严格验证 GitHub Release 中的 `digest`，使用 UPX **5.2.1** `--lzma --best` 压缩、`upx -t` 校验及解压往返字节比较，生成包含双架构资源的 `manifest.json`。首次构建只代表基础验证，不代表通过设备真实代理连接测试。

以后增加程序，应提供新 `components/<id>.json`，构建器当前已有配置化来源、架构、解包、压缩/不压缩支持；若新程序运行协议、软件包管理或服务健康检查不同，则新增适配器。V0.1 的设备更新器只允许 NaiveProxy，不会执行任意组件提供的 Shell 指令。

### 手动本地测试

```sh
python3 -m unittest discover -s tests -v
python3 tools/component_builder.py --component naiveproxy --dry-run
python3 tools/component_builder.py --component naiveproxy --output dist
python3 tools/package_ipk.py --out dist
```

后两项涉及 GitHub 外部网络；`package_ipk.py` 可离线运行。正式软件包也可用根目录内 `luci-app-component-updater/Makefile` 在 OpenWrt SDK 构建。

## 设备端

安装开发版 IPK 后可使用：

```sh
component-updaterctl status
component-updaterctl check
component-updaterctl plan
component-updaterctl start
component-updaterctl status
component-updaterctl rollback
```

LuCI → 系统 → 组件更新。设备端需要可用的 GitHub HTTPS、CA 证书以及支持 xz 的 tar 命令；若条件不满足应报错，不会强制安装依赖或跳过校验。

### MT3600BE 已知安装方式

- `/usr/bin/naive` 由 opkg naiveproxy 软件包登记。
- PassWall 的 `/tmp/etc/passwall/bin/naive` 为指向 `/usr/bin/naive` 的符号链接。
- 用户手动用 UPX 压缩并覆盖后，**`naive --version` 与 `opkg status naiveproxy` 不同属正常情况**。
- 更新器只修改持久化二进制文件，不更新 `opkg` 的版本数据库；只显示真实版本和本工具记录的完整上游 Tag。更新后不会重启 PassWall，旧运行进程可能继续使用旧 inode。

## 安全边界

- 固定可信的上游仓库和构建仓库，不接受浏览器传入的任意 URL、执行路径、组件 ID 或命令参数。
- 校验官方资产 SHA256、设备下载资产 SHA256、二进制 SHA256、实际可执行版本；更新前必须有可读备份与磁盘空间。
- 固定主程序路径 `/usr/bin/naive`，不跟随其软链接写入，临时文件在目标目录创建并通过 `mv` 替换。
- 安装与回滚不会主动重启 PassWall 或修改节点配置。
- **重要：首版 Manifest 尚未启用独立密码学签名，校验哈希用于完整性，并不能防御构建仓库发布权限遭到入侵。** 正式稳定版需要可信公钥验证和签名发布门禁；在此之前保持手动更新、无自动安装。
- GitHub Actions 流水线及 IPK 构建与路由器真机兼容、代理实际功能测试是不同等级的验收，不能等同。

## 扩展组件

参照 `components/naiveproxy.json` 定义版本来源、资源匹配、归档成员、架构和压缩策略。构建器支持 `.tar.xz`、`.tar.gz`、`.zip` 源文件、`upx` 与 `none` 策略；设备端新增安装适配器仍需要人工审查，不允许直接执行组件配置中的任意程序。

## 自动化单元测试与实机验收门禁

详见 [`docs/acceptance-gates.md`](docs/acceptance-gates.md)。G0 离线单元与模拟路由器事务测试、G1 真实官方 Release 构建与产物验证均必须完成，G2/G3 需要 MT3600BE、N1 各自实机验收，G4 才允许正式稳定发布。CI 通过并不表示已经通过真机。

**体验：路由器点击“更新”不会现场等待 UPX。** 默认分支的定时 Actions 提前发现上游版本（每 20 分钟检查一次，GitHub 可能延迟），压缩并发布候选；若尚未完成则显示 `pending`，不可更新。查看官方最新版本与下载可安装的最新构建是两个不同的状态。

## 进度

- [x] 空仓库初始化、通用构建器、NaiveProxy 定义、两目标构建矩阵
- [x] LuCI 页面、rpcd Shell 兼容接口、基本安装回滚事务
- [x] 离线单元测试、IPK 组包
- [x] GitHub Actions 两个 ARM64 官方文件实际 UPX 5.2.1 压缩成功（仅基础验证）
- [ ] MT3600BE / N1 真机安装、服务验证及断电恢复测试
- [ ] 独立签名 Manifest、公钥固定及正式稳定发布
