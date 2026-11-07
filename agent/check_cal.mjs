// Agent-local compatibility checker; removed automatically from use when server.checker.run exists.
import vm from 'node:vm';
try {
  let input='';for await(const chunk of process.stdin)input+=chunk;
  const {code,lines,tests}=JSON.parse(input);
  const selected=tests==null?null:new Set(tests);
  let matched=0,total=0;const results=[],mismatches=[];
  for(const row of lines){
    if(row.deleted||(selected&&!selected.has(row.test)))continue;
    const context=vm.createContext(Object.create(null),{codeGeneration:{strings:false,wasm:false}});
    vm.runInContext(code,context,{timeout:1000});
    const got=vm.runInContext(`Cal.run(...${JSON.stringify(row.args)})`,context,{timeout:1000});
    const pass=typeof got==='string'&&got===row.output;total++;if(pass)matched++;
    results.push({test:row.test,pass});
    if(!pass)mismatches.push({test:row.test,seq:row.seq,args:row.args,expected:row.output,got:typeof got==='string'?got:null});
  }
  process.stdout.write(JSON.stringify({match_pct:total?Math.round(matched/total*10000)/100:0,matched,total,tests:results,mismatches})+'\n');
}catch(error){process.stdout.write(JSON.stringify({error:String(error.message),match_pct:0})+'\n');}
