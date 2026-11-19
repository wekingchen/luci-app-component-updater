'use strict';
'require view';
'require form';

return view.extend({
    render: function() {
        var m = new form.Map('component-updater', 'GitHub 下载设置',
            '反代仅用于改善特定网络环境中的官方 GitHub API 查询及 Releases 文件下载，不更改官方来源。下载后仍需验证内置公钥签名与 SHA256。');
        var s = m.section(form.NamedSection, 'main', 'updater', '网络与反代');
        s.anonymous = true;

        var mode = s.option(form.ListValue, 'github_proxy_mode', 'GitHub 反代');
        mode.value('off', '关闭（直连 GitHub）');
        mode.value('assets', '仅代理压缩包及签名文件');
        mode.value('all', '同时代理 GitHub API 查询与文件下载');
        mode.default = 'off';
        mode.rmempty = false;

        var prefix = s.option(form.Value, 'github_proxy_prefix', 'HTTPS 反代前缀');
        prefix.placeholder = 'https://mirror.example/';
        prefix.description = '格式：HTTPS 镜像前缀 + 完整 GitHub URL，例如 https://mirror.example/https://github.com/...。请使用自己信任的代理，公开代理能观察请求。';
        prefix.depends('github_proxy_mode', 'assets');
        prefix.depends('github_proxy_mode', 'all');
        prefix.validate = function(section_id, value) {
            if (!value || !/^https:\/\/[A-Za-z0-9.-]+\/[A-Za-z0-9._~\/-]*\/$/.test(value) ||
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
