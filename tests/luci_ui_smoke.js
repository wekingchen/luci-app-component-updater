'use strict';
// A zero-dependency LuCI JS logic harness for both legacy and modern view API.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const base = 'luci-app-component-updater/htdocs/luci-static/resources/view/component-updater/';
const E = (tag, attributes, children) => ({
  tag, attributes: attributes || {}, children: children == null ? [] : children
});
// LuCI dom.attr(): null is skipped, all other non-functions use setAttribute().
function disabledInRealDom(node) {
  return Object.prototype.hasOwnProperty.call(node.attributes, 'disabled') &&
    node.attributes.disabled != null;
}
function simulateEnabledClick(node) {
  assert.strictEqual(typeof node.attributes.click,'function');
  if (disabledInRealDom(node)) return false;
  node.attributes.click();
  return true;
}
const callbacks = [];
let modal = null;
const ctx = {
  E, L: {url: x => '/cgi-bin/luci/' + x},
  rpc: {declare: spec => function () {
    callbacks.push(spec.method);
    return Promise.resolve({status: 'ok', message: 'test only'});
  }},
  view: {extend: x => x},
  ui: {
    showModal: (title, content) => {modal={title, content}},
    hideModal: () => {modal=null},
    addNotification: () => {}
  },
  dom: {content: () => {}},
  poll: {add: () => {}},
  form: {},
  Promise, Date
};
function load(name) {
  const source=fs.readFileSync(base+name,'utf8');
  // LuCI wraps view modules in a function so top-level return is supported.
  return vm.runInNewContext('(function(){\n'+source+'\n})()',ctx,{filename:name});
}
function flatten(node) {
  if (Array.isArray(node)) return node.flatMap(flatten);
  if (node && typeof node === 'object' && node.tag) return [node, ...flatten(node.children)];
  return [];
}
const dashboard=load('overview.js');
const status={
  installed_version:'154.0.8037.49',
  package_version:'150.0.7871.63.1-r1',
  architecture:'aarch64_cortex-a53',
  official_tag:'v154.0.8037.49-5',
  github_proxy_mode:'assets',
  runtime_processes:'2',
  check_state:'ready', check_message:'Verified native IPK is available',
  job_state:'idle'
};
const plan={ready:'true',filename:'naiveproxy_154.0.8037.49.5-r3_aarch64_cortex-a53.ipk'};
const nodes=flatten(dashboard.renderContent(status,plan));
const buttons=nodes.filter(n=>n.tag==='button');
assert.strictEqual(buttons.length,3);
const update=buttons.find(b=>b.children==='下载并更新');
assert(update);
// Regression: LuCI turns { disabled: false } into HTML disabled="false",
 // which still disables the button in *real browsers*.
const checkButton=buttons.find(b=>b.children==='检查官方更新');
const rollbackButton=buttons.find(b=>b.children==='恢复上一个版本');
assert(checkButton && rollbackButton);
assert.strictEqual(disabledInRealDom(checkButton),false,
  'idle status MUST permit the official update check to be clicked');
assert.strictEqual(disabledInRealDom(update),false);
assert.strictEqual(disabledInRealDom(rollbackButton),false);
assert.strictEqual(simulateEnabledClick(checkButton),true);
assert(callbacks.includes('check'));

const readOnlyNodes=flatten(dashboard.renderContent({...status,job_state:'installing'},plan));
assert.strictEqual(disabledInRealDom(readOnlyNodes.find(b=>b.tag==='button'&&b.children==='下载并更新')),true);
assert.strictEqual(disabledInRealDom(readOnlyNodes.find(b=>b.tag==='button'&&b.children==='检查官方更新')),true);
assert.strictEqual(disabledInRealDom(readOnlyNodes.find(b=>b.tag==='button'&&b.children==='恢复上一个版本')),true);
const noPlanButtons=flatten(dashboard.renderContent(
  {...status, check_state:'', job_state:'idle'}, {ready:'false'}
)).filter(b=>b.tag==='button');
assert.strictEqual(disabledInRealDom(noPlanButtons.find(b=>b.children==='下载并更新')),true);
assert.strictEqual(disabledInRealDom(noPlanButtons.find(b=>b.children==='检查官方更新')),false,
  'check must remain usable before the first update check');
assert.strictEqual(disabledInRealDom(noPlanButtons.find(b=>b.children==='恢复上一个版本')),false,
  'rollback must remain clickable when idle; backend checks actual backup');

dashboard.confirmInstall();
assert(modal && modal.title.includes('NaiveProxy'));
dashboard.confirmRollback();
assert(modal && modal.title.includes('恢复旧版'));
const rendered=dashboard.render([status,plan]);
assert(rendered && rendered.tag==='div');
class Section {
  constructor(){this.fields=[]}
  option(_type,name,label) {
    const field={name,label,values:[],value:function(k,v){this.values.push([k,v])},
      depends:function(){},validate:function(){return true}};
    this.fields.push(field);
    return field;
  }
}
class Map {
  constructor(){this.sections=[]}
  section(){let s=new Section();this.sections.push(s);return s}
  render(){return this}
}
ctx.form={Map,NamedSection:function(){},ListValue:function(){},Value:function(){},Flag:function(){}};
const settings=load('settings.js');
const map=settings.render();
assert.strictEqual(map.sections.length,1);
const fields=map.sections[0].fields;
assert.deepStrictEqual(Array.from(fields.map(x=>x.name)),['github_proxy_mode','github_proxy_site','github_proxy_prefix','github_proxy_fallback']);
const providers=fields[1];
assert.deepStrictEqual(Array.from(providers.values.map(x=>x[0])),
  ['gh-proxy.org','ghproxy.cc','ghproxy.com','ghfast.top','custom']);
const p=fields[2];
assert.strictEqual(p.validate('main','https://trusted.example/'),true);
for (const invalid of ['http://test.example/','https://localhost/..','https://evil.example/?p=1','']) {
  assert.notStrictEqual(p.validate('main',invalid),true,invalid);
}
console.log('LuCI JS dashboard actions, pending state and proxy settings smoke PASS');
