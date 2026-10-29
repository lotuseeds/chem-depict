"""chemstyle —— 药物化学结构式统一画风（RDKit）   用法见 ../SKILL.md

画风：ACS1996 线宽/字号比例 + 元素习惯色 + 灰绿色 H + 浅红高亮（高亮原子保留元素色）
排版：默认 RDKit 环系模板；内置经典教材式吗啡烷坐标；可传 coord_map / align_to / 模板 mol 文件
氢：OH、NH 合写；只标关键氢（桥头/稠环立体中心的 H + key_h 指定的教学关键氢）
交叉键：自动检测，压在下方的键在交叉处断开（白色衬底）；上下关系可用 over 指定
尺寸：统一键长 BOND_PX（默认 26 px，画框 360×260），放不下才单图等比缩小
"""
import re, math, ast, html, os
from rdkit import Chem
from rdkit.Chem import rdDepictor, Draw
from rdkit.Chem.Draw import rdMolDraw2D
from rdkit.Geometry import Point2D, Point3D

# 元素习惯色（CPK/Jmol 系，调暗以适合白底）；H 为灰绿
PALETTE = {1: (0.38, 0.54, 0.46), 6: (0, 0, 0), 7: (0.10, 0.25, 0.85), 8: (0.85, 0.05, 0.05),
           9: (0.10, 0.60, 0.30), 15: (0.90, 0.45, 0.00), 16: (0.75, 0.60, 0.00),
           17: (0.10, 0.60, 0.10), 35: (0.60, 0.15, 0.10), 53: (0.45, 0.10, 0.55)}
HIGHLIGHT = (1, .82, .82)
BOND_PX = 26          # 网页显示键长（CSS px，约为 ACS 印刷尺寸的 1.35 倍，便于投影）
# ACS Document 1996：键长 14.4 pt、线宽 0.6 pt、Arial 10 pt、留白（margin）1.6 pt；导出图按此物理尺寸
ACS_BOND_PT = 14.4
ACS_MARGIN_PT = 1.6
ARIAL = next((f for f in ("C:/Windows/Fonts/arial.ttf", "/Library/Fonts/Arial.ttf",
                          "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf") if os.path.exists(f)), None)
UNIT = 1.5            # RDKit 坐标中 1 个键长 = 1.5；本模块对外坐标一律以「键长」为单位

# —— 经典教材式吗啡烷（芳环在上、4,5-醚桥在左、6-OH 左下、N-CH3 在右）——
# 键为吗啡 SMILES 原子序：0 N-CH3,1 N17,2 C16,3 C15,4 C13,5 C14,6 C9,7 C10,8 C11,9 C12,
# 10 C4,11 C3,12 C2,13 C1,14 3-O,15 4,5-O,16 C5,17 C6,18 C7,19 C8,20 6-O
MORPHINE_SMILES = "CN1CC[C@]23[C@@H]4[C@H]1CC5=C2C(=C(C=C5)O)O[C@H]3[C@H](C=C4)O"
MORPHINAN_CLASSIC = {12: (0, 1), 13: (0.866, 0.5), 8: (0.866, -0.5), 9: (0, -1), 10: (-0.866, -0.5),
    11: (-0.866, 0.5), 7: (1.732, -1), 6: (1.732, -2), 5: (0.866, -2.5), 4: (0, -2),
    19: (0.866, -3.5), 18: (0, -4), 17: (-0.866, -3.5), 16: (-0.866, -2.5),
    15: (-1.6, -1.5), 14: (-1.732, 1.0), 20: (-1.732, -4.0),
    3: (1.2, -1.5), 2: (2.55, -1.5), 1: (2.6, -2.5), 0: (3.47, -3.0)}
MORPHINAN_CLASSIC_H = {16: (-1.45, -2.95), 5: (1.35, -3.05), 6: (2.05, -2.75)}   # C5/C14/C9 的 H，互不遮挡
TEMPLATES = {"morphinan_classic": (MORPHINE_SMILES, MORPHINAN_CLASSIC, MORPHINAN_CLASSIC_H)}


def layout(smi, template=None, coord_map=None, align_to=None):
    """生成 2D 坐标。
    template : TEMPLATES 键名（如 "morphinan_classic"），分子须含该骨架（可多取代，如海洛因、可待因）
    coord_map: {原子序: (x, y)}，键长单位，固定部分原子，其余自动
    align_to : 已排好坐标的分子，按其全部原子做子结构对齐（同组对比分子用，保证骨架同朝向）
    都不给   : RDKit 环系模板（useRingTemplates）"""
    m = Chem.MolFromSmiles(smi)
    if template:
        tsmi, tc, th = TEMPLATES[template]
        mt = m.GetSubstructMatch(Chem.MolFromSmiles(tsmi))
        if not mt:
            raise ValueError("分子不含模板骨架：" + template)
        coord_map = {mt[k]: v for k, v in tc.items()}
        m.SetProp("_key_h_pos", repr({mt[k]: v for k, v in th.items()}))
    if coord_map:
        rdDepictor.Compute2DCoords(m, coordMap={k: Point2D(UNIT * x, UNIT * y) for k, (x, y) in coord_map.items()})
    elif align_to is not None:
        q = Chem.MolFromSmarts(Chem.MolToSmiles(align_to, isomericSmiles=False))
        a, b = m.GetSubstructMatch(q), align_to.GetSubstructMatch(q)
        if not a:
            raise ValueError("align_to 的骨架不在本分子中")
        cf = align_to.GetConformer()
        rdDepictor.Compute2DCoords(m, coordMap={i: Point2D(cf.GetAtomPosition(j).x, cf.GetAtomPosition(j).y) for i, j in zip(a, b)})
    else:
        rdDepictor.Compute2DCoords(m, useRingTemplates=True)
    return m


def from_molfile(path, smi):
    """读取手工定好坐标的 mol 文件（templates/ 下），并核对与 SMILES 是同一分子（含立体）"""
    m = Chem.MolFromMolFile(path)
    if Chem.MolToSmiles(m) != Chem.MolToSmiles(Chem.MolFromSmiles(smi)):
        raise ValueError("mol 文件与 SMILES 不是同一分子：" + path)
    return m


def coords(m):
    """{原子序: (x, y)}，键长单位——手工微调前先打印看"""
    c = m.GetConformer()
    return {i: (round(c.GetAtomPosition(i).x / UNIT, 3), round(c.GetAtomPosition(i).y / UNIT, 3)) for i in range(m.GetNumAtoms())}


def place(m, pos):
    """手工指定部分原子坐标（键长单位），其余原子保持原位"""
    cur = coords(m)
    cur.update(pos)
    m = Chem.Mol(m)
    rdDepictor.Compute2DCoords(m, coordMap={k: Point2D(UNIT * x, UNIT * y) for k, (x, y) in cur.items()})
    return m


def close_contacts(m, limit=0.5):
    """非键合原子间距 < limit×平均键长 的原子对（画面重叠隐患）。出图前必查。"""
    c = m.GetConformer()
    P = [c.GetAtomPosition(i) for i in range(m.GetNumAtoms())]
    bl = [(P[b.GetBeginAtomIdx()] - P[b.GetEndAtomIdx()]).Length() for b in m.GetBonds()]
    L = sum(bl) / len(bl) if bl else UNIT
    return [(i, j, round((P[i] - P[j]).Length() / L, 2)) for i in range(len(P)) for j in range(i + 1, len(P))
            if m.GetBondBetweenAtoms(i, j) is None and (P[i] - P[j]).Length() < limit * L]


def hits(m, smarts):
    """SMARTS 命中的全部原子序（用于高亮）"""
    return sorted({i for t in m.GetSubstructMatches(Chem.MolFromSmarts(smarts)) for i in t})


def _add_key_h(m, key_h):
    if not key_h:
        return m
    ref = Chem.MolToSmiles(m)
    mh = Chem.AddHs(m, onlyOnAtoms=list(key_h), addCoords=True)
    cf = mh.GetConformer()
    for a, pos in key_h.items():
        hs = [n.GetIdx() for n in mh.GetAtomWithIdx(a).GetNeighbors() if n.GetAtomicNum() == 1]
        if pos and hs:
            cf.SetAtomPosition(hs[0], Point3D(UNIT * pos[0], UNIT * pos[1], 0))
    if Chem.MolToSmiles(Chem.RemoveHs(mh)) != ref:
        raise ValueError("加 H 后立体信息变化")
    return mh


def _seg_x(p1, p2, p3, p4):
    d1 = (p2[0] - p1[0], p2[1] - p1[1]); d2 = (p4[0] - p3[0], p4[1] - p3[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((p3[0] - p1[0]) * d2[1] - (p3[1] - p1[1]) * d2[0]) / den
    u = ((p3[0] - p1[0]) * d1[1] - (p3[1] - p1[1]) * d1[0]) / den
    if 0.02 < t < 0.98 and 0.02 < u < 0.98:
        return (p1[0] + t * d1[0], p1[1] + t * d1[1]), abs(den) / (math.hypot(*d1) * math.hypot(*d2))
    return None


def _upper(pm, b1, b2, over):
    """两交叉键谁在上：over 指定 > 非环键 > 含实楔形宽端原子的键 > 序号大者"""
    for b in (b1, b2):
        if tuple(sorted((b.GetBeginAtomIdx(), b.GetEndAtomIdx()))) in over:
            return b
    if b1.IsInRing() != b2.IsInRing():
        return b2 if b1.IsInRing() else b1
    wide = {b.GetEndAtomIdx() for b in pm.GetBonds() if b.GetBondDir() == Chem.BondDir.BEGINWEDGE}
    w1 = bool({b1.GetBeginAtomIdx(), b1.GetEndAtomIdx()} & wide)
    w2 = bool({b2.GetBeginAtomIdx(), b2.GetEndAtomIdx()} & wide)
    if w1 != w2:
        return b1 if w1 else b2
    return b1 if b1.GetIdx() > b2.GetIdx() else b2


def _cut_d(d, p0, n, g):
    """把路径 d 中落在带状区 |n·(p-p0)| < g/2 内的部分剪掉，返回若干新 d（折线按段剪，闭合多边形按半平面裁剪）"""
    pts = [(float(x), float(y)) for x, y in re.findall(r"(-?[\d.]+),(-?[\d.]+)", d)]
    sd = lambda q: (q[0] - p0[0]) * n[0] + (q[1] - p0[1]) * n[1]
    lo, hi = -g / 2, g / 2
    out = []
    if d.strip().endswith("Z") and len(pts) >= 3:
        for keep in (lambda v: v <= lo, lambda v: v >= hi):
            poly, edge = [], (lo if keep(lo - 1) else hi)
            for i in range(len(pts)):
                P, Q = pts[i], pts[(i + 1) % len(pts)]
                sp, sq = sd(P), sd(Q)
                if keep(sp):
                    poly.append(P)
                if keep(sp) != keep(sq) and sq != sp:
                    t = (edge - sp) / (sq - sp)
                    poly.append((P[0] + t * (Q[0] - P[0]), P[1] + t * (Q[1] - P[1])))
            if len(poly) >= 3:
                out.append("M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in poly) + " Z")
        return out
    for P, Q in zip(pts, pts[1:]):
        sp, sq = sd(P), sd(Q)
        for rlo, rhi in ((-1e9, lo), (hi, 1e9)):
            if sq == sp:
                t0, t1 = (0, 1) if rlo <= sp <= rhi else (1, 0)
            else:
                ta, tb = (rlo - sp) / (sq - sp), (rhi - sp) / (sq - sp)
                t0, t1 = max(0, min(ta, tb)), min(1, max(ta, tb))
            if t1 - t0 > 1e-3:
                A = (P[0] + t0 * (Q[0] - P[0]), P[1] + t0 * (Q[1] - P[1]))
                B = (P[0] + t1 * (Q[0] - P[0]), P[1] + t1 * (Q[1] - P[1]))
                out.append(f"M {A[0]:.2f},{A[1]:.2f} L {B[0]:.2f},{B[1]:.2f}")
    return out


def _break_crossings(svg, pm, pos, over):
    """交叉键：把压在下方的键在交叉处真正剪断（不用白线遮挡，透明背景下也不露白）"""
    bonds = list(pm.GetBonds())
    lw = re.search(r"<path class='bond-\d+ [^>]*?fill:none;[^>]*?stroke-width:([\d.]+)px", svg)   # 取键的线宽（不能取高亮椭圆的描边）
    bl = [math.dist(pos[b.GetBeginAtomIdx()], pos[b.GetEndAtomIdx()]) for b in bonds
          if b.GetBeginAtom().GetAtomicNum() > 1 and b.GetEndAtom().GetAtomicNum() > 1]
    unit_per_pt = (sum(bl) / len(bl)) / ACS_BOND_PT if bl else 1
    gap = (float(lw.group(1)) if lw else 0.6) + 2 * ACS_MARGIN_PT * unit_per_pt
    cuts = {}
    for x in range(len(bonds)):
        for y in range(x + 1, len(bonds)):
            b1, b2 = bonds[x], bonds[y]
            if {b1.GetBeginAtomIdx(), b1.GetEndAtomIdx()} & {b2.GetBeginAtomIdx(), b2.GetEndAtomIdx()}:
                continue
            r = _seg_x(pos[b1.GetBeginAtomIdx()], pos[b1.GetEndAtomIdx()], pos[b2.GetBeginAtomIdx()], pos[b2.GetEndAtomIdx()])
            if not r:
                continue
            (px, py), _ = r
            up = _upper(pm, b1, b2, over)
            low = b2 if up is b1 else b1
            a, b = pos[up.GetBeginAtomIdx()], pos[up.GetEndAtomIdx()]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            cuts.setdefault(low.GetIdx(), []).append(((px, py), (-(b[1] - a[1]) / L, (b[0] - a[0]) / L)))
    for k, lst in cuts.items():
        def rep(mm):
            ds = [mm.group(2)]
            for p0, n in lst:
                ds = [nd for d in ds for nd in _cut_d(d, p0, n, gap)]
            return "".join(f"{mm.group(1)}{d}{mm.group(3)}" for d in ds)
        svg = re.sub(rf"(<path class='bond-{k} [^>]*? d=')([^']*)('[^>]*/>)", rep, svg)
    return svg


def _content_bbox(svg, pad):
    """内容边界框（viewBox 单位，不含白底矩形）：路径坐标 + 椭圆外接框"""
    body = svg.split("<!-- END OF HEADER -->")[-1]
    xs, ys = [], []
    for d in re.findall(r" d='([^']*)'", body):
        for x, y in re.findall(r"(-?[\d.]+)[ ,](-?[\d.]+)", d):
            xs.append(float(x)); ys.append(float(y))
    for cx, cy, rx, ry in re.findall(r"<ellipse cx='(-?[\d.]+)' cy='(-?[\d.]+)' rx='([\d.]+)' ry='([\d.]+)'", body):
        cx, cy, rx, ry = map(float, (cx, cy, rx, ry))
        xs += [cx - rx, cx + rx]; ys += [cy - ry, cy + ry]
    return (min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)


def draw(m, highlight=(), key_h=None, over=(), w=360, h=260, bond_px=None, chiral_h=True):
    """返回 SVG 字符串（外框 w×h，统一键长居中；放不下时单图等比缩小）。
    highlight: 高亮原子序（整环在内 → 环内涂色；开链 → 键色带；孤立原子 → 圆点）；key_h: 教学关键氢 {原子序: None 或 (x, y) 键长单位}
    over: [(i, j), ...] 交叉时强制在上方的键；chiral_h: 桥头/稠环立体中心自动标 H"""
    m = Chem.Mol(m)
    if chiral_h:
        tmp = rdMolDraw2D.PrepareMolForDrawing(m, addChiralHs=True)
        auto = [b.GetOtherAtomIdx(a.GetIdx()) for a in tmp.GetAtoms() if a.GetAtomicNum() == 1 for b in a.GetBonds()]
        preset = ast.literal_eval(m.GetProp("_key_h_pos")) if m.HasProp("_key_h_pos") else {}
        key_h = {**{i: preset.get(i) for i in auto if i < m.GetNumAtoms()}, **(key_h or {})}
    m = _add_key_h(m, key_h)
    pm = rdMolDraw2D.PrepareMolForDrawing(m, addChiralHs=False)
    d = rdMolDraw2D.MolDraw2DSVG(-1, -1)
    o = d.drawOptions()
    rdMolDraw2D.SetACS1996Mode(o, Draw.MeanBondLength(pm) or UNIT)
    o.updateAtomPalette(PALETTE)
    o.standardColoursForHighlightedAtoms = True
    o.setHighlightColour(HIGHLIGHT); o.highlightRadius = 0.35
    o.highlightBondWidthMultiplier = 96     # 开链高亮色带宽度（ACS 线宽下默认 32 太细，几乎看不见）
    o.prepareMolsBeforeDrawing = False
    if ARIAL:
        o.fontFile = ARIAL
    S = {i for i in highlight if i < pm.GetNumAtoms()}
    rings = [r for r in pm.GetRingInfo().AtomRings() if set(r) <= S]            # 环上原子全在高亮内 → 整环涂色
    ring_bonds = {pm.GetBondBetweenAtoms(r[i], r[(i + 1) % len(r)]).GetIdx() for r in rings for i in range(len(r))}
    hb = [b.GetIdx() for b in pm.GetBonds() if b.GetBeginAtomIdx() in S and b.GetEndAtomIdx() in S
          and b.GetIdx() not in ring_bonds]                                      # 开链高亮 → 键色带
    covered = {a for r in rings for a in r} | {x for b in hb for x in (pm.GetBondWithIdx(b).GetBeginAtomIdx(), pm.GetBondWithIdx(b).GetEndAtomIdx())}
    lone = sorted(S - covered)                                                   # 孤立原子 → 圆点
    d.DrawMolecule(pm, highlightAtoms=lone, highlightBonds=hb)
    d.FinishDrawing()
    svg = d.GetDrawingText()
    pos = {i: (d.GetDrawCoords(i).x, d.GetDrawCoords(i).y) for i in range(pm.GetNumAtoms())}
    svg = _break_crossings(svg, pm, pos, {tuple(sorted(x)) for x in over})
    if rings:
        col = "#{:02X}{:02X}{:02X}".format(*[round(255 * c) for c in HIGHLIGHT])
        polys = "".join("<path class='hl-ring' d='M " + " L ".join(f"{pos[a][0]:.2f},{pos[a][1]:.2f}" for a in r)
                        + f" Z' style='fill:{col};fill-rule:evenodd;stroke:none' />\n" for r in rings)
        svg = re.sub(r"(<rect style='opacity:1.0;fill:#FFFFFF;stroke:none'[^>]*>\s*</rect>\n?)", lambda mm: mm.group(1) + polys, svg, count=1)
    svg = re.sub(r"^<\?xml[^>]*\?>\s*", "", svg).rstrip()
    heavy = [math.dist(pos[b.GetBeginAtomIdx()], pos[b.GetEndAtomIdx()]) for b in pm.GetBonds()
             if b.GetBeginAtom().GetAtomicNum() > 1 and b.GetEndAtom().GetAtomicNum() > 1]
    vb = [float(x) for x in re.search(r"viewBox='([^']+)'", svg).group(1).split()]
    s = (bond_px or BOND_PX) / (sum(heavy) / len(heavy)) if heavy else 1
    s = min(s, w / vb[2], h / vb[3])
    W, H = w / s, h / s
    x0, y0 = vb[0] - (W - vb[2]) / 2, vb[1] - (H - vb[3]) / 2
    svg = re.sub(r"viewBox='[^']+'", f"viewBox='{x0:.1f} {y0:.1f} {W:.1f} {H:.1f}'", svg, count=1)
    svg = re.sub(r"<rect style='opacity:1.0;fill:#FFFFFF;stroke:none' width='[\d.]+' height='[\d.]+' x='[\d.-]+' y='[\d.-]+'>",
                 f"<rect style='opacity:1.0;fill:#FFFFFF;stroke:none' width='{W:.1f}' height='{H:.1f}' x='{x0:.1f}' y='{y0:.1f}'>", svg, count=1)
    bx = _content_bbox(svg, pad=3 / s)
    svg = svg.replace("<svg ", f"<svg data-bbox='{bx[0]:.1f} {bx[1]:.1f} {bx[2]:.1f} {bx[3]:.1f}' data-bond='{sum(heavy) / len(heavy) if heavy else 0:.3f}' ", 1)
    return re.sub(r"width='[\d.]+px' height='[\d.]+px'", f"width='{w}px' height='{h}px'", svg, count=1)


def export_svg(svg, crop=True, transparent=True):
    """导出用 SVG：去白底、裁到内容边界（data-bbox），物理尺寸按 ACS Document 1996（键长 14.4 pt，线宽 0.6 pt，Arial 10 pt）"""
    vb = [float(x) for x in re.search(r"viewBox='([^']+)'", svg).group(1).split()]
    k = float(re.search(r"width='([\d.]+)px'", svg).group(1)) / vb[2]
    if crop and "data-bbox=" in svg:
        vb = [float(x) for x in re.search(r"data-bbox='([^']+)'", svg).group(1).split()]
        svg = re.sub(r"viewBox='[^']+'", "viewBox='{:.1f} {:.1f} {:.1f} {:.1f}'".format(*vb), svg, count=1)
    if transparent:
        svg = re.sub(r"<rect style='opacity:1.0;fill:#FFFFFF;stroke:none'[^>]*>\s*</rect>", "", svg, count=1)
    mb = re.search(r"data-bond='([\d.]+)'", svg)
    pt_per_unit = ACS_BOND_PT / float(mb.group(1)) if mb and float(mb.group(1)) > 0 else k * 0.75
    svg = re.sub(r"width='[\d.]+px' height='[\d.]+px'", f"width='{vb[2] * pt_per_unit:.2f}pt' height='{vb[3] * pt_per_unit:.2f}pt'", svg, count=1)
    return svg


def to_png(svg, dpi=600, transparent=True, crop=True):
    """SVG → PNG 字节：裁白边、透明背景、600 dpi、ACS 印刷尺寸（键长 14.4 pt ≈ 120 px），PNG 内写 dpi。
    供本地预览或拼图自查；交付给用户的图一律走 HTML 图板上的按钮。"""
    import fitz, io
    from PIL import Image
    ex = export_svg(svg, crop=crop, transparent=transparent)
    pix = fitz.open(stream=ex.encode(), filetype="svg")[0].get_pixmap(dpi=dpi, alpha=transparent)
    im = Image.open(io.BytesIO(pix.tobytes("png")))
    buf = io.BytesIO(); im.save(buf, "PNG", dpi=(dpi, dpi))
    return buf.getvalue()


def preview_png(svg, scale=1.5):
    """整框（360×260）白底渲染，只用于自查拼图"""
    import fitz
    return fitz.open(stream=svg.encode(), filetype="svg")[0].get_pixmap(dpi=round(72 * scale)).tobytes("png")


# —— 网页卡片：结构式右上角三个方形图标按钮（自上而下：复制 SMILES / 复制图片 / 下载 SVG），悬停左侧提示 ——
def _ico(body):
    return ("<svg viewBox='0 0 16 16' width='15' height='15' fill='none' stroke='currentColor' stroke-width='1.4' "
            "stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'>" + body + "</svg>")
ICON_SMILES = _ico("<path d='M3.5 11.5V3a1 1 0 0 1 1-1H10'/><rect x='6' y='4.5' width='7.5' height='9.5' rx='1'/>"
                   "<path d='M8 7.5h3.5M8 9.5h3.5M8 11.5h2'/>")
ICON_IMAGE = _ico("<rect x='2' y='3' width='12' height='10' rx='1.5'/><circle cx='5.5' cy='6.5' r='1.1'/>"
                  "<path d='M2.5 12l3.5-3.5 2.5 2.5 2-2 3 3'/>")
ICON_DOWN = _ico("<path d='M8 2.5v8M4.8 7.5L8 10.7l3.2-3.2M3 13.5h10'/>")

CARD_CSS = (".mol{text-align:center;font-size:18px}.en{font-size:16px;color:#555;font-style:italic}"
            ".sv{position:relative;display:inline-block;line-height:0}"
            ".sv .ibtns{position:absolute;top:6px;right:6px;display:flex;flex-direction:column;gap:4px;z-index:2;line-height:0}"
            ".sv .ibtns .ib{position:relative;width:26px;height:26px;padding:0;display:flex;align-items:center;justify-content:center;"
            "border:1px solid #d5dce6;border-radius:6px;background:rgba(255,255,255,.92);color:#5a6b82;cursor:pointer;opacity:.45;"
            "transition:opacity .15s,background .15s,color .15s,border-color .15s;font-size:0}"
            ".sv:hover .ibtns .ib{opacity:1}.sv .ibtns .ib:hover{background:#eef4ff;border-color:#8fa8c8;color:#1f4f8f}"
            ".sv .ibtns .ib.ok{color:#2e8b57;border-color:#2e8b57;background:#effaf3;opacity:1}"
            ".sv .ibtns .ib.err{color:#c0392b;border-color:#c0392b;background:#fdf0ee;opacity:1}"
            ".sv .ibtns .ib::after{content:attr(data-tip);position:absolute;right:calc(100% + 7px);top:50%;transform:translateY(-50%);"
            "background:#2b3645;color:#fff;font-size:12px;line-height:1.3;padding:3px 8px;border-radius:4px;white-space:nowrap;"
            "opacity:0;pointer-events:none;transition:opacity .12s}.sv .ibtns .ib:hover::after{opacity:1}")
COPY_JS = "<script>\n" + open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "card.js"), encoding="utf-8").read() + "</script>"


def mol_card(svg, zh, en, smi, cid=None):
    """单个结构卡片：结构式 + 右上角图标按钮 + 中文名 + 英文通用名（页面需含 CARD_CSS 与 COPY_JS；board() 已自带）"""
    e = lambda t: html.escape(str(t), quote=True)
    return (f"<div class='mol'><div class='sv'>{svg}<div class='ibtns'>"
            f"<button type='button' class='ib smi' data-smiles='{e(smi)}' data-tip='复制 SMILES' aria-label='复制 SMILES'>{ICON_SMILES}</button>"
            f"<button type='button' class='ib cimg' data-name='{e(zh)}' data-tip='复制图片（600 dpi，透明背景）' aria-label='复制图片'>{ICON_IMAGE}</button>"
            f"<button type='button' class='ib dsvg' data-name='{e(zh)}' data-tip='下载 SVG 矢量图' aria-label='下载 SVG'>{ICON_DOWN}</button>"
            f"</div></div>\n<br>{e(zh)}<br><span class='en'>{e(en)}</span>"
            + (f"<br><span class='cid'>PubChem CID {e(cid)}</span>" if cid else "") + "</div>")


def board(title, cards, note=""):
    """完整的结构式图板 HTML（交付物）。cards: mol_card() 的列表；note: 页脚附加说明（如高亮含义）"""
    import datetime
    e = lambda t: html.escape(str(t), quote=True)
    foot = (f"结构式由 RDKit 依据 PubChem SMILES 生成（{datetime.date.today():%Y-%m-%d}，chem-depict）。"
            "结构式右上角三个按钮，自上而下：复制 SMILES；复制图片（PNG 600 dpi、透明背景、已裁白边 + SVG，粘贴进 Word 为矢量图）；"
            "下载 SVG 矢量图。导出图按 ACS Document 1996 印刷尺寸：键长 14.4 pt、线宽 0.6 pt、Arial 10 pt。" + (" " + e(note) if note else ""))
    return ("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{e(title)}</title><style>body{{font-family:'Microsoft YaHei',sans-serif;max-width:1180px;margin:auto;padding:20px;"
            "background:#fff;color:#1f2d3d}h1{font-size:24px}.grid{display:flex;flex-wrap:wrap;gap:20px}.cid{font-size:13px;color:#8796aa}"
            f".foot{{margin-top:28px;font-size:13px;color:#667}}{CARD_CSS}</style></head><body><h1>{e(title)}</h1>"
            f"<div class='grid'>{''.join(cards)}</div><p class='foot'>{foot}</p>{COPY_JS}</body></html>")
