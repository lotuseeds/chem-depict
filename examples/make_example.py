"""生成示例图板 examples/example_board.html（在仓库根目录运行：python examples/make_example.py）"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "plugins", "chem-depict", "skills", "chem-depict", "scripts"))
import chemstyle as cs

# (中文名, 英文通用名, PubChem CID, SMILES, 排版参数, 高亮 SMARTS 或 None)
MOLS = [
    ("吗啡", "Morphine", 5288826, "CN1CC[C@]23[C@@H]4[C@H]1CC5=C2C(=C(C=C5)O)O[C@H]3[C@H](C=C4)O",
     {"template": "morphinan_classic"}, "[OX2H]"),
    ("可待因", "Codeine", 5284371, "CN1CC[C@]23[C@@H]4[C@H]1CC5=C2C(=C(C=C5)OC)O[C@H]3[C@H](C=C4)O",
     {"template": "morphinan_classic"}, "c[OX2][CH3]"),
    ("海洛因", "Heroin (Diamorphine)", 5462328, "CC(=O)O[C@H]1C=C[C@H]2[C@H]3CC4=C5[C@]2([C@H]1OC5=C(C=C4)OC(=O)C)CCN3C",
     {"template": "morphinan_classic"}, "OC(=O)[CH3]"),
    ("环丙沙星", "Ciprofloxacin", 2764, "C1CC1N2C=C(C(=O)C3=CC(=C(C=C32)N4CCNCC4)F)C(=O)O", {}, ("C(=O)[OH]", "C1CNCCN1")),
    ("东莨菪碱", "Scopolamine (Hyoscine)", 3000322, "CN1[C@@H]2CC(C[C@H]1[C@H]3[C@@H]2O3)OC(=O)[C@H](CO)C4=CC=CC=C4", {}, None),
    ("奥美拉唑", "Omeprazole", 4594, "CC1=CN=C(C(=C1OC)C)CS(=O)C2=NC3=C(N2)C=C(C=C3)OC", {}, "n1ccccc1"),
]

cards = []
for zh, en, cid, smi, kw, hl in MOLS:
    m = cs.layout(smi, **kw)
    bad = [c for c in cs.close_contacts(m) if c[2] < 0.44]
    assert not bad, (zh, bad)
    pats = hl if isinstance(hl, tuple) else ((hl,) if hl else ())
    atoms = sorted({i for p in pats for i in cs.hits(m, p)})
    cards.append(cs.mol_card(cs.draw(m, atoms), zh, en, smi, cid))

out = os.path.join(HERE, "example_board.html")
open(out, "w", encoding="utf-8").write(cs.board(
    "chem-depict 示例图板", cards,
    note="示例高亮：吗啡羟基（孤立原子→圆点）、可待因甲氧基与海洛因乙酰氧基（开链→键色带）、环丙沙星羧基与哌嗪环、奥美拉唑吡啶环（整环→涂色）；东莨菪碱不高亮。"))
print("written", out)
