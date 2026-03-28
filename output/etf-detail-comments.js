// ── etf-detail-comments.js ───────────────────────────────────────────────────
// 댓글 시스템 + 종목 좋아요 (IIFE)
// 의존성: TICKER (etf-detail.js), CorryuAuth·_sb (supabase-client.js)
// ─────────────────────────────────────────────────────────────────────────────

// ═══════════════════════════════════════════════════════════════════════════
// 💬 댓글 시스템
// ═══════════════════════════════════════════════════════════════════════════
(async function initComments() {
  const section = document.getElementById('comment-section');
  section.style.display = 'block';

  // Supabase 미연결 상태
  if (!CorryuAuth.isConfigured) {
    document.getElementById('c-not-configured').style.display = 'block';
    return;
  }

  // ── 아바타 색상 팔레트 ────────────────────────────────────────────
  const AVATAR_COLORS = [
    '#3b82f6','#8b5cf6','#f59e0b','#22c55e','#ef4444',
    '#0ea5e9','#f97316','#a855f7','#06b6d4','#84cc16',
  ];
  function nickColor(nick) {
    let h = 0; for (const c of nick) h = (Math.imul(31,h)+c.charCodeAt(0))|0;
    return AVATAR_COLORS[Math.abs(h) % AVATAR_COLORS.length];
  }

  // ── 시간 포맷 ─────────────────────────────────────────────────────
  function timeAgo(iso) {
    const diff = (Date.now() - new Date(iso)) / 1000;
    if (diff < 60)       return '방금 전';
    if (diff < 3600)     return Math.floor(diff/60) + '분 전';
    if (diff < 86400)    return Math.floor(diff/3600) + '시간 전';
    if (diff < 604800)   return Math.floor(diff/86400) + '일 전';
    return new Date(iso).toLocaleDateString('ko-KR', {year:'numeric',month:'2-digit',day:'2-digit'}).replace(/\. /g,'.').replace('.','');
  }

  // ── HTML 이스케이프 ───────────────────────────────────────────────
  function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

  // ── 상태 ─────────────────────────────────────────────────────────
  let currentUser = null;
  let currentProfile = null;
  let myVotes = {}; // {comment_id: 'like'|'dislike'}
  let comments = [];
  let sortBy = 'recent'; // 'recent' | 'likes'
  let offset = 0;
  const PAGE_SIZE = 20;
  const GUEST_LIMIT = 3; // 비로그인 시 보여줄 최대 수

  // ── 로그인 상태 초기화 ────────────────────────────────────────────
  currentUser = await CorryuAuth.getUser();
  if (currentUser) {
    currentProfile = await CorryuAuth.getProfile(currentUser.id);
    showWriteForm();
    await loadMyVotes();
  } else {
    document.getElementById('c-login-banner').style.display = 'block';
  }

  // 문자 수 카운터
  document.getElementById('c-textarea')?.addEventListener('input', function() {
    document.getElementById('c-char-count').textContent = this.value.length + ' / 2000';
  });

  // ── 내 투표 내역 로드 ─────────────────────────────────────────────
  async function loadMyVotes() {
    if (!currentUser) return;
    const { data } = await _sb.from('comment_votes')
      .select('comment_id, vote_type').eq('user_id', currentUser.id);
    if (data) data.forEach(v => myVotes[v.comment_id] = v.vote_type);
  }

  // ── 댓글 로드 ─────────────────────────────────────────────────────
  async function loadComments(reset = false) {
    if (reset) { comments = []; offset = 0; }

    let q = _sb.from('comments')
      .select('*')
      .eq('ticker', TICKER)
      .is('parent_id', null)
      .eq('is_deleted', false);

    if (sortBy === 'likes') q = q.order('likes', { ascending: false }).order('created_at', { ascending: false });
    else                    q = q.order('created_at', { ascending: false });

    const limit = currentUser ? PAGE_SIZE : GUEST_LIMIT + 1;
    q = q.range(offset, offset + limit - 1);

    const { data, error } = await q;
    if (error) { console.error('[CORRYU comments]', error); return; }

    // 각 상위 댓글의 답글 로드
    if (data && data.length > 0) {
      const ids = data.map(c => c.id);
      const { data: replies } = await _sb.from('comments')
        .select('*').in('parent_id', ids).eq('is_deleted', false)
        .order('created_at', { ascending: true });

      const replyMap = {};
      (replies || []).forEach(r => {
        if (!replyMap[r.parent_id]) replyMap[r.parent_id] = [];
        replyMap[r.parent_id].push(r);
      });
      data.forEach(c => c.replies = replyMap[c.id] || []);
    }

    if (reset) comments = data || [];
    else       comments = comments.concat(data || []);
    offset += data?.length || 0;

    renderComments(data?.length || 0, limit);
    await updateTotal();
  }

  // ── 전체 댓글 수 업데이트 ─────────────────────────────────────────
  async function updateTotal() {
    const { count } = await _sb.from('comments')
      .select('*', { count: 'exact', head: true })
      .eq('ticker', TICKER).eq('is_deleted', false).is('parent_id', null);
    document.getElementById('c-total-badge').textContent = count ?? 0;
  }

  // ── 댓글 렌더링 ───────────────────────────────────────────────────
  function renderComments(fetchedCount, limit) {
    const list = document.getElementById('c-list');
    const empty = document.getElementById('c-empty');
    const gate  = document.getElementById('c-guest-gate');
    const more  = document.getElementById('c-load-more');

    if (comments.length === 0) {
      list.innerHTML = ''; empty.style.display = 'block'; gate.style.display = 'none'; more.style.display = 'none'; return;
    }
    empty.style.display = 'none';

    // 게스트 제한
    const display = currentUser ? comments : comments.slice(0, GUEST_LIMIT);
    const hasMore  = currentUser ? (fetchedCount >= limit) : (comments.length > GUEST_LIMIT);

    list.innerHTML = display.map(c => renderTopComment(c)).join('');

    gate.style.display = (!currentUser && comments.length >= GUEST_LIMIT) ? 'block' : 'none';
    more.style.display = (currentUser && hasMore) ? 'block' : 'none';
  }

  function renderTopComment(c) {
    const color = nickColor(c.nickname);
    const myVote = myVotes[c.id];
    const isOwn = currentUser && currentUser.id === c.user_id;
    const repliesHtml = (c.replies || []).map(r => renderReply(r)).join('');
    const replyCount = c.replies?.length || 0;
    return `<div class="c-item" id="c-${c.id}">
      <div style="display:flex;gap:10px;align-items:flex-start">
        <div class="c-avatar" style="background:${color}">${esc(c.nickname.charAt(0).toUpperCase())}</div>
        <div style="flex:1;min-width:0">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
            <span class="c-nick">${esc(c.nickname)}</span>
            <span class="c-time">${timeAgo(c.created_at)}</span>
            ${isOwn ? `<button class="c-del-btn" onclick="deleteComment('${c.id}',false)">삭제</button>` : ''}
          </div>
          <div class="c-body">${esc(c.content)}</div>
          <div class="c-action-row">
            <button class="c-vote-btn ${myVote==='like'?'voted-like':''}" onclick="vote('${c.id}','like')">
              👍 <span id="lk-${c.id}">${c.likes}</span>
            </button>
            <button class="c-vote-btn ${myVote==='dislike'?'voted-dislike':''}" onclick="vote('${c.id}','dislike')">
              👎 <span id="dk-${c.id}">${c.dislikes}</span>
            </button>
            ${currentUser ? `<button class="c-reply-toggle" onclick="toggleReplyForm('${c.id}')">💬 답글</button>` : ''}
            ${replyCount > 0 ? `<span class="c-reply-count">${replyCount}개 답글</span>` : ''}
          </div>
          <!-- 답글 작성 폼 -->
          <div id="rf-${c.id}" style="display:none;margin-top:10px">
            <div class="c-reply-form" style="margin-left:0">
              <textarea class="c-reply-textarea" id="rt-${c.id}" placeholder="답글을 작성하세요…" maxlength="2000"></textarea>
              <div style="display:flex;flex-direction:column;gap:5px">
                <button class="c-reply-submit" onclick="submitReply('${c.id}')">등록</button>
                <button class="c-reply-cancel" onclick="toggleReplyForm('${c.id}')">취소</button>
              </div>
            </div>
          </div>
          <!-- 답글 목록 -->
          <div class="c-replies-list" id="rl-${c.id}" style="${replyCount===0?'display:none':'display:block'}">${repliesHtml}</div>
        </div>
      </div>
    </div>`;
  }

  function renderReply(r) {
    const color = nickColor(r.nickname);
    const myVote = myVotes[r.id];
    const isOwn = currentUser && currentUser.id === r.user_id;
    return `<div class="c-reply-item-inner" id="c-${r.id}">
      <div style="display:flex;gap:8px;align-items:flex-start">
        <div class="c-avatar" style="width:28px;height:28px;font-size:.72rem;background:${color}">${esc(r.nickname.charAt(0).toUpperCase())}</div>
        <div style="flex:1;min-width:0">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
            <span class="c-nick" style="font-size:.8rem">${esc(r.nickname)}</span>
            <span class="c-time">${timeAgo(r.created_at)}</span>
            ${isOwn ? `<button class="c-del-btn" onclick="deleteComment('${r.id}',true)">삭제</button>` : ''}
          </div>
          <div class="c-body" style="font-size:.82rem">${esc(r.content)}</div>
          <div class="c-action-row">
            <button class="c-vote-btn ${myVote==='like'?'voted-like':''}" onclick="vote('${r.id}','like')">
              👍 <span id="lk-${r.id}">${r.likes}</span>
            </button>
            <button class="c-vote-btn ${myVote==='dislike'?'voted-dislike':''}" onclick="vote('${r.id}','dislike')">
              👎 <span id="dk-${r.id}">${r.dislikes}</span>
            </button>
          </div>
        </div>
      </div>
    </div>`;
  }

  // ── 작성 폼 표시 ─────────────────────────────────────────────────
  function showWriteForm() {
    const form = document.getElementById('c-write-form');
    const av   = document.getElementById('c-my-avatar');
    form.style.display = 'block';
    if (currentProfile) {
      const color = nickColor(currentProfile.nickname);
      av.style.background = color;
      av.textContent = currentProfile.nickname.charAt(0).toUpperCase();
    }
  }

  // ── 댓글 등록 ─────────────────────────────────────────────────────
  window.submitTopComment = async function() {
    if (!currentUser || !currentProfile) return;
    const ta = document.getElementById('c-textarea');
    const content = ta.value.trim();
    if (!content) return;
    const { error } = await _sb.from('comments').insert({
      ticker: TICKER, user_id: currentUser.id, nickname: currentProfile.nickname,
      content, parent_id: null, depth: 0,
    });
    if (error) { alert('등록 실패: ' + error.message); return; }
    ta.value = ''; document.getElementById('c-char-count').textContent = '0 / 2000';
    await loadComments(true);
  };

  // ── 답글 폼 토글 ─────────────────────────────────────────────────
  window.toggleReplyForm = function(parentId) {
    const form = document.getElementById('rf-' + parentId);
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
    if (form.style.display === 'block') document.getElementById('rt-' + parentId)?.focus();
  };

  // ── 답글 등록 ─────────────────────────────────────────────────────
  window.submitReply = async function(parentId) {
    if (!currentUser || !currentProfile) return;
    const ta = document.getElementById('rt-' + parentId);
    const content = ta?.value.trim();
    if (!content) return;
    const { error } = await _sb.from('comments').insert({
      ticker: TICKER, user_id: currentUser.id, nickname: currentProfile.nickname,
      content, parent_id: parentId, depth: 1,
    });
    if (error) { alert('등록 실패: ' + error.message); return; }
    ta.value = '';
    document.getElementById('rf-' + parentId).style.display = 'none';
    await loadComments(true);
  };

  // ── 댓글 삭제 (소프트) ───────────────────────────────────────────
  window.deleteComment = async function(id, isReply) {
    if (!confirm('댓글을 삭제하시겠습니까?')) return;
    await _sb.from('comments').update({ is_deleted: true }).eq('id', id);
    await loadComments(true);
  };

  // ── 좋아요 / 싫어요 ──────────────────────────────────────────────
  window.vote = async function(commentId, type) {
    if (!currentUser) { goLogin(); return; }
    const prev = myVotes[commentId];
    const lkEl = document.getElementById('lk-' + commentId);
    const dkEl = document.getElementById('dk-' + commentId);

    if (prev === type) {
      // 같은 버튼 → 취소
      await _sb.from('comment_votes').delete()
        .eq('comment_id', commentId).eq('user_id', currentUser.id);
      delete myVotes[commentId];
    } else {
      // 새 투표 또는 변경
      await _sb.from('comment_votes').upsert(
        { comment_id: commentId, user_id: currentUser.id, vote_type: type },
        { onConflict: 'comment_id,user_id' }
      );
      myVotes[commentId] = type;
    }

    // 최신 카운트 가져오기
    const { data } = await _sb.from('comments').select('likes,dislikes').eq('id', commentId).single();
    if (data && lkEl && dkEl) { lkEl.textContent = data.likes; dkEl.textContent = data.dislikes; }

    // 버튼 스타일 업데이트
    const lkBtn = document.querySelector(`#c-${commentId} .c-vote-btn:first-child`);
    const dkBtn = document.querySelector(`#c-${commentId} .c-vote-btn:nth-child(2)`);
    lkBtn?.classList.toggle('voted-like',    myVotes[commentId] === 'like');
    dkBtn?.classList.toggle('voted-dislike', myVotes[commentId] === 'dislike');
  };

  // ── 정렬 전환 ─────────────────────────────────────────────────────
  window.setSortBy = function(s) {
    sortBy = s;
    document.querySelectorAll('.c-sort-btn').forEach(b => b.classList.toggle('c-sort-on', b.dataset.sort === s));
    loadComments(true);
  };

  // ── 더 보기 ────────────────────────────────────────────────────────
  window.loadMoreComments = function() { loadComments(false); };

  // ── 로그인 리디렉션 ──────────────────────────────────────────────
  window.goLogin = function(e) {
    e?.preventDefault();
    location.href = '/login?redirect=' + encodeURIComponent(location.href);
  };

  // ── 최초 로드 ─────────────────────────────────────────────────────
  await loadComments(true);

  // ── 실시간 구독 (새 댓글 알림) ───────────────────────────────────
  _sb.channel('comments:' + TICKER)
    .on('postgres_changes',
      { event: 'INSERT', schema: 'public', table: 'comments', filter: 'ticker=eq.' + TICKER },
      () => { loadComments(true); }
    ).subscribe();

})();

// ═══════════════════════════════════════════════════════════════════════════
// ❤️ 종목 좋아요 시스템
// ═══════════════════════════════════════════════════════════════════════════
(async function initTickerLike() {
  if (!CorryuAuth.isConfigured) return;

  const btn   = document.getElementById('tl-btn');
  const icon  = document.getElementById('tl-icon');
  const countEl = document.getElementById('tl-count');

  let liked = false;
  let currentUser = null;

  // ── 좋아요 수 조회 ────────────────────────────────────────────────
  async function fetchCount() {
    const { count } = await _sb.from('ticker_likes')
      .select('id', { count: 'exact', head: true })
      .eq('ticker', TICKER);
    return count ?? 0;
  }

  // ── 본인 좋아요 여부 조회 ─────────────────────────────────────────
  async function fetchMyLike(userId) {
    const { data } = await _sb.from('ticker_likes')
      .select('id').eq('ticker', TICKER).eq('user_id', userId).maybeSingle();
    return !!data;
  }

  // ── UI 업데이트 ────────────────────────────────────────────────────
  function updateUI(count, isLiked) {
    countEl.textContent = count;
    if (isLiked) {
      btn.style.background   = 'rgba(244,114,182,0.18)';
      btn.style.borderColor  = 'rgba(244,114,182,0.55)';
      btn.style.color        = '#f472b6';
      icon.setAttribute('fill', '#f472b6');
      icon.setAttribute('stroke', '#f472b6');
    } else {
      btn.style.background   = 'rgba(244,114,182,0.07)';
      btn.style.borderColor  = 'rgba(244,114,182,0.25)';
      btn.style.color        = '#94a3b8';
      icon.setAttribute('fill', 'none');
      icon.setAttribute('stroke', 'currentColor');
    }
    btn.style.display = 'inline-flex';
  }

  // ── 최초 로드 ─────────────────────────────────────────────────────
  currentUser = await CorryuAuth.getUser();
  const [count, myLike] = await Promise.all([
    fetchCount(),
    currentUser ? fetchMyLike(currentUser.id) : Promise.resolve(false),
  ]);
  liked = myLike;
  updateUI(count, liked);

  // ── 좋아요 토글 ───────────────────────────────────────────────────
  window.tickerLikeToggle = async function() {
    if (!currentUser) {
      location.href = '/login?redirect=' + encodeURIComponent(location.href);
      return;
    }
    btn.disabled = true;
    try {
      if (liked) {
        await _sb.from('ticker_likes').delete()
          .eq('ticker', TICKER).eq('user_id', currentUser.id);
      } else {
        await _sb.from('ticker_likes').insert({ ticker: TICKER, user_id: currentUser.id });
      }
      liked = !liked;
      const newCount = await fetchCount();
      updateUI(newCount, liked);
    } catch(e) {
      console.warn('[CORRYU] ticker like error:', e.message);
    } finally {
      btn.disabled = false;
    }
  };

  // ── Auth 상태 변화 감지 ───────────────────────────────────────────
  CorryuAuth.onAuthChange(async (_event, session) => {
    currentUser = session?.user ?? null;
    const myLike = currentUser ? await fetchMyLike(currentUser.id) : false;
    liked = myLike;
    const count = await fetchCount();
    updateUI(count, liked);
  });
})();
