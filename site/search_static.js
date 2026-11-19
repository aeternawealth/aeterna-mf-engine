/* Search on the static pages (fund, category, stock, calculator, guide pages): opens on the page itself instead of
   sending the visitor to the home page. Reads /data/search.json (funds, stocks, pages), built by build_site.py.
   Same results and keys as the app's own search (site/app.html, drawSearch). */
(function(){
  var D=null,loading=false;
  var esc=function(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})};
  var TC={'A+':'t-ap','A':'t-a','B':'t-b','C':'t-c'};
  var tier=function(t){return '<span class="tier '+(TC[t]||'t-u')+'">'+esc(t&&t!=='Unrated'?t:'–')+'</span>'};
  var o,q,res;
  function build(){
    o=document.createElement('div');o.className='overlay';o.id='srch';o.hidden=true;
    o.setAttribute('role','dialog');o.setAttribute('aria-modal','true');o.setAttribute('aria-label','Search');
    o.innerHTML='<div class="palette"><input id="srchQ" type="search" placeholder="Search a fund, fund house, stock or page…" autocomplete="off" aria-label="Search"><div class="res" id="srchRes"></div></div>';
    document.body.appendChild(o);q=o.querySelector('#srchQ');res=o.querySelector('#srchRes');
    o.addEventListener('click',function(e){if(e.target===o)close()});
    q.addEventListener('input',function(){draw(q.value)});
    q.addEventListener('keydown',function(e){
      var as=[].slice.call(res.querySelectorAll('a')),i=-1;as.forEach(function(a,j){if(a.getAttribute('aria-selected')==='true')i=j});
      if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();if(!as.length)return;i=(i+(e.key==='ArrowDown'?1:-1)+as.length)%as.length;
        as.forEach(function(a,j){a.setAttribute('aria-selected',j===i)});as[i].scrollIntoView({block:'nearest'})}
      else if(e.key==='Enter'){var a=as[i>=0?i:0];if(a){e.preventDefault();location.href=a.getAttribute('href')}}
      else if(e.key==='Escape')close()});
  }
  function load(){if(D||loading)return;loading=true;
    fetch('/data/search.json').then(function(r){return r.json()}).then(function(d){D=d;if(o&&!o.hidden)draw(q.value)})
    .catch(function(){loading=false;res.innerHTML='<p class="muted" style="padding:14px">Search could not load. <a href="/?q=">Open search on the home page</a>.</p>'})}
  function draw(v){
    var t=v.toLowerCase().trim().split(/\s+/).filter(Boolean),has=function(h){h=h.toLowerCase();return t.every(function(w){return h.indexOf(w)>=0})};
    if(!D){res.innerHTML='<p class="muted" style="padding:14px">Loading…</p>';return}
    var pg=D.p.filter(function(p){return !t.length||has(p[0]+' '+p[2])}).slice(0,t.length?4:8);
    var fs=t.length?D.f.filter(function(f){return has(f[0]+' '+f[3]+' '+f[2]+' '+f[1])})
      .sort(function(a,b){return (a[1]==='Regular'?0:1)-(b[1]==='Regular'?0:1)||(b[6]||0)-(a[6]||0)}).slice(0,10):[];
    var st=t.length?D.s.filter(function(x){return has(x[0])}).slice(0,5):[];
    var ext=function(h){return /^http/.test(h)?' target="_blank" rel="noopener"':''};
    res.innerHTML=(fs.length?'<div class="grp">Funds</div>'+fs.map(function(f){return '<a href="'+f[5]+'"><span style="min-width:0"><span style="display:block">'+esc(f[0])+'</span><small>'+esc(f[1])+' · '+esc(f[2])+'</small></span>'+tier(f[4])+'</a>'}).join(''):'')
      +(st.length?'<div class="grp">Stocks: which funds hold it</div>'+st.map(function(x){return '<a href="'+x[1]+'"><span>'+esc(x[0])+'</span><small>'+x[2]+' schemes hold it</small></a>'}).join(''):'')
      +(pg.length?'<div class="grp">Pages</div>'+pg.map(function(p){return '<a href="'+p[1]+'"'+ext(p[1])+'><span>'+esc(p[0])+'</span><small>'+esc(p[2])+'</small></a>'}).join(''):'')
      ||'<p class="muted" style="padding:14px">No match. Try a fund house, like "HDFC", a category, like "small cap", or a stock, like "Reliance".</p>';
  }
  function open(){if(!o)build();o.hidden=false;q.value='';draw('');load();setTimeout(function(){q.focus()},10)}
  function close(){if(o){o.hidden=true;q.blur()}}
  window.aeSearch=open;
  document.addEventListener('keydown',function(e){if(e.key==='Escape'&&o&&!o.hidden)close()});
})();
