"""
question_bank.py - builds 1000+ questions per subject (Math, Science, English, Reasoning).

* Fact tables (animals, elements, idioms, ...) become questions in both directions.
* Number templates (Math, Reasoning, Physics/Chemistry sums) draw fresh values from a seeded
  random generator, so the bank is identical on every start (question ids stay stable).
Every question carries an explanation. Bands: a=6-8, b=9-11, c=12-14, d=15-17.
"""
import math, random
from collections import Counter
from fractions import Fraction

SUBS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
P = lambda s: [tuple(x.strip().split("=", 1)) for x in s.replace("\n", "").split(";") if "=" in x]
L = lambda s: [x.strip() for x in s.replace("\n", "").split(",") if x.strip()]
sym = lambda p: p + [(b, a) for a, b in p]
cap1 = lambda s: s[0].upper() + s[1:]
def frac(x): x = Fraction(x); return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"
def num(x): return str(int(x)) if float(x).is_integer() else f"{x:g}"


def mk(S, B, q, ans, wrongs, why, r):
    ws = [w for w in dict.fromkeys(wrongs) if w != ans]
    if len(ws) < 3:
        return None
    o = [ans] + ws[:3]
    r.shuffle(o)
    return dict(subject=S, band=B, q=q, opts=[str(x) for x in o], ans=o.index(ans), why=why)


def near(c, r):
    d = [1, -1, 2, -2, 3, -3, 5, -5, 10, -10]
    if abs(c) >= 30:
        d += [round(c * .1), -round(c * .1), round(c * .2)]
    w = [c + x for x in dict.fromkeys(d) if x and (c + x >= 0 or c < 0)]
    r.shuffle(w)
    return w


def pq(S, B, pairs, fwd, rev, why, r, extra=()):
    out = []
    for k, v in pairs:
        w = why(k, v) if callable(why) else why.format(k=k, v=v)
        fm = dict(k=k, v=v, vl=v.lower())
        if fwd:
            ws = [x for x in dict.fromkeys(b for a, b in pairs) if x != v]; r.shuffle(ws)
            out.append(mk(S, B, fwd.format(**fm), v, ws + list(extra), w, r))
        if rev:
            ws = [a for a, b in pairs if b != v]; r.shuffle(ws)
            out.append(mk(S, B, rev.format(**fm), k, ws, w, r))
    return [x for x in out if x]


# =========================================================== MATH generators
M = lambda b, q, a, w, why, r: mk("Math", b, q, a, w, why, r)
NAMES = L("Aarav,Diya,Kabir,Meera,Rohan,Anaya,Ishaan,Sara,Vihaan,Tara")
THINGS = L("marbles,stickers,apples,pencils,candies,balloons,coins,books")


def ma_add(r):
    a, b = r.randint(5, 60), r.randint(5, 60); c = a + b
    return M("a", f"What is {a} + {b}?", c, near(c, r), f"{a} + {b} = {c}. Add the tens, then the ones.", r)
def ma_sub(r):
    a = r.randint(20, 99); b = r.randint(3, a - 1); c = a - b
    return M("a", f"What is {a} − {b}?", c, near(c, r), f"{a} − {b} = {c}.", r)
def ma_mul(r):
    a, b = r.randint(2, 10), r.randint(2, 10); c = a * b
    return M("a", f"What is {a} × {b}?", c, [a * (b + 1), a * (b - 1)] + near(c, r), f"{a} groups of {b} make {c}.", r)
def ma_miss(r):
    a, b = r.randint(2, 40), r.randint(2, 40)
    return M("a", f"{a} + ? = {a + b}", b, near(b, r), f"{a + b} − {a} = {b}.", r)
def ma_dbl(r):
    n = r.randint(2, 50)
    if r.random() < .5:
        return M("a", f"What is double {n}?", 2 * n, near(2 * n, r), f"Double means × 2: {n} + {n} = {2 * n}.", r)
    return M("a", f"What is half of {2 * n}?", n, near(n, r), f"Half means ÷ 2: {2 * n} ÷ 2 = {n}.", r)
def ma_cmp(r):
    n = r.sample(range(10, 100), 4); big = r.random() < .5; a = max(n) if big else min(n)
    return M("a", f"Which number is the {'greatest' if big else 'smallest'}?  {', '.join(map(str, n))}", a, [x for x in n if x != a],
             f"Compare the tens first, then the ones. {a} is the {'greatest' if big else 'smallest'}.", r)
def ma_word(r):
    n, t = r.choice(NAMES), r.choice(THINGS); a = r.randint(10, 40); b = r.randint(3, 9)
    if r.random() < .5:
        return M("a", f"{n} has {a} {t} and gets {b} more. How many {t} now?", a + b, near(a + b, r), f"Getting more means adding: {a} + {b} = {a + b}.", r)
    return M("a", f"{n} has {a} {t} and gives away {b}. How many are left?", a - b, near(a - b, r), f"Giving away means taking away: {a} − {b} = {a - b}.", r)
def ma_place(r):
    n = r.randint(100, 999); p = r.randrange(3); d = int(str(n)[p]); ans = d * 10 ** (2 - p)
    if d == 0: return None
    return M("a", f"What is the value of the digit {d} in {n}?", ans, [d, d * 10, d * 100, d * 1000], f"The digit {d} is in the {['hundreds','tens','ones'][p]} place, so its value is {ans}.", r)
def ma_even(r):
    ev = r.random() < .5; a = r.randrange(10, 99) // 2 * 2 + (0 if ev else 1)
    o = [x for x in r.sample(range(10, 100), 8) if x % 2 != (a % 2)][:3]
    return M("a", f"Which of these is an {'even' if ev else 'odd'} number?", a, o, f"{a} ends in {a % 10}, so it is {'even' if ev else 'odd'}.", r)

def mb_frac(r):
    q = r.randint(2, 10); p = r.randint(1, q - 1); n = q * r.randint(2, 12); a = n // q * p
    return M("b", f"What is {p}/{q} of {n}?", a, near(a, r) + [n // q], f"{n} ÷ {q} = {n // q}; then × {p} = {a}.", r)
def mb_perim(r):
    l, w = r.randint(4, 30), r.randint(2, 20); a = 2 * (l + w)
    return M("b", f"A rectangle is {l} cm long and {w} cm wide. What is its perimeter?", f"{a} cm", [f"{l * w} cm", f"{l + w} cm", f"{a + 2} cm", f"{a - 2} cm"], f"Perimeter = 2 × (length + width) = 2 × ({l} + {w}) = {a} cm.", r)
def mb_area(r):
    l, w = r.randint(3, 25), r.randint(2, 18); a = l * w
    return M("b", f"What is the area of a rectangle {l} m long and {w} m wide?", f"{a} sq m", [f"{2 * (l + w)} sq m", f"{a + l} sq m", f"{a - w} sq m", f"{l + w} sq m"], f"Area = length × width = {l} × {w} = {a} square metres.", r)
def mb_mul(r):
    a, b = r.randint(11, 99), r.randint(3, 9); c = a * b
    return M("b", f"What is {a} × {b}?", c, near(c, r), f"{a} × {b} = {c}. (Multiply the tens and ones separately, then add.)", r)
def mb_div(r):
    b, c = r.randint(3, 12), r.randint(5, 40)
    return M("b", f"What is {b * c} ÷ {b}?", c, near(c, r), f"{b} × {c} = {b * c}, so {b * c} ÷ {b} = {c}.", r)
def mb_pct(r):
    p = r.choice([10, 20, 25, 50]); n = 20 * r.randint(1, 25); a = n * p // 100
    return M("b", f"What is {p}% of {n}?", a, near(a, r), f"{p}% means {p} out of 100: {n} × {p} ÷ 100 = {a}.", r)
def mb_avg(r):
    a = r.randint(5, 40); x, y = r.randint(1, 9), r.randint(1, 9); n = [a - x, a + x - y, a + y]
    return M("b", f"What is the average of {n[0]}, {n[1]} and {n[2]}?", a, near(a, r), f"Sum = {sum(n)}; ÷ 3 = {a}.", r)
def mb_unit(r):
    k = r.choice([("m", "cm", 100), ("km", "m", 1000), ("kg", "g", 1000), ("hours", "minutes", 60), ("litres", "ml", 1000)]); n = r.randint(2, 15)
    return M("b", f"Convert {n} {k[0]} into {k[1]}.", n * k[2], [n * k[2] * 10, n * k[2] // 10, n + k[2], n * k[2] + k[2]], f"1 {k[0][:-1] if k[0].endswith('s') and k[0]!='kg' else k[0]} = {k[2]} {k[1]}, so {n} × {k[2]} = {n * k[2]}.", r)
def mb_money(r):
    p, n = r.randint(3, 25), r.randint(3, 12); a = p * n
    return M("b", f"A pen costs ₹{p}. How much do {n} pens cost?", f"₹{a}", [f"₹{a + p}", f"₹{a - p}", f"₹{p + n}", f"₹{a + 10}"], f"{n} × ₹{p} = ₹{a}.", r)

def sg(n): return "+" if n >= 0 else "−"
def mc_lin(r):
    x, a, b = r.randint(-9, 12), r.randint(2, 9), r.randint(-15, 15); c = a * x + b
    return M("c", f"Solve: {a}x {sg(b)} {abs(b)} = {c}", f"x = {x}", [f"x = {x + 1}", f"x = {x - 1}", f"x = {-x}", f"x = {x + 2}"], f"Move {b:+d} across: {a}x = {c - b}. Divide by {a}: x = {x}.", r)
def mc_poly(r):
    n = r.choice([5, 6, 7, 8, 9, 10, 12])
    if r.random() < .5:
        a = (n - 2) * 180; return M("c", f"What is the sum of the interior angles of a polygon with {n} sides?", f"{a}°", [f"{a + 180}°", f"{a - 180}°", f"{n * 180}°", f"{a + 90}°"], f"Sum = (n − 2) × 180° = {n - 2} × 180° = {a}°.", r)
    n = r.choice([3, 4, 5, 6, 8, 9, 10, 12]); a = (n - 2) * 180 // n
    return M("c", f"What is each interior angle of a regular polygon with {n} sides?", f"{a}°", [f"{a + 10}°", f"{a - 10}°", f"{360 // n}°", f"{a + 20}°"], f"Total = (n − 2) × 180° = {(n - 2) * 180}°; divided by {n} equal angles gives {a}°.", r)
def mc_disc(r):
    p = 100 * r.randint(2, 20); d = r.choice([10, 20, 25, 30, 40, 50]); a = p * (100 - d) // 100
    return M("c", f"A shirt costs ₹{p}. After a {d}% discount, what is its price?", f"₹{a}", [f"₹{p - d}", f"₹{p * d // 100}", f"₹{a + p // 10}", f"₹{a - p // 10}"], f"Discount = {d}% of {p} = ₹{p * d // 100}. Price = {p} − {p * d // 100} = ₹{a}.", r)
def mc_sq(r):
    n = r.randint(3, 30)
    if r.random() < .5: return M("c", f"What is √{n * n}?", n, near(n, r), f"{n} × {n} = {n * n}, so √{n * n} = {n}.", r)
    return M("c", f"What is {n}²?", n * n, near(n * n, r), f"{n}² = {n} × {n} = {n * n}.", r)
def mc_si(r):
    p, rt, t = 1000 * r.randint(1, 10), r.choice([4, 5, 6, 8, 10, 12]), r.randint(1, 5); a = p * rt * t // 100
    return M("c", f"Find the simple interest on ₹{p} at {rt}% per year for {t} years.", f"₹{a}", [f"₹{a + p // 10}", f"₹{a * 2}", f"₹{a // 2}", f"₹{p + a}"], f"SI = P × R × T ÷ 100 = {p} × {rt} × {t} ÷ 100 = ₹{a}.", r)
def mc_ratio(r):
    a, b = r.randint(1, 5), r.randint(2, 7)
    if a == b: return None
    k = r.randint(2, 15); t = (a + b) * k * 10; big = max(a, b) * k * 10
    return M("c", f"Divide ₹{t} in the ratio {a}:{b}. What is the larger share?", f"₹{big}", [f"₹{t - big}", f"₹{big + 10 * k}", f"₹{t // 2}", f"₹{big - 10 * k}"], f"Total parts = {a + b}. One part = {t} ÷ {a + b} = ₹{t // (a + b)}. Larger share = {max(a, b)} × ₹{t // (a + b)} = ₹{big}.", r)
def mc_tri(r):
    b, h = 2 * r.randint(2, 15), r.randint(3, 20); a = b * h // 2
    return M("c", f"Find the area of a triangle with base {b} cm and height {h} cm.", f"{a} sq cm", [f"{b * h} sq cm", f"{a + b} sq cm", f"{a - h} sq cm", f"{b + h} sq cm"], f"Area = ½ × base × height = ½ × {b} × {h} = {a} sq cm.", r)
def mc_hcf(r):
    a, b = r.randint(4, 40), r.randint(4, 40)
    if a == b: return None
    g = math.gcd(a, b); l = a * b // g
    if r.random() < .5: return M("c", f"What is the HCF of {a} and {b}?", g, [x for x in near(g, r) if x > 0] + [l], f"The largest number that divides both {a} and {b} is {g}.", r)
    return M("c", f"What is the LCM of {a} and {b}?", l, [a * b if a * b != l else l + a, l + g, max(a, b), l * 2], f"LCM = (a × b) ÷ HCF = {a * b} ÷ {g} = {l}.", r)
def mc_pyth(r):
    a, b, c = r.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25)]); k = r.randint(1, 6)
    return M("c", f"The two shorter sides of a right triangle are {a * k} cm and {b * k} cm. What is the hypotenuse?", f"{c * k} cm", [f"{(a + b) * k} cm", f"{c * k + 1} cm", f"{c * k - 1} cm", f"{(a + b) * k - 2} cm"], f"c² = {a * k}² + {b * k}² = {(a * k) ** 2 + (b * k) ** 2}, so c = {c * k} cm.", r)
def mc_tri_ang(r):
    a, b = r.randint(20, 90), r.randint(20, 80); c = 180 - a - b
    return M("c", f"Two angles of a triangle are {a}° and {b}°. What is the third angle?", f"{c}°", [f"{c + 10}°", f"{c - 10}°", f"{360 - a - b}°", f"{c + 20}°"], f"Angles of a triangle add to 180°: 180 − {a} − {b} = {c}°.", r)

def pol(p, q):
    s, pr = p + q, p * q
    t = "x²" + (f" {sg(-s)} {abs(s)}x" if s else "") + (f" {sg(pr)} {abs(pr)}" if pr else "")
    return t + " = 0"
def pair(a, b): a, b = sorted((a, b)); return f"{a} and {b}"
def md_quad(r):
    p, q = r.randint(-9, 9), r.randint(-9, 9)
    if p == 0 or q == 0 or p == q: return None
    return M("d", f"Find the roots of {pol(p, q)}", pair(p, q), [pair(-p, -q), pair(p, -q), pair(-p, q), pair(p + 1, q)], f"Factorise: (x {sg(-p)} {abs(p)})(x {sg(-q)} {abs(q)}) = 0, so x = {p} or x = {q}.", r)
def md_log(r):
    b, k = r.choice([2, 3, 5, 10]), r.randint(2, 6)
    if r.random() < .5: return M("d", f"What is log base {b} of {b ** k}?", k, near(k, r), f"{b}^{k} = {b ** k}, so log_{b}({b ** k}) = {k}.", r)
    return M("d", f"If log base {b} of x = {k}, what is x?", b ** k, [b * k, k ** b, b ** k + b, b ** (k - 1)], f"x = {b}^{k} = {b ** k}.", r)
def md_ap(r):
    a, d, n = r.randint(1, 20), r.randint(1, 9), r.randint(5, 25)
    if r.random() < .5:
        s = n * (2 * a + (n - 1) * d) // 2
        return M("d", f"Find the sum of the first {n} terms of the AP {a}, {a + d}, {a + 2 * d}, …", s, near(s, r), f"Sₙ = n/2 × [2a + (n−1)d] = {n}/2 × [{2 * a} + {(n - 1) * d}] = {s}.", r)
    t = a + (n - 1) * d
    return M("d", f"Find the {n}th term of the AP {a}, {a + d}, {a + 2 * d}, …", t, near(t, r) + [a + n * d], f"aₙ = a + (n − 1)d = {a} + {n - 1} × {d} = {t}.", r)
def md_comb(r):
    n, k = r.randint(5, 14), r.randint(2, 4); c = math.comb(n, k)
    return M("d", f"In how many ways can {k} students be chosen from {n}?", c, [math.perm(n, k), c + n, c - 1, math.comb(n, k - 1)], f"ⁿCᵣ = {n}! ÷ ({k}! × {n - k}!) = {c}.", r)
def md_slope(r):
    x1, y1, m, dx = r.randint(-5, 5), r.randint(-5, 5), r.randint(-6, 6), r.randint(1, 5)
    if m == 0: return None
    return M("d", f"Find the slope of the line through ({x1}, {y1}) and ({x1 + dx}, {y1 + m * dx}).", m, [-m, m + 1, m - 1, m * dx], f"Slope = (y₂ − y₁) ÷ (x₂ − x₁) = {m * dx} ÷ {dx} = {m}.", r)
def md_dist(r):
    a, b, c = r.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17), (6, 8, 10)]); k = r.randint(1, 4); x, y = r.randint(-5, 5), r.randint(-5, 5)
    return M("d", f"Find the distance between ({x}, {y}) and ({x + a * k}, {y + b * k}).", c * k, [(a + b) * k, c * k + 1, c * k - 1, c * k + 2], f"d = √[({a * k})² + ({b * k})²] = √{(a * k) ** 2 + (b * k) ** 2} = {c * k}.", r)
def md_gp(r):
    a, q, n = r.randint(1, 5), r.randint(2, 4), r.randint(4, 7); t = a * q ** (n - 1)
    return M("d", f"Find the {n}th term of the GP {a}, {a * q}, {a * q * q}, …", t, [a * q ** n, t + a, t - a, a * q * (n - 1)], f"aₙ = a·rⁿ⁻¹ = {a} × {q}^{n - 1} = {t}.", r)
def md_dice(r):
    s = r.randint(2, 12); w = 6 - abs(s - 7)
    return M("d", f"Two fair dice are rolled. What is the probability that the sum is {s}?", frac(Fraction(w, 36)), [frac(Fraction(x, 36)) for x in range(1, 7) if x != w] + ["1/2"], f"{w} of the 36 equally likely outcomes give a sum of {s}, so P = {w}/36 = {frac(Fraction(w, 36))}.", r)
def md_ci(r):
    p = 100 * r.randint(2, 30); rt, n = r.choice([(10, 2), (20, 2), (10, 3)]); a = p * (100 + rt) ** n // 100 ** n
    return M("d", f"What is the compound interest amount on ₹{p} at {rt}% per year for {n} years?", f"₹{a}", [f"₹{p + p * rt * n // 100}", f"₹{a + p // 10}", f"₹{a - p // 10}", f"₹{p * 2}"], f"A = P(1 + R/100)ⁿ = {p} × (1.{rt:02d})^{n} = ₹{a}.", r)
def md_sim(r):
    x, y = r.randint(2, 20), r.randint(1, 19)
    if x == y: return None
    return M("d", f"If x + y = {x + y} and x − y = {x - y}, what is x?", x, [y, x + 1, x - 1, x + y], f"Add the equations: 2x = {2 * x}, so x = {x}.", r)
def md_diag(r):
    n = r.randint(5, 20); a = n * (n - 3) // 2
    return M("d", f"How many diagonals does a polygon with {n} sides have?", a, [n * (n - 1) // 2, a + n, a - n, n * (n - 3)], f"Diagonals = n(n − 3)/2 = {n} × {n - 3} ÷ 2 = {a}.", r)
def md_cyl(r):
    rr, h = r.choice([7, 14, 21]), r.randint(2, 20); v = 22 * rr * rr * h // 7
    return M("d", f"Find the volume of a cylinder with radius {rr} cm and height {h} cm (use π = 22/7).", f"{v} cm³", [f"{v * 2} cm³", f"{v // 2} cm³", f"{2 * 22 * rr * h // 7} cm³", f"{v + 100} cm³"], f"V = πr²h = 22/7 × {rr}² × {h} = {v} cm³.", r)
def md_med(r):
    n = r.sample(range(1, 60), 5); s = sorted(n); m = s[2]
    return M("d", f"Find the median of {', '.join(map(str, n))}.", m, [s[1], s[3], round(sum(n) / 5), s[0]], f"Sorted: {', '.join(map(str, s))}. The middle value is {m}.", r)
TRIG = P("sin 30°=1/2;cos 60°=1/2;sin 45°=1/√2;cos 45°=1/√2;tan 45°=1;sin 90°=1;cos 0°=1;tan 60°=√3;cos 30°=√3/2;sin 60°=√3/2;tan 30°=1/√3;sin 0°=0;cos 90°=0;tan 0°=0")


# ========================================================== REASONING gens
RQ = lambda b, q, a, w, why, r: mk("Reasoning", b, q, a, w, why, r)
CATS = {"fruits": L("apple,banana,mango,orange,grapes,papaya,guava,pear,plum,cherry"), "vegetables": L("carrot,potato,onion,spinach,tomato,cabbage,peas,beetroot,radish,brinjal"),
        "animals": L("dog,cat,cow,horse,lion,tiger,rabbit,goat,monkey,sheep"), "birds": L("crow,parrot,eagle,sparrow,owl,peacock,duck,pigeon,hen,swan"),
        "vehicles": L("car,bus,train,bicycle,truck,scooter,aeroplane,ship,tractor"), "colours": L("red,blue,green,yellow,pink,purple,brown,black,white,grey"),
        "body parts": L("hand,leg,eye,ear,nose,mouth,arm,foot,knee,finger"), "furniture": L("table,chair,bed,sofa,desk,shelf,stool,cupboard"),
        "stationery items": L("pen,pencil,eraser,ruler,sharpener,notebook,stapler,crayon"), "shapes": L("circle,square,triangle,rectangle,oval,pentagon,hexagon"),
        "clothes": L("shirt,skirt,trousers,sock,jacket,cap,shoes,scarf"), "musical instruments": L("drum,flute,guitar,piano,violin,sitar,tabla,trumpet")}
DAYS = L("Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday")
ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
PEOPLE = L("Aman,Bela,Charu,Dev,Esha,Farid,Gita,Hari,Isha,Jay,Kiran,Lata")
WORDS3 = L("CAT,DOG,SUN,BAD,FAN,HEN,JAM,KEY,LAB,MAP,NET,PEN,RAT,TEA,VAN,WEB,BEE,COW,EGG,ICE,BOX,CUP,ARM,BAG,DAD,FIG,GUM,HAT,INK,JAR,LID,MUD,NUT,OWL,PIG,RUG,SKY,TOY,YAK")
WORDS5 = WORDS3 + L("LAMP,BOOK,CHAIR,MANGO,PLANT,TIGER,BREAD,WATER,HOUSE,SMILE,CLOUD,RIVER")
RELS = [P("dog=bark;cat=meow;cow=moo;lion=roar;duck=quack;frog=croak;horse=neigh"), P("cow=calf;dog=puppy;cat=kitten;horse=foal;sheep=lamb;hen=chick;goat=kid"), P("bird=nest;bee=hive;lion=den;spider=web;horse=stable;cow=shed;fish=water")]
RELN = ["makes the sound", "has the baby", "lives in / at"]
PR = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
WORK = [(2, 2, 1), (3, 6, 2), (10, 15, 6), (12, 24, 8), (20, 30, 12), (6, 6, 3), (4, 12, 3), (15, 30, 10), (12, 12, 6), (9, 18, 6), (8, 8, 4), (5, 20, 4), (30, 60, 20), (10, 40, 8)]
SPD = [(40, 60, 48), (30, 60, 40), (60, 90, 72), (20, 30, 24), (50, 75, 60), (60, 120, 80), (30, 45, 36), (40, 120, 60), (10, 15, 12), (100, 150, 120)]
ARR = L("PLANE,APPLE,LEVEL,BANANA,MOON,TREE,BOOK,SCHOOL,MATH,SMILE,ERROR,PAPER,LETTER,TOOTH,GRADE,ROUND,CIRCLE,NUMBER,PENCIL,STUDY,GREEN,SEEDS,MAMMAL")

def ra_odd(r):
    x, y = r.sample(list(CATS), 2); t = r.sample(CATS[x], 3); o = r.choice(CATS[y]); opts = t + [o]
    r.shuffle(opts)
    return RQ("a", f"Which one is different?  {', '.join(opts)}", o, t, f"{t[0]}, {t[1]} and {t[2]} are all {x}. {cap1(o)} belongs to {y}.", r)
def ra_series(r):
    d = r.choice([1, 2, 3, 4, 5, 10]) * r.choice([1, -1]); s = r.randint(1, 30) + (25 * (-d // 1 if d < 0 else 0) // 5 if d < 0 else 0); t = [s + i * d for i in range(4)]
    if min(t + [t[-1] + d]) < 0: return None
    n = t[-1] + d
    return RQ("a", f"What comes next?  {', '.join(map(str, t))}, ?", n, near(n, r), f"Each number {'goes up' if d > 0 else 'goes down'} by {abs(d)}, so {t[-1]} {sg(d)} {abs(d)} = {n}.", r)
def ra_alpha(r):
    i = r.randint(1, 24)
    if r.random() < .5: a = ALPHA[i + 1]; q = f"Which letter comes just after {ALPHA[i]}?"
    else: a = ALPHA[i - 1]; q = f"Which letter comes just before {ALPHA[i]}?"
    return RQ("a", q, a, [ALPHA[(ALPHA.index(a) + k) % 26] for k in (-2, 2, 3, -3)], f"The alphabet goes …{ALPHA[i - 1]}, {ALPHA[i]}, {ALPHA[i + 1]}… so the answer is {a}.", r)
def ra_day(r):
    i = r.randrange(7); aft = r.random() < .5; a = DAYS[(i + (1 if aft else -1)) % 7]
    return RQ("a", f"Which day comes just {'after' if aft else 'before'} {DAYS[i]}?", a, [d for d in DAYS if d != a], f"The days go {DAYS[(i - 1) % 7]}, {DAYS[i]}, {DAYS[(i + 1) % 7]}.", r)
def rb_series(r):
    if r.random() < .5:
        d, s = r.randint(2, 15), r.randint(1, 40); t = [s + i * d for i in range(5)]; n = t[-1] + d; why = f"Add {d} each time: {t[-1]} + {d} = {n}."
    else:
        m, s = r.choice([2, 3, 4]), r.randint(1, 6); t = [s * m ** i for i in range(5)]; n = t[-1] * m; why = f"Multiply by {m} each time: {t[-1]} × {m} = {n}."
    return RQ("b", f"Find the next number:  {', '.join(map(str, t))}, ?", n, near(n, r), why, r)
def rb_alpha(r):
    st = r.randint(1, 4); s = r.randint(0, 25 - 4 * st); t = [ALPHA[s + i * st] for i in range(4)]; a = ALPHA[s + 4 * st]
    return RQ("b", f"Find the next letter:  {', '.join(t)}, ?", a, [ALPHA[(s + 4 * st + k) % 26] for k in (1, -1, 2, -2)], f"Each letter moves {st} step(s) forward in the alphabet, so after {t[-1]} comes {a}.", r)
def rb_code(r):
    w = r.choice(WORDS3); v = [ALPHA.index(c) + 1 for c in w]
    if r.random() < .5:
        a = "-".join(map(str, v)); ws = []
        for k in range(3):
            u = v[:]; u[r.randrange(len(u))] += r.choice([1, -1, 2]); ws.append("-".join(map(str, u)))
        return RQ("b", f"If A = 1, B = 2, C = 3 … what is the code for {w}?", a, ws, f"Letter positions: " + ", ".join(f"{c} = {x}" for c, x in zip(w, v)) + ".", r)
    s = sum(v)
    return RQ("b", f"If A = 1, B = 2 … Z = 26, what is the sum of the letter values in {w}?", s, near(s, r), "Add the positions: " + " + ".join(map(str, v)) + f" = {s}.", r)
def rb_dayn(r):
    i, n = r.randrange(7), r.randint(8, 45); a = DAYS[(i + n) % 7]
    return RQ("b", f"Today is {DAYS[i]}. What day will it be after {n} days?", a, [d for d in DAYS if d != a], f"{n} days = {n // 7} weeks and {n % 7} days. Moving {n % 7} day(s) ahead of {DAYS[i]} gives {a}.", r)
def rb_order(r):
    a, b, c = r.sample(PEOPLE, 3); st = [f"{a} is taller than {b}.", f"{b} is taller than {c}."]; r.shuffle(st)
    k = r.choice(["tallest", "shortest", "in the middle (by height)"]); ans = {"tallest": a, "shortest": c}.get(k, b)
    return RQ("b", f"{' '.join(st)} Who is {k}?", ans, [x for x in (a, b, c) if x != ans] + ["Cannot be determined"], f"Order the statements: {a} > {b} > {c}, so {ans} is {k}.", r)
def rb_analogy(r):
    i = r.randrange(3); pr = RELS[i]; (a, b), (c, d) = r.sample(pr, 2)
    return RQ("b", f"{cap1(a)} : {b} :: {cap1(c)} : ?", d, [y for x, y in pr if y not in (b, d)], f"A {a} {RELN[i]} '{b}'; in the same way a {c} {RELN[i]} '{d}'.", r)
def rc_series(r):
    k, d, s = r.randint(1, 5), r.randint(1, 4), r.randint(1, 15); t = [s]; df = k
    for _ in range(5): t.append(t[-1] + df); df += d
    return RQ("c", f"Find the next number:  {', '.join(map(str, t[:5]))}, ?", t[5], near(t[5], r), f"The differences ({', '.join(str(t[i + 1] - t[i]) for i in range(4))}) rise by {d} each time, so the next difference is {t[5] - t[4]}.", r)
def rc_pow(r):
    e, n, c = r.choice([2, 3]), r.randint(1, 8), r.choice([0, 1, 2, 3, 5]); t = [i ** e + c for i in range(n, n + 5)]; a = (n + 5) ** e + c
    return RQ("c", f"Find the next number:  {', '.join(map(str, t))}, ?", a, near(a, r), f"The terms are n{'²' if e == 2 else '³'}{' + ' + str(c) if c else ''} for n = {n}, {n + 1}, …; the next is n = {n + 5}: {a}.", r)
def rc_shift(r):
    w, s = r.choice(WORDS5), r.randint(1, 4); enc = lambda x, k: "".join(ALPHA[(ALPHA.index(c) + k) % 26] for c in x); a = enc(w, s)
    return RQ("c", f"In a code every letter is replaced by the letter {s} place(s) ahead in the alphabet (A→{ALPHA[s]}). What is the code for {w}?", a, [enc(w, s + 1), enc(w, s - 1), enc(w, -s), enc(w, s + 2)], f"Shift each letter forward by {s}: {w[0]} → {a[0]}, {w[1]} → {a[1]}, … giving {a}.", r)
def rc_clock(r):
    h, m = r.randint(1, 11), r.choice(range(0, 60, 5)); a = abs(30 * h - 5.5 * m); a = 360 - a if a > 180 else a
    ws = [num(abs(a + x)) + "°" for x in (15, -15, 30, 7.5, -7.5, 45)] + [num(360 - a if a else 90) + "°"]
    return RQ("c", f"What is the angle between the hands of a clock at {h}:{m:02d}?", num(a) + "°", ws, f"Angle = |30 × {h} − 5.5 × {m}| = {num(abs(30 * h - 5.5 * m))}°" + (f", and the smaller angle is 360° − that = {num(a)}°." if abs(30 * h - 5.5 * m) > 180 else "."), r)
def rc_cal(r):
    i, d = r.randrange(7), r.randint(6, 28); a = DAYS[(i + d - 5) % 7]
    return RQ("c", f"If the 5th of a month is a {DAYS[i]}, what day is the {d}th of that month?", a, [x for x in DAYS if x != a], f"From the 5th to the {d}th is {d - 5} days; {d - 5} mod 7 = {(d - 5) % 7}, so move {(d - 5) % 7} day(s) ahead of {DAYS[i]}.", r)
def rc_dir(r):
    a, b, c = r.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25)]); k = r.randint(1, 6); d1, d2 = r.choice([("north", "east"), ("south", "west"), ("east", "south"), ("west", "north")]); n = r.choice(NAMES)
    return RQ("c", f"{n} walks {a * k} m {d1} and then {b * k} m {d2}. How far is {n} from the starting point?", f"{c * k} m", [f"{(a + b) * k} m", f"{c * k + 5} m", f"{c * k - 5} m", f"{(b - a) * k} m"], f"The two walks are at right angles: √({a * k}² + {b * k}²) = {c * k} m.", r)
def rc_rank(r):
    n = r.choice(NAMES)
    if r.random() < .5:
        l, rr = r.randint(3, 20), r.randint(3, 20); a = l + rr - 1
        return RQ("c", f"In a row, {n} is {l}th from the left and {rr}th from the right. How many people are in the row?", a, near(a, r) + [l + rr], f"Total = {l} + {rr} − 1 = {a} ({n} is counted twice, so subtract 1).", r)
    N, x = r.randint(20, 60), r.randint(3, 19); a = N - x + 1
    return RQ("c", f"In a class of {N}, {n}'s rank is {x} from the top. What is the rank from the bottom?", a, near(a, r) + [N - x], f"Rank from bottom = {N} − {x} + 1 = {a}.", r)
def rc_nana(r):
    a, e = r.randint(2, 15), r.choice([2, 3]); b = r.randint(2, 15)
    if a == b: return None
    return RQ("c", f"{a} : {a ** e} :: {b} : ?", b ** e, [b * e, b ** e + b, b ** (3 if e == 2 else 2), b ** e - b], f"The second number is the {'square' if e == 2 else 'cube'} of the first, so {b}{'²' if e == 2 else '³'} = {b ** e}.", r)
def rd_alt(r):
    a, b, d1, d2 = r.randint(1, 15), r.randint(1, 30), r.randint(2, 6), r.randint(2, 9); t = [a, b, a + d1, b + d2, a + 2 * d1, b + 2 * d2]; n = a + 3 * d1
    return RQ("d", f"Find the next number:  {', '.join(map(str, t))}, ?", n, [b + 3 * d2, n + 1, n - 1, n + d1], f"Two series are mixed. Odd places: {t[0]}, {t[2]}, {t[4]} (+{d1}); even places: {t[1]}, {t[3]}, {t[5]} (+{d2}). The 7th term is {t[4]} + {d1} = {n}.", r)
def rd_fib(r):
    a, b = r.randint(1, 9), r.randint(1, 9); t = [a, b]
    for _ in range(4): t.append(t[-1] + t[-2])
    return RQ("d", f"Find the next number:  {', '.join(map(str, t[:5]))}, ?", t[5], near(t[5], r) + [t[4] * 2], f"Each term is the sum of the two before it: {t[3]} + {t[4]} = {t[5]}.", r)
def rd_prime(r):
    i = r.randint(0, 14); t = PR[i:i + 5]; n = PR[i + 5]
    return RQ("d", f"Find the next number:  {', '.join(map(str, t))}, ?", n, near(n, r), f"These are consecutive prime numbers; the next prime after {t[-1]} is {n}.", r)
def rd_prod(r):
    k, n = r.randint(1, 3), r.randint(1, 8); t = [i * (i + k) for i in range(n, n + 5)]; a = (n + 5) * (n + 5 + k)
    return RQ("d", f"Find the next number:  {', '.join(map(str, t))}, ?", a, near(a, r), f"The terms are n × (n + {k}) for n = {n}, {n + 1}, …; for n = {n + 5} we get {a}.", r)
def rd_work(r):
    x, y, t = r.choice(WORK); k = r.randint(1, 3); x, y, t = x * k, y * k, t * k
    return RQ("d", f"A can finish a job in {x} days and B in {y} days. Working together, how many days do they need?", f"{t} days", [f"{t + 1} days", f"{t + 2} days", f"{(x + y) // 2} days", f"{max(t - 1, 1)} days"], f"Per day they do 1/{x} + 1/{y} = 1/{t} of the job, so they need {t} days.", r)
def rd_arr(r):
    w = r.choice(ARR); n = len(w); a = math.factorial(n)
    for c in Counter(w).values(): a //= math.factorial(c)
    return RQ("d", f"How many different arrangements can be made using all the letters of the word {w}?", a, [math.factorial(n), math.factorial(n - 1), a * 2, a // 2 if a > 1 else 7, a + 10], f"{n}! divided by the factorial of each repeated letter's count gives {a}.", r)
def rd_prob(r):
    a, b = r.randint(2, 9), r.randint(2, 9); n = a + b; col = r.choice(["red", "green", "white", "yellow"]); oc = r.choice(["blue", "black", "pink"])
    if r.random() < .5:
        p = Fraction(a, n)
        return RQ("d", f"A bag has {a} {col} and {b} {oc} balls. One ball is picked at random. What is the probability it is {col}?", frac(p), [frac(Fraction(b, n)), frac(Fraction(a, b)), frac(Fraction(a + 1, n)), frac(Fraction(a - 1, n)), frac(Fraction(1, n))], f"P = favourable ÷ total = {a}/{n} = {frac(p)}.", r)
    p = Fraction(a * (a - 1), n * (n - 1))
    return RQ("d", f"A bag has {a} {col} and {b} {oc} balls. Two balls are drawn without replacement. What is the probability both are {col}?", frac(p), [frac(Fraction(a * a, n * n)), frac(Fraction(a, n)), frac(Fraction(a * (a + 1), n * (n + 1))), frac(Fraction(2 * a, n * (n - 1)))], f"P = {a}/{n} × {a - 1}/{n - 1} = {frac(p)}.", r)
def rd_speed(r):
    u, v, a = r.choice(SPD)
    if r.random() < .5: u, v = v, u
    return RQ("d", f"A car goes from A to B at {u} km/h and returns at {v} km/h. What is the average speed for the whole trip?", f"{a} km/h", [f"{(u + v) // 2} km/h", f"{a + 2} km/h", f"{a - 2} km/h", f"{u + v - a} km/h"], f"Average speed = 2uv ÷ (u + v) = 2 × {u} × {v} ÷ {u + v} = {a} km/h (not the simple mean).", r)
def rd_profit(r):
    c, p = 20 * r.randint(5, 100), r.choice(range(5, 55, 5)); gain = r.random() < .5; s = c * (100 + (p if gain else -p)) // 100
    return RQ("d", f"An article bought for ₹{c} is sold for ₹{s}. What is the {'profit' if gain else 'loss'} percent?", f"{p}%", [f"{p + 5}%", f"{max(p - 5, 1)}%", f"{p + 10}%", f"{p * 2}%"], f"{'Profit' if gain else 'Loss'} = ₹{abs(s - c)}; percent = {abs(s - c)} ÷ {c} × 100 = {p}%.", r)
def rd_count(r):
    k = r.randint(2, 19); a = 99 // k - 9 // k
    return RQ("d", f"How many two-digit numbers are divisible by {k}?", a, near(a, r), f"Multiples of {k} up to 99: {99 // k}; those below 10: {9 // k}. So {99 // k} − {9 // k} = {a}.", r)


# ============================================================ SCIENCE gens
SQ = lambda b, q, a, w, why, r: mk("Science", b, q, a, w, why, r)
def sc_speed(r):
    v, t = r.randint(10, 90), r.randint(2, 9); d = v * t; k = r.random()
    if k < .5: return SQ("c", f"A car travels {d} km in {t} hours at constant speed. What is its speed?", f"{v} km/h", [f"{v + 5} km/h", f"{v - 5} km/h", f"{d + t} km/h", f"{v * 2} km/h"], f"Speed = distance ÷ time = {d} ÷ {t} = {v} km/h.", r)
    return SQ("c", f"A cyclist moves at {v} km/h. How far does the cyclist go in {t} hours?", f"{d} km", [f"{d + v} km", f"{d - v} km", f"{v + t} km", f"{d * 2} km"], f"Distance = speed × time = {v} × {t} = {d} km.", r)
def sc_dens(r):
    p, V = r.randint(1, 12), r.randint(5, 50); m = p * V
    return SQ("c", f"A block has mass {m} g and volume {V} cm³. What is its density?", f"{p} g/cm³", [f"{p + 1} g/cm³", f"{p + 2} g/cm³", f"{max(p - 1, 0.5):g} g/cm³", f"{p * 2} g/cm³"], f"Density = mass ÷ volume = {m} ÷ {V} = {p} g/cm³.", r)
def sc_ohm(r):
    i, R = r.randint(1, 10), r.randint(2, 50); v = i * R
    if r.random() < .5: return SQ("c", f"A current of {i} A flows through a {R} Ω resistor. What is the voltage across it?", f"{v} V", [f"{v + R} V", f"{v - i} V", f"{R + i} V", f"{v * 2} V"], f"V = I × R = {i} × {R} = {v} V (Ohm's law).", r)
    return SQ("c", f"A {R} Ω resistor has {v} V across it. What current flows?", f"{i} A", [f"{i + 1} A", f"{i + 2} A", f"{v - R} A", f"{max(i - 1, 0.5):g} A"], f"I = V ÷ R = {v} ÷ {R} = {i} A.", r)
def sc_force(r):
    m, a = r.randint(2, 50), r.randint(1, 10); f = m * a
    return SQ("c", f"What force is needed to give a {m} kg object an acceleration of {a} m/s²?", f"{f} N", [f"{f + m} N", f"{f - a} N", f"{m + a} N", f"{f * 2} N"], f"F = m × a = {m} × {a} = {f} N (Newton's second law).", r)
def sc_work(r):
    f, d = 5 * r.randint(1, 20), r.randint(2, 20); w = f * d; t = r.randint(2, 10)
    if r.random() < .5: return SQ("c", f"A force of {f} N moves an object {d} m in its own direction. How much work is done?", f"{w} J", [f"{w + f} J", f"{w - d} J", f"{f + d} J", f"{w * 2} J"], f"Work = force × distance = {f} × {d} = {w} J.", r)
    return SQ("c", f"A machine does {w * t} J of work in {t} s. What is its power?", f"{w} W", [f"{w + t} W", f"{w * t * t} W", f"{w - t} W", f"{w * 2} W"], f"Power = work ÷ time = {w * t} ÷ {t} = {w} W.", r)
def sc_press(r):
    A, p = r.randint(2, 20), 50 * r.randint(1, 10); F = A * p
    return SQ("c", f"A force of {F} N acts on an area of {A} m². What is the pressure?", f"{p} Pa", [f"{p + A} Pa", f"{p * 2} Pa", f"{F - A} Pa", f"{p // 2} Pa"], f"Pressure = force ÷ area = {F} ÷ {A} = {p} Pa.", r)
def sd_ke(r):
    m, v = 2 * r.randint(1, 10), r.randint(2, 20); k = m * v * v // 2
    return SQ("d", f"What is the kinetic energy of a {m} kg object moving at {v} m/s?", f"{k} J", [f"{m * v} J", f"{k * 2} J", f"{m * v * v} J", f"{k + m} J"], f"KE = ½mv² = ½ × {m} × {v}² = {k} J.", r)
def sd_mom(r):
    m, v = r.randint(2, 40), r.randint(2, 30)
    return SQ("d", f"What is the momentum of a {m} kg object moving at {v} m/s?", f"{m * v} kg m/s", [f"{m + v} kg m/s", f"{m * v * v // 2} kg m/s", f"{m * v + m} kg m/s", f"{m * v * 2} kg m/s"], f"Momentum = mass × velocity = {m} × {v} = {m * v} kg m/s.", r)
def sd_pe(r):
    m, h = r.randint(1, 20), r.randint(1, 50)
    return SQ("d", f"What is the potential energy of a {m} kg object raised {h} m? (g = 10 m/s²)", f"{m * h * 10} J", [f"{m * h} J", f"{m * h * 100} J", f"{m * h * 10 + m} J", f"{(m + h) * 10} J"], f"PE = mgh = {m} × 10 × {h} = {m * h * 10} J.", r)
def sd_res(r):
    if r.random() < .5:
        a, b, c = r.randint(2, 30), r.randint(2, 30), r.randint(2, 30); s = a + b + c
        return SQ("d", f"Three resistors of {a} Ω, {b} Ω and {c} Ω are in series. What is the total resistance?", f"{s} Ω", [f"{s + 5} Ω", f"{s - 3} Ω", f"{a * b * c} Ω", f"{s * 2} Ω"], f"In series, resistances add: {a} + {b} + {c} = {s} Ω.", r)
    x, y, t = r.choice([(2, 2, 1), (3, 6, 2), (4, 12, 3), (5, 20, 4), (6, 12, 4), (10, 15, 6), (20, 30, 12), (12, 12, 6)]); k = r.randint(1, 4)
    return SQ("d", f"Two resistors of {x * k} Ω and {y * k} Ω are connected in parallel. What is the combined resistance?", f"{t * k} Ω", [f"{(x + y) * k} Ω", f"{t * k + 1} Ω", f"{max(t * k - 1, 1)} Ω", f"{(x + y) * k // 2} Ω"], f"1/R = 1/{x * k} + 1/{y * k} = 1/{t * k}, so R = {t * k} Ω.", r)
def sd_wave(r):
    f, l = r.randint(2, 50), r.randint(1, 20)
    return SQ("d", f"A wave has frequency {f} Hz and wavelength {l} m. What is its speed?", f"{f * l} m/s", [f"{f + l} m/s", f"{f * l + f} m/s", f"{f * l - l} m/s", f"{f * l * 2} m/s"], f"v = f × λ = {f} × {l} = {f * l} m/s.", r)
def sd_ph(r):
    n = r.randint(1, 13)
    if r.random() < .5: return SQ("d", f"A solution has hydrogen-ion concentration 10⁻{str(n).translate(SUBS)} mol/L. What is its pH?", n, near(n, r) if n > 3 else [n + 1, n + 2, n + 3, n + 4], f"pH = −log[H⁺] = −log(10⁻{n}) = {n}. " + ("It is acidic." if n < 7 else "It is neutral." if n == 7 else "It is basic."), r)
    return SQ("d", f"A solution has pH {n}. What is [H⁺] in mol/L?", f"10⁻{str(n).translate(SUBS)}", [f"10⁻{str(x).translate(SUBS)}" for x in (n + 1, n - 1, n + 2, n + 3) if x > 0] + [f"10{str(n).translate(SUBS)}"], f"[H⁺] = 10^(−pH) = 10⁻{n} mol/L.", r)
MOLAR = [("H₂O", 18), ("CO₂", 44), ("O₂", 32), ("CaCO₃", 100), ("NH₃", 17), ("CH₄", 16), ("N₂", 28), ("H₂SO₄", 98), ("NaOH", 40), ("MgO", 40), ("SO₂", 64)]
def sd_mole(r):
    f, M_ = r.choice(MOLAR); n = r.randint(1, 10)
    if r.random() < .5: return SQ("d", f"How many moles are there in {n * M_} g of {f}? (molar mass = {M_} g/mol)", f"{n} mol", [f"{n + 1} mol", f"{n * 2} mol", f"{max(n - 1, 0.5):g} mol", f"{n + 2} mol"], f"moles = mass ÷ molar mass = {n * M_} ÷ {M_} = {n}.", r)
    return SQ("d", f"What is the mass of {n} mol of {f}? (molar mass = {M_} g/mol)", f"{n * M_} g", [f"{n * M_ + M_} g", f"{n * M_ - M_ // 2} g", f"{M_ + n} g", f"{n * M_ * 2} g"], f"mass = moles × molar mass = {n} × {M_} = {n * M_} g.", r)
def sd_heat(r):
    m, t = r.randint(1, 5), r.randint(1, 20); q = m * 4200 * t
    return SQ("d", f"How much heat is needed to warm {m} kg of water by {t} °C? (c = 4200 J/kg°C)", f"{q} J", [f"{q // 2} J", f"{q * 2} J", f"{m * 4200 + t} J", f"{q + 4200} J"], f"Q = m × c × ΔT = {m} × 4200 × {t} = {q} J.", r)
def sd_per(r):
    f = r.choice([2, 4, 5, 10, 20, 25, 50, 100, 200]); T = 1 / f
    return SQ("d", f"A wave has frequency {f} Hz. What is its time period?", f"{T:g} s", [f"{f:g} s", f"{T * 10:g} s", f"{T / 2:g} s", f"{T * 2:g} s"], f"T = 1 ÷ f = 1 ÷ {f} = {T:g} s.", r)
def sd_half(r):
    k, rem, t = r.randint(1, 4), 5 * r.randint(1, 12), r.randint(2, 12); N = rem * 2 ** k
    return SQ("d", f"A radioactive sample of {N} g has a half-life of {t} days. How much is left after {k * t} days?", f"{rem} g", [f"{rem * 2} g", f"{rem // 2 if rem % 2 == 0 else rem + 5} g", f"{N // 2} g", f"{rem + 5} g"], f"{k * t} days = {k} half-lives, so the mass is halved {k} time(s): {N} ÷ {2 ** k} = {rem} g.", r)
ATOM = [("Na", 11, 23), ("C", 6, 12), ("O", 8, 16), ("Mg", 12, 24), ("Al", 13, 27), ("Ca", 20, 40), ("K", 19, 39), ("Cl", 17, 35), ("Fe", 26, 56), ("Cu", 29, 64), ("Li", 3, 7), ("S", 16, 32)]
def sd_atom(r):
    s, z, a = r.choice(ATOM)
    if r.random() < .5: return SQ("d", f"An atom of {s} has atomic number {z} and mass number {a}. How many neutrons does it have?", a - z, [z, a, a - z + 1, a - z - 1, a + z], f"Neutrons = mass number − atomic number = {a} − {z} = {a - z}.", r)
    return SQ("d", f"An atom of {s} has {z} protons and {a - z} neutrons. What is its mass number?", a, [z, a - z, a + 1, a - 1, a + z], f"Mass number = protons + neutrons = {z} + {a - z} = {a}.", r)


# ====================================================== SCIENCE / ENGLISH facts
CD = dict(Mammal="mammals have hair or fur, are warm-blooded and feed milk to their babies", Bird="birds have feathers and wings and lay eggs", Fish="fish live in water and breathe with gills",
          Reptile="reptiles have dry, scaly skin and are cold-blooded", Amphibian="amphibians spend part of their life in water and part on land", Insect="insects have six legs and three body parts",
          Herbivore="herbivores eat only plants", Carnivore="carnivores eat only meat", Omnivore="omnivores eat both plants and animals",
          Personification="it gives human qualities to something that is not human", Simile="it compares two things using 'like' or 'as'", Metaphor="it says one thing IS another without using 'like' or 'as'",
          Hyperbole="it is a deliberate exaggeration", Alliteration="it repeats the same starting sound", Onomatopoeia="the words imitate real sounds", Oxymoron="it joins two opposite ideas")
a_an = lambda w: "an" if w[0].lower() in "aeiou" else "a"


def sci_a(r):
    S, B = "Science", "a"; o = []
    o += pq(S, B, P("dog=Mammal;cat=Mammal;cow=Mammal;elephant=Mammal;lion=Mammal;whale=Mammal;bat=Mammal;horse=Mammal;monkey=Mammal;tiger=Mammal;rabbit=Mammal;dolphin=Mammal;kangaroo=Mammal;goat=Mammal;parrot=Bird;eagle=Bird;sparrow=Bird;penguin=Bird;owl=Bird;peacock=Bird;crow=Bird;ostrich=Bird;duck=Bird;shark=Fish;goldfish=Fish;salmon=Fish;tuna=Fish;seahorse=Fish;snake=Reptile;crocodile=Reptile;lizard=Reptile;turtle=Reptile;frog=Amphibian;toad=Amphibian;salamander=Amphibian;newt=Amphibian;butterfly=Insect;ant=Insect;bee=Insect;mosquito=Insect;grasshopper=Insect;ladybird=Insect"),
            "Which group of animals does a {k} belong to?", "Which of these animals is a {vl}?", lambda k, v: f"A {k} is a {v.lower()}: {CD[v]}.", r)
    o += pq(S, B, P("cow=Herbivore;goat=Herbivore;horse=Herbivore;rabbit=Herbivore;deer=Herbivore;elephant=Herbivore;giraffe=Herbivore;zebra=Herbivore;sheep=Herbivore;buffalo=Herbivore;lion=Carnivore;tiger=Carnivore;shark=Carnivore;eagle=Carnivore;crocodile=Carnivore;snake=Carnivore;wolf=Carnivore;owl=Carnivore;cheetah=Carnivore;bear=Omnivore;crow=Omnivore;pig=Omnivore;monkey=Omnivore;hen=Omnivore;rat=Omnivore"),
            "What type of eater is a {k}?", "Which of these animals is a {vl}?", lambda k, v: f"A {k} is a {v.lower()} — {CD[v]}.", r)
    o += pq(S, B, P("cow=calf;dog=puppy;cat=kitten;horse=foal;sheep=lamb;goat=kid;hen=chick;duck=duckling;frog=tadpole;kangaroo=joey;swan=cygnet;deer=fawn;pig=piglet;bear=cub;lion=cub;elephant=calf"),
            "What is a baby {k} called?", "Whose baby is called a {v}?", "A baby {k} is called a {v}.", r)
    o += pq(S, B, P("dog=bark;cat=meow;cow=moo;lion=roar;horse=neigh;sheep=bleat;duck=quack;frog=croak;snake=hiss;bee=buzz;elephant=trumpet;crow=caw;owl=hoot;donkey=bray;pig=grunt;hen=cluck"),
            "Which sound does a {k} make?", "Which animal makes the sound '{v}'?", "A {k} goes '{v}'.", r)
    o += pq(S, B, P("camel=desert;polar bear=Arctic;penguin=Antarctica;whale=ocean;frog=pond;bat=cave;bee=hive;spider=web;ant=anthill;yak=mountains;crocodile=river;rabbit=burrow;monkey=forest;lion=grassland;bird=nest"),
            "Where does a {k} live or stay?", "Which animal's home is the {v}?", "A {k} lives in or on: {v}.", r)
    o += pq(S, B, P("eyes=see;ears=hear;nose=smell;tongue=taste;skin=touch"), "We use our {k} to:", "Which body part helps us to {v}?", "We {v} with our {k}.", r)
    o += pq(S, B, P("roots=absorb water from the soil;stem=carry water to the leaves;leaves=make food using sunlight;flower=make seeds;fruit=protect the seeds"),
            "What is the main job of a plant's {k}?", "Which part of a plant helps to {v}?", "Job of the {k}: {v}.", r)
    o += pq(S, B, P("heart=pump blood;lungs=breathe in air;brain=control the body;stomach=digest food;bones=support the body;teeth=chew food;skin=cover and protect the body"),
            "What is the job of the {k}?", "Which body part helps us to {v}?", "The {k} helps us to {v}.", r)
    return o


def sci_b(r):
    S, B = "Science", "b"; o = []
    pl = L("Mercury,Venus,Earth,Mars,Jupiter,Saturn,Uranus,Neptune")
    o += pq(S, B, [(str(i + 1), p) for i, p in enumerate(pl)], "Counting outward from the Sun, which planet is number {k}?", None, "{v} is planet number {k} from the Sun.", r)
    o += pq(S, B, P("Mars=the Red Planet;Jupiter=the largest planet;Mercury=the planet closest to the Sun;Venus=the hottest planet;Saturn=the planet famous for its bright rings;Neptune=the farthest planet from the Sun;Earth=the only planet known to have life;Uranus=the planet that spins on its side"),
            "What is {k} known for?", "Which planet is {v}?", "{k} is {v}.", r)
    o += pq(S, B, P("kidneys=filter waste from the blood;liver=make bile and clean the blood;small intestine=absorb digested food;large intestine=absorb water from waste;pancreas=make insulin and digestive juices;spinal cord=carry messages between brain and body;muscles=help the body move;windpipe=carry air to the lungs;food pipe=carry food to the stomach;veins=carry blood back to the heart;arteries=carry blood away from the heart"),
            "What is the main function of the {k}?", "Which body part's job is to {v}?", "Function of the {k}: {v}.", r)
    o += pq(S, B, P("Hydrogen=H;Helium=He;Carbon=C;Nitrogen=N;Oxygen=O;Sodium=Na;Calcium=Ca;Iron=Fe;Gold=Au;Silver=Ag;Copper=Cu;Chlorine=Cl"), "What is the chemical symbol of {k}?", "Which element has the symbol {v}?", "{k} has the symbol {v}.", r)
    o += pq(S, B, P("Vitamin A=night blindness;Vitamin B1=beriberi;Vitamin C=scurvy;Vitamin D=rickets;Iron=anaemia;Iodine=goitre"), "A lack of {k} can cause:", "Which deficiency causes {v}?", "Lack of {k} causes {v}.", r)
    o += pq(S, B, P("force=newton (N);energy=joule (J);power=watt (W);pressure=pascal (Pa);frequency=hertz (Hz);electric current=ampere (A);resistance=ohm (Ω);electric charge=coulomb (C);voltage=volt (V);temperature=kelvin (K);mass=kilogram (kg);time=second (s);length=metre (m)"),
            "What is the SI unit of {k}?", "Which quantity is measured in the {v}?", "The SI unit of {k} is the {v}.", r)
    o += pq(S, B, P("thermometer=temperature;barometer=air pressure;ammeter=electric current;seismograph=earthquakes;microscope=very small things;telescope=distant stars and planets;speedometer=speed of a vehicle;stethoscope=heartbeat;hygrometer=humidity;anemometer=wind speed;voltmeter=voltage;lactometer=purity of milk"),
            "A {k} is used to measure:", "Which instrument measures {v}?", "A {k} measures {v}.", r)
    o += pq(S, B, P("copper=Conductor;iron=Conductor;aluminium=Conductor;silver=Conductor;graphite=Conductor;salt water=Conductor;rubber=Insulator;plastic=Insulator;wood=Insulator;glass=Insulator;dry cloth=Insulator;ceramic=Insulator;paper=Insulator;wool=Insulator"),
            "Is {k} a conductor or an insulator of electricity?", "Which of these is an electrical {vl}?", lambda k, v: f"{cap1(k)} is an electrical {v.lower()}: " + ("electric current flows through it easily." if v == "Conductor" else "it does not let electric current pass."), r, ["Both", "Neither"])
    o += pq(S, B, P("stone=Solid;iron=Solid;wood=Solid;ice=Solid;sugar=Solid;milk=Liquid;oil=Liquid;juice=Liquid;mercury=Liquid;water=Liquid;oxygen=Gas;steam=Gas;helium=Gas;hydrogen=Gas;carbon dioxide=Gas"),
            "What state of matter is {k}?", "Which of these is a {vl}?", "{cap}", r, ["Plasma"]) if False else []
    for k, v in P("stone=Solid;iron=Solid;wood=Solid;ice=Solid;sugar=Solid;milk=Liquid;oil=Liquid;juice=Liquid;mercury=Liquid;water=Liquid;oxygen=Gas;steam=Gas;helium=Gas;hydrogen=Gas;carbon dioxide=Gas"):
        ws = [x for x in ("Solid", "Liquid", "Gas") if x != v] + ["Plasma"]
        o.append(mk(S, B, f"What state of matter is {k}?", v, ws, f"{cap1(k)} is a {v.lower()}: " + {"Solid": "it has a fixed shape and volume.", "Liquid": "it flows and takes the shape of its container.", "Gas": "it spreads out to fill any container."}[v], r))
    o += pq(S, B, P("rice=Carbohydrates;bread=Carbohydrates;potato=Carbohydrates;egg=Proteins;fish=Proteins;dal=Proteins;chicken=Proteins;butter=Fats;ghee=Fats;groundnut oil=Fats;orange=Vitamin C;lemon=Vitamin C;guava=Vitamin C;carrot=Vitamin A;spinach=Iron"),
            "{k} is a rich source of:", "Which food is a rich source of {v}?", "{k} is rich in {v}.", r)
    return o


def sci_c(r):
    S, B = "Science", "c"; o = []
    o += pq(S, B, P("Lithium=Li;Beryllium=Be;Boron=B;Fluorine=F;Neon=Ne;Magnesium=Mg;Aluminium=Al;Silicon=Si;Phosphorus=P;Sulfur=S;Argon=Ar;Potassium=K;Lead=Pb;Mercury=Hg;Tin=Sn;Zinc=Zn"), "What is the chemical symbol of {k}?", "Which element has the symbol {v}?", "{k} has the symbol {v}.", r)
    o += pq(S, B, P("Hydrogen=1;Helium=2;Lithium=3;Beryllium=4;Boron=5;Carbon=6;Nitrogen=7;Oxygen=8;Fluorine=9;Neon=10;Sodium=11;Magnesium=12;Aluminium=13;Silicon=14;Phosphorus=15;Sulfur=16;Chlorine=17;Argon=18;Potassium=19;Calcium=20"),
            "What is the atomic number of {k}?", "Which element has atomic number {v}?", "{k} has atomic number {v}, i.e. {v} protons in its nucleus.", r)
    o += pq(S, B, P("nucleus=control all activities of the cell;mitochondria=release energy from food;chloroplast=carry out photosynthesis;ribosome=make proteins;cell wall=give shape and support to plant cells;vacuole=store water and nutrients;cell membrane=control what enters and leaves the cell;Golgi body=package and send out substances;lysosome=digest waste and germs"),
            "What is the job of the {k}?", "Which cell part's job is to {v}?", "The {k}'s job is to {v}.", r)
    o += pq(S, B, [(k.translate(SUBS), v) for k, v in P("NaCl=common salt;H2O=water;CO2=carbon dioxide;NaHCO3=baking soda;CaCO3=limestone or chalk;HCl=hydrochloric acid;H2SO4=sulfuric acid;NH3=ammonia;CH4=methane;NaOH=caustic soda")],
            "What is the common name of {k}?", "Which formula represents {v}?", "{k} is {v}.", r)
    o += pq(S, B, P("Isaac Newton=the law of gravity and the laws of motion;Albert Einstein=the theory of relativity;Charles Darwin=the theory of evolution;Marie Curie=radioactivity;Gregor Mendel=the laws of heredity;Louis Pasteur=pasteurisation;Michael Faraday=electromagnetic induction;Alexander Fleming=penicillin;Ernest Rutherford=the atomic nucleus;Edwin Hubble=the expanding universe;Archimedes=the principle of buoyancy;Georg Ohm=Ohm's law;Alexander Graham Bell=the telephone"),
            "{k} is famous for:", "Who is famous for {v}?", "{k} is famous for {v}.", r)
    for k, v in P("lemon juice=Acid;vinegar=Acid;orange juice=Acid;tomato juice=Acid;curd=Acid;milk of magnesia=Base;baking soda=Base;soap solution=Base;ammonia solution=Base;lime water=Base;toothpaste=Base;pure water=Neutral;salt solution=Neutral;sugar solution=Neutral"):
        ws = [x for x in ("Acid", "Base", "Neutral") if x != v] + ["Both an acid and a base"]
        o.append(mk(S, B, f"Is {k} an acid, a base or neutral?", v, ws, f"{cap1(k)} is {a_an(v)} {v.lower()}. " + {"Acid": "Acids taste sour and turn blue litmus red.", "Base": "Bases feel soapy and turn red litmus blue.", "Neutral": "Neutral substances do not change litmus."}[v], r))
    return o


def sci_d(r):
    S, B = "Science", "d"; o = []
    o += pq(S, B, P("insulin=Pancreas;thyroxine=Thyroid gland;adrenaline=Adrenal gland;growth hormone=Pituitary gland;testosterone=Testes;melatonin=Pineal gland;oestrogen=Ovaries"), "Which gland or organ produces {k}?", "Which hormone is produced by the {vl}?", "{k} is produced by the {vl}.", r)
    o += pq(S, B, [(k, v.translate(SUBS)) for k, v in P("methane=CH4;ethane=C2H6;propane=C3H8;butane=C4H10;ethene=C2H4;ethyne=C2H2")], "What is the molecular formula of {k}?", "Which compound has the formula {v}?", "{k} has the formula {v}.", r)
    for k, v in P("rusting of iron=Chemical change;melting of ice=Physical change;burning of paper=Chemical change;dissolving sugar in water=Physical change;cooking an egg=Chemical change;boiling water=Physical change;curdling of milk=Chemical change;tearing paper=Physical change;ripening of fruit=Chemical change;evaporation of water=Physical change;digestion of food=Chemical change;breaking a glass=Physical change"):
        ws = [x for x in ("Chemical change", "Physical change") if x != v] + ["Nuclear change", "No change at all"]
        o.append(mk(S, B, f"Is {k} a chemical or a physical change?", v, ws, f"{cap1(k)} is a {v.lower()}: " + ("a new substance is formed." if v[0] == "C" else "only the form or state changes; no new substance forms."), r))
    o += pq(S, B, P("Sodium=Alkali metal;Potassium=Alkali metal;Lithium=Alkali metal;Calcium=Alkaline earth metal;Magnesium=Alkaline earth metal;Fluorine=Halogen;Chlorine=Halogen;Bromine=Halogen;Helium=Noble gas;Neon=Noble gas;Argon=Noble gas"),
            "To which group of the periodic table does {k} belong?", "Which of these elements is classified as: {v}?", "{k} belongs to the group of {v}s.", r)
    o += pq(S, B, P("Adenine=Thymine;Guanine=Cytosine;Thymine=Adenine;Cytosine=Guanine"), "In DNA, {k} pairs with:", None, "In DNA, A pairs with T and G pairs with C, so {k} pairs with {v}.", r)
    return o


# ================================================================ ENGLISH
EQ = lambda b, q, a, w, why, r: mk("English", b, q, a, w, why, r)
IRR = [tuple(x.split("/")) for x in L("go/went/gone,eat/ate/eaten,see/saw/seen,take/took/taken,give/gave/given,write/wrote/written,drink/drank/drunk,swim/swam/swum,sing/sang/sung,begin/began/begun,break/broke/broken,speak/spoke/spoken,choose/chose/chosen,drive/drove/driven,ride/rode/ridden,fly/flew/flown,draw/drew/drawn,know/knew/known,grow/grew/grown,wake/woke/woken,forget/forgot/forgotten,fall/fell/fallen,steal/stole/stolen,wear/wore/worn,tear/tore/torn,hide/hid/hidden,bite/bit/bitten,shake/shook/shaken,throw/threw/thrown,do/did/done")]
RH = [L(x) for x in ("cat,hat,bat,mat", "dog,log,frog,fog", "sun,fun,run,bun", "bed,red,fed,led", "cake,lake,make,bake", "tree,bee,knee,free", "ring,sing,king,wing", "star,car,far,jar", "night,light,kite,bright", "rain,train,plane,chain", "book,look,cook,hook", "boat,coat,goat,float", "ball,tall,wall,call")]
VERBS = [tuple(x.split("/")) for x in L("play/plays/playing/played,eat/eats/eating/ate,run/runs/running/ran,like/likes/liking/liked,walk/walks/walking/walked,sing/sings/singing/sang,jump/jumps/jumping/jumped,write/writes/writing/wrote,watch/watches/watching/watched,study/studies/studying/studied,go/goes/going/went,fly/flies/flying/flew")]
SING = L("She,He,My brother,The dog,Riya,The teacher,My mother,Our principal,The bird,Rahul")
PLUR = L("They,We,The dogs,My friends,The students,Birds,Ravi and Meena,The boys")
POS = dict(Noun=L("table,river,teacher,happiness,garden,city,mountain,friend,music,doctor"), Verb=L("jump,write,think,swim,laugh,build,carry,explore,listen,discover"),
           Adjective=L("beautiful,tall,brave,cold,noisy,clever,gentle,shiny,sleepy,honest"), Adverb=L("quickly,slowly,loudly,carefully,happily,bravely,always,softly,quietly,never"))
CONF = """The medicine had a positive ___ on her health.|effect|affect|affects|effected
Bad weather can ___ the match.|affect|effect|effects|affection
The dog wagged ___ tail.|its|it's|its'|their
___ going to be a great day.|It's|Its|Its'|Is
I am taller ___ my brother.|than|then|that|thin
First wash your hands, ___ eat.|then|than|there|thin
___ books are on the table.|Their|There|They're|Thier
Put the box over ___.|there|their|they're|therr
___ my best friend.|You're|Your|Youre|Yore
Don't ___ your keys again.|lose|loose|loss|lost
The knot is too ___.|loose|lose|loss|lost
Please ___ me what to do.|advise|advice|advices|advisor
She gave me good ___.|advice|advise|advices|advisor
Everyone ___ Rahul came.|except|accept|expect|excepts
I ___ your invitation.|accept|except|expect|excerpt
The ___ of the school gave a speech.|principal|principle|principel|princepal
Honesty is a basic ___.|principle|principal|principles|principel
We had chocolate cake for ___.|dessert|desert|desserts|deserts
The camel lives in the ___.|desert|dessert|deserts|desart"""
PREPS = """She is good ___ mathematics.|at
He is afraid ___ spiders.|of
I am very proud ___ my team.|of
She is fond ___ music.|of
They are interested ___ science.|in
He is married ___ my cousin.|to
I depend ___ my parents.|on
She is tired ___ waiting.|of
Ram is very bad ___ drawing.|at
Please listen ___ the teacher.|to
Don't laugh ___ others.|at
This house belongs ___ my uncle.|to
The soup is full ___ vegetables.|of
He is allergic ___ peanuts.|to
She is jealous ___ her friend's success.|of
He insisted ___ paying the bill.|on
He was accused ___ stealing.|of
I look forward ___ meeting you.|to
Look ___ the beautiful rainbow.|at
Water consists ___ hydrogen and oxygen.|of
He is keen ___ cricket.|on
She is famous ___ her paintings.|for
He apologised ___ being late.|for
She is capable ___ solving hard puzzles.|of
He suffers ___ headaches.|from
They escaped ___ the burning house.|from
We must protect birds ___ hunters.|from"""
IRR_P = "{n} has already ___ ({b}) it."
def misspell(w, r):
    out = []
    for _ in range(12):
        i = r.randint(1, len(w) - 2); t = r.choice("dswv")
        s = w[:i] + w[i + 1:] if t == "d" else w[:i] + w[i] + w[i:] if t == "s" else (w[:i] + w[i + 1] + w[i] + w[i + 2:] if i + 1 < len(w) else None) if t == "w" else w[:i] + r.choice([x for x in "aeiou" if x != w[i]]) + w[i + 1:] if w[i] in "aeiou" else None
        if s and s != w: out.append(s)
    return out
def spell(B, words, r):
    res = []
    for w in words:
        for _ in range(2):
            m = misspell(w, r)
            res.append(mk("English", B, "Which word is spelled correctly?", w, m, f"The correct spelling is '{w}'.", r))
    return res

def eng_a(r):
    S, B = "English", "a"; o = []
    o += pq(S, B, sym(P("big=small;tall=short;hot=cold;up=down;in=out;day=night;happy=sad;fast=slow;old=new;open=shut;hard=soft;full=empty;clean=dirty;push=pull;come=go;yes=no;black=white;good=bad;high=low")), "What is the opposite of '{k}'?", None, "The opposite of '{k}' is '{v}'.", r)
    o += pq(S, B, IRR[:20] and [(a, b) for a, b, c in IRR[:20]], "What is the past tense of '{k}'?", None, "The past tense of '{k}' is '{v}'.", r)
    for k, v in P("child=children;man=men;woman=women;foot=feet;tooth=teeth;mouse=mice;goose=geese;box=boxes;bus=buses;baby=babies;leaf=leaves;knife=knives;city=cities;dish=dishes;watch=watches;potato=potatoes;wolf=wolves;story=stories;day=days;toy=toys;boy=boys;key=keys;book=books;cat=cats;fox=foxes;lady=ladies;shelf=shelves;church=churches"):
        o.append(mk(S, B, f"What is the plural of '{k}'?", v, [k + "s", k + "es", k[:-1] + "ies", k + "en", k[:-1] + "ves"], f"The plural of '{k}' is '{v}'.", r))
    for w in L("apple,egg,umbrella,hour,orange,elephant,owl,ant,ink,onion,uncle,island,eye,aeroplane,artist,engine"):
        o.append(mk(S, B, f"Fill in the blank with 'a' or 'an':  ___ {w}", "an", ["a", "both a and an", "neither a nor an"], f"Use 'an' before a vowel sound: an {w}.", r))
    for w in L("book,dog,ball,university,unicorn,cat,table,pencil,European,house,uniform,horse,chair,zebra,tree"):
        o.append(mk(S, B, f"Fill in the blank with 'a' or 'an':  ___ {w}", "a", ["an", "both a and an", "neither a nor an"], f"Use 'a' before a consonant sound: a {w}.", r))
    for s, v in P("I=am;he=is;she=is;it=is;you=are;we=are;they=are;the cat=is;my parents=are;the boys=are;Riya=is;the children=are;this book=is;these books=are"):
        for adj in L("happy,tired,ready,late,hungry,kind"):
            o.append(mk(S, B, f"{cap1(s)} ___ {adj} today.", v, [x for x in ("am", "is", "are", "be", "been") if x != v], f"'{cap1(s)}' goes with '{v}'. (I → am; he/she/it/one thing → is; you/we/they/many → are.)", r))
    for g in RH:
        for w in g:
            for x in g:
                if x != w: o.append(mk(S, B, f"Which word rhymes with '{w}'?", x, [y for h in RH if h is not g for y in h if y[-2:] != x[-2:]][::7][:6] if False else r.sample([y for h in RH if h is not g for y in h], 5), f"'{w}' and '{x}' end with the same sound.", r))
    return o


def eng_b(r):
    S, B = "English", "b"; o = []
    o += pq(S, B, sym(P("happy=joyful;big=large;small=tiny;fast=quick;smart=clever;begin=start;end=finish;shut=close;rich=wealthy;angry=furious;sad=unhappy;brave=courageous;kind=gentle;silent=quiet;buy=purchase;look=glance;tired=weary;pretty=beautiful;simple=easy;strange=odd;calm=peaceful;honest=truthful;error=mistake;trip=journey")), "Which word means the same as '{k}'?", None, "'{k}' and '{v}' have similar meanings.", r)
    o += pq(S, B, sym(P("rich=poor;day=night;love=hate;win=lose;accept=reject;arrive=depart;ancient=modern;increase=decrease;always=never;polite=rude;generous=selfish;tight=loose;thick=thin;early=late;strong=weak;rough=smooth;wet=dry;dark=bright;hot=cold")), "What is the opposite of '{k}'?", None, "The opposite of '{k}' is '{v}'.", r)
    o += pq(S, B, P("sheep=flock;birds=flock;cows=herd;elephants=herd;wolves=pack;fish=school;lions=pride;bees=swarm;flowers=bouquet;grapes=bunch;cards=deck;sailors=crew;singers=choir;players=team;puppies=litter;ants=colony;geese=gaggle;stars=cluster"),
            "What do we call a group of {k}?", "'{v}' is the collective noun for which group?", "A group of {k} is called a {v}.", r)
    for s in SING + PLUR:
        pl = s in PLUR
        for v in VERBS:
            a = v[0] if pl else v[1]
            o.append(mk(S, B, f"{s} ___ every morning.", a, [x for x in v if x != a], f"'{s}' is {'plural' if pl else 'singular'}, so the verb is '{a}'.", r))
    for n, ps in POS.items():
        for w in ps:
            o.append(mk(S, B, f"What part of speech is '{w}'?", n, [x for x in ("Noun", "Verb", "Adjective", "Adverb", "Pronoun", "Preposition") if x != n], f"'{w}' is {a_an(n)} {n.lower()}: " + {"Noun": "a naming word.", "Verb": "an action word.", "Adjective": "a word that describes a noun.", "Adverb": "a word that tells how, when or where something happens."}[n], r))
    return o


def eng_c(r):
    S, B = "English", "c"; o = []
    o += pq(S, B, P("a piece of cake=something very easy;break the ice=start a conversation in an awkward situation;hit the sack=go to bed;spill the beans=reveal a secret;under the weather=feeling slightly ill;once in a blue moon=very rarely;cost an arm and a leg=be very expensive;burn the midnight oil=work late into the night;bite the bullet=face a difficult situation bravely;beat around the bush=avoid the main point;cry over spilt milk=worry about something that cannot be changed;a blessing in disguise=something good that seemed bad at first;kill two birds with one stone=solve two problems at once;at the drop of a hat=immediately;call it a day=stop working;back to square one=start again from the beginning;on cloud nine=extremely happy;raining cats and dogs=raining very heavily;speak of the devil=the person we were talking about arrives;pull someone's leg=tease or joke;hold your horses=wait and be patient;the last straw=the final problem that makes one lose patience"),
            "What does the idiom '{k}' mean?", "Which idiom means '{v}'?", "'{k}' means {v}.", r)
    o += pq(S, B, P("abundant=plentiful;reluctant=unwilling;obsolete=no longer in use;fragile=easily broken;meticulous=very careful about details;vivid=bright and clear;transparent=clear enough to see through;rapid=very quick;diligent=hard-working;humble=not proud;generous=willing to give;fatigue=extreme tiredness;scarce=hard to find;inevitable=certain to happen;hostile=unfriendly;optimistic=hopeful about the future;vacant=empty;conceal=hide;triumph=great victory;ferocious=fierce;peculiar=strange;feeble=weak;novice=beginner"),
            "What does '{k}' mean?", "Which word means '{v}'?", "'{k}' means {v}.", r)
    for line in PREPS.split("\n"):
        s, a = line.split("|"); o.append(mk(S, B, f"Choose the correct word:  {s}", a, [x for x in ("at", "on", "of", "for", "with", "to", "by") if x != a], f"'{a}' is the correct preposition here — it is part of a fixed phrase.", r))
    for line in CONF.split("\n"):
        s, a, *w = line.split("|"); o.append(mk(S, B, f"Choose the correct word:  {s}", a, w, f"'{a}' fits this sentence best.", r))
    o += spell(B, L("necessary,separate,definitely,occasion,environment,government,beautiful,calendar,difficult,embarrass,friend,guarantee,height,knowledge,library,neighbour,receive,restaurant,schedule,tomorrow,vegetable,temperature"), r)
    for n in NAMES[:6]:
        for b, p, pp in IRR:
            if r.random() < .5:
                o.append(mk(S, B, f"{n} has already ___ it. ({b})", pp, [p, b, b + "ed", b + "ing"], f"After 'has/have' we use the past participle of '{b}': '{pp}'.", r))
            else:
                o.append(mk(S, B, f"Last year, {n} ___ it. ({b})", p, [pp, b, b + "ed", b + "ing"], f"'Last year' signals the simple past of '{b}': '{p}'.", r))
    return o


def eng_d(r):
    S, B = "English", "d"; o = []
    o += pq(S, B, sym(P("meticulous=careful;benevolent=kind;ephemeral=short-lived;ubiquitous=found everywhere;candid=frank;tenacious=persistent;eloquent=fluent;lucid=clear;frugal=thrifty;arduous=difficult;prudent=wise;zealous=enthusiastic;affluent=wealthy;taciturn=quiet;gregarious=sociable;lethargic=sluggish;verbose=wordy;pragmatic=practical;serene=calm")), "Which word is closest in meaning to '{k}'?", None, "'{k}' and '{v}' have similar meanings.", r)
    o += pq(S, B, sym(P("benevolent=malevolent;scarce=abundant;ancient=modern;expand=contract;optimistic=pessimistic;transparent=opaque;generous=stingy;humble=arrogant;rigid=flexible;temporary=permanent;victory=defeat;mature=immature;vague=precise;ascend=descend;inhale=exhale;hostile=friendly;superior=inferior;synthetic=natural;voluntary=compulsory;exterior=interior")), "What is the antonym of '{k}'?", None, "The antonym of '{k}' is '{v}'.", r)
    o += pq(S, B, P("The wind whispered through the trees.=Personification;Her smile was as bright as the sun.=Simile;Time is a thief.=Metaphor;I have told you a million times to be quiet.=Hyperbole;Peter Piper picked a peck of pickled peppers.=Alliteration;The bees buzzed around the flowers.=Onomatopoeia;The silence was deafening.=Oxymoron;He is as brave as a lion.=Simile;The classroom was a zoo.=Metaphor;The sun smiled down on us.=Personification;I'm so hungry I could eat a horse.=Hyperbole;Sally sells sea shells by the sea shore.=Alliteration;The thunder boomed and the rain splashed down.=Onomatopoeia;It was a bittersweet goodbye.=Oxymoron;Life is a journey.=Metaphor;The leaves danced in the breeze.=Personification;She is as quiet as a mouse.=Simile;This bag weighs a ton.=Hyperbole"),
            "Identify the figure of speech:  \"{k}\"", None, lambda k, v: f"This is {a_an(v)} {v.lower()}: {CD[v]}.", r)
    o += pq(S, B, P("a person who loves books=bibliophile;a person who walks in sleep=somnambulist;fear of closed spaces=claustrophobia;a government by the people=democracy;one who knows everything=omniscient;a person who eats no meat=vegetarian;the study of birds=ornithology;a person who can speak two languages=bilingual;that which cannot be read=illegible;one who is present everywhere=omnipresent;a speech delivered without preparation=extempore;the killing of a king=regicide;a medicine that cures all diseases=panacea;a person who hates mankind=misanthrope;fear of heights=acrophobia"),
            "Choose one word for:  {k}", "Which phrase is best described by the word '{v}'?", "'{v}' means {k}.", r)
    o += pq(S, B, P("Hamlet=William Shakespeare;Romeo and Juliet=William Shakespeare;Macbeth=William Shakespeare;Pride and Prejudice=Jane Austen;Oliver Twist=Charles Dickens;A Tale of Two Cities=Charles Dickens;Gitanjali=Rabindranath Tagore;Malgudi Days=R. K. Narayan;The Jungle Book=Rudyard Kipling;Alice's Adventures in Wonderland=Lewis Carroll;Animal Farm=George Orwell;1984=George Orwell;The Old Man and the Sea=Ernest Hemingway;Treasure Island=Robert Louis Stevenson;Gulliver's Travels=Jonathan Swift;Paradise Lost=John Milton;Wings of Fire=A. P. J. Abdul Kalam;Ramayana=Valmiki;The Adventures of Tom Sawyer=Mark Twain;Little Women=Louisa May Alcott"),
            "Who wrote '{k}'?", "Which of these was written by {v}?", "'{k}' was written by {v}.", r)
    o += spell(B, L("accommodate,acquaintance,bureaucracy,conscientious,entrepreneur,fluorescent,hierarchy,miscellaneous,occurrence,questionnaire,surveillance,rhetoric,perseverance,pneumonia,mischievous,conscience,pronunciation,privilege,rhythm,sincerely,discipline,committee,beginning,independent"), r)
    return o


# ==================================================================== build
SPEC = {
    "Math": {"a": (None, [ma_add, ma_sub, ma_mul, ma_miss, ma_dbl, ma_cmp, ma_word, ma_place, ma_even], 250),
             "b": (None, [mb_frac, mb_perim, mb_area, mb_mul, mb_div, mb_pct, mb_avg, mb_unit, mb_money], 250),
             "c": (None, [mc_lin, mc_poly, mc_disc, mc_sq, mc_si, mc_ratio, mc_tri, mc_hcf, mc_pyth, mc_tri_ang], 250),
             "d": (lambda r: pq("Math", "d", TRIG, "What is the value of {k}?", "Which angle has the value {v}?", "From the standard trigonometric table: {k} = {v}.", r),
                   [md_quad, md_log, md_ap, md_comb, md_slope, md_dist, md_gp, md_dice, md_ci, md_sim, md_diag, md_cyl, md_med], 250)},
    "Science": {"a": (sci_a, [], 250), "b": (sci_b, [], 250), "c": (sci_c, [sc_speed, sc_dens, sc_ohm, sc_force, sc_work, sc_press], 250),
                "d": (sci_d, [sd_ke, sd_mom, sd_pe, sd_res, sd_wave, sd_ph, sd_mole, sd_heat, sd_per, sd_half, sd_atom], 250)},
    "English": {"a": (eng_a, [], 330), "b": (eng_b, [], 340), "c": (eng_c, [], 250), "d": (eng_d, [], 250)},
    "Reasoning": {"a": (lambda r: pq("Reasoning", "a", P("triangle=3;square=4;pentagon=5;hexagon=6;octagon=8;rectangle=4"), "How many sides does a {k} have?", None, "A {k} has {v} sides.", r),
                         [ra_odd, ra_series, ra_alpha, ra_day], 250),
                  "b": (None, [rb_series, rb_alpha, rb_code, rb_dayn, rb_order, rb_analogy], 250),
                  "c": (None, [rc_series, rc_pow, rc_shift, rc_clock, rc_cal, rc_dir, rc_rank, rc_nana], 250),
                  "d": (None, [rd_alt, rd_fib, rd_prime, rd_prod, rd_work, rd_arr, rd_prob, rd_speed, rd_profit, rd_count], 250)},
}


def build():
    """Return a deterministic list of question dicts (same order on every start)."""
    out = []
    for S, bands in SPEC.items():
        for B, (facts, gens, cap) in bands.items():
            r = random.Random(f"olympiad-{S}-{B}")
            seen, res = set(), []

            def add(q):
                if q and (q["q"], q["opts"][q["ans"]]) not in seen and len(set(q["opts"])) == 4:
                    seen.add((q["q"], q["opts"][q["ans"]])); res.append(q)

            F = [q for q in (facts(r) if facts else []) if q]
            r.shuffle(F)
            limit = int(cap * .6) if gens and F else cap
            for q in F:
                if len(res) >= limit: break
                add(q)
            tries = 0
            while gens and len(res) < cap and tries < cap * 80:
                add(gens[tries % len(gens)](r)); tries += 1
            out += res
    return out


if __name__ == "__main__":
    qs = build(); c = Counter((q["subject"], q["band"]) for q in qs)
    for s in SPEC: print(s, sum(v for (a, b), v in c.items() if a == s), {b: c[(s, b)] for b in "abcd"})
