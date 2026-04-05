// State
const state = {
  script: null,
  panelLayouts: [],
  activeView: 'write',
  currentPage: 0,
  readingDirection: 'rtl',
  isGenerating: false,
  agents: []
};

// DOM Elements
const views = {
  write: document.getElementById('view-write'),
  script: document.getElementById('view-script'),
  layout: document.getElementById('view-layout'),
  export: document.getElementById('view-export')
};

const DOM = {
  statusDot: document.getElementById('agent-status-dot'),
  statusTooltip: document.getElementById('agent-status-tooltip'),
  generateBtn: document.getElementById('generate-btn'),
  agentEmptyState: document.getElementById('agent-empty-state'),
  agentPipeline: document.getElementById('agent-pipeline-container'),
  agentsList: document.getElementById('agents-list'),
  pipelineStatus: document.getElementById('pipeline-status'),
  scriptEmpty: document.getElementById('script-empty'),
  scriptContent: document.getElementById('script-content'),
  scriptTabs: document.getElementById('script-tabs'),
  scriptPageContent: document.getElementById('script-page-content'),
  exportEmpty: document.getElementById('export-empty'),
  exportOptions: document.getElementById('export-options'),
  previewPanel: document.getElementById('preview-panel'),
  miniCanvas: document.getElementById('mini-canvas-wrapper'),
  fullCanvas: document.getElementById('layout-full-canvas-container'),
  canvasControls: document.getElementById('mini-canvas-controls'),
  pageIndicator: document.getElementById('page-indicator'),
  readingIndicator: document.getElementById('reading-dir-badge')
};

// --- NAVIGATION ---
document.querySelectorAll('.nav-btn[data-view]').forEach(btn => {
  btn.addEventListener('click', () => {
    state.activeView = btn.getAttribute('data-view');
    document.querySelectorAll('.nav-btn[data-view]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    // Switch views but keep display flex
    Object.keys(views).forEach(v => {
      views[v].style.display = (v === state.activeView) ? 'flex' : 'none';
    });

    if (state.activeView === 'write' || state.activeView === 'script') {
       DOM.previewPanel.style.display = 'flex';
       renderCanvas(DOM.miniCanvas);
    } else {
       DOM.previewPanel.style.display = 'none';
       if(state.activeView === 'layout') {
          renderCanvas(DOM.fullCanvas);
       }
    }
  });
});

// --- GENERATION ---
DOM.generateBtn.addEventListener('click', async () => {
   if (state.isGenerating) return;
   
   const outline = document.getElementById('story-outline-input').value;
   if (!outline.trim()) return;

   const genre = document.getElementById('genre-select').value;
   const style = document.getElementById('format-select').value;
   const pages = document.getElementById('pages-input').value;
   state.readingDirection = document.getElementById('direction-select').value;
   
   DOM.readingIndicator.textContent = state.readingDirection === 'rtl' ? 'RTL ←' : 'LTR →';

   startGeneration();

   try {
      const response = await fetch('/api/generate', {
         method: 'POST',
         headers: {'Content-Type': 'application/json'},
         body: JSON.stringify({
            outline, genre, style, pages_per_chapter: parseInt(pages), reading_direction: state.readingDirection
         })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while(true) {
         const {value, done} = await reader.read();
         if (done) break;
         buffer += decoder.decode(value, {stream: true});
         let parts = buffer.split('\n\n');
         buffer = parts.pop();

         for (let part of parts) {
            if (part.startsWith('data: ')) {
               try {
                  const data = JSON.parse(part.substring(6));
                  handleEvent(data);
               } catch(e) {}
            }
         }
      }
      endGeneration();
   } catch(e) {
      console.error(e);
      endGeneration();
   }
});

function startGeneration() {
   state.isGenerating = true;
   state.agents = [];
   state.script = null;
   state.panelLayouts = [];
   state.currentPage = 0;
   
   DOM.generateBtn.innerHTML = `Generating...`;
   DOM.generateBtn.disabled = true;
   
   DOM.agentEmptyState.style.display = 'none';
   DOM.agentPipeline.style.display = 'flex';
   DOM.agentsList.innerHTML = '';
   
   DOM.statusDot.style.display = 'block';
   DOM.statusTooltip.textContent = 'AI Working...';
}

function endGeneration() {
   state.isGenerating = false;
   DOM.generateBtn.innerHTML = `Generate Script`;
   DOM.generateBtn.disabled = false;
   DOM.pipelineStatus.style.display = 'none';
   
   DOM.statusDot.style.display = 'none';
   DOM.statusTooltip.textContent = 'AI Ready';
   
   if(state.script) {
      renderScriptView();
      renderExportView();
      renderCanvas(DOM.miniCanvas);
   }
}

// --- EVENT HANDLING ---
function handleEvent(data) {
   if (data.event === 'agent_start') {
      let agent = state.agents.find(a => a.id === data.agent_id);
      if(!agent) {
         agent = { id: data.agent_id, name: data.agent_name, status: data.status, output: '' };
         state.agents.push(agent);
      } else {
         agent.status = data.status;
      }
      renderAgents();
   } 
   else if (data.event === 'agent_chunk') {
      let agent = state.agents.find(a => a.id === data.agent_id);
      if(agent) {
         agent.output += data.content;
         const outputEl = document.getElementById(`agent-out-${agent.id}`);
         if(outputEl) {
            outputEl.textContent = agent.output;
            outputEl.scrollTop = outputEl.scrollHeight;
         }
      }
   }
   else if (data.event === 'agent_complete') {
      let agent = state.agents.find(a => a.id === data.agent_id);
      if(agent) {
         agent.status = 'done';
         renderAgents();
      }
   }
   else if (data.event === 'script' || data.event === 'complete') {
      if(data.script) state.script = data.script;
      if(data.pages) state.panelLayouts = data.pages;
   }
   else if (data.event === 'error') {
      alert("Backend Error: " + data.message);
      console.error("Backend Error:", data.message);
   }
}

// --- RENDERERS ---
const AGENT_ICONS = { writer: '✍️', pacer: '📐', polisher: '💎' };
const AGENT_ROLES = { writer: 'Lead Writer', pacer: 'Pacing Editor', polisher: 'Dialogue Polisher'};

function renderAgents() {
   DOM.agentsList.innerHTML = state.agents.map(a => {
      const isThinking = a.status === 'thinking';
      const isDone = a.status === 'done';
      return `
         <div class="agent-card animate-fade-in ${isThinking ? 'agent-active' : ''} ${isDone ? 'agent-done' : ''}">
            <div class="agent-card-header">
               <div class="agent-avatar ${a.id}">${AGENT_ICONS[a.id] || '🤖'}</div>
               <div class="agent-info">
                  <div class="agent-name">${a.name}</div>
                  <div class="agent-role">${AGENT_ROLES[a.id]}</div>
               </div>
               <span class="badge ${isThinking ? 'badge-thinking' : isDone ? 'badge-done' : 'badge-idle'}">
                  <span class="status-dot ${a.status}"></span>
                  ${isThinking ? 'Thinking' : isDone ? 'Complete' : 'Waiting'}
               </span>
            </div>
            ${(a.output || isThinking) ? `
            <div class="agent-card-body">
               <div class="agent-output ${isThinking ? 'typing-cursor' : ''}" id="agent-out-${a.id}">${a.output}</div>
            </div>` : ''}
         </div>
      `;
   }).join('');
}

function renderScriptView() {
   if(!state.script || !state.script.pages) {
      DOM.scriptEmpty.style.display = 'flex';
      DOM.scriptContent.style.display = 'none';
      return;
   }
   DOM.scriptEmpty.style.display = 'none';
   DOM.scriptContent.style.display = 'block';
   
   // Tabs
   DOM.scriptTabs.innerHTML = state.script.pages.map((p, i) => `
      <button class="tab ${state.currentPage === i ? 'active' : ''}" onclick="changePage(${i})" style="flex-shrink:0;">Page ${i+1}</button>
   `).join('');

   // Page Content
   const page = state.script.pages[state.currentPage];
   if(!page) return;

   const panelsHtml = (page.panels || []).map((panel, j) => `
      <div class="script-panel">
         <div class="script-panel-header">Panel ${j+1} 
            ${panel.type ? `<span class="badge badge-genre" style="margin-left:8px">${panel.type}</span>` : ''}
            ${panel.size ? `<span class="badge badge-idle" style="margin-left:4px">${panel.size}</span>` : ''}
         </div>
         ${panel.description ? `<div class="script-panel-desc">${panel.description}</div>` : ''}
         ${(panel.dialogue || []).map(d => `
            <div class="script-dialogue">
               <div class="script-dialogue-char">${d.character}</div>
               <div class="script-dialogue-text">${d.text}</div>
            </div>`).join('')}
         ${(panel.sfx || []).length ? `<div style="margin-top:8px">${panel.sfx.map(s => `<span class="script-sfx">${s}</span>`).join('')}</div>` : ''}
      </div>
   `).join('');

   DOM.scriptPageContent.innerHTML = `
      <div class="script-page-title">Page ${state.currentPage + 1}</div>
      ${panelsHtml}
   `;
}

window.changePage = function(index) {
   state.currentPage = index;
   renderScriptView();
   if(state.activeView === 'layout') renderCanvas(DOM.fullCanvas);
   else renderCanvas(DOM.miniCanvas);
};

// Canvas Navigation Listeners
document.getElementById('prev-page-btn').addEventListener('click', () => {
   if(state.currentPage > 0) changePage(state.currentPage - 1);
});
document.getElementById('next-page-btn').addEventListener('click', () => {
   if(state.currentPage < state.panelLayouts.length - 1) changePage(state.currentPage + 1);
});

function renderCanvas(container) {
   if(!state.panelLayouts || state.panelLayouts.length === 0) {
      container.innerHTML = `<div class="empty-state"><p style="font-size:0.8rem">Generate a script to see layouts</p></div>`;
      if(container.id === 'mini-canvas-wrapper') DOM.canvasControls.style.display = 'none';
      return;
   }

   const pageData = state.panelLayouts[state.currentPage];
   if(!pageData) return;

   if(container.id === 'mini-canvas-wrapper') {
      DOM.canvasControls.style.display = 'flex';
      DOM.pageIndicator.textContent = `${state.currentPage + 1} / ${state.panelLayouts.length}`;
   }

   const rect = container.getBoundingClientRect();
   const padding = 32;
   const availW = Math.max(300, rect.width - padding);
   const availH = Math.max(400, rect.height - padding - (container.id==='mini-canvas-wrapper'?60:0));
   
   let canvasW, canvasH;
   const PAGE_ASPECT = 1.414;
   if (availW / availH > 1 / PAGE_ASPECT) {
      canvasH = Math.min(availH, 700);
      canvasW = canvasH / PAGE_ASPECT;
   } else {
      canvasW = Math.min(availW, 500);
      canvasH = canvasW * PAGE_ASPECT;
   }

   const SVG_NS = "http://www.w3.org/2000/svg";
   const svg = document.createElementNS(SVG_NS, "svg");
   svg.setAttribute("width", canvasW);
   svg.setAttribute("height", canvasH);
   svg.setAttribute("viewBox", `0 0 ${canvasW} ${canvasH}`);
   svg.style.display = "block";

   const bg = document.createElementNS(SVG_NS, "rect");
   bg.setAttribute("width", canvasW);
   bg.setAttribute("height", canvasH);
   bg.setAttribute("fill", "#1a1a2e");
   bg.setAttribute("rx", "4");
   svg.appendChild(bg);

   const GUTTER = 6;
   const isRTL = state.readingDirection === 'rtl';

   (pageData.panels || []).forEach((panel, i) => {
      const layout = panel.layout || {x:0, y:0, w:1, h:1};
      const px = layout.x * (canvasW - GUTTER * 2) + GUTTER;
      const py = layout.y * (canvasH - GUTTER * 2) + GUTTER;
      const pw = layout.w * (canvasW - GUTTER * 2) - GUTTER;
      const ph = layout.h * (canvasH - GUTTER * 2) - GUTTER;

      const g = document.createElementNS(SVG_NS, "g");
      
      const rect = document.createElementNS(SVG_NS, "rect");
      rect.setAttribute("x", px); rect.setAttribute("y", py);
      rect.setAttribute("width", pw); rect.setAttribute("height", ph);
      rect.setAttribute("fill", "#12121a");
      rect.setAttribute("stroke", "#2a2a3e");
      rect.setAttribute("rx", "3");
      g.appendChild(rect);

      const num = document.createElementNS(SVG_NS, "text");
      num.setAttribute("x", px + 8); num.setAttribute("y", py + 16);
      num.setAttribute("fill", "#55556a"); num.setAttribute("font-size", "10");
      num.setAttribute("font-family", "JetBrains Mono");
      num.textContent = i + 1;
      g.appendChild(num);

      if(panel.type && pw > 60) {
         const type = document.createElementNS(SVG_NS, "text");
         type.setAttribute("x", px + pw/2); type.setAttribute("y", py + ph/2 - 6);
         type.setAttribute("fill", "#55556a"); type.setAttribute("font-size", "9");
         type.setAttribute("text-anchor", "middle");
         type.textContent = panel.type;
         g.appendChild(type);
      }

      svg.appendChild(g);
   });

   container.innerHTML = '';
   if(container.id === 'layout-full-canvas-container') {
      const wrapper = document.createElement('div');
      wrapper.className = 'canvas-wrapper';
      wrapper.appendChild(svg);
      container.appendChild(wrapper);
      
      const ctrl = document.createElement('div');
      ctrl.className = 'canvas-controls';
      ctrl.innerHTML = `
         <div class="page-nav">
            <button class="btn-icon" onclick="changePage(Math.max(0, ${state.currentPage-1}))">←</button>
            <span style="font-family:monospace">${state.currentPage + 1} / ${state.panelLayouts.length}</span>
            <button class="btn-icon" onclick="changePage(Math.min(${state.panelLayouts.length-1}, ${state.currentPage+1}))">→</button>
         </div>`;
      container.appendChild(ctrl);
   } else {
      container.appendChild(svg);
   }
}

// Window resize re-renders canvas
window.addEventListener('resize', () => {
   if(state.activeView === 'write' || state.activeView === 'script') renderCanvas(DOM.miniCanvas);
   if(state.activeView === 'layout') renderCanvas(DOM.fullCanvas);
});

// --- EXPORT VIEW ---
function renderExportView() {
   if(!state.script || !state.panelLayouts.length) {
      DOM.exportEmpty.style.display = 'flex';
      DOM.exportOptions.style.display = 'none';
      return;
   }
   DOM.exportEmpty.style.display = 'none';
   DOM.exportOptions.style.display = 'flex';
}

function download(content, fileName, contentType) {
   const a = document.createElement("a");
   const file = new Blob([content], {type: contentType});
   a.href = URL.createObjectURL(file);
   a.download = fileName;
   a.click();
   URL.revokeObjectURL(a.href);
}

document.getElementById('export-text-btn').addEventListener('click', () => {
   if(!state.script) return;
   let text = 'MANGAPOST SCRIPT\n';
   state.script.pages.forEach((p, i) => {
      text += `\nPAGE ${i+1}\n`;
      (p.panels||[]).forEach((panel, j) => {
         text += `[PANEL ${j+1}] ${panel.type||''}\n`;
         if(panel.description) text += ` Visual: ${panel.description}\n`;
         (panel.dialogue||[]).forEach(d => text += ` ${d.character}: "${d.text}"\n`);
      });
   });
   download(text, 'script.txt', 'text/plain');
});

document.getElementById('export-json-btn').addEventListener('click', () => {
   if(!state.script) return;
   const blob = JSON.stringify({script: state.script, layouts: state.panelLayouts}, null, 2);
   download(blob, 'project.json', 'application/json');
});

document.getElementById('export-svg-btn').addEventListener('click', () => {
   const svgNode = DOM.fullCanvas.querySelector('svg') || DOM.miniCanvas.querySelector('svg');
   if(!svgNode) return;
   const svgData = new XMLSerializer().serializeToString(svgNode);
   download(svgData, 'layout.svg', 'image/svg+xml;charset=utf-8');
});

// Copy button
document.getElementById('copy-script-btn').addEventListener('click', () => {
   if(!state.script) return;
   let text = '';
   state.script.pages.forEach((p, i) => {
      text += `PAGE ${i+1}\n`;
      (p.panels||[]).forEach((panel, j) => { text += `[PANEL ${j+1}] ${panel.description}\n`; });
   });
   navigator.clipboard.writeText(text);
   const btn = document.getElementById('copy-script-btn');
   btn.textContent = 'Copied!';
   setTimeout(() => btn.textContent = 'Copy', 2000);
});
