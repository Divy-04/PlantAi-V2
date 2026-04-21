
const API='';
let hasFile=false,sessionId=null,currentLang='en';
let isRecording=false,recognition=null,_pdfBlob=null;
const HEALTHY=['healthy'];
function isHealthy(n){return HEALTHY.some(h=>(n||'').toLowerCase().includes(h))}
function isValidEmail(email){return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((email||'').trim())}
function escapeHtml(value){return String(value??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}

// Scroll reveal
const observer=new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('visible')}})},{threshold:.15});
document.querySelectorAll('.feature-card,.need-card,.reveal').forEach(el=>observer.observe(el));

const dropZone=document.getElementById('drop-zone');
const fileInput=document.getElementById('file-input');
dropZone.addEventListener('click',()=>{if(!hasFile)fileInput.click()});
fileInput.addEventListener('change',()=>{if(fileInput.files[0])handleFile(fileInput.files[0])});
dropZone.addEventListener('dragover',e=>{e.preventDefault();dropZone.classList.add('dragging')});
dropZone.addEventListener('dragleave',()=>dropZone.classList.remove('dragging'));
dropZone.addEventListener('drop',e=>{e.preventDefault();dropZone.classList.remove('dragging');const f=e.dataTransfer.files[0];if(f){fileInput.files=e.dataTransfer.files;handleFile(f)}});

function handleFile(file){
  const r=new FileReader();
  r.onload=e=>{
    document.getElementById('img-preview').src=e.target.result;
    document.getElementById('img-preview').style.display='block';
    document.getElementById('drop-hint').style.display='none';
    hasFile=true;
    show('analyze-wrap');
    ['results-section','chat-section','error-msg','try-again-wrap'].forEach(hide);
  };
  r.readAsDataURL(file);
}

async function analyzeImage(){
  if(!fileInput.files[0])return;
  hide('analyze-wrap');show('loading-bar');
  ['results-section','chat-section','error-msg'].forEach(hide);
  const fd=new FormData();fd.append('file',fileInput.files[0]);
  try{
    const res=await fetch(`${API}/predict`,{method:'POST',body:fd});
    const data=await res.json();
    if(!res.ok)throw new Error(data.detail||'Prediction failed');
    showResults(data);await startChat(data);
  }catch(e){showError(e.message)}
  finally{hide('loading-bar')}
}

function showResults(data){
  const p=(data.name||'').split('___');
  const display=p.length>1?`${p[0].replace(/_/g,' ')} â€” ${p[1].replace(/_/g,' ')}`:data.name.replace(/_/g,' ');
  document.getElementById('analysis-shell').classList.add('has-result');
  show('results-section');show('try-again-wrap');
  if(isHealthy(data.name)){
    showEl('healthy-banner','flex');hide('disease-cards');
  }else{
    hide('healthy-banner');show('disease-cards');
    document.getElementById('result-name').textContent=display;
    document.getElementById('result-cause').textContent=data.cause||'â€”';
    document.getElementById('result-cure').textContent=data.cure||'â€”';
    document.getElementById('result-confidence').textContent=`${data.confidence}% confidence`;
    document.querySelectorAll('.result-card').forEach(c=>{c.style.animation='none';c.offsetHeight;c.style.animation=''});
  }
  scrollPostAnalysisIntoView();
}

async function startChat(data){
  sessionId=data.session_id;
  show('chat-section');
  document.getElementById('chat-messages').innerHTML='';
  const first={en:`I detected "${fmt(data.name)}" in my plant. Can you explain this disease, symptoms, and treatment?`,hi:`à¤®à¥‡à¤°à¥‡ à¤ªà¥Œà¤§à¥‡ à¤®à¥‡à¤‚ "${fmt(data.name)}" à¤®à¤¿à¤²à¤¾à¥¤ à¤•à¥ƒà¤ªà¤¯à¤¾ à¤‡à¤¸ à¤¬à¥€à¤®à¤¾à¤°à¥€, à¤²à¤•à¥à¤·à¤£ à¤”à¤° à¤‰à¤ªà¤šà¤¾à¤° à¤¬à¤¤à¤¾à¤à¤‚à¥¤`,gu:`àª®àª¾àª°àª¾ àª›à«‹àª¡àª®àª¾àª‚ "${fmt(data.name)}" àª®àª³à«àª¯à«‹. àª•à«ƒàªªàª¾ àª•àª°à«€ àª† àª°à«‹àª—, àªšàª¿àª¹à«àª¨à«‹ àª…àª¨à«‡ àª‰àªªàªšàª¾àª° àª¸àª®àªœàª¾àªµà«‹.`};
  await sendMessage(first[currentLang]||first.en,true);
  scrollPostAnalysisIntoView();
}

async function sendMessage(override,isAuto=false){
  if(!sessionId)return;
  const inp=document.getElementById('chat-input');
  const text=override||inp.value.trim();
  if(!text)return;
  if(!isAuto){appendBubble('user',text);inp.value=''}
  const typing=appendTyping();
  try{
    const res=await fetch(`${API}/chat`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId,message:text,language:currentLang})});
    const data=await res.json();
    typing.remove();
    if(!res.ok)throw new Error(data.detail||'Chat failed');
    appendBubble('ai',data.reply);
  }catch(e){typing.remove();appendBubble('ai','âš ï¸ Error: '+e.message)}
}

function appendBubble(role,text){
  const box=document.getElementById('chat-messages');
  const d=document.createElement('div');d.className=`chat-bubble-wrap ${role}`;
  d.innerHTML=`<div class="chat-bubble">${text.replace(/\n/g,'<br/>')}</div>`;
  box.appendChild(d);box.scrollTop=box.scrollHeight;return d;
}
function appendTyping(){
  const box=document.getElementById('chat-messages');
  const d=document.createElement('div');d.className='chat-bubble-wrap ai';
  d.innerHTML='<div class="chat-bubble typing"><span></span><span></span><span></span></div>';
  box.appendChild(d);box.scrollTop=box.scrollHeight;return d;
}
function promptAssistant(text){sendMessage(text)}

function toggleVoice(){isRecording?stopVoice():startVoice()}
function startVoice(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){alert('Voice input requires Google Chrome.');return}
  recognition=new SR();recognition.lang={en:'en-IN',hi:'hi-IN',gu:'gu-IN'}[currentLang]||'en-IN';recognition.interimResults=false;
  document.getElementById('mic-btn').classList.add('recording');document.getElementById('chat-input').placeholder='ðŸŽ¤ Listening...';isRecording=true;
  recognition.onresult=e=>{const t=e.results[0][0].transcript;document.getElementById('chat-input').value=t;stopVoice();sendMessage(t)};
  recognition.onerror=recognition.onend=()=>stopVoice();recognition.start();
}
function stopVoice(){
  isRecording=false;document.getElementById('mic-btn').classList.remove('recording');
  document.getElementById('chat-input').placeholder='Ask about symptoms, prevention, treatment...';
  if(recognition){recognition.stop();recognition=null}
}

function openReportModal(){
  if(!sessionId){alert('Please analyze a plant image first.');return}
  _pdfBlob=null;document.getElementById('modal-email').value='';document.getElementById('modal-error').style.display='none';
  document.getElementById('modal-step1').style.display='block';document.getElementById('modal-step2').style.display='none';
  document.getElementById('report-modal').classList.add('open');
}
function closeModal(){document.getElementById('report-modal').classList.remove('open')}
document.getElementById('report-modal').addEventListener('click',function(e){if(e.target===this)closeModal()});

async function submitReport(){
  const email=document.getElementById('modal-email').value.trim();
  const errEl=document.getElementById('modal-error');errEl.style.display='none';
  if(!isValidEmail(email)){errEl.textContent='Please enter a valid email address.';errEl.style.display='block';return}
  const btn=document.getElementById('modal-send-btn');
  document.getElementById('modal-send-text').style.display='none';document.getElementById('modal-send-spin').style.display='inline';btn.disabled=true;
  try{
    const res=await fetch(`${API}/export/email`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId,to_email:email})});
    if(!res.ok){const d=await res.json();throw new Error(d.detail||'Failed')}
    const blob=await res.blob();if(blob.type==='application/pdf')_pdfBlob=blob;
    document.getElementById('history-email').value=email;
    document.getElementById('modal-success-msg').textContent=`Report sent to ${email}. Download a local copy below.`;
    document.getElementById('modal-step1').style.display='none';document.getElementById('modal-step2').style.display='block';
  }catch(e){errEl.textContent='âš ï¸ '+e.message;errEl.style.display='block'}
  finally{document.getElementById('modal-send-text').style.display='inline';document.getElementById('modal-send-spin').style.display='none';btn.disabled=false}
}
function resetHistoryView(){
  hide('history-loading');hide('history-empty');hide('history-results');
  const errEl=document.getElementById('history-error');
  errEl.style.display='none';errEl.textContent='';
}
function renderHistoryResults(rows){
  const resultsEl=document.getElementById('history-results');
  if(!rows.length){show('history-empty');hide('history-results');return}
  resultsEl.innerHTML=rows.map((row,index)=>{
    const plant=row.plant_common_name||row.plant_species||'Plant scan';
    const species=row.plant_species&&row.plant_species!==plant?`<p class="history-item-copy">${escapeHtml(row.plant_species)}</p>`:'';
    const confidence=(typeof row.confidence==='number'&&Number.isFinite(row.confidence))?`<span>${row.confidence.toFixed(1)}% confidence</span>`:'';
    const lowConfidence=row.low_confidence?'<span class="history-flag warn">Low confidence</span>':'';
    return `<article class="history-item">
      <div class="history-item-top">
        <div>
          <p class="history-item-label">Report ${index+1}</p>
          <h3 class="history-item-title">${escapeHtml(fmt(row.disease||'Unknown disease'))}</h3>
        </div>
        <span class="history-date">${fmtDate(row.created_at)}</span>
      </div>
      <p class="history-item-plant">${escapeHtml(plant)}</p>
      ${species}
      <div class="history-meta">
        ${confidence}
        ${lowConfidence}
      </div>
    </article>`;
  }).join('');
  hide('history-empty');show('history-results');
}
async function lookupHistory(){
  const email=document.getElementById('history-email').value.trim();
  resetHistoryView();
  if(!isValidEmail(email)){
    const errEl=document.getElementById('history-error');
    errEl.textContent='Please enter a valid email address.';
    errEl.style.display='block';
    return;
  }
  show('history-loading');
  try{
    const res=await fetch(`${API}/history/email`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});
    const data=await res.json();
    if(!res.ok)throw new Error(data.detail||'Failed to load history');
    renderHistoryResults(data.history||[]);
  }catch(e){
    const errEl=document.getElementById('history-error');
    errEl.textContent='Error: '+e.message;
    errEl.style.display='block';
  }finally{
    hide('history-loading');
  }
}
function downloadFromBlob(){
  if(!_pdfBlob){fetch(`${API}/export/pdf?session_id=${sessionId}`).then(r=>r.blob()).then(b=>triggerDownload(b));return}
  triggerDownload(_pdfBlob);
}
function triggerDownload(blob){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='plant_disease_report.pdf';a.click();URL.revokeObjectURL(url)}

function switchLanguage(){currentLang=document.getElementById('lang-select').value}
function fmt(raw){const p=(raw||'').split('___');return p.length>1?`${p[0].replace(/_/g,' ')} â€” ${p[1].replace(/_/g,' ')}`:raw.replace(/_/g,' ')}
function scrollSectionIntoView(id,gap=18){
  const el=document.getElementById(id);
  const nav=document.querySelector('nav');
  if(!el)return;
  const navHeight=nav?nav.offsetHeight:0;
  const top=el.getBoundingClientRect().top+window.scrollY-navHeight-gap;
  window.scrollTo({top:Math.max(0,top),behavior:'smooth'});
}
function scrollPostAnalysisIntoView(){
  const isMobile=window.innerWidth<=768;
  scrollSectionIntoView(isMobile?'chat-section':'analysis-shell',isMobile?10:22);
}
function show(id){document.getElementById(id).style.display='block'}
function hide(id){document.getElementById(id).style.display='none'}
function showEl(id,d='block'){document.getElementById(id).style.display=d}
function showError(msg){const el=document.getElementById('error-msg');el.textContent='âš ï¸ '+msg;el.style.display='block';show('analyze-wrap')}
function resetAll(){
  hasFile=false;sessionId=null;_pdfBlob=null;fileInput.value='';
  document.getElementById('analysis-shell').classList.remove('has-result');
  document.getElementById('img-preview').style.display='none';document.getElementById('drop-hint').style.display='block';
  ['analyze-wrap','results-section','healthy-banner','disease-cards','chat-section','try-again-wrap','error-msg'].forEach(hide);
  document.getElementById('chat-messages').innerHTML='';stopVoice();window.scrollTo({top:0,behavior:'smooth'});
}

const nav=document.querySelector('nav');
const navToggle=nav?.querySelector('.nav-toggle');
const navLinks=nav?.querySelector('.nav-links');
if(nav&&navToggle&&navLinks){
  const syncNavState=(isOpen)=>{
    nav.classList.toggle('nav-open',isOpen);
    navToggle.setAttribute('aria-expanded',String(isOpen));
  };
  navToggle.addEventListener('click',()=>{
    syncNavState(!nav.classList.contains('nav-open'));
  });
  navLinks.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>{
    syncNavState(false);
  }));
  window.addEventListener('resize',()=>{
    if(window.innerWidth>768){
      syncNavState(false);
    }
  });
}
const scrollTopBtn=document.getElementById('scroll-top-btn');
const toggleScrollTopBtn=()=>{
  if(!scrollTopBtn)return;
  const scrollable=Math.max(document.documentElement.scrollHeight-window.innerHeight,1);
  const progress=window.scrollY/scrollable;
  scrollTopBtn.classList.toggle('visible',window.innerWidth<=768&&progress>=0.4);
};
window.addEventListener('scroll',toggleScrollTopBtn,{passive:true});
window.addEventListener('resize',toggleScrollTopBtn);
toggleScrollTopBtn();
