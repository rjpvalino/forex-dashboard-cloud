import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ForexFactory publishes a machine-readable JSON feed via their CDN.
# Unlike the HTML calendar page (which Cloudflare blocks from datacenter IPs),
# these CDN endpoints are accessible from server environments.
CDN_URLS = {
    'this': 'https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json',
    'next': 'https://cdn-nfs.faireconomy.media/ff_calendar_nextweek.json',
}

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json, */*',
    'Referer': 'https://www.forexfactory.com/',
}

HIGH_IMPACT = {'High', 'Holiday'}


class ForexFactoryClient:

    def get_calendar_events(self):
        events = []
        for week, url in CDN_URLS.items():
            try:
                resp = requests.get(url, headers=HEADERS, timeout=20)
                resp.raise_for_status()
                raw = resp.json()
                events.extend(self._parse(raw))
                logger.info(f'ForexFactory JSON: {len(raw)} events fetched ({week} week)')
            except Exception as e:
                logger.error(f'ForexFactory fetch failed ({week} week): {e}')
        return events

    def _parse(self, raw_events):
        events = []
        for e in raw_events:
            impact = e.get('impact', '')
            if impact not in HIGH_IMPACT and 'speak' not in impact.lower():
                continue

            normalized_impact = impact
            if 'speak' in impact.lower():
                normalized_impact = 'Speech'

            date_str = self._parse_date(e.get('date', ''))

            events.append({
                'date':     date_str,
                'time':     e.get('time', ''),
                'currency': e.get('country', ''),
                'event':    e.get('title', ''),
                'impact':   normalized_impact,
                'actual':   e.get('actual', ''),
                'forecast': e.get('forecast', ''),
                'previous': e.get('previous', ''),
            })
        return events

    def _parse_date(self, raw):
        for fmt in ('%m-%d-%Y', '%Y-%m-%d', '%b %d %Y', '%B %d %Y'):
            try:
                return datetime.strptime(raw.strip(), fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        return raw
