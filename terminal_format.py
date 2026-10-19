"""Readable terminal formulas, with code blocks preserved."""
import html
import re

SUP = str.maketrans('0123456789+-=()', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾')
SUB = str.maketrans('0123456789+-=()', '₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎')

def math_text(text):
    # Models sometimes double-escape TeX commands in prose.
    text = re.sub(r'\\{2,}(?=[A-Za-z])', lambda m: chr(92), text)
    text = re.sub(r'\\(?:begin|end)\{(?:aligned|align\*?|equation\*?|gather\*?)\}', '', text)
    for _ in range(12):
        previous = text
        text = re.sub(r'\\(?:text|mathrm|mathbf|operatorname|ce)\s*\{([^{}]*)\}', r'\1', text)
        text = re.sub(r'\\(?:frac|dfrac|tfrac)\s*\{([^{}]*)\}\s*\{([^{}]*)\}',
                      lambda m: '(' + m[1] + ')/(' + m[2] + ')', text)
        text = re.sub(r'\\sqrt\s*\{([^{}]*)\}', r'√(\1)', text)
        if previous == text:
            break
    replacements = {'cdot':'·', 'times':'×', 'div':'÷', 'approx':'≈',
        'leq':'≤', 'geq':'≥', 'neq':'≠', 'Delta':'Δ', 'delta':'δ',
        'sigma':'σ', 'tau':'τ', 'rho':'ρ', 'pi':'π', 'mu':'μ', 'Omega':'Ω', 'omega':'ω',
        'circ':'°', 'pm':'±', 'rightarrow':'→', 'left':'', 'right':'',
        'quad':' ', 'qquad':' ', 'to':'→', 'longrightarrow':'→',
        'Rightarrow':'⇒', 'Longrightarrow':'⇒', 'implies':'⇒',
        'leftarrow':'←', 'longleftarrow':'←', 'leftrightarrow':'↔',
        'rightleftharpoons':'⇌', 'leftrightharpoons':'⇋', 'uparrow':'↑',
        'downarrow':'↓', 'ge':'≥', 'le':'≤',
        'alpha':'α','beta':'β','gamma':'γ','theta':'θ','lambda':'λ',
        'epsilon':'ε','eta':'η','phi':'φ','psi':'ψ','nu':'ν',
        'sum':'Σ','prod':'Π','infty':'∞','partial':'∂','nabla':'∇',
        'in':'∈','notin':'∉','forall':'∀','exists':'∃'}
    text = re.sub(r'\\([A-Za-z]+)', lambda m: replacements.get(m[1], m[0]), text)
    text = re.sub(r'\\[,;:! ]', ' ', text)
    text = re.sub(r'\^\s*\{?\s*°\s*\}?', '°', text)
    text = re.sub(r'\^\{([0-9+\-=()]+)\}|\^([0-9]+)',
                  lambda m: (m[1] or m[2]).translate(SUP), text)
    text = re.sub(r'_\{([0-9+\-=()]+)\}|_([0-9]+)',
                  lambda m: (m[1] or m[2]).translate(SUB), text)
    text = re.sub(r'(?<![A-Za-z0-9:])/+(rightarrow|longrightarrow|to|cdot|times)(?![A-Za-z])', lambda m: replacements[m[1]], text)
    text = text.replace(r'\[', '').replace(r'\]', '').replace(r'\(', '').replace(r'\)', '')
    text = text.replace('$$', '')
    text = re.sub(r'\\_\{([^}]+)\}|_\{([^}]+)\}', lambda m: '_' + (m[1] or m[2]), text)
    return text.replace(r'\_', '_').replace(r'\%', '%')

def prose(text):
    # Decode first: escaped tags need the same treatment as ordinary tags.
    for _ in range(2):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded
    text = re.sub(r'<sup>([^<>]*)</sup>', lambda m:m[1].translate(SUP), text, flags=re.I)
    text = re.sub(r'<sub>([^<>]*)</sub>', lambda m:m[1].translate(SUB), text, flags=re.I)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
    text = re.sub(r'</?(?:b|strong|i|em|p|span|div|math|mrow|mi|mn|mo|mtext|table|thead|tbody|tr|td|th|ul|ol|li|h[1-6])(?:\s+[^>]*)?>', '', text, flags=re.I)
    text = html.unescape(text)
    text = re.sub(r'\$\$(.*?)\$\$|\$([^$\n]+)\$', lambda m:math_text(m[1] if m[1] is not None else m[2]), text)
    text = re.sub(r'\\\((.*?)\\\)|\\\[(.*?)\\\]', lambda m:math_text(m[1] if m[1] is not None else m[2]), text)
    text = re.sub(r'\$(?![0-9])', '', math_text(text))
    text = re.sub(r'^(\s*)#{1,6}\s+', r'\1', text)
    return re.sub(r'\*\*(.+?)\*\*', r'\1', text)

class TerminalFormatter:
    def __init__(self, live=False):
        self.live = live
        self.pending = ''
        self.fence = None
        self.math_fence = False

    def line(self, line):
        fence = re.match(r'^\s*(`{3,}|~{3,})', line)
        if fence:
            mark = fence[1][0]
            if self.fence is None:
                self.fence = mark
                language = line[fence.end():].strip().lower()
                self.math_fence = language in {'math', 'latex', 'tex'}
                return '' if self.math_fence else line
            elif self.fence == mark:
                was_math = self.math_fence
                self.fence = None
                self.math_fence = False
                return '' if was_math else line
            return line
        if self.fence and not self.math_fence:
            return line
        parts = re.split(r'(`+[^`]*`+)', line)
        return ''.join(part if part.startswith('`') else prose(part) for part in parts)

    def feed(self, chunk):
        self.pending += chunk
        out = []
        while '\n' in self.pending:
            line, self.pending = self.pending.split('\n', 1)
            out.append(self.line(line) + '\n')
        if self.live and not self.fence and not re.search(r'[\\`$&<>^_*#~]', self.pending):
            boundary = self.pending.rfind(' ') + 1
            if boundary:
                out.append(self.pending[:boundary])
                self.pending = self.pending[boundary:]
        return ''.join(out)

    def finish(self):
        out = self.line(self.pending) if self.pending else ''
        self.pending = ''
        return out
