'use strict';
'require view';
'require rpc';
'require ui';
'require poll';
'require dom';

var statusCall = rpc.declare({object:'component-updater',method:'manager_status'});
var uploadCall = rpc.declare({object:'component-updater',method:'manager_upload',
    params:['kind','sha256','size']});
var checkCall = rpc.declare({object:'component-updater',method:'manager_check'});
var startCall = rpc.declare({object:'component-updater',method:'manager_start'});
var rollbackCall = rpc.declare({object:'component-updater',method:'manager_rollback'});

var JOB = {
    queued:'后台任务已提交，正在准备更新。',
    backing_up:'正在保存当前管理器的恢复包。',
    installing:'正在安装新管理器，请不要关闭设备电源。',
    restoring:'正在恢复上一个管理器版本。',
    completed:'管理器升级已完成。',
    rolled_back:'上一版本已恢复。',
    recovery_required:'恢复操作需要人工处理，请保留所有文件。',
    failed:'最近一次操作未完成，请检查日志。'
};
var MESSAGES = {
    'Upload current version APK for offline rollback':'首次网页更新必须上传当前管理器 APK 作为恢复包。',
    'Insufficient Overlay for manager backup and upgrade':'Overlay 空间不足，无法同时保存升级包和上一版恢复包。',
    'Unsupported manager APK identity or payload':'上传的文件不是符合限制的管理器 APK，已拒绝安装。',
    'Manager plan invalid':'已核验的安装计划不可用，请重新校验。',
    'Manager task started':'后台安装任务已启动，页面会自动刷新。',
    'Manager upgrade completed; one rollback archive retained':'升级成功，已保留一份上一版本恢复包。'
};
return view.extend({
    handleSave:null,
    handleSaveApply:null,
    handleReset:null,
    busy:false,
    planReady:false,
    notice:null,
    lastResult:null,
    load:function() { return statusCall(); },
    response:function(result) {
        result = result || {};
        this.lastResult = result.status || '';
        this.notice = MESSAGES[result.message] || ({
            ready:'新版已通过检查，可确认安装。',
            requires_previous:'请先上传与你当前安装版本完全相同的 APK 作为恢复包。',
            prepared:'文件校验和包内容检查已通过。',
            started:'后台任务已启动，连接暂时中断是正常的。',
            storage_limited:'空间不足，已禁止安装。',
            rolled_back:'已恢复到上一版本。',
            error:'操作未成功，未执行安装。'
        }[result.status] || '操作已结束，请查看下方状态。');
        this.planReady = result.status === 'ready';
        this.repaint();
    },
    refresh:function() {
        var self=this;
        return statusCall().then(function(s) {
            self.currentStatus=s || {};
            self.repaint();
        }).catch(function() {
            // rpcd and uhttpd intentionally restart after a self-upgrade.
            // Preserve the UI and retry through the existing poll interval.
        });
    },
    upload:function(kind) {
        var self=this;
        if (this.busy || this.currentStatus.busy === 'true' ||
            this.currentStatus.recovery_required === 'true')
            return Promise.resolve();
        var path=kind==='previous' ?
            '/tmp/component-updater-manager-current.apk' :
            '/tmp/component-updater-manager-new.apk';
        this.busy=true;
        this.repaint();
        return ui.uploadFile(path).then(function(info) {
            if (!info || !/^[a-f0-9]{64}$/.test(info.sha256sum || '') ||
                !Number.isSafeInteger(info.size) || info.size < 1024 || info.size > 10485760)
                throw new Error('上传响应缺少可信 SHA256 或文件大小异常。');
            return uploadCall(kind,info.sha256sum,info.size);
        }).then(function(result) {
            self.response(result);
            return self.refresh();
        }).catch(function(err) {
            self.notice=String(err).indexOf('cancel')>=0 ? '已取消上传。' :
                '文件上传或校验失败，请重新选择 APK。';
            self.planReady=false;
        }).then(function() {
            self.busy=false;
            self.repaint();
        });
    },
    check:function() {
        var self=this;
        if (this.busy) return Promise.resolve();
        this.busy=true;
        this.repaint();
        return checkCall().then(function(result) {
            self.response(result);
            return self.refresh();
        }).catch(function() {
            self.notice='检查没有完成，请确认设备 RPC 服务正常。';
        }).then(function() {
            self.busy=false;
            self.repaint();
        });
    },
    begin:function(action) {
        var self=this;
        if (this.busy) return Promise.resolve();
        this.busy=true;
        this.planReady=false;
        this.repaint();
        return action().then(function(result) {
            self.response(result);
            return self.refresh();
        }).catch(function() {
            self.notice='启动请求暂时中断。管理器可能正在重启 LuCI，请查看任务状态。';
        }).then(function() {
            self.busy=false;
            self.repaint();
        });
    },
    confirmUpdate:function() {
        var self=this;
        if (!this.planReady || this.busy) return;
        ui.showModal('确认更新管理器',[
            E('p',{},'将安装你主动上传并校验的本地 APK。此包没有独立发布签名；SHA256 只能确认上传前后内容一致，不能证明开发者身份。请仅使用你信任的编译产物。'),
            E('p',{},'执行期间 LuCI 与 rpcd 会短暂重新启动，NaiveProxy 和 PassWall 不会由此功能主动重启。上一版 APK 将保留供离线恢复。'),
            E('div',{'class':'right'},[
                E('button',{'class':'btn',click:ui.hideModal},'取消'),' ',
                E('button',{'class':'btn cbi-button-positive',click:function() {
                    ui.hideModal(); return self.begin(startCall);
                }},'确认安装')
            ])
        ]);
    },
    confirmRollback:function() {
        var self=this;
        if (this.busy || this.currentStatus.recovery_available !== 'true') return;
        ui.showModal('确认恢复管理器',[
            E('p',{},'将使用唯一保留的上一版 APK 进行离线恢复，随后重新加载 LuCI。不会修改 NaiveProxy 的版本恢复目录。'),
            E('div',{'class':'right'},[
                E('button',{'class':'btn',click:ui.hideModal},'取消'),' ',
                E('button',{'class':'btn cbi-button-negative',click:function() {
                    ui.hideModal(); return self.begin(rollbackCall);
                }},'确认恢复')
            ])
        ]);
    },
    renderBody:function() {
        var self=this;
        var s=this.currentStatus || {};
        var working=this.busy || s.busy==='true';
        var supported=s.status==='ok';
        var recover=s.recovery_available==='true';
        var need=s.recovery_required==='true';
        return [
            E('section',{'class':'cu-panel cu-manager-panel'},[
                E('div',{'class':'cu-section-head'},[
                    E('h3',{},'管理器更新'),
                    E('span',{'class':'cu-section-hint'},'仅限当前管理器')
                ]),
                E('p',{'class':'cu-manager-intro'},'直接从 LuCI 上传我们编译的原生 APK，并在安装前完成检查。不会修改系统原有的软件包管理页面。'),
                E('div',{'class':'cu-property-list'},[
                    E('div',{'class':'cu-property'},[
                        E('span',{'class':'cu-property-label'},'当前管理器'),
                        E('strong',{'class':'cu-property-value'},s.installed_version || '尚未检测')
                    ]),
                    E('div',{'class':'cu-property'},[
                        E('span',{'class':'cu-property-label'},'恢复包'),
                        E('strong',{'class':'cu-property-value'},recover?'已保留上一版本':'暂无恢复包')
                    ]),
                    E('div',{'class':'cu-property'},[
                        E('span',{'class':'cu-property-label'},'当前包缓存'),
                        E('strong',{'class':'cu-property-value'},s.current_archive==='true'?'已保存':'首次升级需补充')
                    ]),
                    E('div',{'class':'cu-property'},[
                        E('span',{'class':'cu-property-label'},'任务状态'),
                        E('strong',{'class':'cu-property-value'},JOB[s.job_state] || '没有正在执行的任务')
                    ])
                ]),
                this.notice ? E('div',{'class':'cu-notice '+
                    (this.lastResult==='storage_limited'?'is-warning':
                     this.lastResult==='error'?'is-error':'')},
                    E('div',{'class':'cu-notice-text'},this.notice)) : null,
                E('div',{'class':'cu-manager-actions'},[
                    E('button',{'class':'cu-btn cu-btn-check',disabled:working||!supported||need,
                        click:function(){return self.upload('candidate');}},'上传新版 APK'),
                    E('button',{'class':'cu-btn cu-btn-rollback',disabled:working||!supported||need,
                        click:function(){return self.upload('previous');}},'上传当前版恢复 APK'),
                    E('button',{'class':'cu-btn cu-btn-check',disabled:working||!supported||need,
                        click:function(){return self.check();}},'校验安装包'),
                    E('button',{'class':'cu-btn cu-btn-update',disabled:working||!this.planReady||need,
                        click:function(){self.confirmUpdate();}},'确认后安装'),
                    E('button',{'class':'cu-btn cu-btn-rollback',disabled:working||!recover,
                        click:function(){self.confirmRollback();}},'恢复上一版')
                ]),
                E('p',{'class':'cu-mini-note'},'首次网页更新前，若当前管理器没有本地安装包缓存，必须上传完全相同版本的旧 APK 用于离线回滚。此后每次升级自动保存最新包，历史只保留一个可恢复版本。'),
                E('p',{'class':'cu-mini-note'},'上传文件暂存在 /tmp；恢复文件存放于 /etc/component-updater/manager，独立于 NaiveProxy 的恢复目录。')
            ])
        ];
    },
    repaint:function() {
        if (this.body) dom.content(this.body,this.renderBody());
    },
    render:function(data) {
        this.currentStatus=data || {};
        this.body=E('div',{},this.renderBody());
        poll.add(this.refresh.bind(this),5);
        return E('div',{'class':'cu-app cu-manager'},[
            E('link',{rel:'stylesheet',href:L.resource('component-updater/design.css')+'?v=0.5.6-r1'}),
            E('div',{'class':'cu-page-head'},[
                E('a',{'class':'cu-back',href:L.url('admin/system/component-updater')},'‹ 返回组件更新'),
                E('span',{'class':'cu-overline'},'管理器维护 · 原生 APK'),
                E('div',{'class':'cu-page-title-row'},E('h2',{},'管理器更新')),
                E('p',{},'网页内完成管理器安装与版本恢复，不影响 NaiveProxy 更新流程。')
            ]),
            this.body
        ]);
    }
});
