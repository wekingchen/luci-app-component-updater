'use strict';
'require view';
'require form';

return view.extend({
    render: function() {
        var m = new form.Map('component-updater', 'GitHub 下载设置',
            '反代仅用于改善特定网络环境中的官方 GitHub API 查询及 Releases 文件下载，不更改官方来源。更新器会核对 GitHub Release API 的摘要及文件 SHA256；未启用独立数字签名。');
        var s = m.section(form.NamedSection, 'main', 'updater', '网络与反代');
        s.anonymous = true;

        var mode = s.option(form.ListValue, 'github_proxy_mode', 'GitHub 反代');
        mode.value('off', '关闭（直连 GitHub）');
        mode.value('assets', '仅代理 Manifest 与 IPK 下载');
        mode.value('all', '同时代理 GitHub API 查询与文件下载');
        mode.default = 'off';
        mode.rmempty = false;

        var site = s.option(form.ListValue, 'github_proxy_site', '常用反代节点');
        site.value('gh-proxy.org', 'gh-proxy.org');
        site.value('ghproxy.cc', 'ghproxy.cc（备用）');
        site.value('ghproxy.com', 'ghproxy.com（备用）');
        site.value('ghfast.top', 'ghfast.top');
        site.value('custom', '自定义 HTTPS 地址');
        site.default = 'custom'; // Preserve old installations using github_proxy_prefix
        site.rmempty = false;
        site.description = '预设节点并非实时可用性保证；建议选择「仅代理下载」，保持官方 API 直连。';
        site.depends('github_proxy_mode', 'assets');
        site.depends('github_proxy_mode', 'all');

        var prefix = s.option(form.Value, 'github_proxy_prefix', '自定义 HTTPS 反代前缀');
        prefix.placeholder = 'https://mirror.example/';
        prefix.description = '仅选择「自定义 HTTPS 地址」时需要填写，例如 https://mirror.example/。若把 API 查询也交给反代，该反代能同时影响校验信息。';
        prefix.depends({github_proxy_mode: 'assets', github_proxy_site: 'custom'});
        prefix.depends({github_proxy_mode: 'all', github_proxy_site: 'custom'});
        prefix.validate = function(section_id, value) {
            if (!value || !/^https:\/\/[A-Za-z0-9.-]+(?:\/[A-Za-z0-9._~\/-]*)?$/.test(value) || !value.endsWith('/') ||
                value.indexOf('..') >= 0 || value.indexOf('//', 8) >= 0)
                return '必须填写合法的 HTTPS 前缀，且以 / 结尾，不包含参数、凭证或路径跳转';
            return true;
        };

        var fallback = s.option(form.Flag, 'github_proxy_fallback', '反代失败时尝试直连 GitHub');
        fallback.default = fallback.enabled;
        fallback.rmempty = false;
        fallback.description = '启用后可在镜像临时故障时自动重试官方地址。若所在网络无法直连，可以关闭。';

        return m.render();
    }
});
