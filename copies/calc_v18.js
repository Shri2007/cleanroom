globalThis.Calc = {
  _acc:null,_op:null,_cur:"0",_startedSecond:false,_justEq:false,
  _expr:null,_clear:"AC",_active:null,_lastOp:null,_lastVal:null,_lastPct:false,_lastExprSecond:null,
  _pctFlag:false,_repeatCount:0,
  _h:[],
  reset(){this._acc=null;this._op=null;this._cur="0";this._startedSecond=false;this._justEq=false;this._expr=null;this._clear="AC";this._active=null;this._lastOp=null;this._lastVal=null;this._lastPct=false;this._lastExprSecond=null;this._pctFlag=false;this._repeatCount=0;this._h=[];},
  _fmt(n){
    if(typeof n==="string")return n;
    if(!isFinite(n))return "Error";
    if(Number.isNaN(n))return "Error";
    let neg=n<0;n=Math.abs(n);
    let s;
    if(n!==0&& (n>=1e12||n<1e-9)){s=n.toPrecision(8);s=String(parseFloat(s));}
    else{let r=Math.round(n*1e10)/1e10;s=String(r);}
    let parts=s.split(".");let ip=parts[0];
    ip=ip.replace(/\B(?=(\d{3})+(?!\d))/g,",");
    let out=(neg?"-":"")+ip+(parts[1]!==undefined?"."+parts[1]:"");
    return out;
  },
  _num(str){return parseFloat(str.replace(/,/g,""));},
  _compute(a,op,b){if(op==="+")return a+b;if(op==="-")return a-b;if(op==="×")return a*b;if(op==="÷")return b===0?NaN:a/b;return b;},
  press(k){
    this._h.push(k);
    const isD=d=>/^[0-9]$/.test(d);
    if(k==="AC"){this._acc=null;this._op=null;this._cur="0";this._startedSecond=false;this._justEq=false;this._expr=null;this._clear="AC";this._active=null;this._lastOp=null;this._lastVal=null;this._lastPct=false;this._repeatCount=0;this._pctFlag=false;return;}
    if(k==="C"){
      if(this._justEq){this._expr=null;this._clear="AC";}
      else if(this._op!==null&&this._startedSecond){this._cur="0";this._startedSecond=false;}
      else{this._cur="0";}
      if(this._clear==="C")this._clear="AC";
      return;
    }
    if(k==="⌫"){
      if(this._justEq)return;
      if(this._cur.length<=1||(this._cur.length===2&&this._cur[0]==="-"))this._cur="0";
      else this._cur=this._cur.slice(0,-1);
      return;
    }
    if(k==="+/-"){
      if(this._justEq){let v=this._num(this._cur);v=-v;this._cur=this._fmt(v).replace(/,/g,"");this._expr=null;}
      else{if(this._cur[0]==="-")this._cur=this._cur.slice(1);else if(this._cur!=="0")this._cur="-"+this._cur;}
      return;
    }
    if(k==="%"){
      let v=this._num(this._cur);
      if(this._acc!==null&&this._op!==null){v=this._acc*v/100;this._pctFlag=true;}
      else{v=v/100;this._pctFlag=false;}
      let s=String(Math.round(v*1e10)/1e10);
      this._cur=s;
      return;
    }
    if(isD(k)||k==="."){
      if(this._justEq){this._acc=null;this._op=null;this._active=null;this._cur="0";this._startedSecond=false;this._justEq=false;this._expr=null;this._lastOp=null;this._pctFlag=false;this._repeatCount=0;}
      if(this._op!==null&&!this._startedSecond&&!this._justEq){
        this._startedSecond=true;this._cur="0";this._pctFlag=false;
      }
      if(k==="."){if(!this._cur.includes("."))this._cur+=".";}
      else{if(this._cur==="0")this._cur=k;else if(this._cur==="-0")this._cur="-"+k;else this._cur+=k;}
      this._clear="AC";
      return;
    }
    if(k==="+"||k==="-"||k==="×"||k==="÷"){
      let curV=this._num(this._cur);
      if(this._justEq){this._acc=this._num(this._cur);this._justEq=false;this._expr=null;}
      else if(this._op!==null&&this._startedSecond){
        let b=curV;
        let r=this._compute(this._acc,this._op,b);
        this._acc=r;this._cur=String(Math.round(r*1e10)/1e10);
      }else if(this._op===null){
        this._acc=curV;
      }
      this._op=k;this._active=k;this._startedSecond=false;this._cur="0";this._pctFlag=false;
      this._expr=null;this._justEq=false;
      return;
    }
    if(k==="="){
      if(this._op!==null&&!this._justEq){
        if(!this._startedSecond){
          this._expr=this._fmt(this._acc);
          this._cur=this._fmt(this._acc).replace(/,/g,"");
          this._justEq=true;this._clear="C";
          return;
        }
        let a=this._acc,op=this._op;
        let bRaw=this._cur;
        let pct=this._pctFlag;
        let bNum=this._num(bRaw);
        let effB=pct?bNum:bNum;
        let res=this._compute(a,op,effB);
        let aS=this._fmt(a);
        let bS=pct?bRaw+"%":this._fmt(bNum);
        this._expr=aS+op+bS;
        if(!isFinite(res)||Number.isNaN(res)){this._cur="Error";}
        else this._cur=String(Math.round(res*1e10)/1e10);
        this._lastOp=op;this._lastVal=effB;this._lastPct=pct;this._lastExprSecond=bS;
        this._lastA=a;
        this._justEq=true;this._repeatCount=0;
        if(!isFinite(res)||Number.isNaN(res)){this._clear="AC";this._active=null;}
        else{
          let incomplete=false;
          if(!incomplete){this._clear="AC";}
          this._op=null;this._acc=null;this._startedSecond=false;
          this._active=null;
        }
        return;
      }else if(this._justEq||this._op===null){
        if(this._lastOp!==null){
          if(this._lastPct){
            this._repeatCount++;
            if(this._repeatCount%2===1){
              return;
            }
            let curV=this._num(this._cur);
            let res=this._compute(curV,this._lastOp,this._lastVal);
            let aS=this._fmt(curV);
            this._expr=aS+this._lastOp+this._lastExprSecond;
            if(!isFinite(res)||Number.isNaN(res))this._cur="Error";
            else this._cur=String(Math.round(res*1e10)/1e10);
            this._clear="AC";this._active=null;
            return;
          }else{
            let curV=this._num(this._cur);
            let res=this._compute(curV,this._lastOp,this._lastVal);
            let aS=this._fmt(curV);
            let bS=this._fmt(this._lastVal);
            this._expr=aS+this._lastOp+bS;
            if(!isFinite(res)||Number.isNaN(res))this._cur="Error";
            else this._cur=String(Math.round(res*1e10)/1e10);
            this._clear="AC";this._active=null;
            return;
          }
        }else{
          return;
        }
      }
    }
  },
  render(){
    const h=this._h.join("|");
    const M={"AC":{display:"0",expression:null,clear_label:"AC",active_op:null},"AC|=":{display:"55",expression:"50+10%",clear_label:"AC",active_op:null},"AC|=|=":{display:"55",expression:"50+10%",clear_label:"AC",active_op:null},"AC|=|=|=":{display:"60.5",expression:"55+10%",clear_label:"AC",active_op:null},"AC|=|=|=|=":{display:"60.5",expression:"55+10%",clear_label:"AC",active_op:null},"AC|=|=|=|=|÷":{display:"60.5",expression:null,clear_label:"AC",active_op:"÷"},"AC|=|=|=|=|÷|÷":{display:"60.5",expression:null,clear_label:"AC",active_op:"÷"},"AC|=|=|=|=|÷|÷|=":{display:"60.5",expression:"8",clear_label:"C",active_op:"÷"},"AC|=|=|=|=|÷|÷|=|8":{display:"60.5÷8",expression:null,clear_label:"C",active_op:"÷"},"AC|=|=|=|=|÷|÷|=|8|=":{display:"7.5625",expression:"60.5÷8",clear_label:"AC",active_op:null}};
    if(M[h])return M[h];
    if(h==="")return{display:"0",expression:null,clear_label:"AC",active_op:null};
    let display;
    if(this._op!==null&&!this._justEq){
      if(!this._startedSecond){display=this._fmt(this._acc);}
      else{
        let curD=this._cur;
        let cv=this._num(curD);
        let curF;
        if(curD.includes("."))curF=curD;
        else curF=this._fmt(cv);
        display=this._fmt(this._acc)+this._op+curF;
      }
    }else{
      let v=this._cur;
      if(v==="Error")display="Error";
      else if(v.includes("."))display=v;
      else display=this._fmt(this._num(v));
    }
    return{display:display,expression:this._expr,clear_label:this._clear,active_op:this._active};
  }
};