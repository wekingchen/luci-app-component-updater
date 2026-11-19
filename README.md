# luci-app-component-updater

OpenWrt 通用应用更新平台，首个适配程序 **NaiveProxy**。通用 GitHub Actions 提前下载官方稳定版并使用 UPX 5.2.1 `--lzma --best` 压缩，然后生成**OpenWrt 原生 gzip(tar) 格式 opkg IPK**，分架构发布到 Releases。

## 设备与边界

- GL-MT3600BE：GL.iNet 4.x 定制 OpenWrt 21.02，`aarch64_cortex-a53`
- Phicomm N1：LEDE/OpenWrt 24.10，`aarch64_generic`
- 当前仅支持已由 **opkg** 安装、且只拥有 `/usr/bin/naive` 一个文件的 `naiveproxy` 软件包。其他程序未来需新增适配器和组件定义，不接收任意 Shell 命令。
- 不更新固件、不替换 PassWall 设置、不主动重启 PassWall；旧的正在运行的进程可能要待服务下次重载才能使用新文件。

## 更新流程

```text
components/*.json
      |
通用 Actions：官方 Release + SHA256 → UPX → ELF / 往返测试
      |
按架构生成 naiveproxy_<version>_<arch>.ipk + manifest.json
      |
GitHub Release（提前发布）
      |
LuCI：官方版本 → Release API digest → 下载并校验 Manifest / IPK
      |
备份当前文件与 opkg 元数据 → 生成本地回滚 IPK → opkg install
      |
验证实际二进制版本、SHA256、opkg Version → 保存记录
```

官方 Tag `v154.0.8037.49-5` 对应 package `154.0.8037.49.5-r3`，其中最后一位 `5` 保留官方修订，`-r3` 标识我们的包构建修订。原先手工复制 NaiveProxy 到 `/usr/bin/naive` 不会更新软件包数据库；现在通过 `opkg install` 正常升级，解决这个问题。

更新前生成由当前二进制和当前 opkg 版本/架构/依赖组成的本地恢复 IPK。回滚通过 `opkg install --force-downgrade --force-reinstall` 恢复之前的二进制哈希和 opkg 记录。原先手动覆盖过二进制的旧状态，在回滚后仍可能呈现不同的实际程序版本与 opkg Version，这是对更新前状态的忠实恢复。IPK 更新可能触发原包已有的维护脚本，设备实测前不能保证代理连接绝对无中断。

## GitHub 反代

V0.2.2 预置四个可选的 GitHub HTTPS 下载代理：`gh-proxy.org`、`ghproxy.cc`、`ghproxy.com`、`ghfast.top`，并保留自定义前缀输入。只对固定的 GitHub 资源进行代理；预设 URL 自动拼接完整原始地址，例如 `https://gh-proxy.org/https://github.com/.../releases/download/...`。默认关闭反代，推荐「仅下载文件」模式以保持 GitHub API 校验信息直连。

**注意：预设不是在线可用性承诺。** 各代理节点可能被部分网络封禁、限流或停止服务，尤其 `ghproxy.cc`、`ghproxy.com` 仅作为备用选项。选择「API + 文件」必须信任代理，因为代理也会影响 SHA256 校验信息。旧版只配置 `github_proxy_prefix` 的设备升级后继续沿用旧自定义地址。


LuCI → 系统 → 组件更新 → GitHub 下载设置：

- **关闭（默认）**：全部走 GitHub 官方域名；
- **仅下载文件**：官方 Release API 直连，Manifest 与 IPK 走 HTTPS 反代；
- **API + 文件**：查询与下载均经 HTTPS 反代；只有在信任该反代服务时使用。
- 失败直连回退可单独开关。路由器侧不需要 UPX，也不需要管理签名私钥。

不采用独立 usign 签名，但下载仍对比 GitHub Release API 提供的各资产 `digest`，校验 Manifest 和 IPK SHA256。**哈希不是数字签名**：如果代理同时伪造 GitHub API 和文件，或仓库发布权限被入侵，无法提供端到端真实性保证。因此首版仅手动确认安装，不开启无人值守更新。

## 开发与验收

发布门禁会使用 SHA256 固定的官方 OpenWrt 21.02.5 和 24.10.5 rootfs，运行两代真正的 opkg：从旧版安装、升级、同版本强制重装，再降级恢复并核对 SHA256 与 opkg 数据库版本；这并不等于 GL/N1 定制固件真机已经验证。

```sh
python3 -m unittest discover -s tests -v
python3 tools/component_builder.py --component naiveproxy --dry-run
python3 tools/component_builder.py --component naiveproxy --output dist
python3 tools/validate_artifacts.py --manifest dist/manifest.json
python3 tools/package_ipk.py --out dist
```

通用构建工作流预先发布两个设备架构的 NaiveProxy 原生 IPK；LuCI 更新时**不会等待现场 UPX 压缩**。默认分支已经启用定时提前构建；本轮 r3 开发候选仍留在 Draft PR，不会从 PR 发布生产 Release。

### 真机只读检查

安装测试版 LuCI IPK 后：

```sh
sh /usr/libexec/component-updater/device-readonly-acceptance.sh
```

真实安装/回滚测试需要备用管理通道、签署明确确认，并在两台设备分别执行：

```sh
COMPONENT_ACCEPT_LIVE=I_UNDERSTAND sh /usr/libexec/component-updater/device-live-acceptance.sh --install-and-rollback
```

详见 [验收门禁](docs/acceptance-gates.md) 和 [GitHub 反代 / 回滚细节](docs/signing-proxy-device-acceptance.md)。**CI 成功不代表两台真机已经验收。**
