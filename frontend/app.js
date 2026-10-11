/**
 * 企业合同智能审查与风险辅助 Agent —— 前端逻辑
 * 纯原生 JS，无任何外部依赖，直接对接后端 /api 接口。
 */

const API = '/api';
let token = localStorage.getItem('contract_token') || '';
let currentUser = null;

/* ============ 工具函数 ============ */
function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function toast(msg, type = '') {
  const el = $('#toast');
  el.textContent = msg;
  el.className = 'toast ' + type;
  el.style.display = 'block';
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.style.display = 'none'; }, 2600);
}

function fmtSize(bytes) {
  if (bytes == null) return '';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1024 / 1024).toFixed(2) + ' MB';
}

function fmtDate(iso) {
  if (!iso) return '—';
  return iso.replace('T', ' ').slice(0, 16);
}

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

/* ============ HTTP 请求 ============ */
async function request(method, path, body, isForm = false) {
  const headers = {};
  if (token) headers['Authorization'] = 'Bearer ' + token;
  let payload;
  if (isForm) {
    payload = body; // FormData
  } else if (body != null) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }
  const res = await fetch(API + path, { method, headers, body: payload });
  if (res.status === 401) {
    // token 失效，回到登录页
    logout(true);
    throw new Error('登录已失效，请重新登录');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.detail || data.message || ('请求失败 (' + res.status + ')');
    throw new Error(msg);
  }
  return data;
}

/* ============ 认证 ============ */
async function login(username, password) {
  const data = await request('POST', '/auth/login', { username, password });
  token = data.token;
  currentUser = data.user;
  localStorage.setItem('contract_token', token);
  showApp();
  toast('登录成功，欢迎 ' + data.user.username, 'success');
}

function logout(silent = false) {
  token = '';
  currentUser = null;
  localStorage.removeItem('contract_token');
  showLogin();
  if (!silent) toast('已退出登录');
}

function showLogin() {
  $('#login-view').style.display = 'flex';
  $('#app-view').style.display = 'none';
  $('#logout-btn').style.display = 'none';
  $('#user-badge').textContent = '未登录';
}

function showApp() {
  $('#login-view').style.display = 'none';
  $('#app-view').style.display = 'block';
  $('#logout-btn').style.display = 'inline-flex';
  $('#user-badge').textContent = currentUser ? currentUser.username + ' (' + (currentUser.role || 'user') + ')' : '';
  loadMode();
  loadContracts();
  loadKnowledgeStats();
}

/* ============ 运行模式徽章 ============ */
async function loadMode() {
  try {
    const health = await fetch('/health').then(r => r.json());
    const root = await fetch('/').then(r => r.json());
    let mode = '本地降级模式';
    // 通过根接口无法直接判断 LLM 是否 Mock，这里做简单探测
    const badge = $('#mode-badge');
    badge.textContent = '⚙️ ' + mode + ' · API 就绪';
  } catch (e) {
    $('#mode-badge').textContent = '⚠️ 后端未连接';
  }
}

/* ============ Tab 切换 ============ */
function initTabs() {
  $$('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      $$('.nav-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      const tab = item.dataset.tab;
      $$('.tab-panel').forEach(p => p.classList.remove('active'));
      $('#tab-' + tab).classList.add('active');
      if (tab === 'contracts') loadContracts();
      if (tab === 'knowledge') loadKnowledgeStats();
    });
  });
}

/* ============ 文件上传 ============ */
let selectedFile = null;

function initUpload() {
  const dropzone = $('#dropzone');
  const input = $('#file-input');

  dropzone.addEventListener('click', () => input.click());
  input.addEventListener('change', () => {
    if (input.files.length) handleFile(input.files[0]);
  });
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
  });
}

function handleFile(file) {
  const allowed = ['.txt', '.pdf', '.docx'];
  const ext = '.' + (file.name.split('.').pop() || '').toLowerCase();
  if (!allowed.includes(ext)) {
    toast('不支持的文件类型，仅支持 .txt / .pdf / .docx', 'error');
    return;
  }
  selectedFile = file;
  $('#dropzone').style.display = 'none';
  $('#upload-info').style.display = 'flex';
  $('#upload-filename').textContent = file.name;
  $('#upload-filesize').textContent = fmtSize(file.size);
}

function resetUpload() {
  selectedFile = null;
  $('#file-input').value = '';
  $('#dropzone').style.display = 'block';
  $('#upload-info').style.display = 'none';
}

/* ============ 审查流程 ============ */
async function startReview() {
  if (!selectedFile) return;
  const reviewType = $('#review-type').value;

  // 重置结果区
  $('#result-area').style.display = 'none';
  $('#review-progress').style.display = 'none';

  const btn = $('#start-review-btn');
  btn.disabled = true;
  $('#upload-progress').style.display = 'block';

  try {
    // 1. 上传合同
    const fd = new FormData();
    fd.append('file', selectedFile);
    const uploadRes = await request('POST', '/contracts/upload', fd, true);
    const contractId = uploadRes.contract_id;

    $('#upload-progress').style.display = 'none';
    resetUpload();
    toast('合同上传成功，开始审查…', 'success');

    // 2. 创建审查任务
    const createRes = await request('POST', '/reviews/create', {
      contract_id: contractId,
      review_type: reviewType,
    });
    const taskId = createRes.task_id;

    // 3. 轮询状态
    $('#review-progress').style.display = 'block';
    await pollReview(taskId, contractId);
  } catch (e) {
    toast(e.message, 'error');
    $('#upload-progress').style.display = 'none';
  } finally {
    btn.disabled = false;
  }
}

async function pollReview(taskId, contractId) {
  const stepEl = $('#progress-step');
  const percentEl = $('#progress-percent');
  const fillEl = $('#review-progress-fill');

  while (true) {
    const s = await request('GET', `/reviews/${taskId}/status`);
    const progress = s.progress || 0;
    stepEl.textContent = s.current_step || '处理中…';
    percentEl.textContent = progress + '%';
    fillEl.style.width = progress + '%';

    if (s.status === 'completed') {
      fillEl.style.width = '100%';
      percentEl.textContent = '100%';
      stepEl.textContent = '审查完成';
      toast('审查完成', 'success');
      await loadResult(taskId, contractId);
      break;
    } else if (s.status === 'failed') {
      stepEl.textContent = '审查失败';
      toast('审查失败：' + (s.error_message || '未知错误'), 'error');
      break;
    }
    await sleep(800);
  }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

/* ============ 结果展示 ============ */
async function loadResult(taskId, contractId) {
  try {
    // 并行拉取风险、报告、合同条款
    const [risks, report, contract] = await Promise.all([
      request('GET', `/reviews/${taskId}/risks`),
      request('GET', `/reviews/${taskId}/report`).catch(() => null),
      request('GET', `/contracts/${contractId}`),
    ]);

    renderReportOverview(report);
    renderRisks(risks);
    renderClauses(contract.clauses || []);
    $('#result-area').style.display = 'block';
    // 滚动到结果区
    $('#result-area').scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    toast('加载结果失败：' + e.message, 'error');
  }
}

function renderReportOverview(report) {
  const box = $('#report-overview');
  if (!report) {
    box.innerHTML = '<p class="empty-tip">报告尚未生成</p>';
    return;
  }
  const stats = report.risk_statistics || {
    total: report.risk_count || 0,
    high: report.high_risk_count || 0,
    medium: report.medium_risk_count || 0,
    low: report.low_risk_count || 0,
  };
  const level = report.overall_level || 'UNKNOWN';
  const levelColor = { HIGH: '#dc2626', MEDIUM: '#d97706', LOW: '#16a34a' }[level] || '#6b7280';
  const levelText = { HIGH: '高风险', MEDIUM: '中风险', LOW: '低风险', UNKNOWN: '未评级' }[level] || level;

  box.innerHTML = `
    <div class="overview-level">
      <span class="level-tag" style="background:${levelColor}">${levelText}</span>
    </div>
    <p class="overview-summary">${esc(report.summary || '')}</p>
    <div class="overview-stats">
      <div class="stat-box total"><div class="stat-num">${stats.total}</div><div class="stat-label">风险总数</div></div>
      <div class="stat-box high"><div class="stat-num">${stats.high}</div><div class="stat-label">高危</div></div>
      <div class="stat-box medium"><div class="stat-num">${stats.medium}</div><div class="stat-label">中危</div></div>
      <div class="stat-box low"><div class="stat-num">${stats.low}</div><div class="stat-label">低危</div></div>
    </div>
  `;
}

function renderRisks(risks) {
  const list = $('#risk-list');
  if (!risks || !risks.length) {
    list.innerHTML = '<p class="risk-empty">未发现风险</p>';
    return;
  }
  window._allRisks = risks;
  list.innerHTML = risks.map(r => riskItemHtml(r)).join('');
}

function riskItemHtml(r) {
  const evidence = Array.isArray(r.evidence) ? r.evidence : [];
  const evTags = evidence.map(e => {
    const src = typeof e === 'object' ? (e.source || e.text || '') : e;
    return `<span class="ev-tag">${esc(src)}</span>`;
  }).join('');
  return `
    <div class="risk-item level-${esc(r.risk_level)}" data-level="${esc(r.risk_level)}">
      <div class="risk-item-head">
        <span class="risk-level-tag level-tag-${esc(r.risk_level)}">${esc(r.risk_level)}</span>
        <span class="risk-type">${esc(r.risk_type || '风险')}</span>
        ${r.clause_name ? `<span class="risk-clause">${esc(r.clause_name)}</span>` : ''}
      </div>
      <div class="risk-desc">${esc(r.description || '')}</div>
      ${r.suggestion ? `<div class="risk-suggestion"><b>修改建议：</b>${esc(r.suggestion)}</div>` : ''}
      ${evTags ? `<div class="risk-evidence">依据：${evTags}</div>` : ''}
    </div>
  `;
}

function renderClauses(clauses) {
  const list = $('#clause-list');
  if (!clauses || !clauses.length) {
    list.innerHTML = '<p class="empty-tip">暂无条款数据</p>';
    return;
  }
  list.innerHTML = clauses.map(c => `
    <div class="clause-item">
      <div class="clause-name">${esc(c.clause_name || '条款')}<span class="clause-type">${esc(c.clause_type || '')}</span></div>
      <div class="clause-content">${esc(c.content || '')}</div>
    </div>
  `).join('');
}

/* ============ 风险过滤 ============ */
function initRiskFilter() {
  $('#risk-filter').addEventListener('click', (e) => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    $$('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const level = btn.dataset.level;
    $$('.risk-item').forEach(item => {
      const match = level === 'all' || item.dataset.level === level;
      item.style.display = match ? '' : 'none';
    });
  });
}

/* ============ 合同列表 ============ */
async function loadContracts() {
  try {
    const contracts = await request('GET', '/contracts');
    const list = $('#contract-list');
    if (!contracts.length) {
      list.innerHTML = '<p class="empty-tip">暂无合同，请先在「合同审查」页上传</p>';
      return;
    }
    list.innerHTML = contracts.map(c => `
      <div class="contract-item">
        <div class="contract-info">
          <div class="contract-name">${esc(c.name || '未命名合同')}</div>
          <div class="contract-meta">
            ${c.contract_type ? esc(c.contract_type) + ' · ' : ''}${c.amount ? '¥' + esc(c.amount) + ' · ' : ''}${fmtDate(c.created_at)}
          </div>
        </div>
        <div class="contract-actions">
          <span class="status-tag status-${esc(c.status || 'uploaded')}">${statusText(c.status)}</span>
          <button class="btn btn-ghost" data-view="${esc(c.id)}">查看</button>
        </div>
      </div>
    `).join('');

    // 绑定查看事件
    list.querySelectorAll('[data-view]').forEach(btn => {
      btn.addEventListener('click', () => viewContract(btn.dataset.view));
    });
  } catch (e) {
    toast('加载合同列表失败：' + e.message, 'error');
  }
}

function statusText(status) {
  const map = {
    uploaded: '已上传', parsed: '已解析', reviewing: '审查中',
    completed: '已完成', failed: '失败', pending: '待处理', running: '运行中',
  };
  return map[status] || status;
}

async function viewContract(contractId) {
  try {
    const c = await request('GET', `/contracts/${contractId}`);
    // 切到审查 Tab 并展示合同信息
    $$('.nav-item').forEach(i => i.classList.remove('active'));
    $$('.nav-item')[0].classList.add('active');
    $$('.tab-panel').forEach(p => p.classList.remove('active'));
    $('#tab-review').classList.add('active');

    renderClauses(c.clauses || []);
    $('#result-area').style.display = 'block';
    $('#review-progress').style.display = 'none';
    toast('已加载合同：' + c.name);

    // 尝试加载最新报告
    try {
      const report = await request('GET', `/reports/${contractId}`);
      renderReportOverview(report);
    } catch (e) { /* 无报告忽略 */ }
  } catch (e) {
    toast('查看合同失败：' + e.message, 'error');
  }
}

/* ============ 知识库 ============ */
async function loadKnowledgeStats() {
  try {
    const stats = await request('GET', '/knowledge/stats');
    $('#kb-stats').textContent = '知识库共 ' + (stats.total_chunks || 0) + ' 条知识条目';
  } catch (e) {
    $('#kb-stats').textContent = '';
  }
}

async function searchKnowledge() {
  const query = $('#kb-query').value.trim();
  if (!query) { toast('请输入检索关键词', 'error'); return; }
  try {
    const results = await request('POST', '/knowledge/search', { query, top_k: 5 });
    const box = $('#kb-results');
    if (!results || !results.length) {
      box.innerHTML = '<p class="empty-tip">未检索到相关知识</p>';
      return;
    }
    box.innerHTML = results.map(r => {
      const meta = r.metadata || {};
      const source = meta.source || 'unknown';
      const score = r.score != null ? r.score.toFixed(4) : '';
      return `
        <div class="kb-item">
          <div class="kb-item-head">
            <span class="kb-source">${esc(source)}</span>
            ${score ? `<span class="kb-score">相关度 ${score}</span>` : ''}
          </div>
          <div class="kb-text">${esc(r.text || '')}</div>
        </div>
      `;
    }).join('');
  } catch (e) {
    toast('检索失败：' + e.message, 'error');
  }
}

/* ============ 事件绑定 ============ */
function init() {
  // 登录表单
  $('#login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = $('#login-username').value.trim();
    const password = $('#login-password').value;
    if (!username || !password) { toast('请输入用户名和密码', 'error'); return; }
    const btn = $('#login-btn');
    btn.disabled = true;
    btn.textContent = '登录中…';
    try {
      await login(username, password);
    } catch (err) {
      $('#login-error').textContent = err.message;
      $('#login-error').style.display = 'block';
    } finally {
      btn.disabled = false;
      btn.textContent = '登 录';
    }
  });

  $('#logout-btn').addEventListener('click', () => logout());
  $('#start-review-btn').addEventListener('click', startReview);
  $('#kb-search-btn').addEventListener('click', searchKnowledge);
  $('#kb-query').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') searchKnowledge();
  });

  initTabs();
  initUpload();
  initRiskFilter();

  // 若已有 token，尝试直接进入
  if (token) {
    // 简单校验 token 是否有效
    request('GET', '/contracts').then(() => {
      // token 有效，但缺少 user 信息，先尝试用默认展示
      currentUser = currentUser || { username: '已登录' };
      showApp();
    }).catch(() => {
      logout(true);
    });
  } else {
    showLogin();
  }
}

document.addEventListener('DOMContentLoaded', init);
