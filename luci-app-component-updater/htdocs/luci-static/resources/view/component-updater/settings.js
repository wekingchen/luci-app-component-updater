'use strict';
'require view';
'require form';

return view.extend({
    render: function() {
        var m = new form.Map('component-updater', '下载连接设置',
            '选择官方直连或可信的下载中转服务。设置仅影响更新器的连接方式，不会改变 NaiveProxy 的官方来源或自动触发安装。');
        var s = m.section(form.NamedSection, 'main', 'updater', '网络连接');
        s.anonymous = true;

        var mode = s.option(form.ListValue, 'github_proxy_mode', '连接方式');
        mode.value('off', '官方直连（默认）');
        mode.value('assets', '仅下载文件使用中转（推荐）');
        mode.value('all', '版本查询与文件下载均使用中转');
        mode.default = 'off';
        mode.rmempty = false;
        mode.description = '优先使用官方直连。仅在下载文件不稳定时，建议启用“仅下载文件使用中转”。';

        var site = s.option(form.ListValue, 'github_proxy_site', '下载节点');
        site.value('gh-proxy.org', 'gh-proxy.org');
        site.value('ghproxy.cc', 'ghproxy.cc（备用）');
        site.value('ghproxy.com', 'ghproxy.com（备用）');
        site.value('ghfast.top', 'ghfast.top');
        site.value('custom', '自定义安全地址');
        site.default = 'custom'; // Keep existing installations' custom prefix.
        site.rmempty = false;
        site.description = '节点可用性会随网络环境变化，预设节点不代表已通过实时连通性检测。';
        site.depends('github_proxy_mode', 'assets');
        site.depends('github_proxy_mode', 'all');

        var prefix = s.option(form.Value, 'github_proxy_prefix', '自定义中转地址');
        prefix.placeholder = 'https://mirror.example/';
        prefix.description = '仅在选用自定义节点时填写。必须使用加密连接，并以 / 结尾。';
        prefix.depends({github_proxy_mode: 'assets', github_proxy_site: 'custom'});
        prefix.depends({github_proxy_mode: 'all', github_proxy_site: 'custom'});
        prefix.validate = function(section_id, value) {
            if (!value || !/^https:\/\/[A-Za-z0-9.-]+(?:\/[A-Za-z0-9._~\/-]*)?$/.test(value) || !value.endsWith('/') ||
                value.indexOf('..') >= 0 || value.indexOf('//', 8) >= 0)
                return '请输入有效的 HTTPS 地址，以 / 结尾，且不包含参数、账号或路径跳转。';
            return true;
        };

        var fallback = s.option(form.Flag, 'github_proxy_fallback', '中转失败时尝试官方直连');
        fallback.default = fallback.enabled;
        fallback.rmempty = false;
        fallback.description = '中转节点暂时不可用时自动尝试官方地址。如果当前网络无法直连，可关闭此选项。';

        return Promise.resolve(m.render()).then(function(formNode) {
            return E('div', {'class': 'cu-app cu-settings'}, [
                E('link', {rel: 'stylesheet', href: L.resource('component-updater/design.css')}),
                E('header', {'class': 'cu-settings-heading'}, [
                    E('a', {'class': 'cu-back', href: L.url('admin/system/component-updater')}, '‹ 返回组件更新'),
                    E('h2', {}, 'GitHub 下载设置'),
                    E('p', {}, '根据当前网络选择合适的下载方式。选项会保存到设备本地，可以随时切换。')
                ]),
                E('div', {'class': 'cu-settings-form'}, formNode),
                E('div', {'class': 'cu-settings-note'}, [
                    E('strong', {}, '关于校验与可信度'),
                    E('p', {}, '安装前会核对官方发布信息和安装包的 SHA-256 摘要，但它不是独立数字签名。若将版本查询也交给中转节点，校验信息同样经过该节点，请仅使用可信服务。')
                ])
            ]);
        });
    }
});
