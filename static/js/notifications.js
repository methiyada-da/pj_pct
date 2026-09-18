/* =============================================================
   notifications.js — ระบบแจ้งเตือน (user + admin)
   ============================================================= */

const NOTIF_ICONS_FA = {
  booking_new:      'fa-calendar-plus text-primary',
  booking_accepted: 'fa-check-circle text-success',
  booking_rejected: 'fa-times-circle text-danger',
  booking_completed:'fa-flag text-warning',
  booking_credited: 'fa-coins text-success',
  booking_reviewed: 'fa-star text-warning',
  booking_reported: 'fa-exclamation-triangle text-danger',
  booking_cancel_requested: 'fa-hourglass-half text-warning',
  booking_cancel_rejected: 'fa-ban text-danger',
  booking_cancelled: 'fa-calendar-xmark text-danger',
  booking_report_statement: 'fa-comment-dots text-primary',
  booking_report_resolved: 'fa-gavel text-success',
  tutor_approved:   'fa-user-check text-success',
  tutor_rejected:   'fa-user-times text-danger',
  tutor_suspended:  'fa-user-lock text-danger',
  refill_approved:  'fa-wallet text-success',
  refill_rejected:  'fa-wallet text-danger',
  withdraw_paid:    'fa-money-bill-wave text-success',
  admin_refill:     'fa-file-invoice text-primary',
  admin_withdraw:   'fa-hand-holding-usd text-warning',
  admin_tutor_new:  'fa-user-graduate text-primary',
  admin_reported:   'fa-exclamation-triangle text-danger',
};

const NOTIF_ICONS_BI = {
  admin_refill:    'bi-file-earmark-arrow-up text-primary',
  admin_withdraw:  'bi-cash-stack text-warning',
  admin_tutor_new: 'bi-person-plus text-primary',
  admin_reported:  'bi-exclamation-triangle text-danger',
};

function _getNotifIcon(n, iconSet, iconPrefix) {
  return iconSet[n.type] || (iconPrefix === 'fas' ? 'fa-bell text-secondary' : 'bi-bell text-secondary');
}

/* ── สร้าง HTML item แต่ละรายการ ── */
function _buildItem(n, iconSet, iconPrefix) {
  const iconKey = _getNotifIcon(n, iconSet, iconPrefix);
  // พื้นหลัง: ยังไม่อ่าน = ฟ้าอ่อน, อ่านแล้ว = ขาว
  const bg = n.is_read ? '' : 'style="background:#EFF6FF;"';
  return `
    <a href="${n.url || '#'}"
       id="notif-item-${n.notif_id}"
       class="d-flex gap-2 align-items-start px-3 py-2 border-bottom text-decoration-none text-dark notif-item-link"
       ${bg}
       onclick="handleNotifClick(event, ${n.notif_id}, '${n.url || ''}')">
      <i class="${iconPrefix} ${iconKey} mt-1 flex-shrink-0" style="font-size:1rem;"></i>
      <div class="flex-grow-1" style="min-width:0;">
        <div style="font-size:13px;line-height:1.4;white-space:normal;">${n.text}</div>
        <div class="text-muted mt-1" style="font-size:11px;">${n.created_at}</div>
      </div>
      ${!n.is_read ? '<span class="flex-shrink-0 mt-1" style="width:8px;height:8px;border-radius:50%;background:#2563EB;display:inline-block;"></span>' : ''}
    </a>`;
}

function _syncBookingState(data) {
  const nextToken = data.booking_state_token || '';
  if (!window.BOOKING_STATE_TOKEN || !nextToken) return;
  if (nextToken === window.BOOKING_STATE_TOKEN) return;

  const previousToken = window.BOOKING_STATE_TOKEN;
  window.BOOKING_STATE_TOKEN = nextToken;
  window.dispatchEvent(new CustomEvent('booking-time-state-changed', {
    detail: { previousToken, nextToken },
  }));
}

/* ── User Notification ── */
function fetchNotifications() {
  fetch(window.NOTIF_API, { cache: 'no-store' })
    .then(r => r.json())
    .then(data => {
      _syncBookingState(data);
      const badge = document.getElementById('notif-badge');
      const empty = document.getElementById('notif-empty');
      const list  = document.getElementById('notifBell').closest('.dropdown').querySelector('.dropdown-menu');

      // อัพเดต badge
      const count = data.unread_count || 0;
      if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.remove('d-none');
      } else {
        badge.classList.add('d-none');
      }

      // ลบ item เดิม
      list.querySelectorAll('.notif-item-li').forEach(el => el.remove());

      if (!data.notifications || data.notifications.length === 0) {
        empty.classList.remove('d-none');
        return;
      }
      empty.classList.add('d-none');

      data.notifications.forEach(n => {
        const li = document.createElement('li');
        li.className = 'notif-item-li';
        li.innerHTML = _buildItem(n, NOTIF_ICONS_FA, 'fas');
        list.insertBefore(li, empty);
      });
    })
    .catch(() => {});
}

function handleNotifClick(event, notifId, url) {
  event.preventDefault();
  // mark read แล้ว navigate
  fetch(`/notifications/api/${notifId}/read/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': window.NOTIF_CSRF },
  }).finally(() => {
    // เปลี่ยน background เป็นขาว
    const el = document.getElementById(`notif-item-${notifId}`);
    if (el) el.style.background = '';
    // อัพเดต badge แล้ว navigate
    fetchNotifications();
    if (url) window.location.href = url;
  });
}

function markAllRead(event) {
  if (event) event.preventDefault();
  fetch(window.NOTIF_READ_ALL, {
    method: 'POST',
    headers: { 'X-CSRFToken': window.NOTIF_CSRF },
  }).then(() => fetchNotifications()).catch(() => {});
}

/* ── Admin Notification ── */
function adminFetchNotifications() {
  fetch(window.NOTIF_API, { cache: 'no-store' })
    .then(r => r.json())
    .then(data => {
      const badge = document.getElementById('admin-notif-badge');
      const empty = document.getElementById('admin-notif-empty');
      const list  = document.getElementById('adminNotifBell').closest('.dropdown').querySelector('.dropdown-menu');

      const count = data.unread_count || 0;
      if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.remove('d-none');
      } else {
        badge.classList.add('d-none');
      }

      list.querySelectorAll('.admin-notif-item').forEach(el => el.remove());

      if (!data.notifications || data.notifications.length === 0) {
        empty.classList.remove('d-none');
        return;
      }
      empty.classList.add('d-none');

      data.notifications.forEach(n => {
        const li = document.createElement('li');
        li.className = 'admin-notif-item';
        li.innerHTML = _buildItem(n, NOTIF_ICONS_BI, 'bi');
        list.insertBefore(li, empty);
      });
    })
    .catch(() => {});
}

function adminMarkAllRead(event) {
  if (event) event.preventDefault();
  fetch(window.NOTIF_READ_ALL, {
    method: 'POST',
    headers: { 'X-CSRFToken': window.NOTIF_CSRF },
  }).then(() => adminFetchNotifications()).catch(() => {});
}
