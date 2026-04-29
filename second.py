#!/usr/bin/env python3
"""
Graph Visualizer — DFS, BFS, Kruskal
HTML загварыг дуурайсан интерактив Python visualization
Хэрэглээ: python3 graph_viz_gui.py
"""

import pygame
import sys
import math
from collections import deque

pygame.init()

# ── Өнгөний тогтолцоо ────────────────────────────────────────────
BG          = (248, 247, 244)
PANEL_BG    = (240, 239, 235)
WHITE       = (255, 255, 255)
BORDER      = (200, 198, 192)
BORDER_MID  = (180, 178, 172)
TEXT_PRI    = (30,  30,  28)
TEXT_SEC    = (100, 99,  94)
TEXT_DIM    = (150, 148, 142)

# зангилааны өнгөнүүд
NODE_DEF    = (232, 230, 224)   # анхдагч
NODE_VISIT  = ( 29, 158, 117)   # зочилсон  — ногоон
NODE_CUR    = (239, 159,  39)   # одоогийн  — шар
NODE_QUEUE  = ( 59, 139, 212)   # дараалалд — цэнхэр

# ирмэгийн өнгөнүүд
EDGE_DEF    = (190, 188, 182)
EDGE_TREE   = ( 29, 158, 117)   # мод ирмэг — ногоон
EDGE_MST    = ( 29, 158, 117)
EDGE_CHECK  = (239, 159,  39)   # шалгаж байгаа — шар
EDGE_REJECT = (226,  75,  74)   # татгалзсан — улаан

# Tab өнгө
TAB_ACTIVE_BG   = (214, 234, 255)
TAB_ACTIVE_FG   = ( 24,  95, 165)
TAB_ACTIVE_BRD  = ( 24,  95, 165)
TAB_BG          = WHITE
TAB_FG          = TEXT_SEC

INFO_BG  = (235, 234, 228)
LOG_BG   = (235, 234, 228)

BTN_PRI_BG  = (214, 234, 255)
BTN_PRI_FG  = ( 24,  95, 165)
BTN_BG      = WHITE
BTN_FG      = TEXT_PRI
BTN_HOV     = (228, 226, 220)

# ── Хэмжээ ───────────────────────────────────────────────────────
W, H      = 860, 620
TAB_H     = 44
CTRL_H    = 44
GRAPH_H   = 310
INFO_H    = 40
LOG_H     = 36
PAD       = 14
NODE_R    = 22

# ── Граф өгөгдөл (HTML-тэй адил) ─────────────────────────────────
RAW_NODES = {
    'A': (80,  135),
    'B': (200,  60),
    'C': (200, 210),
    'D': (330,  60),
    'E': (330, 210),
    'F': (460, 135),
    'G': (570,  60),
    'H': (570, 210),
}

RAW_EDGES = [
    ('A','B',4), ('A','C',2),
    ('B','D',5), ('B','E',3),
    ('C','E',6), ('D','F',2),
    ('E','F',1), ('F','G',3),
    ('F','H',4), ('G','H',6),
    ('D','G',7),
]

# ── Union-Find ────────────────────────────────────────────────────
class UF:
    def __init__(self, keys):
        self.parent = {k: k for k in keys}
        self.rank   = {k: 0 for k in keys}

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def unite(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return False
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        return True

# ── Туслах функцүүд ───────────────────────────────────────────────
def edge_key(u, v):
    return tuple(sorted([u, v]))

def scale_pos(raw, graph_rect):
    """640×270 SVG координатыг graph_rect дотор хөрвүүлнэ"""
    gx, gy, gw, gh = graph_rect
    sx = gw / 640
    sy = gh / 270
    s  = min(sx, sy) * 0.92
    ox = gx + (gw - 640 * s) / 2
    oy = gy + (gh - 270 * s) / 2
    return {n: (int(ox + x * s), int(oy + y * s)) for n, (x, y) in raw.items()}

def draw_rounded_rect(surf, color, rect, r=8, border=0, border_color=None):
    x, y, w, h = rect
    pygame.draw.rect(surf, color, rect, border_radius=r)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=r)

def draw_text(surf, text, font, color, cx, cy, anchor='center'):
    ts = font.render(text, True, color)
    tr = ts.get_rect()
    if anchor == 'center':
        tr.center = (cx, cy)
    elif anchor == 'left':
        tr.midleft = (cx, cy)
    elif anchor == 'right':
        tr.midright = (cx, cy)
    surf.blit(ts, tr)

# ── Pygame фонтуудыг эхлүүлэх ─────────────────────────────────────
pygame.font.init()
FONT_SM  = pygame.font.SysFont('DejaVu Sans', 12)
FONT_MD  = pygame.font.SysFont('DejaVu Sans', 14)
FONT_B   = pygame.font.SysFont('DejaVu Sans', 14, bold=True)
FONT_LG  = pygame.font.SysFont('DejaVu Sans', 16, bold=True)
FONT_NODE= pygame.font.SysFont('DejaVu Sans', 15, bold=True)
FONT_EDGE= pygame.font.SysFont('DejaVu Sans', 11)

# ── Товч (Button) ─────────────────────────────────────────────────
class Button:
    def __init__(self, rect, label, primary=False):
        self.rect    = pygame.Rect(rect)
        self.label   = label
        self.primary = primary
        self.enabled = True
        self.hovered = False

    def draw(self, surf):
        alpha = 255 if self.enabled else 100
        if self.primary:
            bg  = BTN_PRI_BG if self.enabled else (190, 210, 230)
            fg  = BTN_PRI_FG
            brd = TAB_ACTIVE_BRD
        else:
            bg  = BTN_HOV if (self.hovered and self.enabled) else BTN_BG
            fg  = BTN_FG if self.enabled else TEXT_DIM
            brd = BORDER
        draw_rounded_rect(surf, bg, self.rect, r=7, border=1, border_color=brd)
        draw_text(surf, self.label, FONT_MD, fg, self.rect.centerx, self.rect.centery)

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.enabled and self.rect.collidepoint(event.pos):
                return True
        return False

# ── Граф зурах ───────────────────────────────────────────────────
def draw_graph(surf, graph_rect, nodes_pos, node_colors, edge_colors, node_labels=None):
    # ирмэгүүд
    for u, v, w in RAW_EDGES:
        k = edge_key(u, v)
        col   = edge_colors.get(k, EDGE_DEF)
        thick = 3 if col != EDGE_DEF else 1
        x1, y1 = nodes_pos[u]
        x2, y2 = nodes_pos[v]
        pygame.draw.line(surf, col, (x1, y1), (x2, y2), thick)
        # жингийн label
        mx, my = (x1+x2)//2, (y1+y2)//2
        wlbl = FONT_EDGE.render(str(w), True, TEXT_SEC)
        wr   = wlbl.get_rect(center=(mx, my))
        bg_r = wr.inflate(6, 4)
        draw_rounded_rect(surf, WHITE, bg_r, r=3, border=1, border_color=BORDER)
        surf.blit(wlbl, wr)

    # зангилаанууд
    for n, (x, y) in nodes_pos.items():
        col     = node_colors.get(n, NODE_DEF)
        is_dark = col in (NODE_VISIT, NODE_CUR, NODE_QUEUE)
        pygame.draw.circle(surf, col,   (x, y), NODE_R)
        pygame.draw.circle(surf, BORDER_MID, (x, y), NODE_R, 1)
        txt_col = WHITE if is_dark else TEXT_PRI
        draw_text(surf, n, FONT_NODE, txt_col, x, y)
        if node_labels and n in node_labels:
            draw_text(surf, str(node_labels[n]), FONT_SM, TEXT_DIM, x, y + NODE_R + 8)

# ── Үндсэн апп класс ─────────────────────────────────────────────
class App:
    def __init__(self):
        self.screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
        pygame.display.set_caption('Graph Visualizer — DFS / BFS / Kruskal')
        self.clock  = pygame.time.Clock()
        self.tab    = 'dfs'   # 'dfs' | 'bfs' | 'kruskal'

        # DFS төлөв
        self.dfs = {
            'state': None,
            'info':  'DFS (Гүний хайлт) — Стек ашиглан гүн рүү явна.',
            'log':   '—',
        }
        # BFS төлөв
        self.bfs = {
            'state': None,
            'info':  'BFS (Өргөний хайлт) — Дараалал ашиглан өргөнөөр явна.',
            'log':   '—',
        }
        # Kruskal төлөв
        self.kruskal = {
            'state': None,
            'info':  'Kruskal — Хамгийн бага тархсан мод (MST).',
            'log':   '—',
        }

        self._build_ui()

    # ── UI бүтэц ──────────────────────────────────────────────────
    def _build_ui(self):
        w = self.screen.get_width()

        # Tab товчнууд
        self.tab_btns = {}
        labels = [('dfs', 'DFS'), ('bfs', 'BFS'), ('kruskal', 'Kruskal')]
        tx = PAD
        for key, lbl in labels:
            bw = 90
            self.tab_btns[key] = pygame.Rect(tx, 8, bw, 30)
            tx += bw + 8

        # Граф хэсэг
        self.graph_rect = (PAD, TAB_H + CTRL_H + PAD, w - 2*PAD, GRAPH_H)

        # Мэдээллийн хэсэгнүүд
        gy2 = TAB_H + CTRL_H + PAD + GRAPH_H + 6
        self.info_rect = pygame.Rect(PAD, gy2,        w - 2*PAD, INFO_H)
        self.log_rect  = pygame.Rect(PAD, gy2 + INFO_H + 6, w - 2*PAD, LOG_H)

        # Контрол товчнууд — DFS
        cy = TAB_H + 6
        self.btn_dfs_start = Button((PAD,       cy, 110, 30), '▶ Эхлүүлэх', primary=True)
        self.btn_dfs_step  = Button((PAD+118,   cy, 100, 30), 'Алхам →')
        self.btn_dfs_reset = Button((PAD+226,   cy,  96, 30), '↺ Шинэчлэх')
        self.btn_dfs_step.enabled = False

        # BFS
        self.btn_bfs_start = Button((PAD,       cy, 110, 30), '▶ Эхлүүлэх', primary=True)
        self.btn_bfs_step  = Button((PAD+118,   cy, 100, 30), 'Алхам →')
        self.btn_bfs_reset = Button((PAD+226,   cy,  96, 30), '↺ Шинэчлэх')
        self.btn_bfs_step.enabled = False

        # Kruskal
        self.btn_kr_start  = Button((PAD,       cy, 110, 30), '▶ Эхлүүлэх', primary=True)
        self.btn_kr_step   = Button((PAD+118,   cy, 100, 30), 'Алхам →')
        self.btn_kr_reset  = Button((PAD+226,   cy,  96, 30), '↺ Шинэчлэх')
        self.btn_kr_step.enabled = False

        self._update_nodes_pos()

    def _update_nodes_pos(self):
        w = self.screen.get_width()
        gr = (PAD, TAB_H + CTRL_H + PAD, w - 2*PAD, GRAPH_H)
        self.nodes_pos = scale_pos(RAW_NODES, gr)

    # ── DFS үйлдлүүд ──────────────────────────────────────────────
    def dfs_reset(self):
        self.dfs['state'] = None
        self.dfs['info']  = 'DFS (Гүний хайлт) — Стек ашиглан гүн рүү явна.'
        self.dfs['log']   = '—'
        self.btn_dfs_step.enabled = False

    def dfs_start(self):
        adj = self._build_adj()
        s = {
            'adj':       adj,
            'visited':   {},
            'stack':     ['A'],
            'order':     [],
            'parent':    {'A': None},
            'node_col':  {n: NODE_DEF for n in RAW_NODES},
            'edge_col':  {},
            'done':      False,
        }
        s['node_col']['A'] = NODE_CUR
        self.dfs['state'] = s
        self.dfs['info']  = 'Стек: [A] — "Алхам" товч дарна уу.'
        self.dfs['log']   = 'Стект A нэмлээ'
        self.btn_dfs_step.enabled = True

    def dfs_step(self):
        s = self.dfs['state']
        if not s or s['done']:
            return
        while s['stack']:
            cur = s['stack'].pop()
            if cur in s['visited']:
                continue
            s['visited'][cur] = True
            s['order'].append(cur)
            s['node_col'][cur] = NODE_VISIT
            par = s['parent'].get(cur)
            if par:
                s['edge_col'][edge_key(par, cur)] = EDGE_TREE
            # хөршүүд (буцаа дарааллаар нэмж, жижиг индекс эхэлнэ)
            nbrs = [nb for nb in s['adj'][cur] if nb not in s['visited']]
            for nb in reversed(nbrs):
                s['stack'].append(nb)
                if nb not in s['parent']:
                    s['parent'][nb] = cur
                if s['node_col'].get(nb) == NODE_DEF:
                    s['node_col'][nb] = NODE_QUEUE
            stk_clean = [x for x in reversed(s['stack']) if x not in s['visited']]
            stk_str   = '[' + ', '.join(stk_clean) + ']' if stk_clean else '(хоосон)'
            self.dfs['info'] = f"Одоогийн: {cur}  |  Стек: {stk_str}"
            self.dfs['log']  = 'Зочилсон: ' + ' → '.join(s['order'])
            if not stk_clean:
                s['done'] = True
                self.btn_dfs_step.enabled = False
                self.dfs['info'] = 'DFS дууслаа.  Дараалал: ' + ' → '.join(s['order'])
            return
        s['done'] = True
        self.btn_dfs_step.enabled = False

    # ── BFS үйлдлүүд ──────────────────────────────────────────────
    def bfs_reset(self):
        self.bfs['state'] = None
        self.bfs['info']  = 'BFS (Өргөний хайлт) — Дараалал ашиглан өргөнөөр явна.'
        self.bfs['log']   = '—'
        self.btn_bfs_step.enabled = False

    def bfs_start(self):
        adj = self._build_adj()
        s = {
            'adj':      adj,
            'visited':  {'A'},
            'queue':    deque(['A']),
            'order':    [],
            'parent':   {},
            'dist':     {'A': 0},
            'node_col': {n: NODE_DEF for n in RAW_NODES},
            'edge_col': {},
            'done':     False,
        }
        s['node_col']['A'] = NODE_CUR
        self.bfs['state'] = s
        self.bfs['info']  = 'Дараалал: [A] — "Алхам" товч дарна уу.'
        self.bfs['log']   = 'Дараалалд A нэмлээ'
        self.btn_bfs_step.enabled = True

    def bfs_step(self):
        s = self.bfs['state']
        if not s or s['done']:
            return
        if not s['queue']:
            s['done'] = True
            self.btn_bfs_step.enabled = False
            return
        cur = s['queue'].popleft()
        s['order'].append(cur)
        s['node_col'][cur] = NODE_VISIT
        par = s['parent'].get(cur)
        if par:
            s['edge_col'][edge_key(par, cur)] = EDGE_TREE
        for nb in s['adj'][cur]:
            if nb not in s['visited']:
                s['visited'].add(nb)
                s['queue'].append(nb)
                s['node_col'][nb] = NODE_QUEUE
                s['parent'][nb]   = cur
                s['dist'][nb]     = s['dist'].get(cur, 0) + 1
        q_str = '[' + ', '.join(s['queue']) + ']' if s['queue'] else '(хоосон)'
        self.bfs['info'] = f"Одоогийн: {cur}  |  Дараалал: {q_str}"
        self.bfs['log']  = 'Зочилсон: ' + ' → '.join(s['order'])
        if not s['queue']:
            s['done'] = True
            self.btn_bfs_step.enabled = False
            self.bfs['info'] = 'BFS дууслаа.  Дараалал: ' + ' → '.join(s['order'])

    # ── Kruskal үйлдлүүд ──────────────────────────────────────────
    def kr_reset(self):
        self.kruskal['state'] = None
        self.kruskal['info']  = 'Kruskal — Хамгийн бага тархсан мод (MST).'
        self.kruskal['log']   = '—'
        self.btn_kr_step.enabled = False

    def kr_start(self):
        sorted_edges = sorted(RAW_EDGES, key=lambda e: e[2])
        s = {
            'sorted':   sorted_edges,
            'uf':       UF(list(RAW_NODES.keys())),
            'idx':      0,
            'mst':      [],
            'total_w':  0,
            'node_col': {n: NODE_DEF for n in RAW_NODES},
            'edge_col': {},
            'done':     False,
        }
        self.kruskal['state'] = s
        seq = '  '.join(f"{u}-{v}({w})" for u, v, w in sorted_edges)
        self.kruskal['info'] = 'Жингийн дараалал: ' + seq
        self.kruskal['log']  = 'MST: (хоосон) | Нийт жин: 0'
        self.btn_kr_step.enabled = True

    def kr_step(self):
        s = self.kruskal['state']
        if not s or s['done']:
            return
        if s['idx'] >= len(s['sorted']) or len(s['mst']) >= len(RAW_NODES) - 1:
            s['done'] = True
            self.btn_kr_step.enabled = False
            self.kruskal['info'] = f"MST дууслаа!  Нийт жин: {s['total_w']}"
            return

        u, v, w = s['sorted'][s['idx']]
        s['idx'] += 1
        k = edge_key(u, v)
        s['edge_col'][k] = EDGE_CHECK   # шар — шалгаж байна

        if s['uf'].unite(u, v):
            s['edge_col'][k]    = EDGE_MST
            s['node_col'][u]    = NODE_VISIT
            s['node_col'][v]    = NODE_VISIT
            s['mst'].append((u, v, w))
            s['total_w']       += w
            self.kruskal['info'] = f"✓  {u}–{v} ({w})  MST-д нэмлээ — мөчлөг үүсгэхгүй"
        else:
            s['edge_col'][k] = EDGE_REJECT
            self.kruskal['info'] = f"✗  {u}–{v} ({w})  алгасав — мөчлөг үүсгэнэ"

        mst_str = '  '.join(f"{a}-{b}({c})" for a, b, c in s['mst']) or '—'
        self.kruskal['log'] = f"MST: {mst_str}  |  Нийт: {s['total_w']}"

        if len(s['mst']) >= len(RAW_NODES) - 1:
            s['done'] = True
            self.btn_kr_step.enabled = False
            self.kruskal['info'] = f"MST дууслаа!  Нийт жин: {s['total_w']}"

    # ── Туслах ────────────────────────────────────────────────────
    def _build_adj(self):
        adj = {n: [] for n in RAW_NODES}
        for u, v, _ in RAW_EDGES:
            adj[u].append(v)
            adj[v].append(u)
        return adj

    def _cur_state(self):
        return {'dfs': self.dfs, 'bfs': self.bfs, 'kruskal': self.kruskal}[self.tab]

    # ── Зурах ─────────────────────────────────────────────────────
    def draw(self):
        w = self.screen.get_width()
        self.screen.fill(BG)

        # ── Tab мөр ──
        pygame.draw.rect(self.screen, WHITE, (0, 0, w, TAB_H))
        pygame.draw.line(self.screen, BORDER, (0, TAB_H-1), (w, TAB_H-1), 1)
        for key, rect in self.tab_btns.items():
            active = (key == self.tab)
            bg  = TAB_ACTIVE_BG  if active else TAB_BG
            fg  = TAB_ACTIVE_FG  if active else TAB_FG
            brd = TAB_ACTIVE_BRD if active else BORDER
            lbl = {'dfs':'DFS','bfs':'BFS','kruskal':'Kruskal'}[key]
            draw_rounded_rect(self.screen, bg, rect, r=6, border=1, border_color=brd)
            draw_text(self.screen, lbl, FONT_B, fg, rect.centerx, rect.centery)

        # ── Контрол товчнууд ──
        pygame.draw.rect(self.screen, WHITE, (0, TAB_H, w, CTRL_H))
        pygame.draw.line(self.screen, BORDER, (0, TAB_H+CTRL_H-1), (w, TAB_H+CTRL_H-1), 1)
        if self.tab == 'dfs':
            self.btn_dfs_start.draw(self.screen)
            self.btn_dfs_step.draw(self.screen)
            self.btn_dfs_reset.draw(self.screen)
            lbl = 'Эхлэх зангилаа: A'
            draw_text(self.screen, lbl, FONT_SM, TEXT_DIM, PAD+332, TAB_H+22, 'left')
        elif self.tab == 'bfs':
            self.btn_bfs_start.draw(self.screen)
            self.btn_bfs_step.draw(self.screen)
            self.btn_bfs_reset.draw(self.screen)
            lbl = 'Эхлэх зангилаа: A'
            draw_text(self.screen, lbl, FONT_SM, TEXT_DIM, PAD+332, TAB_H+22, 'left')
        else:
            self.btn_kr_start.draw(self.screen)
            self.btn_kr_step.draw(self.screen)
            self.btn_kr_reset.draw(self.screen)

        # ── Граф хэсэг ──
        gx, gy, gw, gh = PAD, TAB_H + CTRL_H + PAD, w - 2*PAD, GRAPH_H
        draw_rounded_rect(self.screen, WHITE, (gx, gy, gw, gh), r=8, border=1, border_color=BORDER)

        st = self._cur_state()['state']
        if st:
            node_col = st['node_col']
            edge_col = st['edge_col']
            labels   = st.get('dist') if self.tab == 'bfs' else None
        else:
            node_col = {}
            edge_col = {}
            labels   = None

        # Граф clippping
        clip = self.screen.get_clip()
        self.screen.set_clip((gx+4, gy+4, gw-8, gh-8))
        draw_graph(self.screen, (gx, gy, gw, gh),
                   self.nodes_pos, node_col, edge_col, labels)
        self.screen.set_clip(clip)

        # ── Тайлбар ──
        gy2 = TAB_H + CTRL_H + PAD + GRAPH_H + 6
        info_r = (PAD, gy2,        w - 2*PAD, INFO_H)
        log_r  = (PAD, gy2+INFO_H+5, w - 2*PAD, LOG_H)
        draw_rounded_rect(self.screen, INFO_BG, info_r, r=6, border=1, border_color=BORDER)
        draw_rounded_rect(self.screen, LOG_BG,  log_r,  r=6, border=1, border_color=BORDER)
        info_txt = self._cur_state()['info']
        log_txt  = self._cur_state()['log']
        # текстийг잘라서 표시 (урт бол тайрах)
        self._draw_wrapped(info_txt, FONT_MD, TEXT_SEC, info_r, pad=10)
        self._draw_wrapped(log_txt,  FONT_SM, TEXT_DIM, log_r,  pad=10)

        # ── Тайлбарын легенд ──
        lx = w - 220
        ly = gy2 - 2
        items = [
            (NODE_VISIT,  'Зочилсон'),
            (NODE_CUR,    'Одоогийн'),
            (NODE_QUEUE,  'Дараалалд'),
            (EDGE_TREE,   'Мод ирмэг'),
            (EDGE_REJECT, 'Татгалзсан'),
        ]
        for i, (col, lbl) in enumerate(items):
            ix = lx + (i % 3) * 72
            iy = ly + (i // 3) * 18
            pygame.draw.circle(self.screen, col, (ix, iy+7), 5)
            draw_text(self.screen, lbl, FONT_SM, TEXT_DIM, ix+10, iy+7, 'left')

        pygame.display.flip()

    def _draw_wrapped(self, text, font, color, rect, pad=8):
        x, y, w, h = rect
        words = text.split(' ')
        line  = ''
        lines = []
        for word in words:
            test = (line + ' ' + word).strip()
            if font.size(test)[0] > w - 2*pad:
                if line:
                    lines.append(line)
                line = word
            else:
                line = test
        if line:
            lines.append(line)
        total_h = len(lines) * font.get_linesize()
        sy = y + (h - total_h) // 2
        for i, ln in enumerate(lines):
            surf = font.render(ln, True, color)
            self.screen.blit(surf, (x + pad, sy + i * font.get_linesize()))

    # ── Үйл явдал боловсруулах ────────────────────────────────────
    def handle(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            self._update_nodes_pos()
            return True

        # Tab сонгох
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in self.tab_btns.items():
                if rect.collidepoint(event.pos):
                    self.tab = key
                    return True

        # DFS товчнууд
        if self.tab == 'dfs':
            if self.btn_dfs_start.handle(event): self.dfs_start()
            if self.btn_dfs_step.handle(event):  self.dfs_step()
            if self.btn_dfs_reset.handle(event): self.dfs_reset()
        elif self.tab == 'bfs':
            if self.btn_bfs_start.handle(event): self.bfs_start()
            if self.btn_bfs_step.handle(event):  self.bfs_step()
            if self.btn_bfs_reset.handle(event): self.bfs_reset()
        else:
            if self.btn_kr_start.handle(event): self.kr_start()
            if self.btn_kr_step.handle(event):  self.kr_step()
            if self.btn_kr_reset.handle(event): self.kr_reset()

        # Hover шинэчлэх
        for btn in [self.btn_dfs_start, self.btn_dfs_step, self.btn_dfs_reset,
                    self.btn_bfs_start, self.btn_bfs_step, self.btn_bfs_reset,
                    self.btn_kr_start,  self.btn_kr_step,  self.btn_kr_reset]:
            btn.handle(event)
        return True

    # ── Үндсэн давталт ────────────────────────────────────────────
    def run(self):
        while True:
            for event in pygame.event.get():
                if not self.handle(event):
                    pygame.quit()
                    sys.exit()
            self.draw()
            self.clock.tick(60)


if __name__ == '__main__':
    App().run()