globalThis.Calc=(()=>{let a=null,op=null,firstEntry="0",second=null,pct=false,justEq=false,expr=null,error=false;
function fmt(n){if(typeof n!=="number"||!isFinite(n))return"Error";let s=String(n);if(s.includes("e")||s.includes("E")){s=(Number(n.toPrecision(12)))+"";}let neg=s.startsWith("-");if(neg)s=s.slice(1);let p=s.split(".");let A=p[0].replace(/\B(?=(\d{3})+(?!\d))/g,",");if(p.length>1){let b=p[1].replace(/0+$/,"");if(b==="")return(neg?"-":"")+A;return(neg?"-":"")+A+"."+b;}return(neg?"-":"")+A;}
function fmtE(e){if(e==="Error")return"Error";let neg=e.startsWith("-");let s=neg?e.slice(1):e;let p=s.split(".");let A=p[0]===""?"0":p[0].replace(/^0+(?=\d)/,"").replace(/\B(?=(\d{3})+(?!\d))/g,",");if(p.length>1)return(neg?"-":"")+A+"."+p[1];return(neg?"-":"")+A;}
function num(s){return parseFloat(s);}
function calc(x,o,y){if(o==="+")return x+y;if(o==="-")return x-y;if(o==="×")return x*y;if(o==="÷")return y===0?NaN:x/y;return y;}
function reset(){a=null;op=null;firstEntry="0";second=null;pct=false;justEq=false;expr=null;error=false;}
function press(k){
if(/^[0-9]$/.test(k)){
if(error)reset();
if(justEq){firstEntry=k;second=null;op=null;a=null;expr=null;pct=false;justEq=false;return;}
if(op!==null){
if(second===null){second=k;pct=false;}
else{if(second.replace(/[-.,]/g,"").length<12){if(second==="0")second=k;else if(second==="-0")second="-"+k;else second+=k;}}
return;
}else{
if(expr!==null)expr=null;
if(firstEntry==="0"){firstEntry=k;}else if(firstEntry==="-0"){firstEntry="-"+k;}
else{if(firstEntry.replace(/[-.,]/g,"").length>=12)return;firstEntry+=k;}
return;}
}
if(k==="."){
if(error)reset();
if(justEq){firstEntry="0.";a=null;op=null;second=null;expr=null;justEq=false;pct=false;return;}
if(op!==null){if(second===null){second="0.";pct=false;}else if(!second.includes("."))second+=".";return;}
else{if(!firstEntry.includes("."))firstEntry+=".";return;}
}
if(k==="AC"){reset();return;}
if(k==="C"){
if(error){reset();return;}
if(justEq){
if(op!==null){op=null;second=null;pct=false;}
else{reset();}
return;}
if(op!==null){
if(second!==null){second="0";pct=false;}
return;
}else{
return;
}
}
if(k==="⌫"){
if(error){reset();return;}
if(justEq)return;
if(op!==null){
if(second===null)return;
if(second.length<=1||(second.length===2&&second.startsWith("-"))){second="0";}
else second=second.slice(0,-1);
return;
}else{
if(firstEntry.length<=1||(firstEntry.length===2&&firstEntry.startsWith("-"))){firstEntry="0";}
else firstEntry=firstEntry.slice(0,-1);
return;}
}
if(k==="+/-"){
if(error)return;
if(op!==null){
if(second===null){
let v=num(firstEntry);if(v===0)return;
if(firstEntry.startsWith("-"))firstEntry=firstEntry.slice(1);else firstEntry="-"+firstEntry;
a=num(firstEntry);
}else{
if(second==="0"||second==="0.")return;
if(second.startsWith("-"))second=second.slice(1);else second="-"+second;
}
}else{
if(justEq){let v=num(firstEntry);if(v===0){justEq=false;}else{if(firstEntry.startsWith("-"))firstEntry=firstEntry.slice(1);else firstEntry="-"+firstEntry;a=num(firstEntry);justEq=false;expr=null;return;}}
if(firstEntry==="0"||firstEntry==="0.")return;
if(firstEntry.startsWith("-"))firstEntry=firstEntry.slice(1);else firstEntry="-"+firstEntry;
}
return;}
if(k==="%"){
if(error)return;
if(op!==null&&second!==null&&!pct){pct=true;}
else if(op===null){let v=num(firstEntry)/100;let s=String(v).replace(/,/g,"");firstEntry=s;}
return;}
if(k==="+"||k==="-"||k==="×"||k==="÷"){
if(error)return;
if(justEq){a=num(firstEntry);op=k;second=null;pct=false;justEq=false;expr=null;return;}
if(op!==null&&second!==null){
let sv=num(second);let b=pct?((op==="+"||op==="-")?a*sv/100:sv/100):sv;
let r=calc(a,op,b);
if(!isFinite(r)||isNaN(r)){error=true;expr=null;return;}
a=r;firstEntry=String(r).replace(/,/g,"");op=k;second=null;pct=false;expr=null;
}else if(op!==null){
op=k;return;
}else{
a=num(firstEntry);op=k;second=null;pct=false;expr=null;
}
return;}
if(k==="="){
if(error)return;
if(justEq){return;}
if(op!==null&&second!==null){
let sv=num(second);
let eff=pct?((op==="+"||op==="-")?a*sv/100:sv/100):sv;
let r=calc(a,op,eff);
if(!isFinite(r)||isNaN(r)){error=true;expr=null;op=null;second=null;a=null;return;}
expr=fmt(a)+op+fmtE(second)+(pct?"%":"");
firstEntry=String(r).replace(/,/g,"");a=r;justEq=true;
return;
}else if(op!==null&&second===null){
justEq=false;return;
}else{
return;}
}
}
function render(){
let display,expression=expr;
if(error){display="Error";}
else if(justEq){display=fmt(num(firstEntry));}
else if(op!==null){
if(second!==null){display=fmt(a)+op+fmtE(second)+(pct?"%":"");}
else{display=fmt(a);}
}else{display=fmtE(firstEntry);}
let clear_label;
if(error)clear_label="AC";
else if(justEq)clear_label="AC";
else if(op===null&&firstEntry==="0")clear_label="AC";
else clear_label="C";
let active_op=null;
if(!error&&op!==null)active_op=op;
return{display,expression,clear_label,active_op};}
return{reset,press,render};})();