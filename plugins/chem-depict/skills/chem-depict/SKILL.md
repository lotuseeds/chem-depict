---
name: chem-depict
description: 药物化学结构式图板（medicinal-chemistry structure board）：由 SMILES 或药名（自动查 PubChem）生成统一画风的结构式 HTML 图板——RDKit 环系模板 / 经典教材朝向、ACS Document 1996 规格（导出键长 14.4 pt、线宽 0.6 pt、Arial 10 pt）、元素习惯色 + 灰绿 H、交叉键下方断开、只标关键氢；可按考点高亮（整环涂色、开链键色带）；每个结构右上角三个图标按钮：复制 SMILES / 复制图片（600 dpi 透明裁边，粘贴进 Word 为矢量）/ 下载 SVG。何时用：课件、测验、讲义、汇报材料要用结构式；用户说「画结构式」「用 SMILES 画图」「重画这个结构」「结构式太难看」「出个结构式图板」，或 draw / depict a chemical structure from SMILES。只出 HTML，不直接改 Word/PPT。
---

# chem-depict：药物化学结构式图板

核心代码在本 skill 目录的 `scripts/`：`chemstyle.py`（绘图、导出、卡片、图板）+ `card.js`（网页按钮交互）。**不要另写绘图代码**，一律调用该模块。

依赖：Python 3.9+，`rdkit`、`pymupdf`、`pillow`（`pip install rdkit pymupdf pillow`）。首次使用先 `python -c "import rdkit, fitz, PIL"` 检查，缺什么提示用户安装。

## 定位

- **交付物只有 HTML 结构式图板**：每个化合物一张卡片（结构式、中文名、英文通用名、PubChem CID，右上角三个图标按钮）。图板与所服务的材料放在同一文件夹，命名「结构式图板_主题.html」，日后要用直接打开复制。
- **不直接写 Word / PPT**。要放进 Word：在图板上点「复制图片」后粘贴——Word 收下的是 SVG 矢量，尺寸已是 ACS 印刷尺寸，**不要单独缩放**；确需缩放时同一文档的结构式统一比例。要文件则点「下载 SVG」后插入。

## 画风规格（固定）

| 项 | 规格 |
|---|---|
| 排版 | 默认 RDKit 环系模板（`useRingTemplates`）；吗啡烷类用内置 `morphinan_classic`（芳环在上、4,5-醚桥在左、6-OH 左下、N-CH₃ 在右）；**同组对比分子共用骨架坐标**（`align_to`） |
| ACS Document 1996 | 线宽、双键间距 18%、字号与键长成 ACS 比例；字体 **Arial**（找不到时用 RDKit 内置字体）；交叉断口两侧留白 1.6 pt。**导出**按键长 14.4 pt 定物理尺寸。网页显示键长 26 px（约 1.35 倍，便于投影） |
| 颜色 | O 红、N 蓝、S 暗黄、F 青绿、Cl 绿、Br 棕红、P 橙、I 紫；**H 灰绿**；高亮浅红 #FFD1D1（有意偏离 ACS 的黑白默认，便于教学） |
| 氢 | OH、NH 合写；**只标关键氢**＝①桥头 / 稠环立体中心的 H（程序自动判定）②教学上要指出的 H（`key_h` 指定，如巴比妥酸 C5-H） |
| 交叉键 | 允许；**压在下方的键在交叉处几何剪断**（透明背景也不露白）。上下：`over` 指定 > 非环键 > 含实楔形宽端原子的键 |
| 导出 | 「复制图片」：剪贴板同时写 PNG（600 dpi）与 SVG；「下载 SVG」：矢量。都为**透明背景、裁到内容边界、ACS 印刷尺寸**，文字已转路径 |
| 按钮 | 结构式右上角三个 26 px 方形图标按钮，垂直排列、无文字：文档＝复制 SMILES、图片＝复制图片、下载箭头＝下载 SVG；悬停显示提示，成功绿色对勾、失败红叉 |

## 高亮

- **默认不高亮**。高亮哪里是教学判断，程序不替人决定。
- 有考点时，用 **SMARTS + 一句中文说明**指定（如「酸性位点：`[NH]C(=O)`」「哌嗪环：`C1CNCCN1`」），或直接给原子序。**生成前先列一张高亮方案表请用户确认**（结构 / 高亮部位 / 对应考点）。
- 画法自动拆分：环上原子**全部**在高亮内 → **整环涂满**；开链部分 → **键色带**；孤立单个原子（如羟基 O、季铵 N⁺）→ 圆点。

## 流程

1. **取 SMILES**：从 PubChem 取带立体的 SMILES 与英文名（`https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/<英文名>/property/IsomericSMILES,MolecularFormula,Title/CSV`），用 RDKit 算分子式与 PubChem 核对。一个名称返回多个 CID 时取第一个并向用户说明，立体有疑问就问。英文名用 INN，常见别名括注。**未发表的化合物只用本地 RDKit，不发到在线服务。**
2. **排版**：`cs.layout(smi)`；吗啡烷类 `template="morphinan_classic"`；同组对比 `align_to=母体分子`。
3. **近接检查**：`cs.close_contacts(m)` 必须为空（环内 N-甲基短线 0.45 左右属正常）。不为空说明画面有原子重叠，先修排版——**不能只靠目测**。
4. **高亮方案**（如有）：列表请用户确认。
5. **出图板**：`svg = cs.draw(m, highlight=[...], key_h={...}, over=[...])` → `cs.mol_card(svg, 中文名, 英文名, smi, cid)` → `cs.board(标题, cards, note)` 写成 HTML。
6. **自查**：`cs.preview_png(svg)` 拼图看一遍；有浏览器自动化工具时，打开 HTML 截图并实点三个按钮。改 `card.js` 后先 `node --check`。
7. **交付**：给出图板路径，列出每个结构的 SMILES / CID / 英文名 / 高亮部位；从图中读出的数字或结构特征请用户核实。

## 疑难骨架

- **吗啡烷**（吗啡、可待因、海洛因、纳洛酮……）：`morphinan_classic`；乙胺桥从上方压过 C9–C10（自动剪断）。RDKit 默认与环模板画法会让 C16 与 C8 近乎重合，PubChem 2D 坐标也有近接，均不可用。
- **托品烷**（东莨菪碱、阿托品）：环模板即可。
- **托品烷季铵盐**（丁溴东莨菪碱等）：骨架、甲基、酯侧链 `align_to` 母体叔胺；第二个 N-取代基手工摆——首键近竖直向上压过顶部环键再折向左，甲基环内短线朝右下，对离子放右下远离 OH。现成坐标 `templates/butylscopolamine.mol`（`cs.from_molfile(path, smi)` 读入并核对 SMILES）。注意子结构对齐会把母体 N-CH₃ 错配到丁基首碳，须强制甲基对甲基。
- **双季铵长链二酯**（阿曲库铵等）：`templates/atracurium.mol`；左右镜像，连接链为水平锯齿，两 C=O 朝下，二甲氧苄基垂在两端下方。
- **一般手工微调**：`cs.coords(m)` 打印坐标（键长单位）→ `cs.place(m, {原子序: (x, y)})` → 再跑 `close_contacts`。

## 技术备忘

- Windows Git Bash 的 heredoc 里写 `\\n` 可能被转成真换行，导致 JS / Python 字符串断开且不报错——含反斜杠的代码写成文件再运行。
- 从 SVG 读键线宽时只认 `fill:none` 的 `bond-` 路径；高亮椭圆描边、高亮填充块的 stroke-width 会误导。

## 示例

```python
import sys; sys.path.insert(0, "<本 skill 目录>/scripts")
import chemstyle as cs
mor = cs.layout(MORPHINE_SMI, template="morphinan_classic")
her = cs.layout(HEROIN_SMI, template="morphinan_classic")              # 与吗啡同朝向
assert not cs.close_contacts(mor) and not cs.close_contacts(her)
cards = [cs.mol_card(cs.draw(mor, cs.hits(mor, "[OX2H]")), "吗啡", "Morphine", MORPHINE_SMI, 5288826),
         cs.mol_card(cs.draw(her, cs.hits(her, "OC(=O)[CH3]")), "海洛因", "Heroin (Diamorphine)", HEROIN_SMI, 5462328)]
open("结构式图板_阿片类.html", "w", encoding="utf-8").write(
    cs.board("阿片类结构式", cards, note="浅红色高亮：吗啡 3-OH / 6-OH 及海洛因对应的乙酰氧基。"))
```
