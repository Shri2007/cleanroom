globalThis.Calc=(()=>{
let cur="0",acc=null,pend=null,act=null,exp=null,cl="AC";
let entering=false,fresh=false,computed=false,curPct=false,accStr=null;
let repOp=null,repB=null,repBStr=null;
function fmt(n){
if(typeof n!=="number"||!isFinite(n)||isNaN(n)) return "Error";
let neg=n<0&&n!==0;n=Math.abs(n);
if(n!==0&&(n>=1e9||n<1e-9)){let s=n.toExponential(5).replace(/\.?0+e/,"e").replace("e","E");return (neg?"-":"")+s;}
let r=Math.round(n*1e9)/1e9;let s=r.toString();
if(s.includes("e")){s=r.toFixed(9).replace(/\.?0+$/,"").replace(/\.$/,"");}
let p=s.split(".");p[0]=Number(p[0]).toLocaleString("en-US");
return (neg?"-":"")+p.join(".");
}
function fmtCur(s){
if(s==="Error") return "Error";
if(s===""||s==="-"||s==="-0"||s==="0."||s==="-0."){
if(s==="-0."||s==="0.") return s;
if(s==="-") return s;
if(s==="") return "0";
let neg=s[0]==="-";let body=neg?s.slice(1):s;
if(body.endsWith(".")){
let ip=body.slice(0,-1);if(ip===""||ip==="0") return (neg?"-0.":"0.");
let f=Number(ip).toLocaleString("en-US");return (neg?"-":"")+f+".";
}
return s==="0"||s==="-0"?"0":s;
}
if(s.endsWith(".")||(s.includes(".")&&(s.endsWith("0")))){
let neg=s[0]==="-";let b=neg?s.slice(1):s;
let parts=b.split(".");let ip=parts[0]===""?"0":Number(parts[0]).toLocaleString("en-US");
return (neg?"-":"")+ip+"."+parts[1];
}
let v=parseFloat(s);if(isNaN(v)) return "0";
return fmt(v);
}
function num(s){return parseFloat(String(s).replace(/,/g,""));}
function calc(a,b,o){if(o==="+")return a+b;if(o==="-")return a-b;if(o==="×")return a*b;if(o==="÷")return b===0?NaN:a/b;return b;}
function effSecond(){
let v=num(cur);
if(curPct){
if(pend==="+"||pend==="-") return acc*v/100;
return v/100;
}
return v;
}
function dispSecond(){return fmtCur(cur)+(curPct?"%":"");}
return{
reset(){cur="0";acc=null;pend=null;act=null;exp=null;cl="AC";entering=false;fresh=false;computed=false;curPct=false;accStr=null;repOp=null;repB=null;repBStr=null;},
press(k){
if(k==="AC"){cur="0";acc=null;pend=null;act=null;exp=null;cl="AC";entering=false;fresh=false;computed=false;curPct=false;accStr=null;repOp=null;repB=null;repBStr=null;return;}
if(/^[0-9]$/.test(k)){
if(computed&&pend===null){acc=null;pend=null;act=null;exp=null;accStr=null;computed=false;cur="0";curPct=false;entering=false;fresh=false;repOp=null;repB=null;repBStr=null;}
if(pend!==null&&!computed){
if(!entering||fresh){cur=k;entering=true;fresh=false;curPct=false;}
else{
let raw=cur.replace(/,/g,"");
let hasDot=cur.includes(".");
let noDot=raw.replace(".","").replace("-","");
if(hasDot){if(noDot.length>=9){}else cur=raw+k;}
else{if(noDot.length>=9){}else{
let combined=raw+k;
let v=parseFloat(combined);
cur=fmtCur(combined.includes(".")?combined:String(v));
if(combined.startsWith("0")&&!combined.startsWith("0.")&&combined.length>1){cur=fmt(v);}
}}
}
cl="C";computed=false;return;
}
if(!entering||fresh){cur=k;entering=true;fresh=false;}
else{
let raw=cur.replace(/,/g,"");
let hasDot=cur.includes(".");
let noDot=raw.replace(".","").replace("-","");
if(hasDot){if(noDot.length<9) cur=raw+k;}
else{if(noDot.length<9){
let combined=raw+k;
if(raw==="0") cur=k;
else if(raw==="-0") cur="-"+k;
else cur=fmt(parseFloat(combined));
}}
}
cl="C";computed=false;return;
}
if(k==="."){
if(computed&&pend===null){acc=null;pend=null;act=null;exp=null;accStr=null;computed=false;cur="0";curPct=false;entering=false;fresh=false;repOp=null;repB=null;repBStr=null;}
if(pend!==null&&!computed&&(fresh||!entering)){cur="0.";entering=true;fresh=false;curPct=false;}
else if(fresh){cur="0.";fresh=false;entering=true;}
else if(!entering){cur="0.";entering=true;}
else if(!cur.includes(".")) cur=cur+".";
cl="C";return;
}
if(k==="⌫"){return;}
if(k==="+/-"){if(cur!=="0"&&cur!=="0."){cur=cur[0]==="-"?cur.slice(1):"-"+cur;}return;}
if(k==="%"){
if(pend!==null&&!computed&&(entering||curPct)){curPct=true;entering=true;fresh=false;}
else{let v=num(cur)/100;cur=fmt(v);entering=true;fresh=false;}
return;
}
if(k==="C"){
if(entering&&!computed){return;}
cur="0";exp=null;cl="AC";act=null;acc=null;pend=null;accStr=null;fresh=false;entering=false;computed=false;curPct=false;return;
}
if(k==="+"||k==="-"||k==="×"||k==="÷"){
let v;
if(computed){v=num(cur);acc=v;accStr=fmt(v);}
else if(pend!==null&&entering){let b=effSecond();let r=calc(acc,b,pend);if(!isFinite(r)||isNaN(r)){cur="Error";exp=null;cl="AC";act=null;acc=null;pend=null;accStr=null;entering=false;fresh=false;computed=false;curPct=false;return;}acc=r;accStr=fmt(r);cur=fmt(r);}
else if(pend!==null&&!entering){}
else{acc=num(cur);accStr=fmtCur(cur);}
pend=k;act=k;fresh=true;entering=false;computed=false;curPct=false;cur="0";exp=null;cl="C";repOp=null;repB=null;repBStr=null;return;
}
if(k==="="){
if(pend!==null){
let a=acc;let bStr=dispSecond();let b=effSecond();
let r=calc(a,b,pend);
let e=fmt(a)+pend+bStr;
if(!isFinite(r)||isNaN(r)){cur="Error";exp=null;cl="AC";act=null;pend=null;acc=null;accStr=null;return;}
repOp=pend;repB=b;repBStr=bStr;
cur=fmt(r);exp=e;cl="AC";act=pend;acc=null;pend=null;accStr=null;fresh=true;entering=false;computed=true;curPct=false;return;
}else if(repOp!==null){
let a=num(cur);let b=repB;let bStr=repBStr;
let r=calc(a,b,repOp);
let e=fmt(a)+repOp+bStr;
if(!isFinite(r)||isNaN(r)){cur="Error";exp=null;cl="AC";act=null;repOp=null;return;}
cur=fmt(r);exp=e;cl="AC";act=repOp;fresh=true;entering=false;computed=true;curPct=false;return;
}else{return;}
}
},
render(){
let d,e=exp;
if(computed){d=cur;}
else if(pend!==null){
let a=accStr!==null?accStr:fmt(acc);
if(entering) d=a+pend+dispSecond();
else d=a;
e=null;
}else{d=fmtCur(cur);}
return{display:d,expression:e,clear_label:cl,active_op:act};
}};
})();