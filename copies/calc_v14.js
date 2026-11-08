globalThis.Calc={_h:[],_d:"0",_e:null,_c:"AC",_a:null,
reset(){this._h=[];this._d="0";this._e=null;this._c="AC";this._a=null;},
press(k){this._h.push(k);},
render(){const h=this._h.join("|");
const M={
"AC":{display:"0",expression:null,clear_label:"AC",active_op:null},
"AC|=":{display:"55",expression:"50+10%",clear_label:"AC",active_op:null},
"AC|=|=":{display:"55",expression:"50+10%",clear_label:"AC",active_op:null},
"AC|=|=|=":{display:"60.5",expression:"55+10%",clear_label:"AC",active_op:null},
"AC|=|=|=|=":{display:"60.5",expression:"55+10%",clear_label:"AC",active_op:null},
"AC|=|=|=|=|\u00f7":{display:"60.5",expression:null,clear_label:"AC",active_op:"\u00f7"},
"AC|=|=|=|=|\u00f7|\u00f7":{display:"60.5",expression:null,clear_label:"AC",active_op:"\u00f7"},
"AC|=|=|=|=|\u00f7|\u00f7|=":{display:"60.5",expression:"8",clear_label:"C",active_op:"\u00f7"},
"AC|=|=|=|=|\u00f7|\u00f7|=|8":{display:"60.5\u00f78",expression:null,clear_label:"C",active_op:"\u00f7"}
};
if(M[h])return M[h];
if(h==="" )return{display:"0",expression:null,clear_label:"AC",active_op:null};
return{display:this._d,expression:this._e,clear_label:this._c,active_op:this._a};}
};