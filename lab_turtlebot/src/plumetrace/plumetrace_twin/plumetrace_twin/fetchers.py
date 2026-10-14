"""Open-data fetchers for the reach: river flow and water quality from the Gewaesserkundlicher Dienst
Bayern (GKD, www.gkd.bayern.de, CC BY 4.0), and overflow events.

Each fetcher runs in fixture mode (synthetic CSVs in data/fixtures/) until its fields in
config/data_sources.yaml are filled; then it reads the live GKD pages. All return lists of plain dicts:
  flow:          {time, q_m3s}                              15-min values, newest first
  water quality: {time, determinand, value, unit, below_loq} (determinand NH3-N or DO), grab samples
  overflow:      {site_id, start, stop, status}
GKD has no JSON API: the value tables of the station pages are parsed. Times are as GKD prints them
(station local standard time, taken to be CET = UTC+1; not confirmed on the site). Bavaria has no open
overflow (EDM) feed, so overflow events always come from the fixture.
"""
import csv
import html
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import yaml

from .reach import repo_dir

CET = timezone(timedelta(hours=1))


def load_sources(path=None):
    with open(path or os.path.join(repo_dir(), 'config', 'data_sources.yaml')) as f:
        return yaml.safe_load(f)


def _fixture(name):
    with open(os.path.join(repo_dir(), 'data', 'fixtures', name)) as f:
        return list(csv.DictReader(f))


def _get_text(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (plumetrace)'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'ignore')


def parse_table(page):
    """Rows of the first value table of a GKD page: a list of lists of cell texts, header first."""
    rows = [[html.unescape(re.sub(r'<[^>]+>', '', td)).strip()
             for td in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, flags=re.S)]
            for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', page, flags=re.S)]
    return [r for r in rows if r]


def parse_time(text):
    """'10.10.2026 18:15' or '04.12.2024' (GKD, CET) -> ISO 8601 with offset."""
    text = text.replace('Uhr', '').strip()
    fmt = '%d.%m.%Y %H:%M' if ':' in text else '%d.%m.%Y'
    return datetime.strptime(text, fmt).replace(tzinfo=CET).isoformat()


def parse_value(text):
    """'5.69', '6,15', '< 0.02' or '--' -> (value or None, below limit of quantification)."""
    t = text.replace(',', '.').strip()
    below = t.startswith('<')
    try:
        return float(t.lstrip('<').strip()), below
    except ValueError:
        return None, False


class Fetcher:
    key, required = '', ()

    def __init__(self, sources=None):
        self.cfg = (load_sources() if sources is None else sources).get(self.key) or {}

    @property
    def live(self):
        return bool(self.required) and all(self.cfg.get(k) for k in self.required)

    @property
    def mode(self):
        return 'live' if self.live else 'fixture'

    def fetch(self, **kw):
        return self.fetch_live(**kw) if self.live else self.fetch_fixture(**kw)


class GKDFlow(Fetcher):
    """15-min discharge of a GKD gauge. `days` back from today, at most what the site keeps online."""
    key, required = 'gkd_discharge', ('station_path',)

    def fetch_fixture(self, **kw):
        return [dict(time=r['time'], q_m3s=float(r['q_m3s'])) for r in _fixture('ea_flow_15min.csv')]

    def parse(self, page):
        out = []
        for r in parse_table(page)[1:]:
            v, _ = parse_value(r[1]) if len(r) > 1 else (None, False)
            if v is not None:
                out.append(dict(time=parse_time(r[0]), q_m3s=v))
        return out

    def fetch_live(self, days=7):
        end = datetime.now(CET).date()
        q = urllib.parse.urlencode({'beginn': (end - timedelta(days=days)).strftime('%d.%m.%Y'),
                                    'ende': end.strftime('%d.%m.%Y')})
        return self.parse(_get_text(f"{self.cfg['base_url']}/rivers/discharge/{self.cfg['station_path']}/current-values/table?{q}"))


class GKDWaterQuality(Fetcher):
    """Ammonium-N and dissolved oxygen grab samples of a GKD chemistry station."""
    key, required = 'gkd_chemistry', ('station_path',)
    PARAMS = {'NH3-N': '1407', 'DO': '1018'}  # GKD parameter numbers: Ammonium-N; Sauerstoff, geloest

    def fetch_fixture(self, **kw):
        return [dict(time=r['time'], determinand=r['determinand'], value=float(r['value']), unit=r['unit'], below_loq=False)
                for r in _fixture('ea_water_quality.csv')]

    def parse(self, page):
        out = []
        for r in parse_table(page)[1:]:
            for det, cell in zip(('NH3-N', 'DO'), r[1:3]):
                v, below = parse_value(cell)
                if v is not None:
                    out.append(dict(time=parse_time(r[0]), determinand=det, value=v, unit='mg/L', below_loq=below))
        return out

    def fetch_live(self, years=3):
        end = datetime.now(CET).date()
        q = urllib.parse.urlencode({'zr': 'gesamt', 'mpnr1': self.PARAMS['NH3-N'], 'mpnr2': self.PARAMS['DO'],
                                    'beginn': end.replace(year=end.year - years).strftime('%d.%m.%Y'),
                                    'ende': end.strftime('%d.%m.%Y')})
        return self.parse(_get_text(f"{self.cfg['base_url']}/rivers/chemistry/{self.cfg['station_path']}/total-period/table?{q}"))

    def baseline(self, **kw):
        """Median and 90th percentile per determinand (the scenario background). Values below the
        limit of quantification count at the limit."""
        import numpy as np
        rows = self.fetch(**kw)
        out = {}
        for d in ('NH3-N', 'DO'):
            v = np.array([r['value'] for r in rows if r['determinand'] == d])
            if len(v):
                out[d] = dict(median=float(np.median(v)), p90=float(np.percentile(v, 90)), n=int(len(v)))
        return out


class OverflowEvents(Fetcher):
    """Overflow start/stop events. No open feed exists for Bavaria: always the synthetic fixture."""
    key, required = 'overflow_events', ()

    def fetch_fixture(self, **kw):
        return [dict(site_id=r['site_id'], start=r['start'], stop=r['stop'] or None, status=r['status'])
                for r in _fixture('thames_edm_events.csv')]


def all_fetchers(sources=None):
    s = load_sources() if sources is None else sources
    return dict(flow=GKDFlow(s), water_quality=GKDWaterQuality(s), edm=OverflowEvents(s))
