let currentView = 'unassigned';
let selectedConversationId = null;
let pollTimer = null;

// Agent Helpers
function getSelectedToken() {
  const select = document.getElementById('agentSelect');
  return select.value;
}

function getSelectedAgentInfo() {
  const select = document.getElementById('agentSelect');
  const opt = select.selectedOptions[0];
  return {
    token: opt.value,
    workspace: opt.getAttribute('data-ws'),
    name: opt.getAttribute('data-name')
  };
}

function updateTenantBadge() {
  const info = getSelectedAgentInfo();
  document.getElementById('tenantBadge').innerText = `Workspace: ${info.workspace}`;
}

function formatWaiting(seconds) {
  if (seconds < 60) return `${seconds}s ago`;
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ago`;
}

// Switch between Unassigned and Mine
function switchView(view) {
  currentView = view;
  document.getElementById('tabUnassigned').classList.toggle('active', view === 'unassigned');
  document.getElementById('tabMine').classList.toggle('active', view === 'mine');
  fetchQueue();
}

// Fetch conversation list (Queue)
async function fetchQueue() {
  const token = getSelectedToken();
  try {
    const res = await fetch(`/conversations?view=${currentView}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) return;
    const conversations = await res.json();
    renderQueue(conversations);
  } catch (err) {
    console.error('Queue poll error:', err);
  }
}

function renderQueue(conversations) {
  const listEl = document.getElementById('conversationList');
  if (conversations.length === 0) {
    listEl.innerHTML = `<div class="empty-state">No ${currentView} conversations.</div>`;
    return;
  }

  listEl.innerHTML = conversations.map(c => `
    <div class="conv-card ${c.id === selectedConversationId ? 'selected' : ''}" onclick="selectConversation('${c.id}')">
      <div class="conv-header">
        <span class="conv-name">${escapeHtml(c.customer_name)}</span>
        <span class="conv-timer">${formatWaiting(c.waiting_seconds)}</span>
      </div>
      <div class="conv-snippet">${escapeHtml(c.last_message_text || 'No messages yet')}</div>
    </div>
  `).join('');
}

// Select & Fetch Active Conversation Thread
async function selectConversation(id) {
  selectedConversationId = id;
  clearAlert();
  document.querySelectorAll('.conv-card').forEach(el => el.classList.remove('selected'));
  fetchThread();
}

async function fetchThread() {
  if (!selectedConversationId) return;
  const token = getSelectedToken();

  try {
    const res = await fetch(`/conversations/${selectedConversationId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (res.status === 404) {
      showAlert('Conversation not found in this workspace.');
      resetChatPane();
      return;
    }

    if (!res.ok) return;
    const conv = await res.json();
    renderThread(conv);
  } catch (err) {
    console.error('Thread poll error:', err);
  }
}

function renderThread(conv) {
  const info = getSelectedAgentInfo();
  document.getElementById('chatCustomer').innerText = conv.customer_name;
  
  const claimContainer = document.getElementById('claimContainer');
  const replyInput = document.getElementById('replyInput');
  const sendBtn = document.getElementById('sendBtn');

  // Ownership state
  const isAssignedToMe = conv.assigned_agent_id && conv.assigned_agent_name === info.name;
  const isUnassigned = !conv.assigned_agent_id;

  if (isUnassigned) {
    document.getElementById('chatMeta').innerText = 'Status: Unassigned';
    claimContainer.style.display = 'block';
    replyInput.disabled = true;
    replyInput.placeholder = 'Claim this conversation to reply...';
    sendBtn.disabled = true;
  } else {
    document.getElementById('chatMeta').innerText = `Status: Assigned to ${conv.assigned_agent_name}`;
    claimContainer.style.display = 'none';

    if (isAssignedToMe) {
      replyInput.disabled = false;
      replyInput.placeholder = 'Type your reply...';
      sendBtn.disabled = false;
    } else {
      replyInput.disabled = true;
      replyInput.placeholder = `Assigned to ${conv.assigned_agent_name}`;
      sendBtn.disabled = true;
    }
  }

  // Render Messages
  const msgContainer = document.getElementById('messagesContainer');
  msgContainer.innerHTML = conv.messages.map(m => `
    <div class="message-bubble ${m.sender_type}">
      <div class="msg-text">${escapeHtml(m.text)}</div>
      <div class="msg-info">
        <span>${escapeHtml(m.sender_name)}</span> &bull; 
        <span>${new Date(m.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
    </div>
  `).join('');
}

// Claim Action
async function claimActiveConversation() {
  if (!selectedConversationId) return;
  const token = getSelectedToken();
  clearAlert();

  try {
    const res = await fetch(`/conversations/${selectedConversationId}/claim`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (res.status === 200) {
      await fetchThread();
      await fetchQueue();
    } else if (res.status === 409) {
      const data = await res.json();
      showAlert(`Cannot claim: Already claimed by ${data.claimed_by.name}!`);
      await fetchThread();
      await fetchQueue();
    } else {
      showAlert('Failed to claim conversation.');
    }
  } catch (err) {
    showAlert('Error claiming conversation.');
  }
}

// Send Reply Action
async function sendReply(e) {
  e.preventDefault();
  const input = document.getElementById('replyInput');
  const text = input.value.trim();
  if (!text || !selectedConversationId) return;

  const token = getSelectedToken();
  clearAlert();

  try {
    const res = await fetch(`/conversations/${selectedConversationId}/messages`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ text })
    });

    if (res.status === 201) {
      input.value = '';
      await fetchThread();
      await fetchQueue();
    } else if (res.status === 403) {
      showAlert('Forbidden: Only the assigned agent can reply.');
    } else {
      showAlert('Failed to send reply.');
    }
  } catch (err) {
    showAlert('Network error sending reply.');
  }
}

function showAlert(msg) {
  const el = document.getElementById('bannerAlert');
  el.innerText = msg;
  el.style.display = 'block';
}

function clearAlert() {
  const el = document.getElementById('bannerAlert');
  el.style.display = 'none';
}

function resetChatPane() {
  selectedConversationId = null;
  document.getElementById('chatCustomer').innerText = 'Select a conversation';
  document.getElementById('chatMeta').innerText = 'No conversation selected';
  document.getElementById('claimContainer').style.display = 'none';
  document.getElementById('replyInput').disabled = true;
  document.getElementById('sendBtn').disabled = true;
  document.getElementById('messagesContainer').innerHTML = '<div class="empty-state">Select a conversation from the left to view messages.</div>';
}

function escapeHtml(str) {
  return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Initialize & Polling Loop (every 2.5s)
document.getElementById('agentSelect').addEventListener('change', () => {
  updateTenantBadge();
  resetChatPane();
  fetchQueue();
});

updateTenantBadge();
fetchQueue();
pollTimer = setInterval(() => {
  fetchQueue();
  if (selectedConversationId) {
    fetchThread();
  }
}, 2500);
