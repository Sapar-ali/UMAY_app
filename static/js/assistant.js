(() => {
  // Big kitten teaser button
  const btn = document.createElement('button');
  btn.id = 'umay-assistant-btn';
  btn.setAttribute('aria-label', 'Assistant teaser');
  Object.assign(btn.style, {
    position: 'fixed', zIndex: 60, right: '18px', bottom: '90px', width: '88px', height: '88px',
    borderRadius: '50%', background: '#fff', border: '1px solid rgba(0,0,0,0.08)',
    boxShadow: '0 10px 24px rgba(0,0,0,0.18)', padding: 0, overflow: 'hidden', cursor: 'pointer'
  });
  const img = document.createElement('img');
  img.alt = 'Assistant';
  img.src = window.assistantIconUrl || '/static/assets/AI_assistant.png';
  Object.assign(img.style, { width: '100%', height: '100%', objectFit: 'cover' });
  btn.appendChild(img);

  // Simple toast bubble
  const toast = document.createElement('div');
  toast.id = 'umay-assistant-toast';
  Object.assign(toast.style, {
    position: 'fixed', zIndex: 60, right: '120px', bottom: '108px', maxWidth: '320px',
    background: '#0f172a', color: '#fff', padding: '12px 14px', borderRadius: '12px',
    boxShadow: '0 8px 24px rgba(0,0,0,0.2)', display: 'none', fontSize: '14px', lineHeight: '1.4'
  });
  toast.textContent = 'Скоро здесь будет доступен умный ассистент‑помощник.';

  let hideTimer = null;
  function showToast() {
    toast.style.display = 'block';
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => { toast.style.display = 'none'; }, 3000);
  }

  btn.addEventListener('click', showToast);
  document.body.appendChild(btn);
  document.body.appendChild(toast);
})();


