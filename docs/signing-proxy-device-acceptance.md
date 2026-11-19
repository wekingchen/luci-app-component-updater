# 签名、GitHub 反代与双设备真机验收

## 可信签名：必须由管理员完成密钥初始化

V0.1 安装事务只接受通过 **usign (Ed25519)** 验证的 Manifest。原始发布文件的 SHA256 存在 Manifest 中；反代无法绕过验签。

1. 在可信电脑离线运行（不要在路由器上生成）：`usign -G -s component-updater.sec -p trust.pub -c "Component Updater Release Key"`
2. **仅将公钥** `trust.pub` 放进仓库 `luci-app-component-updater/root/usr/share/component-updater/trust.pub` 并提交 PR。通过 IPK 固定部署，不从下载服务器动态信任新公钥。
3. 私钥保存在安全位置；将 `base64 < component-updater.sec | tr -d '\\n'` 的结果作为仓库 Settings → Secrets and variables → Actions 的 `COMPONENT_USIGN_PRIVATE_KEY_B64`。不要将原始私钥上传 GitHub 文件或发送到对话。
4. 从主分支运行通用 `Component Builder / Official Releases & UPX` 工作流，签名 `manifest.json` 生成 `manifest.json.sig`，在发布前使用仓库固定公钥执行 `usign -V`。
5. 无公钥、无 usign、签名缺失、签名校验失败、发布资产被篡改均拒绝生成安装预案。

**签名能力已编码，但签名密钥不由项目自动生成或托管**。在公钥和 GitHub Secret 未由管理员配置之前，不能发布正式可安装更新。签名密钥丢失需要在受控更新器版本中进行公钥轮换，不能通过不可信远程清单替换。

## GitHub 反代

在 **系统 → 组件更新 → GitHub 下载设置** 选择：
- 关闭（默认）：直接访问 GitHub 官方 API 和 Releases。
- 仅下载包：官方 API 直接查询，Releases 文件、Manifest 及签名经自定义 HTTPS 前缀。
- 查询与下载：查询和文件都经自定义 HTTPS 前缀。

采用 `https://mirror.example/` 前缀约定，最终地址为 `https://mirror.example/https://github.com/... `。这不是任意 HTTP 代理，不支持用户名密码、HTTP 或本地地址；反代失败后是否直接连接 GitHub 由独立开关控制。

反代只能改善下载连接，不能作为供应链信任根。若反代将清单或文件改动，签名或 SHA256 校验必须失败；不能退回无签名模式。

## 两台设备的验收

- GL-MT3600BE / 定制 21.02 / aarch64_cortex-a53：检查已有 LuCI JS、rpcd executable plugin、usign、UCI 和 opkg，留存完整安装和回滚报告。
- N1 / LEDE 24.10 / aarch64_generic：重复同一套验收，不因为架构同属 ARM64 而跳过。
- 在安装 IPK 后运行 `sh scripts/device-readonly-acceptance.sh`（只读）。此脚本不重启服务、不下载新程序、不修改 `/usr/bin/naive`。
- 桌面/手机分别打开 LuCI，核对组件列表、反代配置、版本字段和 ACL 权限。只读脚本不能代替 UI 交互验收。
- 确认有物理或独立 LAN 管理方式后，明确设置 `COMPONENT_ACCEPT_LIVE=I_UNDERSTAND`，运行 `sh scripts/device-live-acceptance.sh --install-and-rollback`。此脚本真实替换并回滚当前程序，**不自动重启 PassWall**，失败时必须保留现场和日志。
- 若官方最新与当前二进制完全一致，或云端签名产物尚未就绪，应记录 **NOT_TESTED**，不能称为成功验收。

### G0-G4 发布判定

G0 单元与 Shell/JS、代理边界；G1 双架构真实上游压缩 + usign 测试；G2 每台设备 LuCI/rpcd 只读测试；G3 每台设备真实更新及回滚；G4 签名密钥已部署、全部日志与代理功能回归验证。**G2/G3/G4 尚未拿到两台真机报告前，禁止宣称生产可用。**

