import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

_TORZNAB_NS = 'http://torznab.com/schemas/2015/feed'


def search(base_url: str, api_key: str, query: str) -> list[dict]:
    params = urllib.parse.urlencode({'apikey': api_key, 't': 'search', 'q': query})
    url = f"{base_url.rstrip('/')}/api/v2.0/indexers/all/results/torznab?{params}"

    req = urllib.request.Request(url, headers={'User-Agent': 'MagnetFisher/1.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()

    root = ET.fromstring(data)
    channel = root.find('channel')
    if channel is None:
        return []

    def _int(val: str) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    results = []
    for item in channel.findall('item'):
        title = (item.findtext('title') or '').strip()

        try:
            size = int(item.findtext('size') or 0)
        except ValueError:
            size = 0

        attrs: dict[str, str] = {
            a.get('name', ''): a.get('value', '')
            for a in item.findall(f'{{{_TORZNAB_NS}}}attr')
            if a.get('name')
        }

        magnet = attrs.get('magneturl', '')
        if not magnet:
            enc = item.find('enclosure')
            if enc is not None:
                candidate = enc.get('url', '')
                if candidate.startswith('magnet:'):
                    magnet = candidate

        if not magnet or not title:
            continue

        results.append({
            'title':    title,
            'size':     size,
            'seeders':  _int(attrs.get('seeders', '0')),
            'leechers': _int(attrs.get('peers',   '0')),
            'indexer':  attrs.get('indexer', ''),
            'magnet':   magnet,
        })

    return results
