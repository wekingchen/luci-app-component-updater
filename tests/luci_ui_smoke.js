'use strict';
// A zero-dependency LuCI JS logic harness for both legacy and modern view API.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const base = 'luci-app-component-updater/htdocs/luci-static/resources/view/component-updater/';
const E = (tag, attributes, children) => ({
  tag, attributes: attributes || {}, children: children == null ? [] : children
});
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
  return vm.runInNewContext(fs.readFileSync(base+name,'utf8'),ctx,{filename:name});
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
assert.strictEqual(update.attributes.disabled,false);
const readOnlyNodes=flatten(dashboard.renderContent({...status,job_state:'installing'},plan));
assert.strictEqual(readOnlyNodes.find(b=>b.tag==='button'&&b.children==='下载并更新').attributes.disabled,true);
assert.strictEqual(flatten(dashboard.renderContent(status,{ready:'false'})).find(b=>b.tag==='button'&&b.children==='下载并更新').attributes.disabled,true);
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
assert.deepStrictEqual(Array.from(fields.map(x=>x.name)),['github_proxy_mode','github_proxy_prefix','github_proxy_fallback']);
const p=fields[1];
assert.strictEqual(p.validate('main','https://trusted.example/'),true);
for (const invalid of ['http://test.example/','https://localhost/..','https://evil.example/?p=1','']) {
  assert.notStrictEqual(p.validate('main',invalid),true,invalid);
}
console.log('LuCI JS dashboard actions, pending state and proxy settings smoke PASS');
