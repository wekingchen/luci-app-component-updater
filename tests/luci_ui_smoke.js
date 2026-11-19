'use strict';
// Zero-dependency regression suite for GL.iNet legacy and current LuCI views.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const base = 'luci-app-component-updater/htdocs/luci-static/resources/view/component-updater/';
const css = fs.readFileSync('luci-app-component-updater/htdocs/luci-static/resources/component-updater/design.css', 'utf8');
const calls = [];
let modal = null;
let formMap = null;
let renderCount = 0;
const E = (tag, attributes, children) => ({tag, attributes: attributes || {}, children: children == null ? [] : children});
function flatten(node) {
  if (Array.isArray(node)) return node.flatMap(flatten);
  if (node && typeof node === 'object' && node.tag) return [node, ...flatten(node.children)];
  return [];
}
function visibleText(node) {
  if (node == null) return '';
  if (Array.isArray(node)) return node.map(visibleText).join(' ');
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (node && node.tag) return visibleText(node.children);
  return '';
}
function disabledInRealDom(node) {
  // On legacy LuCI, disabled:false is still a *present* HTML attribute.
  return Object.prototype.hasOwnProperty.call(node.attributes, 'disabled') && node.attributes.disabled != null;
}
function button(tree, caption) {
  const node = flatten(tree).find(n => n.tag === 'button' && n.children === caption);
  assert(node, 'missing button: ' + caption);
  return node;
}
function Section() { this.fields = []; }
Section.prototype.option = function(_type, name, label) {
  const field = {name, label, values: [], value: function(k,v) {this.values.push([k,v])},
    depends: function(){}, validate: function(){return true}};
  this.fields.push(field);
  return field;
};
function Map() { this.sections = []; formMap = this; }
Map.prototype.section = function() { const s = new Section(); this.sections.push(s); return s; };
Map.prototype.render = function() { return Promise.resolve(E('div', {'class':'cbi-map'}, '测试表单')); };
const ctx = {
  E, Promise, Date, JSON, String,
  L: {url: x => '/cgi-bin/luci/' + x, resource: x => '/luci-static/resources/' + x},
  rpc: {declare: spec => function() {
    calls.push(spec.method);
    return Promise.resolve({status:'ok', message:'Native IPK installation started'});
  }},
  view: {extend: x => x},
  ui: {
    showModal: (title, content) => {modal = {title,content}},
    hideModal: () => {modal = null},
    addNotification: () => {throw new Error('legacy LuCI toast must not be used')}
  },
  dom: {content: () => {renderCount++}},
  poll: {add: (_cb, interval) => {assert.strictEqual(interval, 5)}},
  form: {Map, NamedSection: function(){}, ListValue: function(){}, Value: function(){}, Flag: function(){}}
};
function load(name) {
  const source = fs.readFileSync(base + name, 'utf8');
  // LuCI wraps views in functions, allowing top-level return.
  return vm.runInNewContext('(function(){\n' + source + '\n})()', ctx, {filename:name});
}
async function main() {
  const dashboard = load('overview.js');
  const status = {
    installed_version:'154.0.8037.49',
    package_version:'150.0.7871.63.1-r1',
    architecture:'aarch64_cortex-a53',
    official_tag:'v154.0.8037.49-5',
    github_proxy_mode:'assets',
    github_proxy_site:'gh-proxy.org',
    runtime_processes:'2',
    check_state:'ready',
    check_message:'Verified native IPK is available for manual installation',
    job_state:'idle'
  };
  const plan = {ready:'true',filename:'naiveproxy_154.0.8037.49.5-r3_aarch64_cortex-a53.ipk'};
  const rendered = dashboard.render([status,plan]);
  assert(rendered.tag === 'div');
  assert(flatten(rendered).some(n => n.tag === 'link' && /design\.css$/.test(n.attributes.href)));
  let nodes = dashboard.renderContent(status,plan);
  const actions = flatten(nodes).filter(n => n.tag === 'button');
  assert.strictEqual(actions.length,3, 'only three clearly prioritized actions');
  for (const caption of ['检查官方更新','下载并更新','恢复上一个版本'])
    assert.strictEqual(disabledInRealDom(button(nodes,caption)),false);
  assert(visibleText(nodes).includes('新版本已准备就绪'));
  assert(visibleText(nodes).includes('安装包已通过'));
  assert(!visibleText(nodes).includes('Verified native IPK'));
  assert(visibleText(nodes).includes('预设节点一'));

  // Before an update check, checking and rollback remain available.
  const noPlan = dashboard.renderContent({...status,check_state:''}, {ready:'false'});
  assert.strictEqual(disabledInRealDom(button(noPlan,'检查官方更新')),false);
  assert.strictEqual(disabledInRealDom(button(noPlan,'下载并更新')),true);
  assert.strictEqual(disabledInRealDom(button(noPlan,'恢复上一个版本')),false);
  for (const jobState of ['queued','downloading','verifying','backing_up','installing']) {
    nodes = dashboard.renderContent({...status,job_state:jobState},plan);
    assert(visibleText(nodes).includes('更新进行中'));
    for (const caption of ['检查官方更新','下载并更新','恢复上一个版本'])
      assert.strictEqual(disabledInRealDom(button(nodes,caption)),true, jobState + ': ' + caption);
  }
  nodes = dashboard.renderContent({...status,check_state:'up_to_date'},plan);
  assert(visibleText(nodes).includes('组件已保持最新'));
  assert.strictEqual(disabledInRealDom(button(nodes,'下载并更新')),true);
  nodes = dashboard.renderContent({...status, installed_upstream_tag:status.official_tag},plan);
  assert.strictEqual(disabledInRealDom(button(nodes,'下载并更新')),true);
  nodes = dashboard.renderContent({...status,job_state:'idle',check_state:'pending'}, {ready:'false'});
  assert(visibleText(nodes).includes('云端准备中'));
  assert.strictEqual(disabledInRealDom(button(nodes,'下载并更新')),true);
  nodes = dashboard.renderContent({...status,check_state:'error',check_message:'Official GitHub API unavailable'}, {ready:'false'});
  assert(visibleText(nodes).includes('无法连接官方发布接口'));
  nodes = dashboard.renderContent({...status,job_state:'recovery_required'}, {ready:'false'});
  assert(visibleText(nodes).includes('需要恢复'));

  // A native APK device must NEVER see enabled opkg IPK actions,
  // even if a stale valid IPK plan remains from an earlier firmware.
  const ax6s = {...status, package_manager:'apk', compatibility:'ax6s-apk-readonly',
    firmware_target:'mediatek/mt7622', check_state:'ready'};
  const apkNodes = dashboard.renderContent(ax6s, plan);
  assert(visibleText(apkNodes).includes('已识别红米 AX6S'));
  assert(visibleText(apkNodes).includes('原生 APK'));
  assert(!visibleText(apkNodes).includes('新版本已准备就绪'));
  for (const caption of ['检查官方更新','下载并更新','恢复上一个版本'])
    assert.strictEqual(disabledInRealDom(button(apkNodes,caption)),true, 'APK: '+caption);
  dashboard.currentStatus = ax6s;
  dashboard.currentPlan = plan;
  modal = null;
  dashboard.confirmInstall();
  dashboard.confirmRollback();
  assert.strictEqual(modal,null,'APK protection must reject direct modal invocations');
  dashboard.currentStatus = status;

  // Never surface raw English diagnostic messages in white LuCI toast boxes.
  dashboard.notify({status:'up_to_date',message:'Installed native IPK matches the latest official build'});
  assert(visibleText(dashboard.renderContent(status,plan)).includes('当前安装版本与官方最新构建一致'));
  dashboard.notify({status:'error',message:'Unexpected unlocalized backend error details'});
  const notificationText = visibleText(dashboard.renderContent(status,plan));
  assert(notificationText.includes('操作没有成功'));
  assert(!notificationText.includes('Unexpected unlocalized'));
  dashboard.notice = null;

  dashboard.confirmInstall();
  assert(modal && modal.title.includes('NaiveProxy'));
  assert(visibleText(modal.content).includes('先备份当前版本'));
  dashboard.confirmRollback();
  assert(modal && modal.title.includes('恢复上一个版本'));
  assert(visibleText(modal.content).includes('有效备份'));
  modal = null;
  assert.strictEqual(typeof button(dashboard.renderContent(status,plan),'检查官方更新').attributes.click,'function');
  await button(dashboard.renderContent(status,plan),'检查官方更新').attributes.click();
  assert(calls.includes('check'));
  assert(renderCount > 0,'inline notice updates the view');

  // Refreshing unchanged data must not erase focus or expanded diagnostics.
  const previousRenders = renderCount;
  await dashboard.refresh();
  const afterFirstRefresh = renderCount;
  await dashboard.refresh();
  assert.strictEqual(renderCount, afterFirstRefresh,'unchanged model must not redraw the page');
  assert(afterFirstRefresh >= previousRenders);

  const settings = load('settings.js');
  const settingsPage = await settings.render();
  assert(settingsPage.tag === 'div');
  assert(visibleText(settingsPage).includes('GitHub 下载设置'));
  assert(flatten(settingsPage).some(n => n.tag === 'link' && /design\.css$/.test(n.attributes.href)));
  assert.strictEqual(formMap.sections.length,1);
  const fields = formMap.sections[0].fields;
  assert.deepStrictEqual(Array.from(fields.map(x => x.name)),
    ['github_proxy_mode','github_proxy_site','github_proxy_prefix','github_proxy_fallback']);
  assert.deepStrictEqual(Array.from(fields[1].values.map(v => v[0])),
    ['gh-proxy.org','ghproxy.cc','ghproxy.com','ghfast.top','custom']);
  assert.strictEqual(fields[2].validate('main','https://trusted.example/'),true);
  for (const invalid of ['http://test.example/','https://localhost/..','https://evil.example/?p=1','']) {
    assert.notStrictEqual(fields[2].validate('main',invalid),true,invalid);
  }
  // Core mobile, keyboard and reduced-motion affordances are part of the UI contract.
  for (const selector of ['.cu-actions','@media (max-width: 600px)',':focus-visible','prefers-reduced-motion','.cu-notice','.cu-detail']) {
    assert(css.includes(selector), 'missing design token or accessibility contract: '+selector);
  }
  console.log('LuCI 产品界面：状态中文化、按钮可用性、安装确认、滚动刷新、移动端与下载设置 PASS');
}
main().catch(err => {console.error(err); process.exitCode=1;});
