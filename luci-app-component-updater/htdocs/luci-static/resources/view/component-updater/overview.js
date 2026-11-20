'use strict';
'require view';
'require rpc';
'require ui';
'require poll';
'require dom';

var getStatus = rpc.declare({object: 'component-updater', method: 'status'});
var check = rpc.declare({object: 'component-updater', method: 'check'});
var getPlan = rpc.declare({object: 'component-updater', method: 'plan'});
var start = rpc.declare({object: 'component-updater', method: 'start'});
var rollback = rpc.declare({object: 'component-updater', method: 'rollback'});

var BUSY_STATES = ['queued', 'downloading', 'verifying', 'backing_up', 'installing'];
var CHECK_TEXT = {
    'Verified native IPK is available for manual installation': '安装包已通过校验，可安全发起手动更新。',
    'Installed native IPK matches the latest official build': '当前安装版本与官方最新构建一致。',
    'Official update found; native IPKs are being prepared': '发现官方新版，云端正在生成适配安装包。',
    'Published manifest digest not ready': '云端正在发布校验清单，请稍后重试。',
    'Native IPK digest not ready': '云端正在发布安装包校验信息，请稍后重试。',
    'Official GitHub API unavailable': '无法连接官方发布接口，请检查网络或下载设置。',
    'Unexpected official release tag': '官方发布版本格式异常，已停止更新。',
    'Unsupported release version format': '暂不支持这个版本格式，未执行安装。',
    'Published release tag mismatch': '发布版本信息不一致，已停止更新。',
    'Invalid release digest': '发布文件摘要异常，已停止更新。',
    'Manifest download / GitHub API digest mismatch': '校验清单与官方摘要不一致，已停止更新。',
    'Manifest identity mismatch': '安装清单中的组件信息不一致，已停止更新。',
    'Native IPK architecture/version mismatch': '安装包与设备架构或目标版本不匹配。',
    'Invalid asset SHA256': '安装包校验值格式异常，已停止更新。',
    'Release API and manifest digest disagree': '安装包校验结果不一致，已停止更新。',
    'Previous update must be restored first': '上一轮更新尚未恢复，请先执行版本恢复。',
    'This version requires opkg': '当前系统未提供所需的软件包管理工具。',
    'Unsupported OpenWrt architecture': '当前设备架构尚未获得支持。',
    'Existing naive binary is missing or symlinked': '未找到符合要求的现有程序文件。',
    'naiveproxy must already be installed through opkg': '需要先通过系统软件包管理器安装 NaiveProxy。',
    'Missing installed libgcc1 runtime dependency; no package changes made': '缺少必要运行依赖，未修改设备上的任何软件包。',
    'Insufficient tmp or overlay space': '临时空间或系统可写空间不足，未执行安装。',
    'Native IPK installation started': '安装任务已启动，完成后状态将自动更新。',
    'Native IPK installation queued': '安装任务已加入队列。',
    'Downloading verified native IPK': '正在下载安装包。',
    'Installing native IPK via opkg; PassWall will not be restarted by this updater': '正在安装，更新器不会主动重启 PassWall。',
    'Native IPK installed; existing PassWall processes not restarted': '安装完成；已运行的 PassWall 进程不会被主动重启。',
    'Install failed; previous native IPK restored': '安装未成功，已恢复更新前的版本。',
    'Version mismatch; original IPK restored': '安装后校验未通过，已恢复旧版本。',
    'IPK installed but receipt writing failed; recover from backup': '安装记录写入异常，请使用版本恢复功能处理。',
    'Previous opkg package and file content restored': '上一版本的软件包与程序文件已恢复。',
    'Previous native package restored; PassWall not restarted': '上一版本已恢复；PassWall 未被主动重启。',
    'Previous IPK transaction needs manual rollback': '存在未完成的更新事务，请先恢复旧版本。',
    'Already updating': '已有更新任务正在运行。',
    'Check for updates before installing': '请先检查更新，再执行安装。',
    'Verified native APK is ready for manual installation': '原生 APK 安装包已通过校验，可以手动更新。',
    'Installed native APK matches latest official binary': '当前 APK 已是官方最新版本。',
    'Cloud APK package is being prepared': '云端正在生成并验证原生 APK 安装包。',
    'APK installation failed; previous package restored': 'APK 更新失败，已自动恢复上一版本。',
    'APK install failed; recovery files retained': 'APK 更新失败，恢复文件已保留，请检查日志。',
    'Original APK version and configuration restored': '上一版本及原有配置均已恢复。',
    'Native APK package ownership or installed firmware does not match the verified AX6S baseline': '当前软件包文件或设备环境与经过验证的 AX6S 基线不匹配，已禁止安装。',
    'Native APK firmware requires a verified APK package and rollback workflow; no changes made': '已识别 APK 软件包环境；原生 APK 更新与回滚尚未完成验收，未修改任何文件。',
    'libgcc1 must already be installed': '缺少必要的运行依赖。',
    'Insufficient space for APK backup': 'Overlay 持久空间不足，无法安全保存 APK 恢复包；未开始安装。',
    'Cannot determine safe APK storage budget': '无法可靠计算 APK 更新所需空间，已禁止安装。',
    'Previous APK transaction must be recovered first': '上一次 APK 更新事务尚未完成，请先恢复。',
    'Unsupported official release version': '官方版本格式不符合当前适配规则，已停止检查。',
    'APK release identity mismatch': 'APK 发布版本标识不一致，已拒绝继续更新。',
    'Missing APK manifest checksum': 'APK 发布信息缺少校验清单 SHA256，已拒绝更新。',
    'APK manifest download failed': '无法下载 APK 校验清单。请检查 GitHub 文件下载连接或中转设置。',
    'APK manifest hash mismatch': 'APK 校验清单 SHA256 不匹配，已拒绝更新。',
    'APK manifest platform mismatch': 'APK 校验清单与当前设备或固件平台不匹配。',
    'APK baseline recovery identity mismatch': 'APK 原厂恢复包身份校验不通过，已拒绝更新。',
    'Invalid native APK SHA256': 'APK 文件摘要格式异常，已拒绝更新。',
    'APK asset digest does not match Release API': 'APK 下载包摘要与发布接口不一致，已拒绝更新。',
    'Insufficient temporary space for APK verification': '临时空间不足，无法预检 APK 安装包。',
    'APK recovery asset size unavailable': '无法取得原版恢复包的实际大小，已停止检查。',
    'APK candidate asset size unavailable': '无法取得新版 APK 的实际大小，已停止检查。',
    'APK candidate download failed': '新版 APK 下载失败，请检查 GitHub 文件下载连接或中转设置。',
    'APK candidate hash mismatch': '新版 APK 文件 SHA256 校验不通过，已拒绝更新。',
    'APK candidate size mismatch': '新版 APK 大小与官方发布信息不一致，已拒绝更新。',
    'APK candidate extraction or binary verification failed': '无法安全检查新版 APK 的 ELF 内容或校验值，已拒绝更新。',
    'Insufficient overlay capacity for APK recovery': 'Overlay 空间不足以完成安全更新与恢复，安装没有继续。',
    'APK candidate size changed since check': 'APK 安装包大小与检查时不一致，已停止安装。',
    'APK binary size changed since check': '新版程序大小与检查时不一致，已停止安装。',
    'Cloud APK package is being prepared': '尚未取得对应 APK 发布信息，可能仍在准备或连接异常，请稍后重试。',
    'Check for verified APK update before installing': '安装前必须先完成 APK 更新检查。',
    'Update in progress': '已有更新任务执行中，请勿重复操作。'
};
var JOB_TEXT = {
    idle: '当前没有正在执行的任务。',
    queued: '更新任务正在排队。',
    downloading: '正在下载经过校验的安装包。',
    verifying: '正在校验安装文件。',
    backing_up: '正在备份旧版本。',
    installing: '正在安装新版本。',
    completed: '最近一次安装已完成。',
    rolled_back: '旧版本已经恢复。',
    failed: '最近一次更新失败，请检查状态后重试。',
    recovery_required: '上一轮更新需要恢复旧版本。'
};
var PROXY_LABELS = {
    'gh-proxy.org': '预设节点一',
    'ghproxy.cc': '预设节点二',
    'ghproxy.com': '预设节点三',
    'ghfast.top': '预设节点四'
};

return view.extend({
    handleSave: null,
    handleSaveApply: null,
    handleReset: null,

    load: function() {
        return Promise.all([getStatus(), getPlan()]);
    },

    val: function(value, fallback) {
        if (value === undefined || value === null || value === '' || value === 'not-installed')
            return fallback || '暂无数据';
        return String(value);
    },

    isBusy: function(status) {
        return BUSY_STATES.indexOf(status.job_state) >= 0 || !!this.operationBusy;
    },

    isCurrent: function(status) {
        return status.check_state === 'up_to_date' ||
            (!!status.official_tag && !!status.installed_upstream_tag &&
                status.official_tag === status.installed_upstream_tag);
    },

    messageText: function(message, fallback) {
        if (!message)
            return fallback || '操作已提交。';
        if (CHECK_TEXT[message])
            return CHECK_TEXT[message];
        // Backend diagnostics are in English. Never leak their raw text into
        // the UI; preserve those details in system logs for troubleshooting.
        return fallback || '操作已结束；如需排查，请查看系统日志。';
    },

    noteForResult: function(result) {
        result = result || {};
        var status = result.status || '';
        var failure = ['error', 'failed', 'unsupported', 'recovery_required', 'unavailable'].indexOf(status) >= 0;
        var missing = !status;
        var fallback = missing ? '设备没有返回有效的操作结果。请查看检查状态或诊断信息。' :
            failure ? '操作没有成功，请查看检查原因或系统日志。' :
            status === 'up_to_date' ? '当前已是最新版本，无需重新安装。' :
            status === 'pending' ? '当前云端版本暂不可确认，可稍后重新检查。' :
            status === 'storage_limited' ? '已查到官方版本，但 Overlay 空间不足，无法安全安装。' :
            status === 'rolled_back' ? '上一版本已恢复。' :
            status === 'busy' ? '已有任务正在运行，请勿重复操作。' :
            '操作已提交，页面会自动更新进度。';
        return {error: failure || missing, warning: status === 'storage_limited',
            text: this.messageText(result.message || result.error, fallback)};
    },

    notify: function(result) {
        this.notice = this.noteForResult(result);
        this.repaint();
    },

    renderNotice: function() {
        var self = this;
        if (!this.notice)
            return null;
        return E('div', {'class': 'cu-notice' +
            (this.notice.error ? ' is-error' : this.notice.warning ? ' is-warning' : ''),
            role: this.notice.error ? 'alert' : 'status'}, [
            E('div', {'class': 'cu-notice-text'}, this.notice.text),
            E('button', {'class': 'cu-notice-dismiss', type: 'button', 'aria-label': '关闭提示',
                click: function() { self.notice = null; self.repaint(); }}, '×')
        ]);
    },

    row: function(label, value) {
        return E('div', {'class': 'cu-property'}, [
            E('span', {'class': 'cu-property-label'}, label),
            E('strong', {'class': 'cu-property-value'}, this.val(value))
        ]);
    },

    proxyLabel: function(status) {
        if (status.github_proxy_mode === 'off' || !status.github_proxy_mode)
            return '官方直连';
        var site = status.github_proxy_site || 'custom';
        var node = site === 'custom' ? '自定义节点' : (PROXY_LABELS[site] || '预设节点');
        return node + (status.github_proxy_mode === 'assets' ? ' · 仅文件下载' : ' · 查询和下载');
    },

    statusModel: function(status, plan) {
        var checkState = status.check_state || '';
        var jobState = status.job_state || 'idle';
        if (status.package_manager === 'apk' && status.compatibility !== 'ax6s-apk-native')
            return status.compatibility === 'ax6s-apk-readonly' ?
                {tone:'warn', label:'适配预检', title:'已识别红米 AX6S', description:'当前固件采用原生 APK 软件包。管理界面与只读诊断可用；完整安装、备份和回滚尚未通过验证，更新操作暂时锁定。'} :
                {tone:'error', label:'暂不支持', title:'当前 APK 环境未适配', description:'已识别 APK 软件包管理器，但设备不属于已知 AX6S 环境。不会执行 IPK 安装。'};
        if (jobState === 'recovery_required' || checkState === 'recovery_required')
            return {tone:'error', label:'需要恢复', title:'上一次更新需要处理', description:status.rollback_available === 'true' ? '检测到未完成的更新事务，请先恢复旧版本。' : '存在未完成的更新事务，但未找到本地恢复包；请查看诊断，不要重复安装。'};
        if (this.operationBusy && this.operationKind === 'check' && BUSY_STATES.indexOf(jobState) < 0)
            return {tone:'warn', label:'正在检查', title:'正在检查官方更新', description:'正在核对官方版本、设备环境和安装包校验信息。'};
        if (this.isBusy(status))
            return {tone:'warn', label:'更新进行中', title:'正在处理更新任务', description:BUSY_STATES.indexOf(jobState) >= 0 ?
                JOB_TEXT[jobState] : '正在提交更新操作，请勿重复点击。'};
        if (jobState === 'failed')
            return {tone:'error', label:'更新失败', title:'本次安装未成功', description:JOB_TEXT.failed};
        if (checkState === 'error' || checkState === 'unsupported')
            return {tone:'error', label:'检查未通过', title:'暂时无法更新', description:this.messageText(status.check_message, '检查失败，请确认设备环境及网络配置。')};
        if (checkState === 'storage_limited') {
            var required = Number(status.overlay_required_kib);
            var available = Number(status.overlay_available_kib);
            var detail = isFinite(required) && isFinite(available) && required > 0 && available >= 0 ?
                '至少需要 ' + Math.ceil(required / 1024) + ' MiB 的空闲 Overlay，当前约 ' +
                (available / 1024).toFixed(1) + ' MiB。' : '';
            return {tone:'warn', label:'空间不足', title:'已查到官方版本，但暂不能安装',
                description:detail + '为保留完整离线回滚能力，更新器不会在空间不足时写入固件。'};
        }
        if (this.isCurrent(status))
            return {tone:'ok', label:'已是最新版本', title:'组件已保持最新', description:'当前安装版本与已检查的官方版本一致，无需重复安装。'};
        if (checkState === 'pending')
            return {tone:'warn', label:'云端准备中', title:'新版正在准备', description:'发现官方新版本，预压缩安装包尚未发布。当前程序可继续正常使用。'};
        if (plan.ready === 'true' || plan.ready === true)
            return {tone:'ok', label:'可以更新', title:'新版本已准备就绪', description:'安装包已完成匹配及完整性校验，可以手动更新。'};
        if (jobState === 'rolled_back')
            return {tone:'muted', label:'已恢复旧版', title:'旧版本已恢复', description:'建议检查现有服务是否运行正常，再决定是否重新检查更新。'};
        return {tone:'muted', label:'等待检查', title:'尚未检查更新', description:'先检查官方版本与设备架构，确认有可安装的软件包后再更新。'};
    },

    renderContent: function(status, plan) {
        status = status || {};
        plan = plan || {};
        var self = this;
        var state = this.statusModel(status, plan);
        var busy = this.isBusy(status);
        var isApk = status.package_manager === 'apk';
        var apkGuard = isApk && status.compatibility !== 'ax6s-apk-native';
        var current = state.label === '已是最新版本';
        var ready = !apkGuard && (plan.ready === 'true' || plan.ready === true) && !this.isCurrent(status);
        var canRollback = !apkGuard && status.rollback_available === 'true';
        var extraRows = [
            this.row('已安装软件包', status.package_version),
            this.row('设备架构', status.architecture),
            this.row('软件包管理器', isApk ? '原生 APK' : 'opkg'),
            this.row('下载连接', this.proxyLabel(status))
        ];
        var hero = E('section', {'class': 'cu-hero', 'aria-label': '组件更新状态'}, [
            E('div', {'class': 'cu-heading-row'}, [
                E('div', {'class': 'cu-identity'}, [
                    E('div', {'class': 'cu-symbol', 'aria-hidden': 'true'}, 'N'),
                    E('div', {}, [
                        E('div', {'class': 'cu-name'}, 'NaiveProxy'),
                        E('div', {'class': 'cu-subname'}, '官方项目 · klzgrad/naiveproxy')
                    ])
                ]),
                E('span', {'class': 'cu-status' + (state.tone === 'warn' ? ' is-warn' : state.tone === 'error' ? ' is-error' : state.tone === 'muted' ? ' is-muted' : '')}, state.label)
            ]),
            E('h3', {'class': 'cu-headline'}, state.title),
            E('p', {'class': 'cu-lead'}, state.description),
            E('div', {'class': 'cu-versions', 'aria-label': '版本比较'}, [
                E('div', {'class': 'cu-version-block'}, [
                    E('span', {'class': 'cu-version-label'}, '当前程序版本'),
                    E('strong', {'class': 'cu-version-value'}, this.val(status.installed_version, '未检测'))
                ]),
                E('div', {'class': 'cu-version-block'}, [
                    E('span', {'class': 'cu-version-label'}, '官方最新版本'),
                    E('strong', {'class': 'cu-version-value'}, this.val(status.official_tag, '尚未检查'))
                ])
            ]),
            E('div', {'class': 'cu-actions' + (ready ? ' is-ready' : current ? ' is-current' : '')}, [
                E('button', {'class': 'cu-btn cu-btn-check', type: 'button', disabled: (busy || apkGuard) ? true : null,
                    click: function() { return self.handleCheck(); }}, current ? '重新检查更新' : '检查官方更新'),
                E('button', {'class': 'cu-btn cu-btn-update', type: 'button', disabled: (!ready || busy || apkGuard) ? true : null,
                    click: function() { return self.confirmInstall(); }}, '下载并更新'),
                E('button', {'class': 'cu-btn cu-btn-rollback', type: 'button', disabled: (busy || !canRollback) ? true : null,
                    click: function() { return self.confirmRollback(); }}, '恢复上一个版本')
            ]),
            E('p', {'class': 'cu-action-hint', role: 'status'}, apkGuard ? '当前固件未通过兼容性检测，更新与恢复均不可用。' :
                busy ? (this.operationKind === 'check' && BUSY_STATES.indexOf(status.job_state) < 0 ?
                    '正在检查官方更新，请勿重复点击。' : '正在执行操作，请勿重复点击。') :
                ready ? '已找到适配安装包。确认后才会开始更新。' :
                current ? (canRollback ? '已核对官方最新版本，无需重复安装。如有需要，可恢复已备份的上一版本。' : '已核对官方最新版本，无需重复安装。当前没有可用的旧版备份。') :
                canRollback ? '请先检查官方更新；已有旧版备份可供恢复。' :
                '先检查官方更新；没有有效备份时无法恢复上一版本。'),
            E('p', {'class': 'cu-mini-note'}, apkGuard ? '原生 APK 环境尚未开启安装；请先通过设备兼容性验收。' :
                (isApk ? 'APK 安装前先保存完整恢复包及原配置 · 不主动重启 PassWall' :
                    '安装前自动准备恢复包 · 不主动重启 PassWall · 已运行连接可能继续使用旧进程'))
        ]);
        var overview = E('section', {'class': 'cu-panel', 'aria-label': '设备与安装信息'}, [
            E('div', {'class': 'cu-section-head'}, [
                E('h3', {}, '设备与安装信息'),
                E('span', {'class': 'cu-section-hint'}, '系统检测')
            ]),
            E('div', {'class': 'cu-property-list'}, extraRows)
        ]);
        var details = E('details', {'class': 'cu-detail'}, [
            E('summary', {}, '查看构建与诊断详情'),
            E('div', {'class': 'cu-detail-body'}, [
                this.row('固件平台', status.firmware_target || '尚未识别'),
                this.row('安装方式', isApk ? (apkGuard ? 'APK（只读）' : '系统原生 APKv3') : '系统原生 IPK · opkg'),
                this.row('运行中进程', status.runtime_processes === '' || status.runtime_processes === undefined ? '未检测' : status.runtime_processes + ' 个'),
                this.row('恢复备份', canRollback ? '已找到本地恢复包' : '未找到有效备份'),
                this.row('最近检查结果', this.messageText(status.check_message, '尚无检查记录。')),
                this.row('当前任务', JOB_TEXT[status.job_state] || '尚无任务记录。'),
                this.row('安装来源版本', status.installed_upstream_tag || '未记录'),
                this.row('构建来源', 'wekingchen/luci-app-component-updater'),
                this.row('候选构建版本', plan.build_tag || '尚未生成'),
                this.row('候选安装文件', plan.filename || '尚未生成'),
                this.row('文件校验', '官方发布摘要与 SHA-256 核对'),
                E('p', {}, '安装包在云端提前压缩并发布，设备不会现场等待压缩。检查到新版但暂无安装包时，将显示“云端准备中”，页面保持打开期间每五分钟自动复查一次。'),
                E('p', {}, '当前采用文件摘要校验，不包含独立数字签名。启用查询反代时，需要自行信任反代服务提供的校验信息。')
            ])
        ]);
        // IPK and APKv3 use different package-release suffix conventions.
        // Always show the installed manager package revision unambiguously.
        var managerBuild = status.package_manager === 'apk' ? 'v0.5.5-r4' : 'v0.5.5-4';
        var content = [];
        var notice = this.renderNotice();
        if (notice)
            content.push(notice);
        content.push(hero, overview, details,
            E('div', {'class': 'cu-footer'}, [
                E('span', {}, '组件更新器 · ' + managerBuild + ' · 原生 IPK / APK 双模式')
            ]));
        return content;
    },

    repaint: function() {
        if (!this.page)
            return;
        var open = this.page.querySelector && this.page.querySelector('details.cu-detail');
        var wasOpen = !!(open && open.open);
        dom.content(this.page, this.renderContent(this.currentStatus, this.currentPlan));
        if (wasOpen && this.page.querySelector) {
            var detail = this.page.querySelector('details.cu-detail');
            if (detail) detail.open = true;
        }
    },

    refresh: function() {
        var self = this;
        if (self.refreshInFlight)
            return self.refreshInFlight;
        self.refreshInFlight = Promise.all([getStatus(), getPlan()]).then(function(data) {
            var signature = JSON.stringify(data);
            self.currentStatus = data[0] || {};
            self.currentPlan = data[1] || {};
            if (signature !== self.lastSignature) {
                self.lastSignature = signature;
                self.repaint();
            }
            // Pending means a cloud-side build, not a local task.
            if (!self.operationBusy && self.currentStatus.check_state === 'pending' &&
                Date.now() - (self.lastPendingCheck || 0) >= 300000) {
                self.lastPendingCheck = Date.now();
                return check().then(function() {
                    return Promise.all([getStatus(), getPlan()]);
                }).then(function(next) {
                    self.currentStatus = next[0] || {};
                    self.currentPlan = next[1] || {};
                    self.lastSignature = JSON.stringify(next);
                    self.repaint();
                }).catch(function() { /* Preserve the last known status. */ });
            }
        }).then(function() { self.refreshInFlight = null; }, function(err) {
            self.refreshInFlight = null;
            self.notify({status:'error', message:String(err)});
            self.repaint();
        });
        return self.refreshInFlight;
    },

    handleCheck: function() {
        var self = this;
        if (self.isBusy(self.currentStatus || {}))
            return Promise.resolve();
        self.operationBusy = true;
        self.operationKind = 'check';
        self.repaint();
        self.lastPendingCheck = Date.now();
        return check().then(function(result) {
            self.notify(result);
        }).catch(function(err) {
            self.notify({status:'error', message:String(err)});
        }).then(function() {
            self.operationBusy = false;
            self.operationKind = null;
            self.repaint();
            return self.refresh();
        });
    },

    startAction: function(method) {
        var self = this;
        if (self.isBusy(self.currentStatus || {}))
            return Promise.resolve();
        self.operationBusy = true;
        self.operationKind = 'install';
        self.repaint();
        return method().then(function(result) {
            self.notify(result);
        }).catch(function(err) {
            self.notify({status:'error', message:String(err)});
        }).then(function() {
            self.operationBusy = false;
            self.operationKind = null;
            self.repaint();
            return self.refresh();
        });
    },

    confirmInstall: function() {
        var self = this;
        if (self.isBusy(self.currentStatus || {}) ||
            ((self.currentStatus || {}).package_manager === 'apk' &&
             (self.currentStatus || {}).compatibility !== 'ax6s-apk-native') ||
            !(self.currentPlan && (self.currentPlan.ready === 'true' || self.currentPlan.ready === true)) ||
            self.isCurrent(self.currentStatus || {}))
            return;
        ui.showModal('确认更新 NaiveProxy', [
            E('p', {}, '更新器会先备份当前版本，再通过系统软件包管理器安装已校验的安装包。不会主动重启 PassWall，但现有连接仍可能短暂受到安装过程影响。'),
            E('div', {'class': 'right'}, [
                E('button', {'class': 'btn', click: ui.hideModal}, '取消'),
                ' ',
                E('button', {'class': 'btn cbi-button-positive', click: function() {
                    ui.hideModal();
                    return self.startAction(start);
                }}, '确认更新')
            ])
        ]);
    },

    confirmRollback: function() {
        var self = this;
        if (((self.currentStatus || {}).package_manager === 'apk' &&
             (self.currentStatus || {}).compatibility !== 'ax6s-apk-native') || self.isBusy(self.currentStatus || {}) ||
             (self.currentStatus || {}).rollback_available !== 'true')
            return;
        ui.showModal('恢复上一个版本', [
            E('p', {}, '将尝试通过先前生成的恢复包还原软件包与程序文件。仅在存在有效备份时才能恢复；更新器不会主动重启 PassWall。'),
            E('div', {'class': 'right'}, [
                E('button', {'class': 'btn', click: ui.hideModal}, '取消'),
                ' ',
                E('button', {'class': 'btn cbi-button-negative', click: function() {
                    ui.hideModal();
                    return self.startAction(rollback);
                }}, '确认恢复')
            ])
        ]);
    },

    render: function(data) {
        this.currentStatus = data[0] || {};
        this.currentPlan = data[1] || {};
        this.lastSignature = JSON.stringify(data);
        this.page = E('div', {}, this.renderContent(this.currentStatus, this.currentPlan));
        poll.add(this.refresh.bind(this), 5);
        return E('div', {'class': 'cu-app'}, [
            E('link', {rel: 'stylesheet', href: L.resource('component-updater/design.css') + '?v=0.5.5-r4'}),
            E('div', {'class': 'cu-page-head'}, [
                E('span', {'class': 'cu-overline'}, '组件管理 · 安全更新'),
                E('div', {'class': 'cu-page-title-row'}, [
                    E('h2', {}, '组件更新'),
                    E('a', {'class': 'cu-page-settings', href: L.url('admin/system/component-updater/settings')}, '下载设置')
                ]),
                E('p', {}, '先检查可用更新，再决定安装；需要时可恢复已备份的版本。')
            ]),
            this.page
        ]);
    }
});
