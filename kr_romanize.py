#!/usr/bin/env python3
r"""
kr_romanize.py — Revised Romanization (RR) of Korean for admin names.
Pure Python, no dependencies. Used by build_crosswalk.py for the *_name_en columns.

Method (documented in the methods note):
- Hangul syllables decomposed via Unicode arithmetic; RR transcription with
  the standard sound-change rules between syllables (nasalization of stops
  before nasals, ㄹ-assimilation incl. 종로->Jongno, ㄴ/ㄹ->ll as in 신라->
  Silla, liaison before vowels, ㅎ-aspiration).
- Administrative suffixes (도/시/군/구/읍/면/동/리/가) are split with a
  hyphen and sound changes are NOT applied across the hyphen, per the
  official RR rule for administrative units (삼죽면 -> Samjuk-myeon).
- Non-Hangul characters (digits, '·') pass through and block assimilation.
- Sido English names come from a curated 16-entry table (official short
  forms: Seoul, Busan, ... Jeonnam-Gwangju for the 2026 merged city).
- v2 (2026-08-19): administrative dongs built on street-block
  ("N-ga") legal dongs are written in the official admin-dong form with
  separators: 금호1가동 -> 'Geumho 1-ga-dong' (v1: 'Geumho1ga-dong');
  double-numbered forms: 성수1가2동 -> 'Seongsu 1-ga 2-dong'. Exactly 13
  of 3,558 names carry this pattern (2026-07-01 vintage). NOTE: consumer
  basemaps usually label the LEGAL dongs ('Geumho-dong 1-ga') — a different
  unit family; this table is administrative dongs, so the admin-dong form
  is used.
- Scope: romanize() is for administrative-unit NAMES (…구, …시, …동, …면).
  It splits the trailing unit suffix, so a bare place name like '대구' comes
  out as 'Dae-gu'; province/metro names are taken from SIDO_EN instead.
"""
import re

INITIALS = ['g','kk','n','d','tt','r','m','b','pp','s','ss','','j','jj','ch','k','t','p','h']
MEDIALS  = ['a','ae','ya','yae','eo','e','yeo','ye','o','wa','wae','oe','yo',
            'u','wo','we','wi','yu','eu','ui','i']
# final consonant index -> (coda letter(s) when NOT followed by vowel, onset form on liaison)
FINALS = [None,
    ('k','g'),('k','kk'),('k','gs'),('n','n'),('n','nj'),('n','nh'),('t','d'),
    ('l','r'),('k','lg'),('m','lm'),('l','lb'),('l','ls'),('l','lt'),('p','lp'),
    ('l','lh'),('m','m'),('p','b'),('p','bs'),('t','s'),('t','ss'),('ng','ng'),
    ('t','j'),('t','ch'),('k','k'),('t','t'),('p','p'),('t','h')]

ADMIN_SUFFIX = {'도':'do','시':'si','군':'gun','구':'gu','읍':'eup','면':'myeon',
                '동':'dong','리':'ri','가':'ga'}

SIDO_EN = {  # KOSTAT 2-digit -> official short English name (2026-07 state)
 '11':'Seoul','12':'Jeonnam-Gwangju','21':'Busan','22':'Daegu','23':'Incheon',
 '25':'Daejeon','26':'Ulsan','29':'Sejong','31':'Gyeonggi-do','32':'Gangwon-do',
 '33':'Chungcheongbuk-do','34':'Chungcheongnam-do','35':'Jeonbuk-do',
 '37':'Gyeongsangbuk-do','38':'Gyeongsangnam-do','39':'Jeju-do'}

def _decomp(ch):
    o = ord(ch) - 0xAC00
    if 0 <= o < 11172:
        return o // 588, (o % 588) // 28, o % 28
    return None

def _roman_syllables(sylls):
    """RR-transcribe a list of decomposed syllables with sound-change rules."""
    out = []
    n = len(sylls)
    for i, (ini, med, fin) in enumerate(sylls):
        onset = INITIALS[ini]
        # previous syllable's coda may have modified this onset (handled below
        # via lookahead from the coda side), so onsets are adjusted when we
        # emit the previous coda. Here handle onset after emitted coda:
        out.append(('onset', onset, ini))
        out.append(('vowel', MEDIALS[med], med))
        if fin:
            nxt = sylls[i+1][0] if i + 1 < n else None   # next onset index
            coda, liaison = FINALS[fin]
            out.append(('coda', coda, fin, liaison, nxt))
    # resolve interactions
    res = []
    i = 0
    toks = out
    while i < len(toks):
        t = toks[i]
        if t[0] == 'coda':
            _, coda, fin, liaison, nxt = t
            if nxt is None:                      # word-final
                res.append(coda)
            else:
                nxt_onset = INITIALS[nxt]
                if nxt == 11:                    # next is ㅇ (vowel onset): liaison
                    res.append('' if liaison == 'ng' and False else _liaise(liaison))
                elif nxt == 5:                   # next is ㄹ
                    if coda in ('n',):           # ㄴ+ㄹ -> ll
                        res.append('l'); _patch_next_onset(toks, i, 'l')
                    elif coda == 'l':            # ㄹ+ㄹ -> ll
                        res.append('l'); _patch_next_onset(toks, i, 'l')
                    elif coda in ('k','t','p'):  # stop+ㄹ -> nasal + n
                        res.append({'k':'ng','t':'n','p':'m'}[coda])
                        _patch_next_onset(toks, i, 'n')
                    elif coda in ('m','ng'):     # ㅁ/ㅇ + ㄹ -> n  (종로 Jongno)
                        res.append(coda); _patch_next_onset(toks, i, 'n')
                    else:
                        res.append(coda)
                elif nxt in (2, 6):              # next is ㄴ or ㅁ (nasal)
                    if coda in ('k','t','p'):    # nasalization
                        res.append({'k':'ng','t':'n','p':'m'}[coda])
                    elif coda == 'l' and nxt == 2:  # ㄹ+ㄴ -> ll (실내 sillae)
                        res.append('l'); _patch_next_onset(toks, i, 'l')
                    else:
                        res.append(coda)
                elif nxt == 18:                  # next is ㅎ: aspiration
                    if coda in ('k','t','p'):
                        res.append('')           # merge into aspirate
                        _patch_next_onset(toks, i, {'k':'k','t':'t','p':'p'}[coda])
                    else:
                        res.append(coda)
                elif fin == 27:                  # coda ㅎ + stop onset -> aspirate
                    if nxt_onset in ('g','d','j'):
                        res.append('')
                        _patch_next_onset(toks, i, {'g':'k','d':'t','j':'ch'}[nxt_onset])
                    else:
                        res.append('')           # ㅎ before other: usually silent-ish; keep simple
                else:
                    res.append(coda)
        elif t[0] == 'onset':
            res.append(t[1])
        else:
            res.append(t[1])
        i += 1
    return ''.join(res)

def _liaise(liaison):
    # compound codas split on liaison: first part stays as coda letter, second
    # becomes onset; encode combined (e.g. 'lg' -> 'lg'); simple codas: onset form.
    m = {'g':'g','kk':'kk','n':'n','d':'d','r':'r','m':'m','b':'b','s':'s',
         'ss':'ss','ng':'ng','j':'j','ch':'ch','k':'k','t':'t','p':'p','h':'h',
         'gs':'gs','nj':'nj','nh':'nh','lg':'lg','lm':'lm','lb':'lb','ls':'ls',
         'lt':'lt','lp':'lp','lh':'l'}
    return m.get(liaison, liaison)

def _patch_next_onset(toks, coda_idx, new_onset):
    for j in range(coda_idx + 1, len(toks)):
        if toks[j][0] == 'onset':
            toks[j] = ('onset', new_onset, toks[j][2])
            return

def _roman_run(text):
    """Romanize one run of pure Hangul."""
    sylls = [_decomp(c) for c in text]
    return _roman_syllables(sylls)

GA_DONG = re.compile(r'^([가-힣]+?)([0-9][0-9·]*)가([0-9]*)동$')

def romanize(name):
    """Romanize a Korean admin-unit name (one token, e.g. '종로구', '송림3·5동')."""
    if not name:
        return ''
    # v2: street-block administrative dongs (…N가동 / …N가M동) — official
    # admin-dong form with separators; see module docstring.
    m = GA_DONG.match(name)
    if m:
        stem, ganum, dongnum = m.groups()
        base = _roman_run(stem)
        base = base[:1].upper() + base[1:]
        if dongnum:
            return f"{base} {ganum}-ga {dongnum}-dong"
        return f"{base} {ganum}-ga-dong"
    # split admin suffix (last char) with hyphen, no assimilation across it
    suffix = ''
    stem = name
    if len(name) >= 2 and name[-1] in ADMIN_SUFFIX:
        stem, suffix = name[:-1], ADMIN_SUFFIX[name[-1]]
    # tokenize stem into hangul / non-hangul runs (digits, '·' pass through)
    parts, cur, is_h = [], '', None
    for ch in stem:
        h = _decomp(ch) is not None
        if is_h is None or h == is_h:
            cur += ch
        else:
            parts.append((is_h, cur)); cur = ch
        is_h = h
    if cur:
        parts.append((is_h, cur))
    rom = ''.join(_roman_run(p) if h else p for h, p in parts)
    rom = rom[:1].upper() + rom[1:]
    return f"{rom}-{suffix}" if suffix else rom

def romanize_path(full_name):
    """'서울특별시 동대문구 용두동' -> 'Yongdu-dong' style per-token; returns list."""
    return [romanize(tok) for tok in full_name.split()]

if __name__ == '__main__':
    tests = {
        '종로구': 'Jongno-gu', '강남구': 'Gangnam-gu', '수원시': 'Suwon-si',
        '사직동': 'Sajik-dong', '신설동': 'Sinseol-dong', '청량리동': 'Cheongnyangni-dong',
        '독립문': 'Dongnimmun', '신라': 'Silla', '울산': 'Ulsan', '중구': 'Jung-gu',
        '제물포구': 'Jemulpo-gu', '해운대구': 'Haeundae-gu', '설악면': 'Seorak-myeon',
        '금호1가동': 'Geumho 1-ga-dong', '성수1가2동': 'Seongsu 1-ga 2-dong',
        '종로1·2·3·4가동': 'Jongno 1·2·3·4-ga-dong',
    }
    for k, want in tests.items():
        got = romanize(k)
        print(f"{'OK ' if got == want else 'DIFF'} {k}: {got}" + ('' if got == want else f"  (expected {want})"))
