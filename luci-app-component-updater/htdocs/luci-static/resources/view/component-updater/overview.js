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

return view.extend({
    handleSave: null,
    handleSaveApply: null,
    handleReset: null,

    load: function() {
        return Promise.all([getStatus(), getPlan()]);
    },

    val: function(value) {
        return value || '—';
    },

    row: function(label, value) {
        return E('div', {style: 'display:flex;align-items:center;justify-content:space-between;gap:1em;padding:0.6em 0;border-bottom:1px solid var(--border-color-low, #d8d8d8);'}, [
            E('span', {'class': 'text-muted'}, label),
            E('strong', {style: 'overflow-wrap:anywhere;text-align:right'}, this.val(value))
        ]);
    },

    notify: function(result) {
        if (!result)
            return;
        var msg = result.message || result.error || '操作已提交';
        ui.addNotification(null, E('p', {}, msg), result.status === 'error' ? 'danger' : 'info');
    },

    renderContent: function(status, plan) {
        status = status || {};
        plan = plan || {};
        var ready = plan.ready === 'true';
        var progress = status.job_state || 'idle';
        var jobBusy = ['downloading', 'verifying', 'backing_up', 'installing', 'queued'].indexOf(progress) >= 0;
        var checkState = status.check_state || '';
        var checkMessage = status.check_message || '';
        var currentTag = status.installed_upstream_tag || '未记录（历史手动安装）';
        var official = status.official_tag || '尚未检查';
        var version = status.installed_version || '未检测';
        var self = this;
        var section = E('div', {'class':'cbi-section', style:'padding:1em;border:1px solid var(--border-color-low, #ddd);border-radius:12px'}, [
            E('div', {style:'display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:1em'}, [
                E('div', {}, [E('h3', {style:'margin:0'}, 'NaiveProxy'), E('small', {}, '官方来源：klzgrad/naiveproxy')]),
                E('span', {'class':'label'}, ready ? '压缩更新已就绪' : (jobBusy ? '更新中' : (checkState === 'pending' ? '云端压缩准备中' : (checkState === 'signature_error' ? '签名验证失败' : (checkState === 'trust_unconfigured' ? '缺少可信签名配置' : (checkState === 'error' ? '检查失败' : '等待检查'))))))
            ]),
            this.row('实际程序版本', version),
            this.row('官方最新 Release', official),
            this.row('本工具安装的完整版本', currentTag),
            this.row('opkg / apk 记录', status.package_version),
            this.row('设备软件架构', status.architecture),
            this.row('GitHub 反代', status.github_proxy_mode === 'off' ? '关闭（直连）' : (status.github_proxy_mode === 'assets' ? '仅下载包' : '查询与下载')),
            this.row('可信签名', status.signing_status === 'configured' ? '公钥及 usign 已配置' : '缺少可信公钥或 usign，禁止安装'),
            this.row('运行中 NaiveProxy 进程', status.runtime_processes),
            this.row('当前任务状态', progress),
            this.row('最近检查结果', checkMessage),
            checkState === 'pending' ? E('p', {'class':'description'}, '云端正在等待预压缩产物发布。页面保持打开时每 5 分钟自动复查一次；当前程序继续正常运行。') : E('span'),
            status.job_message ? E('p', {'class':'alert-message'}, status.job_message) : E('span'),
            E('p', {'class':'description'}, 'GitHub Actions 在云端预先压缩并发布；点击更新不会现场等待压缩。如果发现官方新版但尚无候选包，此页显示准备中，稍后重新检查即可。'),
            E('p', {'class':'description',style:'margin-top:1em'}, '更新仅替换已备份的 /usr/bin/naive；不修改 opkg 数据库，不自动重启 PassWall。原有进程可能仍在使用旧版本。'),
            E('div', {style:'display:flex;flex-wrap:wrap;gap:0.6em;margin-top:1em'}, [
                E('button', {'class':'btn cbi-button cbi-button-action', disabled:jobBusy, click:function(){self.handleCheck();}}, '检查官方更新'),
                E('button', {'class':'btn cbi-button cbi-button-positive', disabled:!ready || jobBusy, click:function(){self.confirmInstall();}}, '下载并更新'),
                E('button', {'class':'btn cbi-button cbi-button-neutral', disabled:jobBusy, click:function(){self.confirmRollback();}}, '恢复上一个版本')
            ])
        ]);
        var extra = E('div', {'class':'cbi-section', style:'margin-top:1.5em'}, [
            E('h3', {}, '安装预案'),
            this.row('构建来源', 'wekingchen/luci-app-component-updater'),
            this.row('构建版本', plan.build_tag || '尚未获取'),
            this.row('下载资源', plan.filename || '尚未获取'),
            E('p', {'class':'description'}, 'GitHub Actions 对官方二进制执行 UPX --lzma --best；由云端每 20 分钟轮询官方版本（调度可能延迟）。安装前必须验证 usign/Ed25519 签名、SHA256 和程序可执行性；真机代理功能需要单独验收。')
        ]);
        return [section, extra, E('p', {}, E('a', {href: L.url('admin/system/component-updater/settings')}, 'GitHub 反代及下载设置'))];
    },

    refresh: function() {
        var self = this;
        return Promise.all([getStatus(), getPlan()]).then(function(data) {
            if (self.page)
                dom.content(self.page, self.renderContent(data[0], data[1]));
            // Pending is a cloud-side build, not a local job. Recheck only once
            // per five minutes while the page stays open (avoid API polling spam).
            if (data[0] && data[0].check_state === 'pending' &&
                Date.now() - (self.lastPendingCheck || 0) >= 300000) {
                self.lastPendingCheck = Date.now();
                return check().then(function() {
                    return Promise.all([getStatus(), getPlan()]);
                }).then(function(next) {
                    if (self.page)
                        dom.content(self.page, self.renderContent(next[0], next[1]));
                }).catch(function() { /* next manual check will show the error */ });
            }
        });
    },

    handleCheck: function() {
        var self = this;
        self.lastPendingCheck = Date.now();
        return check().then(function(result) {
            self.notify(result);
            return self.refresh();
        }).catch(function(err) { ui.addNotification(null, E('p', {}, String(err)), 'danger'); });
    },

    confirmInstall: function() {
        var self = this;
        ui.showModal('确认更新 NaiveProxy', [
            E('p', {}, '本操作会备份并替换 /usr/bin/naive。正在运行的 PassWall 进程不会被自动重启。若通过 opkg 安装，软件包数据库版本仍可能保持旧值。'),
            E('div', {'class':'right'}, [
                E('button', {'class':'btn', click:ui.hideModal}, '取消'),
                ' ',
                E('button', {'class':'btn cbi-button-positive', click:function(){
                    ui.hideModal();
                    start().then(function(r) {self.notify(r);return self.refresh();}).catch(function(err){self.notify({status:'error',message:String(err)});});
                }}, '确认安装')
            ])
        ]);
    },

    confirmRollback: function() {
        var self = this;
        ui.showModal('恢复旧版', [
            E('p', {}, '从上次受本工具管理的备份恢复 NaiveProxy 二进制。运行中的 PassWall 不会自动重启。'),
            E('div', {'class':'right'}, [
                E('button', {'class':'btn', click:ui.hideModal}, '取消'),
                ' ',
                E('button', {'class':'btn cbi-button-negative', click:function(){
                    ui.hideModal();
                    rollback().then(function(r){self.notify(r);return self.refresh();}).catch(function(err){self.notify({status:'error',message:String(err)});});
                }}, '确认恢复')
            ])
        ]);
    },

    render: function(data) {
        this.page = E('div', {}, this.renderContent(data[0], data[1]));
        poll.add(this.refresh.bind(this), 5);
        return E('div', {}, [
            E('h2', {}, '组件更新'),
            E('p', {}, '通用组件更新引擎 · V1.0 首批支持 NaiveProxy'),
            this.page
        ]);
    }
});
