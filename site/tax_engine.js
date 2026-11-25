/* Aeterna income tax engine: individuals, FY 2026-27 (AY 2027-28), old and new regimes.
   Rules last checked 25 Nov 2026 (Income-tax Act, 2025 in force from 1 Apr 2026; Budget 2026 left slabs and limits unchanged).
   One source of truth: the calculator page loads this file; tests/test_tax_engine.py runs it with node.
   All amounts in rupees a year. Not covered: agricultural income, HUFs, firms, AMT, foreign tax credit, clubbing. */
const TAXRULES={fy:'2026-27',checked:'25 Nov 2026',
 newSlabs:[[4e5,0],[8e5,.05],[12e5,.10],[16e5,.15],[20e5,.20],[24e5,.25],[null,.30]],
 oldSlabs:{'<60':[[2.5e5,0],[5e5,.05],[10e5,.20],[null,.30]],'60-79':[[3e5,0],[5e5,.05],[10e5,.20],[null,.30]],'80+':[[5e5,0],[10e5,.20],[null,.30]]},
 sur:[[5e7,.37],[2e7,.25],[1e7,.15],[5e6,.10]],cess:.04,
 stdNew:75000,stdOld:50000,rebNew:[12e5,60000],rebOld:[5e5,12500],ltcgEx:125000,
 r111A:.20,r112A:.125,r112:.125,rVDA:.30,rLottery:.30};

function txSlabTax(x,S){let t=0,lo=0;for(const [hi,r] of S){const top=hi==null?x:Math.min(x,hi);if(top>lo)t+=(top-lo)*r;if(hi==null||x<=hi)break;lo=hi}return t}
const n0=v=>Math.max(0,+v||0);

function txHRA(p){/* HRA exemption, old regime: least of HRA received, rent paid minus 10% of salary, 50% (metro) or 40% of salary; salary = basic + DA */
 const s=n0(p.basic),h=n0(p.hraRecd),r=n0(p.rent);if(!h||!r)return 0;
 return Math.max(0,Math.min(h,r-.1*s,(p.metro?.5:.4)*s))}

function txBase(p,regime,cut){
 cut=cut||0;const R=TAXRULES,res=p.resident!==false,age=p.age||'<60',NEW=regime==='new',L=[];
 // salary
 const sal=n0(p.salary),std=sal>0?Math.min(sal,NEW?R.stdNew:R.stdOld):0;
 const hra=NEW?0:Math.min(txHRA(p),sal);
 const ptax=NEW?0:Math.min(n0(p.profTax),2500);
 const salInc=Math.max(0,sal-std-hra-ptax);
 // house property
 const letRent=n0(p.letRent),munic=n0(p.municipal),nav=Math.max(0,letRent-munic);
 const letInc=nav*.7-n0(p.letInterest);                 // 30% standard deduction, less interest on the let-out home
 const selfInt=NEW?0:Math.min(n0(p.selfInterest),200000);
 let hp=letInc-selfInt;
 if(hp<0)hp=NEW?0:Math.max(hp,-200000);                 // loss: none set off in the new regime; up to 2 lakh in the old
 // other heads at slab rates
 const biz=n0(p.business),oth=n0(p.interestSav)+n0(p.interestFD)+n0(p.dividends)+n0(p.otherIncome)+n0(p.stcgSlab);
 const gtiNormal=Math.max(0,salInc+hp+biz+oth);
 // special-rate income
 let s111A=n0(p.stcg111A),l112A=n0(p.ltcg112A),l112=n0(p.ltcgOther),vda=n0(p.vda),lot=n0(p.lottery);
 const special=s111A+l112A+l112+vda+lot;
 // deductions (chapter VIA; the new Act keeps the same limits under new section numbers)
 let ded=0;const D=[];const add=(k,v)=>{v=Math.max(0,Math.round(v));if(v){ded+=v;D.push([k,v])}};
 const empNPS=Math.min(n0(p.employerNPS),(NEW?.14:.10)*n0(p.basic||p.salary));
 add('Employer NPS, 80CCD(2)',empNPS);
 if(!NEW){
  add('80C (EPF, PPF, ELSS, insurance, principal)',Math.min(n0(p.c80),150000));
  add('NPS, 80CCD(1B)',Math.min(n0(p.nps1b),50000));
  const sen=age!=='<60';
  add('Health insurance, 80D (self and family)',Math.min(n0(p.d80self),sen?50000:25000));
  add('Health insurance, 80D (parents)',Math.min(n0(p.d80parents),p.parentsSenior?50000:25000));
  add('Education loan interest, 80E',n0(p.e80));
  add('Donations, 80G (eligible amount)',n0(p.g80));
  add('Disability, 80U/80DD',n0(p.u80));
  if(res&&sen)add('Deposit interest, 80TTB',Math.min(n0(p.interestSav)+n0(p.interestFD),50000));
  else add('Savings interest, 80TTA',Math.min(n0(p.interestSav),10000));
  add('Other deductions',n0(p.otherDed));
 }
 ded=Math.min(ded,gtiNormal);                           // deductions do not reduce special-rate gains
 let normal=Math.max(0,gtiNormal-ded);const cutN=Math.min(cut,normal);normal-=cutN;
 const total=normal+special;
 // tax on normal income
 const S=NEW?R.newSlabs:R.oldSlabs[res?age:'<60'];      // higher old-regime exemption for seniors is for residents only
 let tN=txSlabTax(normal,S);
 // unused basic exemption absorbs 111A, then 112A gains (residents only)
 const exLimit=S[0][0];let gap=res?Math.max(0,exLimit-normal):0;
 const a111=Math.min(gap,s111A);gap-=a111;
 const l112Atax=Math.max(0,l112A-R.ltcgEx);const a112=Math.min(gap,l112Atax);gap-=a112;
 const t111=(s111A-a111)*R.r111A,t112A=(l112Atax-a112)*R.r112A,t112=l112*R.r112,tVDA=vda*R.rVDA,tLot=lot*R.rLottery;
 const tSpecial=t111+t112A+t112+tVDA+tLot;
 // rebate (residents only)
 let reb=0;
 if(res){if(NEW){if(total<=R.rebNew[0])reb=Math.min(tN,R.rebNew[1]);else {/* marginal relief: tax on slab income need not exceed the income above 12 lakh */
     const over=total-R.rebNew[0];if(tN>over)reb=tN-over}}
  else if(total<=R.rebOld[0])reb=Math.min(tN+t111,R.rebOld[1])}  // old regime: rebate also covers 111A tax, not 112A
 let tax=Math.max(0,tN+tSpecial-reb);
 return {regime,gross:sal+letRent+biz+oth+special,salInc,hp,gtiNormal,ded,D,normal,special,total,tN,tSpecial,t111,t112A,t112,tVDA,tLot,reb,tax,hra,std};
}

function txSur(b,regime,th,r){/* surcharge at rate r; tax on capital gains (111A, 112A, 112) capped at 15% */
 const cg=b.t111+b.t112A+b.t112;return Math.max(0,b.tax-cg)*r+cg*Math.min(r,.15)}

function txCompute(p,regime){
 const R=TAXRULES,NEW=regime==='new',cap=NEW?.25:.37,b=txBase(p,regime);let sur=0;
 for(let k=0;k<R.sur.length;k++){const [th,r0]=R.sur[k];if(b.total>th){
   sur=txSur(b,regime,th,Math.min(r0,cap));
   // marginal relief: tax plus surcharge may exceed the tax at the threshold by no more than the income above it
   const at=txBase(p,regime,b.total-th),nx=R.sur[k+1],atTax=at.tax+(nx?txSur(at,regime,nx[0],Math.min(nx[1],cap)):0);
   sur=Math.max(0,Math.min(sur,atTax+(b.total-th)-b.tax));break}}
 const preCess=b.tax+sur,cess=preCess*R.cess,payable=Math.round(preCess+cess);
 return {...b,sur,cess,preCess,payable,eff:b.total?payable/b.total:0};
}

function txBoth(p){const N=txCompute(p,'new'),O=txCompute(p,'old');return {N,O,best:O.payable<N.payable?'old':'new',saving:Math.abs(N.payable-O.payable)}}
if(typeof module!=='undefined')module.exports={TAXRULES,txCompute,txBoth,txHRA,txSlabTax};
