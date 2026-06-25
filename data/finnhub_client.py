import requests
from datetime import date, timedelta, datetime
import logging

logger = logging.getLogger(__name__)

# 2-letter ISO country code → 3-letter forex currency
COUNTRY_TO_CURRENCY = {
    'US': 'USD',
    'EU': 'EUR', 'DE': 'EUR', 'FR': 'EUR', 'IT': 'EUR', 'ES': 'EUR',
    'GB': 'GBP',
    'JP': 'JPY',
    'AU': 'AUD',
    'CA': 'CAD',
    'CH': 'CHF',
    'NZ': 'NZD',
}


class FinnhubCalendarClient:
    BASE_URL = 'https://finnhub.io/api/v1/calendar/economic'
    HIGH_IMPACT = {'high', 'medium'}

    def __init__(self, api_key):
        self.api_key = api_key

    def get_calendar_events(self):
        today = date.today()
        try:
            resp = requests.get(
                self.BASE_URL,
                params={
                    'from':  today.strftime('%Y-%m-%d'),
                    'to':    (today + timedelta(days=14)).strftime('%Y-%m-%d'),
                    'token': self.api_key,
                },
                timeout=20,
            )
            resp.raise_for_status()
            raw = resp.json().get('economicCalendar', [])
            logger.info(f'Finnhub: {len(raw)} raw events fetched')
            return self._parse(raw)
        except Exception as e:
            logger.error(f'Finnhub fetch failed: {e}')
            return []

    def _parse(self, raw_events):
        events = []
        for e in raw_events:
            impact = (e.get('impact') or '').lower()
            if impact not in self.HIGH_IMPACT:
                continue

            country  = e.get('country', '')
            currency = COUNTRY_TO_CURRENCY.get(country, '')
            if not currency:
                continue

            date_str, time_str = self._parse_datetime(e.get('time', ''))
            unit = e.get('unit', '')

            events.append({
                'date':     date_str,
                'time':     time_str,
                'currency': currency,
                'event':    e.get('event', ''),
                'impact':   impact.capitalize(),  # 'High' or 'Medium'
                'actual':   self._fmt(e.get('actual'),   unit),
                'forecast': self._fmt(e.get('estimate'), unit),
                'previous': self._fmt(e.get('prev'),     unit),
            })
        return events

    @staticmethod
    def _fmt(val, unit=''):
        """Numeric value + unit → display string. None → empty string."""
        if val is None:
            return ''
        s = str(val)
        if s.endswith('.0'):
            s = s[:-2]
        return f"{s}{unit}"

    @staticmethod
    def _parse_datetime(raw):
        """Parse Finnhub datetime string into (date_str, time_str)."""
        if not raw:
            return '', ''
        try:
            cleaned = raw.strip().replace(' ', 'T').replace('Z', '+00:00')
            dt = datetime.fromisoformat(cleaned)
            date_str = dt.strftime('%Y-%m-%d')
            h = dt.hour % 12 or 12
            time_str = f"{h}:{dt.minute:02d}{'am' if dt.hour < 12 else 'pm'}"
            return date_str, time_str
        except (ValueError, TypeError):
            return (raw[:10] if len(raw) >= 10 else raw), ''
