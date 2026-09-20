# Proponowany kontrakt API dla backendu RadioDrive

Docelowy endpoint:

`GET /wp-json/iptv/v1/radio/stations`

Przykładowa odpowiedź:

```json
{
  "version": 1,
  "updated_at": "2026-09-20T07:00:00+02:00",
  "stations": [
    {
      "id": "radio-przyklad",
      "name": "Radio Przykład",
      "subtitle": "Przemyśl • muzyka i informacje",
      "stream_url": "https://radio.example/stream.aac",
      "logo_url": "https://radio.example/logo.png",
      "category": "Lokalne",
      "enabled": true,
      "order": 10
    }
  ]
}
```

## Zasady

- tylko HTTPS w produkcji
- stabilne `id` niezależne od nazwy
- brak sekretów/API keys w aplikacji
- cache po stronie aplikacji, aby katalog startował przy słabym internecie
- ETag / `If-None-Match` albo `Last-Modified`
- timeout i fallback do ostatniego poprawnego katalogu
- pole `enabled` pozwala wycofać stację bez aktualizacji APK
- backend może później dodać `now_playing`, `next`, `epg_id`, `country`, `language`, `tags`
