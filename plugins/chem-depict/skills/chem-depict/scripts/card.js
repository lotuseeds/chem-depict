/* chem-depict 结构式卡片交互：复制 SMILES / 复制图片 / 下载 SVG
   导出规格：ACS Document 1996 印刷尺寸（平均键长 = 14.4 pt，见 svg 的 data-bond）、透明背景、裁到内容边界（data-bbox）、
   PNG 600 dpi（补写 pHYs）。剪贴板同时写 PNG 与 SVG，Word 会收下 SVG 矢量。 */
(function(){
  var DPI=600, ACS_BOND_PT=14.4;
  var OK='<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 8.5l3 3 6-7"/></svg>';
  var ERR='<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 4.5l7 7M11.5 4.5l-7 7"/></svg>';
  function flash(b,ok){if(b._busy)return;b._busy=1;var o=b.innerHTML;b.innerHTML=ok?OK:ERR;b.classList.add(ok?'ok':'err');
    setTimeout(function(){b.innerHTML=o;b.classList.remove('ok','err');b._busy=0;},1500);}
  function exportSvg(svg){
    var c=svg.cloneNode(true), vb=svg.viewBox.baseVal, k=svg.width.baseVal.value/vb.width;
    var bb=(svg.getAttribute('data-bbox')||'').trim().split(/\s+/).map(Number);
    if(bb.length!==4||bb.some(isNaN)) bb=[vb.x,vb.y,vb.width,vb.height];
    c.setAttribute('viewBox',bb.join(' '));
    var bg=c.querySelector('rect'); if(bg&&/fill:\s*#FFFFFF/i.test(bg.getAttribute('style')||'')) bg.parentNode.removeChild(bg);
    var bond=parseFloat(svg.getAttribute('data-bond')), ptu=(bond>0)?ACS_BOND_PT/bond:k*0.75, wp=bb[2]*ptu, hp=bb[3]*ptu;
    c.setAttribute('width',wp.toFixed(2)+'pt'); c.setAttribute('height',hp.toFixed(2)+'pt');
    c.removeAttribute('data-bbox'); c.removeAttribute('data-bond');
    var s=new XMLSerializer().serializeToString(c);
    if(s.indexOf('xmlns=')<0) s=s.replace('<svg','<svg xmlns="http://www.w3.org/2000/svg"');
    return {text:'<?xml version="1.0" encoding="UTF-8"?>'+String.fromCharCode(10)+s, wPt:wp, hPt:hp};
  }
  var CRC=(function(){var t=[];for(var n=0;n<256;n++){var c=n;for(var j=0;j<8;j++)c=c&1?0xEDB88320^(c>>>1):c>>>1;t[n]=c>>>0;}return t;})();
  function crc32(u8){var c=0xFFFFFFFF;for(var i=0;i<u8.length;i++)c=CRC[(c^u8[i])&255]^(c>>>8);return (c^0xFFFFFFFF)>>>0;}
  function withDpi(blob,dpi){return blob.arrayBuffer().then(function(buf){
    var src=new Uint8Array(buf), ppm=Math.round(dpi/0.0254), at=33;
    var ch=new Uint8Array(21), dv=new DataView(ch.buffer);
    dv.setUint32(0,9); ch.set([0x70,0x48,0x59,0x73],4); dv.setUint32(8,ppm); dv.setUint32(12,ppm); ch[16]=1;
    dv.setUint32(17,crc32(ch.subarray(4,17)));
    var out=new Uint8Array(src.length+21); out.set(src.subarray(0,at)); out.set(ch,at); out.set(src.subarray(at),at+21);
    return new Blob([out],{type:'image/png'});});}
  function toPng(ex){return new Promise(function(res,rej){
    var W=Math.round(ex.wPt*DPI/72), H=Math.round(ex.hPt*DPI/72), img=new Image();
    var url=URL.createObjectURL(new Blob([ex.text],{type:'image/svg+xml'}));
    img.onload=function(){var c=document.createElement('canvas');c.width=W;c.height=H;
      c.getContext('2d').drawImage(img,0,0,W,H); URL.revokeObjectURL(url);
      c.toBlob(function(b){b?res(withDpi(b,DPI)):rej(new Error('toBlob'));},'image/png');};
    img.onerror=function(e){URL.revokeObjectURL(url);rej(e);};img.src=url;});}
  function save(blob,name){var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;
    document.body.appendChild(a);a.click();setTimeout(function(){URL.revokeObjectURL(a.href);a.remove();},500);}
  document.addEventListener('click',function(e){
    var b=e.target.closest('.ibtns .ib'); if(!b) return;
    if(b.classList.contains('smi')){
      var t=b.getAttribute('data-smiles');
      var fb=function(){var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();
        try{document.execCommand('copy');flash(b,true);}catch(x){prompt('请手动复制 SMILES：',t);}document.body.removeChild(a);};
      if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(function(){flash(b,true);},fb);}else{fb();}
      return;}
    var svg=b.closest('.sv').querySelector('svg[data-bbox]'), name=b.getAttribute('data-name')||'structure', ex=exportSvg(svg);
    if(b.classList.contains('dsvg')){save(new Blob([ex.text],{type:'image/svg+xml'}),name+'.svg');flash(b,true);return;}
    var png=toPng(ex);
    if(navigator.clipboard&&window.ClipboardItem&&window.isSecureContext){
      var items={'image/png':png};
      try{if(ClipboardItem.supports&&ClipboardItem.supports('image/svg+xml'))items['image/svg+xml']=new Blob([ex.text],{type:'image/svg+xml'});}catch(x){}
      navigator.clipboard.write([new ClipboardItem(items)]).then(function(){flash(b,true);},
        function(){png.then(function(p){save(p,name+'.png');flash(b,false);});});
    }else{png.then(function(p){save(p,name+'.png');flash(b,false);});}
  });
})();
